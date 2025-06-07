import discord
from .bot import bot
import logging
import asyncio
import re
from datetime import datetime, timedelta
import random
import json
import io
from typing import Optional, List, Tuple
from PIL import Image
import magic
import bleach
import time
from .config import ROLES_CONFIG, DEFAULT_STARLOCKS, DEFAULT_TRAINING_QUESTS

logger = logging.getLogger(__name__)
def extract_emojis(text):
    """Extract all emojis from text using regex"""
    emoji_pattern = re.compile(
        "[\U0001F600-\U0001F64F]|"  # emoticons
        "[\U0001F300-\U0001F5FF]|"  # symbols & pictographs
        "[\U0001F680-\U0001F6FF]|"  # transport & map symbols
        "[\U0001F1E0-\U0001F1FF]|"  # flags (iOS)
        "[\U00002702-\U000027B0]|"
        "[\U000024C2-\U0001F251]|"
        "[\U0001f926-\U0001f937]|"
        "[\U00010000-\U0010ffff]|"
        "[\u200d]|"
        "[\u2640-\u2642]|"
        "[\u2600-\u2B55]|"
        "[\u23cf]|"
        "[\u23e9]|"
        "[\u231a]|"
        "[\ufe0f]|"
        "[\u3030]", 
        flags=re.UNICODE
    )
    return emoji_pattern.findall(text)

def find_contiguous_emoji_chains(text):
    """Return lists of emojis that appear consecutively"""
    emoji_pattern = re.compile("[\U0001F600-\U0001F64F]|[\U0001F300-\U0001F5FF]|[\U0001F680-\U0001F6FF]|[\U0001F1E0-\U0001F1FF]|[\U00002702-\U000027B0]|[\U000024C2-\U0001F251]|[\U0001f926-\U0001f937]|[\U00010000-\U0010ffff]|[\u200d]|[\u2640-\u2642]|[\u2600-\u2B55]|[\u23cf]|[\u23e9]|[\u231a]|[\ufe0f]|[\u3030]", flags=re.UNICODE)
    chains=[]
    current=[]
    last_end=None
    for m in emoji_pattern.finditer(text):
        if last_end is not None and m.start()==last_end:
            current.append(m.group())
        else:
            if len(current)>=2:
                chains.append(current)
            current=[m.group()]
        last_end=m.end()
    if len(current)>=2:
        chains.append(current)
    return chains

async def safe_add_roles(member, *roles):
    """Add roles while checking hierarchy and handling rate limits"""
    assignable = []
    for role in roles:
        if member.guild.me.top_role <= role:
            logger.warning(
                f"Cannot assign role {role.name} to {member}: role higher than bot's top role"
            )
        else:
            assignable.append(role)

    if not assignable:
        return

    try:
        await member.add_roles(*assignable)
    except discord.Forbidden:
        logger.debug(
            f"Missing permissions to add roles {', '.join(r.name for r in assignable)} to {member}"
        )
    except discord.HTTPException as e:
        if getattr(e, "status", None) == 429:
            await asyncio.sleep(getattr(e, "retry_after", 5))
            await safe_add_roles(member, *assignable)
        else:
            raise

async def safe_edit_message(message, **kwargs):
    """Edit a message handling rate limits"""
    while True:
        try:
            return await message.edit(**kwargs)
        except discord.HTTPException as e:
            if getattr(e, 'status', None) == 429:
                await asyncio.sleep(getattr(e, 'retry_after', 5))
            else:
                raise

async def safe_send(destination, *args, **kwargs):
    """Send a message handling rate limits"""
    while True:
        try:
            return await destination.send(*args, **kwargs)
        except discord.HTTPException as e:
            if getattr(e, 'status', None) == 429:
                await asyncio.sleep(getattr(e, 'retry_after', 5))
            else:
                raise

def detect_starcode_chain(emojis):
    """Detect if emojis form a meaningful StarCode chain"""
    return len(emojis) >= 2

def calculate_chain_influence(chain, author_id, bot):
    """Calculate influence based on chain reuse and blessings"""
    base_influence = 5
    chain_key = "".join(chain)
    
    # Check if chain is registered
    if chain_key in bot.starcode_patterns:
        pattern_data = bot.starcode_patterns[chain_key]
        reuse_count = pattern_data.get("uses", 0)
        
        # Original author bonus
        if pattern_data["author"] == author_id:
            base_influence += reuse_count  # +1 per reuse
        else:
            base_influence += 2  # Adopter bonus
            
    # Check if blessed
    if chain_key in bot.blessed_chains:
        if bot.blessed_chains[chain_key]["alignment"] == bot.divine_alignment:
            base_influence *= 2  # Double if aligned with current mood
            
    return base_influence

async def get_member_by_reference(ctx, reference: str):
    """Get a member by ID, username, or display name without mentioning"""
    # Try as user ID
    try:
        user_id = int(reference)
        member = ctx.guild.get_member(user_id)
        if member:
            return member
    except ValueError:
        pass
    
    # Try as username or display name
    reference_lower = reference.lower()
    for member in ctx.guild.members:
        if (member.name.lower() == reference_lower or 
            member.display_name.lower() == reference_lower or
            reference_lower in member.name.lower() or
            reference_lower in member.display_name.lower()):
            return member
    
    return None
async def fetch_history_batched(channel, limit=None, batch_size=100, base_delay=0.2, start_before=None, progress_callback=None):
    """Yield channel history in batches with adaptive delays for rate limits.

    Parameters
    ----------
    channel: discord.TextChannel
        Channel to fetch history from.
    limit: Optional[int]
        Maximum number of messages to retrieve.
    batch_size: int
        Number of messages per request.
    base_delay: float
        Base delay between batches to smooth requests.
    start_before: Optional[int]
        Message ID to start before when resuming a backfill.
    progress_callback: Optional[Callable[[int], Awaitable]]
        Called with the oldest fetched message ID after each batch.
    """
    fetched = 0
    before = start_before
    delay = base_delay
    while limit is None or fetched < limit:
        pull = batch_size if limit is None else min(batch_size, limit - fetched)
        while True:
            try:
                before_obj = discord.Object(id=before) if before else None
                batch = [m async for m in channel.history(limit=pull, before=before_obj)]
                break
            except discord.HTTPException as e:
                if getattr(e, 'status', None) == 429:
                    wait = getattr(e, 'retry_after', 5)
                    await asyncio.sleep(wait)
                    continue
                else:
                    raise
        if not batch:
            break
        for message in batch:
            yield message
        fetched += len(batch)
        before = batch[-1].id
        if progress_callback:
            await progress_callback(before)
        await asyncio.sleep(delay)

async def fetch_reaction_users_with_retry(reaction, batch_size=100, base_delay=0.2):
    """Yield users from a reaction while respecting rate limits."""
    after = None
    delay = base_delay
    while True:
        try:
            after_obj = discord.Object(id=after.id) if after else None
            users = [u async for u in reaction.users(limit=batch_size, after=after_obj)]
        except discord.HTTPException as e:
            if getattr(e, 'status', None) == 429:
                wait = getattr(e, 'retry_after', 5)
                await asyncio.sleep(wait)
                continue
            else:
                raise
        if not users:
            break
        for user in users:
            yield user
        after = users[-1]
        await asyncio.sleep(delay)

async def check_starlock(chain, member, guild):
    """Check if a chain unlocks a StarLock"""
    chain_key = "".join(chain)
    
    # Check custom starlocks first
    if chain_key in bot.custom_starlocks:
        lock_data = bot.custom_starlocks[chain_key]
        unlock_id = f"{guild.id}_{member.id}_{chain_key}"
        
        if unlock_id not in bot.starlock_unlocks[member.id]:
            bot.starlock_unlocks[member.id].append(unlock_id)
            
            if lock_data["type"] == "channel":
                # Create or reveal channel
                channel = discord.utils.get(guild.channels, name=lock_data["unlock"])
                if not channel:
                    category = discord.utils.get(guild.categories, name="📜 The Vault")
                    channel = await guild.create_text_channel(
                        name=lock_data["unlock"],
                        category=category,
                        topic=f"Unlocked by {lock_data['name']} StarLock"
                    )
                
                # Grant access
                await channel.set_permissions(member, read_messages=True)
                
                return f"🔓 **StarLock Unlocked!** Access granted to {channel.mention}"
                
            elif lock_data["type"] == "role":
                # Grant special role
                role = discord.utils.get(guild.roles, name=lock_data["name"])
                if not role:
                    role = await guild.create_role(
                        name=lock_data["name"],
                        color=0xFFD700,
                        mentionable=True
                    )
                
                await safe_add_roles(member, role)
                return f"🔓 **StarLock Unlocked!** Granted role: **{role.name}**"
    
    # Then check default starlocks
    elif chain_key in DEFAULT_STARLOCKS:
        lock_data = DEFAULT_STARLOCKS[chain_key]
        unlock_id = f"{guild.id}_{member.id}_{chain_key}"
        
        if unlock_id not in bot.starlock_unlocks[member.id]:
            bot.starlock_unlocks[member.id].append(unlock_id)
            
            if lock_data["type"] == "channel":
                # Create or reveal channel
                channel = discord.utils.get(guild.channels, name=lock_data["unlock"])
                if not channel:
                    category = discord.utils.get(guild.categories, name="📜 The Vault")
                    channel = await guild.create_text_channel(
                        name=lock_data["unlock"],
                        category=category,
                        topic=f"Unlocked by {lock_data['name']} StarLock"
                    )
                
                # Grant access
                await channel.set_permissions(member, read_messages=True)
                
                return f"🔓 **StarLock Unlocked!** Access granted to {channel.mention}"
                
            elif lock_data["type"] == "role":
                # Grant special role
                role = discord.utils.get(guild.roles, name=lock_data["name"])
                if not role:
                    role = await guild.create_role(
                        name=lock_data["name"],
                        color=0xFFD700,
                        mentionable=True
                    )
                
                await safe_add_roles(member, role)
                return f"🔓 **StarLock Unlocked!** Granted role: **{role.name}**"
    
    return None

async def check_role_progression(member, guild, channel=None):
    """Enhanced role progression with Knight/Ghost permissions

    Parameters
    ----------
    member : discord.Member
        The member earning a new role.
    guild : discord.Guild
        Guild context for role creation/lookups.
    channel : Optional[discord.TextChannel]
        Channel to post the progression announcement. If ``None`` the
        configured ``vault_progression`` channel for the guild is used.
    """
    user_stats = bot.user_data[member.id]
    current_roles = [role.name for role in member.roles]
    
    for role_key, config in ROLES_CONFIG.items():
        role_name = config["name"]
        
        if role_name in current_roles:
            continue
            
        qualified = False
        
        # Standard progression checks
        if role_key == "initiate_drone" and user_stats["reaction_count"] >= 1:
            qualified = True
        elif role_key == "wakened_seeker" and len(user_stats["emojis_used"]) >= 5:
            qualified = True
        elif role_key == "lore_harvester" and user_stats["reaction_count"] >= 10:
            qualified = True
        elif role_key == "memory_mason" and len(user_stats["starcode_chains"]) >= 3:
            qualified = True
        elif role_key == "index_guard" and user_stats["corrections"] >= 5:
            qualified = True
        elif role_key == "starforger" and user_stats["influence_score"] >= 50:
            qualified = True
        elif role_key == "vault_knight" and user_stats["corrections"] >= 3 and user_stats["problematic_flags"] >= 2:
            qualified = True
        elif role_key == "ghost_walker" and user_stats["influence_score"] >= 100 and len(user_stats["definitions_created"]) >= 3:
            qualified = True
        
        if qualified:
            # Create role if it doesn't exist
            role = discord.utils.get(guild.roles, name=role_name)
            if not role:
                role = await guild.create_role(
                    name=role_name,
                    color=config["color"],
                    mentionable=True
                )
            
            await safe_add_roles(member, role)
            
            # Announce progression in the invoking channel when provided
            if channel is None:
                channel_id = bot.get_channel_for_feature(guild.id, "vault_progression")
                if channel_id:
                    channel = guild.get_channel(int(channel_id))
                else:
                    channel = discord.utils.get(guild.channels, name="vault-progression")

            if channel:
                embed = discord.Embed(
                    title="✨ Role Ascension ✨",
                    description=f"{member.mention} has achieved **{role_name}**",
                    color=config["color"]
                )
                embed.add_field(
                    name="Requirement Met",
                    value=config["requirement"],
                    inline=False
                )
                
                # Show new permissions for Knight/Ghost
                if "permissions" in config:
                    perms_text = "\n".join([f"• `!vault {perm}`" for perm in config["permissions"]])
                    embed.add_field(
                        name="🔓 New Commands Unlocked",
                        value=perms_text,
                        inline=False
                    )
                
                embed.set_footer(text="The Nephesh Grid recognizes your growth")
                await channel.send(embed=embed)

def has_vault_role(member, role_key):
    """Check if member has a specific vault role"""
    role_config = ROLES_CONFIG.get(role_key)
    if not role_config:
        return False
    
    role_name = role_config["name"]
    return any(role.name == role_name for role in member.roles)

def has_permission(member, permission):
    """Check if member has a specific permission through their vault roles"""
    if member.guild_permissions.administrator:
        return True
        
    for role_key, config in ROLES_CONFIG.items():
        role_name = config["name"]
        if any(role.name == role_name for role in member.roles):
            if "permissions" in config and permission in config["permissions"]:
                return True
    
    return False

async def check_training_progress(user_id, action_type, context=None, channel=None):
    """Enhanced training detection with chain verification"""
    user_data = bot.user_data[user_id]
    current_training = user_data.get("training_quest")
    
    if not current_training:
        return False
        
    # Get quest data
    if current_training in DEFAULT_TRAINING_QUESTS:
        quest = DEFAULT_TRAINING_QUESTS[current_training]
    elif current_training in bot.custom_trainings:
        quest = bot.custom_trainings[current_training]
    else:
        return False
    
    # Check if action matches quest detection type
    if quest.get("detection") != action_type:
        return False
    
    # ENHANCED: Verify the actual content matches
    quest_chain = "".join(quest.get("chain", []))
    
    # Different verification for each type
    if action_type == "message" and context:
        # Check if the required chain is in the message
        message_emojis = "".join(extract_emojis(context))
        if quest_chain not in message_emojis:
            return False
            
    elif action_type == "starcode" and context:
        # Check if the registered starcode matches
        if quest_chain != context:
            return False
            
    elif action_type == "define" and context:
        # Check if user defined one of the required emojis
        defined_emoji = context.get("emoji")
        if defined_emoji not in quest.get("chain", []):
            return False
            
    elif action_type == "bless" and context:
        # Check if blessed chain matches
        if quest_chain != context:
            return False
            
    elif action_type == "shield":
        # Shield doesn't need chain verification
        pass
    
    # Track progress
    progress_key = f"{current_training}_progress"
    if progress_key not in user_data["training_progress"]:
        user_data["training_progress"][progress_key] = 0
    
    user_data["training_progress"][progress_key] += 1
    
    # Check if quest is complete
    required_count = quest.get("count", 1)
    current_progress = user_data["training_progress"][progress_key]
    
    if current_progress >= required_count:
        # Reset progress for this quest
        user_data["training_progress"][progress_key] = 0
        return True
    
    # Show progress update if channel provided and count > 1
    if channel and required_count > 1:
        embed = discord.Embed(
            title="📊 Quest Progress",
            description=f"**{quest['name']}**",
            color=0x87CEEB
        )
        embed.add_field(
            name="Progress",
            value=f"{current_progress}/{required_count}",
            inline=True
        )
        embed.add_field(
            name="Task",
            value=quest["task"],
            inline=False
        )
        await channel.send(embed=embed)
    
    return False

async def unregister_chain(chain_key, reason="unspecified", by_user_id=None):
    """Unregister a chain and revert its effects"""
    if chain_key not in bot.starcode_patterns:
        return False
    
    pattern_data = bot.starcode_patterns[chain_key]
    author_id = pattern_data["author"]
    
    # Revert influence for original author
    if author_id in bot.influence_history:
        reverted = 0
        remaining_history = []
        
        for entry in bot.influence_history[author_id]:
            if entry.get("chain") == chain_key and entry.get("reversible", False):
                # Revert this influence
                bot.user_data[author_id]["influence_score"] -= entry["amount"]
                reverted += entry["amount"]
            else:
                remaining_history.append(entry)
        
        bot.influence_history[author_id] = remaining_history
    
    # Revert influence for all adopters
    adopter_count = pattern_data.get("uses", 1) - 1
    if adopter_count > 0:
        # Find all users who adopted this chain
        for user_id, user_data in bot.user_data.items():
            if chain_key in user_data.get("chains_adopted", {}):
                adopt_count = user_data["chains_adopted"][chain_key]
                influence_to_revert = adopt_count * 2  # 2 influence per adoption
                bot.user_data[user_id]["influence_score"] -= influence_to_revert
                del user_data["chains_adopted"][chain_key]
    
    # Remove from author's originated chains
    if chain_key in bot.user_data[author_id].get("chains_originated", {}):
        del bot.user_data[author_id]["chains_originated"][chain_key]
    
    # Remove from patterns
    del bot.starcode_patterns[chain_key]
    
    # Remove from blessed chains if blessed
    if chain_key in bot.blessed_chains:
        del bot.blessed_chains[chain_key]
    
    # Log unregistration
    logger.info(
        f"Unregistered chain {chain_key} - Reason: {reason}, By: {by_user_id}"
    )
    
    return True

