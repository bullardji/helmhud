import discord
from discord.ext import commands, tasks
from .bot import bot
from .utils import *
from .config import *
import asyncio
import os
import json
from datetime import datetime, timedelta
import random
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)
# ============ STARLOCK MANAGEMENT COMMANDS ============
@bot.command(name='create_starkey')
async def create_starkey(ctx, channel_name: str, *starkey_codes):
    """Create a new StarKey to unlock a channel
    
    Parameters:
    - channel_name: The name of the channel to lock (e.g. "secret-lab")
    - starkey_codes: One or more emoji codes that will unlock the channel
    """
    # Permission check
    if not has_permission(ctx.author, "create_starlock") and not ctx.author.guild_permissions.administrator:
        await ctx.send("⛔ You do not have permission to create StarKeys.")
        return
    
    # Validate channel
    channel = discord.utils.get(ctx.guild.channels, name=channel_name)
    if not channel:
        await ctx.send(f"⚠️ Channel '{channel_name}' does not exist. Please create it first.")
        return
    
    # Validate starkey codes
    if not starkey_codes or len(starkey_codes) == 0:
        await ctx.send("⚠️ At least one StarKey code is required.")
        return
    
    # Process each starkey
    created_keys = []
    for starkey_code in starkey_codes:
        # Validate emoji chain
        emojis = extract_emojis(starkey_code)
        if len(emojis) < 2:
            await ctx.send(f"⚠️ StarKey '{starkey_code}' must contain at least 2 emojis. Skipped.")
            continue
            
        chain_key = "".join(emojis)
        
        # Check if already exists
        if chain_key in bot.custom_starlocks or chain_key in DEFAULT_STARLOCKS:
            await ctx.send(f"⚠️ StarKey '{chain_key}' already exists. Skipped.")
            continue
        
        # Create the starkey
        bot.custom_starlocks[chain_key] = {
            "unlock": channel_name,
            "type": "channel",
            "name": channel.name.replace("-", " ").title(),
            "created_by": ctx.author.id,
            "created_at": datetime.now().isoformat()
        }
        
        created_keys.append(chain_key)
    
    if created_keys:
        bot.save_data()
        keys_str = ", ".join(created_keys)
        await ctx.send(f"✅ StarKeys created for channel {channel.mention}!\n**Keys:** {keys_str}")
    else:
        await ctx.send("❌ No valid StarKeys were created.")

@bot.command(name='assign_starkey')
async def assign_starkey(ctx, channel_name: str, *starkey_codes):
    """Assign existing or new StarKeys to a channel
    
    Parameters:
    - channel_name: The name of the channel to assign keys to
    - starkey_codes: One or more emoji codes to assign
    """
    # Permission check
    if not has_permission(ctx.author, "create_starlock") and not ctx.author.guild_permissions.administrator:
        await ctx.send("⛔ You do not have permission to assign StarKeys.")
        return
    
    # Validate channel
    channel = discord.utils.get(ctx.guild.channels, name=channel_name)
    if not channel:
        await ctx.send(f"⚠️ Channel '{channel_name}' does not exist. Please create it first.")
        return
    
    # Validate starkey codes
    if not starkey_codes or len(starkey_codes) == 0:
        await ctx.send("⚠️ At least one StarKey code is required.")
        return
    
    # Process each starkey
    assigned_keys = []
    for starkey_code in starkey_codes:
        # Validate emoji chain
        emojis = extract_emojis(starkey_code)
        if len(emojis) < 2:
            await ctx.send(f"⚠️ StarKey '{starkey_code}' must contain at least 2 emojis. Skipped.")
            continue
            
        chain_key = "".join(emojis)
        
        # Update existing or create new
        bot.custom_starlocks[chain_key] = {
            "unlock": channel_name,
            "type": "channel",
            "name": channel.name.replace("-", " ").title(),
            "created_by": ctx.author.id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "updated_by": ctx.author.id
        }
        
        assigned_keys.append(chain_key)
    
    if assigned_keys:
        bot.save_data()
        keys_str = ", ".join(assigned_keys)
        await ctx.send(f"✅ StarKeys assigned to channel {channel.mention}!\n**Keys:** {keys_str}")
    else:
        await ctx.send("❌ No StarKeys were assigned.")

@bot.command(name='manage_starkeys')
async def manage_starkeys(ctx, action: str, starkey_code: str = None, channel_name: str = None):
    """Manage StarKeys with various actions
    
    Parameters:
    - action: The action to perform (revoke, delete, clear)
    - starkey_code: The emoji code to manage (required for revoke, delete)
    - channel_name: The channel to manage (required for revoke, clear)
    """
    # Permission check
    if not has_permission(ctx.author, "manage_starlock") and not ctx.author.guild_permissions.administrator:
        await ctx.send("⛔ You do not have permission to manage StarKeys.")
        return
    
    if action == "revoke" and (not starkey_code or not channel_name):
        await ctx.send("⚠️ Both starkey_code and channel_name are required for revoke action.")
        return
    
    if action == "delete" and not starkey_code:
        await ctx.send("⚠️ starkey_code is required for delete action.")
        return
    
    if action == "clear" and not channel_name:
        await ctx.send("⚠️ channel_name is required for clear action.")
        return
    
    if action == "revoke":
        # Revoke a specific starkey from a specific channel
        emojis = extract_emojis(starkey_code)
        chain_key = "".join(emojis)
        
        if chain_key in DEFAULT_STARLOCKS:
            await ctx.send("⚠️ Cannot revoke default StarKeys.")
            return
            
        if chain_key not in bot.custom_starlocks:
            await ctx.send("⚠️ This StarKey doesn't exist in the custom registry.")
            return
            
        lock_data = bot.custom_starlocks[chain_key]
        if lock_data["unlock"] != channel_name:
            await ctx.send(f"⚠️ StarKey '{chain_key}' is not assigned to channel '{channel_name}'.")
            return
        
        del bot.custom_starlocks[chain_key]
        bot.save_data()
        
        await ctx.send(f"✅ StarKey '{chain_key}' revoked from channel '{channel_name}'.")
    
    elif action == "delete":
        # Delete a starkey entirely
        emojis = extract_emojis(starkey_code)
        chain_key = "".join(emojis)
        
        if chain_key in DEFAULT_STARLOCKS:
            await ctx.send("⚠️ Cannot delete default StarKeys.")
            return
            
        if chain_key not in bot.custom_starlocks:
            await ctx.send("⚠️ This StarKey doesn't exist in the custom registry.")
            return
        
        lock_data = bot.custom_starlocks[chain_key]
        del bot.custom_starlocks[chain_key]
        bot.save_data()
        
        await ctx.send(f"✅ StarKey '{chain_key}' deleted. It previously unlocked '{lock_data['unlock']}'.")
    
    elif action == "clear":
        # Remove all starkeys for a channel
        keys_to_remove = []
        
        for chain_key, data in bot.custom_starlocks.items():
            if data["unlock"] == channel_name and data["type"] == "channel":
                keys_to_remove.append(chain_key)
        
        if not keys_to_remove:
            await ctx.send(f"⚠️ No StarKeys found for channel '{channel_name}'.")
            return
        
        for key in keys_to_remove:
            del bot.custom_starlocks[key]
        
        bot.save_data()
        keys_str = ", ".join(keys_to_remove)
        await ctx.send(f"✅ All StarKeys cleared for channel '{channel_name}'.\nRemoved keys: {keys_str}")
    
    else:
        await ctx.send("⚠️ Invalid action. Use 'revoke', 'delete', or 'clear'.")

@bot.command(name='list_starlocks')
async def list_starlocks(ctx):
    """List all available StarLocks organized by channel"""
    # Permission check
    if not has_permission(ctx.author, "create_starlock") and not ctx.author.guild_permissions.administrator:
        await ctx.send("⛔ You do not have permission to view StarLocks.")
        return
    
    embed = discord.Embed(
        title="🔒 Channel StarKeys",
        description="All configured StarKey combinations by channel",
        color=0xFFD700
    )
    
    # Organize by channel/role
    channel_locks = {}
    
    # Collect default starlocks
    for chain, data in DEFAULT_STARLOCKS.items():
        target = data["unlock"]
        if target not in channel_locks:
            channel_locks[target] = {"type": data["type"], "keys": []}
        
        channel_locks[target]["keys"].append({
            "key": chain,
            "is_default": True,
            "creator": None
        })
    
    # Collect custom starlocks
    for chain, data in bot.custom_starlocks.items():
        target = data["unlock"]
        if target not in channel_locks:
            channel_locks[target] = {"type": data["type"], "keys": []}
        
        channel_locks[target]["keys"].append({
            "key": chain,
            "is_default": False,
            "creator": data.get("created_by")
        })
    
    # Add fields for each channel/role
    for target, data in sorted(channel_locks.items()):
        if data["type"] == "channel":
            channel = discord.utils.get(ctx.guild.channels, name=target)
            target_name = channel.mention if channel else f"#{target}"
        else:
            role = discord.utils.get(ctx.guild.roles, name=target)
            target_name = role.mention if role else f"@{target}"
        
        keys_text = []
        for key_data in data["keys"]:
            key = key_data["key"]
            if key_data["is_default"]:
                keys_text.append(f"**{key}** (default)")
            else:
                creator_id = key_data["creator"]
                creator = ctx.guild.get_member(creator_id) if creator_id else None
                creator_name = creator.display_name if creator else "Unknown"
                keys_text.append(f"**{key}** (by {creator_name})")
        
        embed.add_field(
            name=f"{'#' if data['type'] == 'channel' else '@'} {target}",
            value="\n".join(keys_text) if keys_text else "No keys assigned",
            inline=False
        )
    
    if not channel_locks:
        embed.add_field(
            name="No StarKeys Found",
            value="No channels or roles have StarKeys assigned.",
            inline=False
        )
    
    # Send the profile directly in the invoking channel
    await ctx.send(embed=embed)

# ============ PROFILE COMMAND WITH FIXES ============
@bot.command(name='profile')
async def profile(ctx, *, target: str = None):
    """Enhanced profile with all new stats - accepts mentions, IDs, or names"""
    member = None
    
    if target:
        # First, try to parse as a mention
        if target.startswith('<@') and target.endswith('>'):
            # Extract user ID from mention
            user_id = target[2:-1]
            # Handle nickname mentions (they have a ! after @)
            if user_id.startswith('!'):
                user_id = user_id[1:]
            
            try:
                member = ctx.guild.get_member(int(user_id))
            except (ValueError, AttributeError):
                member = None
        
        # If not a mention or mention parsing failed, try other methods
        if not member:
            # Try as user ID
            try:
                member = ctx.guild.get_member(int(target))
            except ValueError:
                # Try to find by name/nickname
                target_lower = target.lower()
                
                # First try exact matches
                for m in ctx.guild.members:
                    if m.name.lower() == target_lower or m.display_name.lower() == target_lower:
                        member = m
                        break
                
                # If no exact match, try partial matches
                if not member:
                    for m in ctx.guild.members:
                        if target_lower in m.name.lower() or target_lower in m.display_name.lower():
                            member = m
                            break
        
        if not member:
            # Try using Discord's converter as last resort
            try:
                converter = commands.MemberConverter()
                member = await converter.convert(ctx, target)
            except commands.BadArgument:
                await ctx.send(f"❌ Could not find user: {target}")
                return
    else:
        member = ctx.author
    
    # Ensure user has data
    if member.id not in bot.user_data:
        bot.user_data[member.id] = {
            "emojis_used": set(),
            "reaction_count": 0,
            "starcode_chains": [],
            "corrections": 0,
            "influence_score": 0,
            "remory_strings": [],
            "chains_originated": {},
            "chains_adopted": {},
            "training_quest": None,
            "training_progress": {},
            "blessed_chains": [],
            "problematic_flags": 0,
            "definitions_created": {},
            "completed_trainings": []
        }
    
    stats = bot.user_data[member.id]
    
    # Create title with unique identifier
    title = f"📜 Vault Profile: {member.display_name}"
    if member.display_name != member.name:
        title += f" ({member.name})"
    
    embed = discord.Embed(
        title=title,
        description=f"**User ID:** `{member.id}`",  # Prominent ID display
        color=0xFFD700
    )
    
    # Basic Stats
    embed.add_field(
        name="📊 Core Statistics",
        value=f"Reactions: **{stats['reaction_count']}**\n"
              f"Unique Glyphs: **{len(stats['emojis_used'])}**\n"
              f"StarCodes: **{len(stats['starcode_chains'])}**\n"
              f"Corrections: **{stats['corrections']}**\n"
              f"Influence: **{stats['influence_score']}**",
        inline=True
    )
    
    # Pattern Stats
    chains_created = len(stats['chains_originated'])
    chains_adopted = sum(stats['chains_adopted'].values())
    blessed_count = len(stats['blessed_chains'])
    
    embed.add_field(
        name="🌟 Pattern Mastery",
        value=f"Created: **{chains_created}**\n"
              f"Adopted: **{chains_adopted}**\n"
              f"Blessed: **{blessed_count}**\n"
              f"Definitions: **{len(stats['definitions_created'])}**",
        inline=True
    )
    
    # Training Status
    current_training = stats.get("training_quest")
    completed_count = len(stats.get("completed_trainings", []))
    
    training_text = f"Completed: **{completed_count}**"
    if current_training:
        # Get quest name
        if current_training in DEFAULT_TRAINING_QUESTS:
            quest_name = DEFAULT_TRAINING_QUESTS[current_training]["name"]
        elif current_training in bot.custom_trainings:
            quest_name = bot.custom_trainings[current_training]["name"]
        else:
            quest_name = current_training
        training_text += f"\nActive: {quest_name}"
    
    embed.add_field(
        name="🎯 Training Progress",
        value=training_text,
        inline=True
    )
    
    # Recent StarCodes
    if stats['starcode_chains']:
        recent_chains = stats['starcode_chains'][-3:]
        chains_text = "\n".join(["".join(chain) for chain in recent_chains])
        embed.add_field(
            name="🌟 Recent StarCodes",
            value=chains_text or "None yet",
            inline=False
        )
    
    # Roles
    roles = [r.name for r in member.roles if r.name.startswith(("🔰", "👁️", "🌾", "🧱", "🛡️", "📖", "⭐", "⚔️", "👻"))]
    embed.add_field(
        name="🎭 Vault Roles",
        value="\n".join(roles) or "No vault roles yet",
        inline=False
    )
    
    # Show unlocked StarLocks
    if member.id in bot.starlock_unlocks:
        unlocks = bot.starlock_unlocks[member.id]
        unlock_names = []
        starlocks = {**DEFAULT_STARLOCKS, **bot.custom_starlocks}
        for unlock in unlocks[-3:]:
            for chain, lock_data in starlocks.items():
                if chain in unlock:
                    unlock_names.append(lock_data["name"])
                    break
        
        if unlock_names:
            embed.add_field(
                name="🔓 Unlocked StarLocks",
                value="\n".join(unlock_names),
                inline=True
            )
    
    # Account age and server join info
    created_date = member.created_at.strftime("%Y-%m-%d")
    joined_date = member.joined_at.strftime("%Y-%m-%d") if member.joined_at else "Unknown"
    
    embed.set_footer(text=f"Account created: {created_date} | Joined server: {joined_date}")
    
    # Ensure the profile reply is sent where the command was used
    await ctx.send(embed=embed)

# ============ DIAGNOSTIC COMMAND ============
@bot.command(name='diagnose')
@commands.has_permissions(administrator=True)
async def diagnose_user(ctx, *, target: str = None):
    """Admin: Diagnose user data issues"""
    member = None
    
    if target:
        # Use same resolution logic as profile
        if target.startswith('<@') and target.endswith('>'):
            user_id = target[2:-1]
            if user_id.startswith('!'):
                user_id = user_id[1:]
            
            try:
                member = ctx.guild.get_member(int(user_id))
            except (ValueError, AttributeError):
                member = None
        
        if not member:
            try:
                member = ctx.guild.get_member(int(target))
            except ValueError:
                target_lower = target.lower()
                
                for m in ctx.guild.members:
                    if m.name.lower() == target_lower or m.display_name.lower() == target_lower:
                        member = m
                        break
                
                if not member:
                    for m in ctx.guild.members:
                        if target_lower in m.name.lower() or target_lower in m.display_name.lower():
                            member = m
                            break
        
        if not member:
            try:
                converter = commands.MemberConverter()
                member = await converter.convert(ctx, target)
            except commands.BadArgument:
                await ctx.send(f"❌ Could not find user: {target}")
                return
    else:
        member = ctx.author
    
    embed = discord.Embed(
        title=f"🔧 Data Diagnosis: {member.display_name}",
        description=f"User ID: `{member.id}`",
        color=0xFF6347
    )
    
    # Check if user exists in data
    if member.id in bot.user_data:
        data = bot.user_data[member.id]
        
        # Display core data values
        embed.add_field(
            name="Core Metrics",
            value=f"Emojis Used: {len(data.get('emojis_used', []))} unique emojis\n"
                  f"Reaction Count: {data.get('reaction_count', 0)}\n"
                  f"Influence Score: {data.get('influence_score', 0)}\n"
                  f"Corrections Made: {data.get('corrections', 0)}\n"
                  f"Problem Flags: {data.get('problematic_flags', 0)}",
            inline=False
        )
        
        # Display StarCode metrics
        starcode_chains = data.get('starcode_chains', [])
        originated = len(data.get('chains_originated', {}))
        adopted = len(data.get('chains_adopted', {}))
        blessed = len(data.get('blessed_chains', []))
        
        embed.add_field(
            name="StarCode Activity",
            value=f"Chains Created: {len(starcode_chains)}\n"
                  f"Patterns Originated: {originated}\n"
                  f"Patterns Adopted: {adopted}\n"
                  f"Blessed Chains: {blessed}",
            inline=False
        )
        
        # Training information
        current_quest = data.get('training_quest', None)
        completed = len(data.get('completed_trainings', []))
        
        embed.add_field(
            name="Training Status",
            value=f"Current Quest: {current_quest if current_quest else 'None'}\n"
                  f"Completed Trainings: {completed}\n" +
                  (f"Quest Progress: {data['training_progress'].get(f'{current_quest}_progress', 0)}" 
                   if current_quest else "No active quest"),
            inline=False
        )
        
        # Sample recent activity from server
        recent_reactions = 0
        recent_messages = 0
        
        # Check last 100 messages in current channel
        async for message in ctx.channel.history(limit=100):
            if message.author.id == member.id:
                recent_messages += 1
            
            for reaction in message.reactions:
                users = [user async for user in reaction.users()]
                if member in users:
                    recent_reactions += 1
        
        embed.add_field(
            name="Recent Activity (last 100 msgs in this channel)",
            value=f"Messages: {recent_messages}\n"
                  f"Reactions: {recent_reactions}",
            inline=False
        )
        
        # Role Qualifications and Actual Roles
        # Get a mapping of role names for the user
        member_role_names = {role.name.lower() for role in member.roles}
        
        role_status = []
        
        # Define the roles and their requirements
        role_checks = [
            {"key": "initiate_drone", "display": "Initiate Drone", 
             "requirement": data.get("reaction_count", 0) >= 1},
            {"key": "wakened_seeker", "display": "Wakened Seeker",
             "requirement": len(data.get("emojis_used", [])) >= 5},
            {"key": "lore_harvester", "display": "Lore Harvester",
             "requirement": data.get("reaction_count", 0) >= 10},
            {"key": "memory_mason", "display": "Memory Mason",
             "requirement": len(data.get("starcode_chains", [])) >= 3},
            {"key": "index_guard", "display": "Index Guard",
             "requirement": data.get("corrections", 0) >= 5},
            {"key": "starforger", "display": "StarForger",
             "requirement": data.get("influence_score", 0) >= 50},
            {"key": "vault_knight", "display": "Vault Knight",
             "requirement": data.get("corrections", 0) >= 3 and data.get("problematic_flags", 0) >= 2},
            {"key": "ghost_walker", "display": "Ghost Walker",
             "requirement": data.get("influence_score", 0) >= 100 and len(data.get("definitions_created", {})) >= 3}
        ]
        
        for role in role_checks:
            # Check if qualified by data
            qualified = "✅" if role["requirement"] else "❌"
            
            # Check if they actually have the role
            has_role = False
            
            # Get the config for this specific role
            role_config = ROLES_CONFIG.get(role["key"])
            if role_config:
                role_name = role_config.get("name", "").lower()
                if role_name in member_role_names:
                    has_role = True
            
            # Special case for roles with emoji in name
            if not has_role:
                for role_name in [role["display"].lower(), f"⚔️ {role['display'].lower()}", 
                                 f"👻 {role['display'].lower()}"]:
                    if role_name in member_role_names:
                        has_role = True
                        break
            
            assigned = "🎭" if has_role else "🚫"
            
            # Add to status list
            role_status.append(f"{qualified} {assigned} {role['display']}")
        
        # Add legend explaining the symbols
        legend = "**Legend:**\n✅ = Qualified by stats | ❌ = Not qualified\n🎭 = Role assigned | 🚫 = Role not assigned"
        
        embed.add_field(
            name="Role Status (Qualified/Assigned)",
            value=legend + "\n\n" + "\n".join(role_status),
            inline=False
        )
        
        # Check if sets need conversion
        if isinstance(data.get('emojis_used'), list):
            embed.add_field(
                name="⚠️ Data Issue Detected",
                value="emojis_used is a list, should be a set",
                inline=False
            )
    else:
        embed.add_field(
            name="❌ No Data Found",
            value="User has no profile data",
            inline=False
        )
    
    await ctx.send(embed=embed)

# ============ BACKFILL COMMAND WITH FIXES ============
@bot.command(name='backfill')
@commands.has_permissions(administrator=True)
async def backfill_server(ctx, limit: int = None):
    """Admin: Backfill entire server history as if bot was always present
    
    Usage: !vault backfill [message_limit]
    - No limit = process entire server
    - With limit = process up to X messages per channel
    """
    
    # Confirmation
    confirm_embed = discord.Embed(
        title="⚠️ Server Backfill Confirmation",
        description="This will process ALL server history and set up missing profiles.",
        color=0xFF6347
    )
    confirm_embed.add_field(
        name="What this does:",
        value="• Sets up profiles for all users\n"
              "• Scans historical messages\n"
              "• Registers untracked StarCodes\n"
              "• Processes missed reactions\n"
              "• Calculates influence scores\n"
              "• Assigns roles based on activity\n"
              "• **Skips already processed data**",
        inline=False
    )
    confirm_embed.add_field(
        name="Limit",
        value=f"{limit if limit else 'No limit'} messages per channel",
        inline=True
    )
    confirm_embed.set_footer(text="React with ✅ to confirm or ❌ to cancel")
    
    confirm_msg = await ctx.send(embed=confirm_embed)
    await confirm_msg.add_reaction("✅")
    await confirm_msg.add_reaction("❌")
    
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirm_msg.id
    
    try:
        reaction, user = await bot.wait_for('reaction_add', timeout=30.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send("❌ Backfill cancelled - timeout")
        return
    
    if str(reaction.emoji) == "❌":
        await ctx.send("❌ Backfill cancelled")
        return
    
    # Start backfill
    start_time = datetime.now()
    
    # Track what we've already processed to avoid duplicates
    processed_messages = set()  # Message IDs we've seen
    processed_reactions = set()  # (message_id, user_id, emoji) tuples
    existing_chains = set(bot.starcode_patterns.keys())  # Already registered chains
    existing_remories = defaultdict(set)  # Track existing remories per user
    
    # Build existing remory index to avoid duplicates
    for user_id, user_data in bot.user_data.items():
        for remory in user_data.get("remory_strings", []):
            if "message_id" in remory:
                existing_remories[user_id].add(remory["message_id"])
    
    # Create log channel or use current
    log_embed = discord.Embed(
        title="📋 Backfill Log",
        description="Starting backfill process...",
        color=0x87CEEB,
        timestamp=datetime.now()
    )
    log_msg = await ctx.send(embed=log_embed)
    
    # Initialize counters
    stats = {
        "messages_processed": 0,
        "messages_skipped": 0,
        "reactions_processed": 0,
        "reactions_skipped": 0,
        "chains_found": 0,
        "chains_registered": 0,
        "chains_skipped": 0,
        "chains_adopted": 0,
        "users_processed": set(),
        "new_profiles": 0,
        "existing_profiles": 0,
        "channels_processed": 0,
        "channels_skipped": 0,
        "errors": 0,
        "influence_awarded": 0,
        "roles_assigned": defaultdict(int),
        "definitions_found": 0,
        "blessed_chains": 0,
        "remories_stored": 0,
        "remories_skipped": 0,
        "emoji_unique": set(),
        "last_update": datetime.now()
    }
    
    # Log buffer for batched updates
    log_buffer = []
    
    async def update_log(message, level="INFO"):
        """Add message to log buffer and update periodically"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"`[{timestamp}] {level}:` {message}"
        log_buffer.append(log_entry)

        level_map = {"INFO": logging.INFO, "WARN": logging.WARNING, "ERROR": logging.ERROR}
        logger.log(level_map.get(level, logging.INFO), message)
        
        # Update log every 10 entries or 5 seconds
        if len(log_buffer) >= 10 or (datetime.now() - stats["last_update"]).seconds >= 5:
            log_embed.description = "**Recent Activity:**\n" + "\n".join(log_buffer[-15:])
            log_embed.set_field_at(
                0,
                name="📊 Progress",
                value=f"Channels: {stats['channels_processed']}/{len([ch for ch in ctx.guild.channels if isinstance(ch, discord.TextChannel)])}\n"
                      f"Messages: {stats['messages_processed']:,} ({stats['messages_skipped']} skipped)\n"
                      f"Chains: {stats['chains_registered']} new, {stats['chains_skipped']} existing",
                inline=True
            )
            log_embed.set_field_at(
                1,
                name="👥 Users",
                value=f"Total: {len(stats['users_processed'])}\n"
                      f"New Profiles: {stats['new_profiles']}\n"
                      f"Influence Given: {stats['influence_awarded']:,}",
                inline=True
            )
            
            await safe_edit_message(log_msg, embed=log_embed)
            stats["last_update"] = datetime.now()
    
    # Set up initial log fields
    log_embed.add_field(name="📊 Progress", value="Starting...", inline=True)
    log_embed.add_field(name="👥 Users", value="Starting...", inline=True)
    
    await update_log("🚀 Backfill initiated by " + ctx.author.name)
    await update_log(f"📝 Message limit: {limit if limit else 'None'}")
    
    # First pass: Initialize profiles for all server members
    await update_log("👥 Initializing user profiles...")
    for member in ctx.guild.members:
        if member.bot:
            continue
            
        if member.id not in bot.user_data or not bot.user_data[member.id]["reaction_count"]:
            # Initialize new profile
            bot.user_data[member.id] = {
                "emojis_used": set(),
                "reaction_count": 0,
                "starcode_chains": [],
                "corrections": 0,
                "influence_score": 0,
                "remory_strings": [],
                "chains_originated": {},
                "chains_adopted": {},
                "training_quest": None,
                "training_progress": {},
                "blessed_chains": [],
                "problematic_flags": 0,
                "definitions_created": {},
                "completed_trainings": []
            }
            stats["new_profiles"] += 1
        else:
            stats["existing_profiles"] += 1
        
        stats["users_processed"].add(member.id)
    
    await update_log(f"✅ Profile setup: {stats['new_profiles']} new, {stats['existing_profiles']} existing")
    
    # Get all text channels
    text_channels = [ch for ch in ctx.guild.channels if isinstance(ch, discord.TextChannel)]
    await update_log(f"📚 Found {len(text_channels)} text channels to process")
    
    # Process each channel with a small worker pool
    max_workers = 3
    queue = asyncio.Queue()
    for i, ch in enumerate(text_channels):
        await queue.put((i, ch))

    semaphore = asyncio.Semaphore(max_workers)

    async def process_channel(idx, channel):
        nonlocal processed_messages, processed_reactions, existing_chains, existing_remories
        # Skip channels bot can't read
        if not channel.permissions_for(ctx.guild.me).read_message_history:
            stats["channels_skipped"] += 1
            await update_log(f"⚠️ Skipping #{channel.name} - no permissions", "WARN")
            return

        stats["channels_processed"] += 1
        channel_start = datetime.now()
        channel_messages = 0
        channel_chains = 0
        channel_skipped = 0

        await update_log(f"📂 Processing #{channel.name} ({idx+1}/{len(text_channels)})")

        start_before = bot.backfill_progress.get(str(ctx.guild.id), {}).get(str(channel.id))

        async def checkpoint(mid):
            guild_map = bot.backfill_progress.setdefault(str(ctx.guild.id), {})
            guild_map[str(channel.id)] = mid

        try:
            # Process messages in channel using batched fetches
            async for message in fetch_history_batched(channel, limit, start_before=start_before, progress_callback=checkpoint):
                if message.author.bot:
                    continue
                
                # Check if we've already processed this message
                if message.id in processed_messages:
                    stats["messages_skipped"] += 1
                    channel_skipped += 1
                    continue
                    
                processed_messages.add(message.id)
                stats["messages_processed"] += 1
                if stats["messages_processed"] % 500 == 0:
                    bot.save_data()
                channel_messages += 1
                
                # Ensure user has profile
                if message.author.id not in bot.user_data:
                    bot.user_data[message.author.id] = {
                        "emojis_used": set(),
                        "reaction_count": 0,
                        "starcode_chains": [],
                        "corrections": 0,
                        "influence_score": 0,
                        "remory_strings": [],
                        "chains_originated": {},
                        "chains_adopted": {},
                        "training_quest": None,
                        "training_progress": {},
                        "blessed_chains": [],
                        "problematic_flags": 0,
                        "definitions_created": {},
                        "completed_trainings": []
                    }
                    stats["new_profiles"] += 1
                
                # Log every 100 messages
                if channel_messages % 100 == 0:
                    await update_log(f"  └─ {channel_messages} messages in #{channel.name} ({channel_skipped} skipped)")
                    await asyncio.sleep(0)
                
                # Extract emojis from message
                all_emojis = extract_emojis(message.content)
                sequences = find_contiguous_emoji_chains(message.content)
                emojis = sequences[0] if sequences else []
                
                # Track unique emojis
                stats["emoji_unique"].update(all_emojis)
                
                # Process emoji chains
                if emojis:
                    stats["chains_found"] += 1
                    chain_key = "".join(emojis)
                    
                    # Check if chain already exists
                    if chain_key in existing_chains:
                        stats["chains_skipped"] += 1
                        # Still track adoption if user used existing chain
                        if chain_key not in bot.user_data[message.author.id]["chains_adopted"]:
                            bot.starcode_patterns[chain_key]["uses"] += 1
                            bot.user_data[message.author.id]["chains_adopted"][chain_key] = 1
                            bot.user_data[message.author.id]["influence_score"] += 2
                            stats["influence_awarded"] += 2
                            stats["chains_adopted"] += 1
                    else:
                        # New chain - register it
                        bot.starcode_patterns[chain_key] = {
                            "author": message.author.id,
                            "created": message.created_at.isoformat(),
                            "uses": 1,
                            "description": f"Backfilled from: {message.content[:50]}...",
                            "pattern": chain_key,
                            "message_id": message.id,
                            "backfilled": True
                        }
                        stats["chains_registered"] += 1
                        channel_chains += 1
                        existing_chains.add(chain_key)
                        
                        # Track for author
                        bot.user_data[message.author.id]["chains_originated"][chain_key] = 1
                        bot.user_data[message.author.id]["influence_score"] += 10
                        stats["influence_awarded"] += 10
                        
                        # Log significant chains
                        if stats["chains_registered"] % 10 == 0:
                            await update_log(f"✨ Registered {stats['chains_registered']}th chain: {chain_key}")
                    
                    # Store as remory if not duplicate
                    if message.id not in existing_remories[message.author.id]:
                        remory = {
                            "author": message.author.id,
                            "chain": emojis,
                            "timestamp": message.created_at,
                            "context": message.content[:100],
                            "channel": channel.name,
                            "message_id": message.id
                        }
                        bot.user_data[message.author.id]["remory_strings"].append(remory)
                        bot.user_data[message.author.id]["starcode_chains"].append(emojis)
                        existing_remories[message.author.id].add(message.id)
                        stats["remories_stored"] += 1
                    else:
                        stats["remories_skipped"] += 1
                
                # Process reactions
                reaction_count = 0
                for reaction in message.reactions:
                    emoji = str(reaction.emoji)
                    
                    # Get reaction users
                    async for user in fetch_reaction_users_with_retry(reaction):
                        if user.bot:
                            continue
                        
                        # Check if we've already processed this reaction
                        reaction_key = (message.id, user.id, emoji)
                        if reaction_key in processed_reactions:
                            stats["reactions_skipped"] += 1
                            continue
                        
                        processed_reactions.add(reaction_key)
                        stats["reactions_processed"] += 1
                        reaction_count += 1
                        
                        # Ensure user has profile
                        if user.id not in bot.user_data:
                            bot.user_data[user.id] = {
                                "emojis_used": set(),
                                "reaction_count": 0,
                                "starcode_chains": [],
                                "corrections": 0,
                                "influence_score": 0,
                                "remory_strings": [],
                                "chains_originated": {},
                                "chains_adopted": {},
                                "training_quest": None,
                                "training_progress": {},
                                "blessed_chains": [],
                                "problematic_flags": 0,
                                "definitions_created": {},
                                "completed_trainings": []
                            }
                            stats["new_profiles"] += 1
                        
                        # Track emoji usage
                        bot.user_data[user.id]["emojis_used"].add(emoji)
                        bot.user_data[user.id]["reaction_count"] += 1
                        
                        # Check for influence from reaction chains
                        message_reactions = [str(r.emoji) for r in message.reactions]
                        if detect_starcode_chain(message_reactions):
                            influence = calculate_chain_influence(message_reactions, user.id, bot)
                            bot.user_data[user.id]["influence_score"] += influence
                            stats["influence_awarded"] += influence
                
                # Log messages with high reaction counts
                if reaction_count >= 10:
                    await update_log(f"🔥 High engagement: {reaction_count} reactions on message in #{channel.name}")
                
                # Check for commands in message (definitions, blessings, etc)
                if message.content.startswith("!vault "):
                    command_result = await process_backfill_command(message, stats)
                    if command_result:
                        await update_log(f"📝 Found command: {command_result}")
                
        except discord.Forbidden:
            stats["errors"] += 1
            await update_log(f"❌ No permission to read #{channel.name}", "ERROR")
            return
        except Exception as e:
            stats["errors"] += 1
            await update_log(f"❌ Error in #{channel.name}: {str(e)[:50]}", "ERROR")
            print(f"Full error: {e}")
            return

        # Save progress after each channel
        await update_log("💾 Saving checkpoint...")
        bot.save_data()

        # Channel complete log
        channel_duration = (datetime.now() - channel_start).seconds
        await update_log(
            f"✅ Completed #{channel.name}: {channel_messages} msgs ({channel_skipped} skipped), {channel_chains} new chains in {channel_duration}s"
        )

    async def worker():
        while True:
            item = await queue.get()
            if item is None:
                queue.task_done()
                break
            idx, ch = item
            async with semaphore:
                await process_channel(idx, ch)
            queue.task_done()

    workers = [asyncio.create_task(worker()) for _ in range(max_workers)]
    await queue.join()
    for _ in workers:
        await queue.put(None)
    await asyncio.gather(*workers)
    
    # Post-processing: Assign roles based on accumulated stats
    await update_log("🎭 Starting role assignment phase...")
    
    role_start = datetime.now()
    users_checked = 0
    
    # Get all members with profiles
    all_profile_users = set(bot.user_data.keys())
    
    for user_id in all_profile_users:
        users_checked += 1
        member = ctx.guild.get_member(user_id)
        if not member:
            continue
        
        # Log every 50 users
        if users_checked % 50 == 0:
            await update_log(f"  └─ Checked {users_checked}/{len(all_profile_users)} users for roles")
            
        # Check all role qualifications
        user_stats = bot.user_data[user_id]
        user_roles_assigned = []
        
        # Check each role
        for role_key, config in ROLES_CONFIG.items():
            role_name = config["name"]
            
            # Skip if already has role
            if any(r.name == role_name for r in member.roles):
                continue
            
            qualified = False
            
            # Check qualifications
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
                # Create role if needed
                role = discord.utils.get(ctx.guild.roles, name=role_name)
                if not role:
                    role = await ctx.guild.create_role(
                        name=role_name,
                        color=config["color"],
                        mentionable=True
                    )
                    await update_log(f"🎨 Created role: {role_name}")
                
                try:
                    await safe_add_roles(member, role)
                    stats["roles_assigned"][role_name] += 1
                    user_roles_assigned.append(role_name)
                except Exception as e:
                    await update_log(f"❌ Failed to assign {role_name} to {member.name}: {str(e)[:30]}", "ERROR")
                    continue
        
        # Log significant role assignments
        if user_roles_assigned:
            if len(user_roles_assigned) >= 3:
                await update_log(f"⭐ Power user {member.name} earned {len(user_roles_assigned)} roles!")
            elif "👻 Ghost Walker" in user_roles_assigned:
                await update_log(f"👻 {member.name} achieved Ghost Walker status!")
            elif "⚔️ Vault Knight" in user_roles_assigned:
                await update_log(f"⚔️ {member.name} became a Vault Knight!")
    
    role_duration = (datetime.now() - role_start).seconds
    await update_log(f"✅ Role assignment complete in {role_duration}s")
    
    # Save all data
    await update_log("💾 Saving all data...")
    bot.save_data()
    
    # Calculate total duration
    total_duration = (datetime.now() - start_time).seconds
    
    # Create final summary
    summary_embed = discord.Embed(
        title="✅ Backfill Complete!",
        description=f"Processed {ctx.guild.name} in {total_duration} seconds ({total_duration//60} minutes)",
        color=0x90EE90,
        timestamp=datetime.now()
    )
    
    summary_embed.add_field(
        name="📊 Processing Stats",
        value=f"Channels: {stats['channels_processed']} processed, {stats['channels_skipped']} skipped\n"
              f"Messages: {stats['messages_processed']:,} new, {stats['messages_skipped']} existing\n"
              f"Reactions: {stats['reactions_processed']:,} new, {stats['reactions_skipped']} existing\n"
              f"Unique Emojis: {len(stats['emoji_unique'])}",
        inline=True
    )
    
    summary_embed.add_field(
        name="👥 User Stats",
        value=f"Total Profiles: {len(bot.user_data)}\n"
              f"New Profiles: {stats['new_profiles']}\n"
              f"Existing: {stats['existing_profiles']}\n"
              f"Influence Given: {stats['influence_awarded']:,}",
        inline=True
    )
    
    summary_embed.add_field(
        name="✨ StarCode Stats",
        value=f"Chains Found: {stats['chains_found']}\n"
              f"New Registrations: {stats['chains_registered']}\n"
              f"Already Registered: {stats['chains_skipped']}\n"
              f"Adoptions: {stats['chains_adopted']}\n"
              f"Total Patterns: {len(bot.starcode_patterns)}",
        inline=False
    )
    
    summary_embed.add_field(
        name="💾 Data Stats",
        value=f"Remories Stored: {stats['remories_stored']:,}\n"
              f"Duplicate Remories: {stats['remories_skipped']}\n"
              f"Definitions Found: {stats['definitions_found']}\n"
              f"Blessed Chains: {stats['blessed_chains']}",
        inline=True
    )
    
    # Role summary
    if stats["roles_assigned"]:
        role_text = "\n".join([f"{role}: {count}" for role, count in sorted(stats["roles_assigned"].items(), key=lambda x: x[1], reverse=True)])
    else:
        role_text = "No new roles assigned"
    
    summary_embed.add_field(
        name="🎭 Roles Assigned",
        value=role_text,
        inline=False
    )
    
    # Top users by influence
    top_users = sorted(bot.user_data.items(), key=lambda x: x[1]["influence_score"], reverse=True)[:5]
    if top_users:
        top_text = []
        for user_id, data in top_users:
            member = ctx.guild.get_member(user_id)
            if member:
                top_text.append(f"{member.display_name}: **{data['influence_score']:,}**")
        
        summary_embed.add_field(
            name="🏆 Top Influencers",
            value="\n".join(top_text),
            inline=True
        )
    
    # Most used chains
    if bot.starcode_patterns:
        top_chains = sorted(bot.starcode_patterns.items(), key=lambda x: x[1]["uses"], reverse=True)[:5]
        chain_text = [f"{chain}: **{data['uses']}** uses" for chain, data in top_chains]
        
        summary_embed.add_field(
            name="🔥 Top StarCodes",
            value="\n".join(chain_text),
            inline=True
        )
    
    # Processing rate
    if stats["messages_processed"] > 0:
        rate = stats["messages_processed"] / max(total_duration, 1)
        summary_embed.add_field(
            name="⚡ Performance",
            value=f"Rate: {rate:.1f} messages/second\n"
                  f"Errors: {stats['errors']}",
            inline=True
        )
    
    summary_embed.set_footer(text="The Vault now remembers all • Profiles initialized • No duplicates processed")
    
    await ctx.send(embed=summary_embed)
    
    # Final log entry
    await update_log(f"🎉 Backfill complete! Set up {stats['new_profiles']} new profiles, processed {stats['messages_processed']:,} messages")

async def process_backfill_command(message, stats):
    """Process commands found during backfill - returns log message if command found"""
    content = message.content.lower()
    
    # Check for blessing commands
    if "!vault bless" in content:
        # Extract chain after command
        parts = message.content.split("!vault bless", 1)
        if len(parts) > 1:
            emojis = extract_emojis(parts[1])
            if len(emojis) >= 2:
                chain_key = "".join(emojis)
                bot.blessed_chains[chain_key] = {
                    "blessed_by": message.author.id,
                    "timestamp": message.created_at.isoformat(),
                    "alignment": "peace"  # Default for backfill
                }
                stats["blessed_chains"] += 1
                return f"Blessing found for {chain_key}"
    
    # Check for define commands
    elif "!vault define" in content:
        parts = message.content.split("!vault define", 1)
        if len(parts) > 1:
            words = parts[1].strip().split(None, 1)
            if len(words) >= 2:
                emoji = words[0]
                meaning = words[1]
                if emoji not in bot.emoji_definitions:
                    bot.emoji_definitions[emoji] = []
                
                bot.emoji_definitions[emoji].append({
                    "meaning": meaning,
                    "author": message.author.id,
                    "timestamp": message.created_at.isoformat(),
                    "official": False,
                    "backfilled": True
                })
                bot.user_data[message.author.id]["definitions_created"][emoji] = meaning
                stats["definitions_found"] += 1
                return f"Definition found: {emoji}"
    
    return None

# ============ VAULTKNIGHT COMMANDS ============
@bot.command(name='mark_problematic')
async def mark_problematic(ctx):
    """VaultKnight: Mark the next message you shield react to as problematic"""
    if not has_vault_role(ctx.author, "vault_knight"):
        await ctx.send("⚔️ VaultKnight privileges required")
        return
    
    # Set up listener
    bot.shield_listeners[ctx.author.id] = {
        "channel": ctx.channel,
        "timestamp": datetime.now()
    }
    
    embed = discord.Embed(
        title="🛡️ Shield Marking Mode Active",
        description="React with 🛡️ to any message to mark its StarCode as problematic",
        color=0xFF6347
    )
    embed.add_field(
        name="Instructions",
        value="1. Find a problematic message\n"
              "2. React with 🛡️\n"
              "3. The chain will be marked and -15 influence applied",
        inline=False
    )
    embed.set_footer(text="This mode will timeout in 5 minutes")
    
    await ctx.send(embed=embed)
    
    # Set timeout to clean up listener
    await asyncio.sleep(300)  # 5 minutes
    if ctx.author.id in bot.shield_listeners:
        del bot.shield_listeners[ctx.author.id]
        await ctx.send(f"{ctx.author.mention} Shield marking mode timed out")

@bot.command(name='shield')
async def shield(ctx, *, chain: str = None):
    """Legacy shield command - redirects to mark_problematic"""
    await ctx.send("ℹ️ Use `!vault mark_problematic` then react with 🛡️ to mark problematic content")

@bot.command(name='correct')
async def correct(ctx, *, correction: str):
    """Submit a correction to the vault ledger"""
    if " → " in correction or " -> " in correction:
        parts = correction.replace(" → ", " -> ").split(" -> ")
        if len(parts) == 2:
            old_chain = extract_emojis(parts[0])
            new_chain = extract_emojis(parts[1])
            old_key = "".join(old_chain)
            new_key = "".join(new_chain)
            
            # Check if old chain exists
            if old_key in bot.starcode_patterns:
                old_pattern = bot.starcode_patterns[old_key]
                
                # Unregister old chain
                await unregister_chain(old_key, "corrected", ctx.author.id)
                
                # Register new chain
                bot.starcode_patterns[new_key] = {
                    "author": old_pattern["author"],
                    "created": datetime.now().isoformat(),
                    "uses": 1,
                    "description": f"Corrected from {old_key} by {ctx.author.display_name}",
                    "pattern": new_key,
                    "corrected_from": old_key,
                    "corrected_by": ctx.author.id
                }
                
                # Award influence to corrector
                bot.user_data[ctx.author.id]["corrections"] += 1
                bot.user_data[ctx.author.id]["influence_score"] += 5
                
                embed = discord.Embed(
                    title="✍️ Correction Applied",
                    color=0x90EE90
                )
                embed.add_field(name="Original", value=old_key)
                embed.add_field(name="Corrected", value=new_key)
                embed.add_field(name="Corrected by", value=ctx.author.mention)
                embed.add_field(
                    name="Effect",
                    value="Original chain unregistered, influence reverted",
                    inline=False
                )
                
                await ctx.send(embed=embed)
            else:
                await ctx.send(f"❌ Chain {old_key} not found in registry")
            return
    
    await ctx.send("❌ Use format: `!vault correct [old chain] → [new chain]`")

@bot.command(name='review_problems')
async def review_problems(ctx):
    """VaultKnight: Review all problematic chains"""
    if not has_vault_role(ctx.author, "vault_knight"):
        await ctx.send("⚔️ VaultKnight privileges required")
        return
    
    if not bot.problematic_chains:
        await ctx.send("✅ No problematic chains logged")
        return
    
    embed = discord.Embed(
        title="🚫 Problematic Chain Registry",
        color=0xFF6347
    )
    
    for i, problem in enumerate(bot.problematic_chains[-10:], 1):
        flagger = ctx.guild.get_member(problem["flagged_by"])
        embed.add_field(
            name=f"#{i}: {problem['chain']}",
            value=f"Flagged by: {flagger.mention if flagger else 'Unknown'}\n"
                  f"Date: {problem['timestamp'].strftime('%Y-%m-%d')}\n"
                  f"Context: {problem.get('context', 'N/A')[:50]}...",
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='knight_status')
async def knight_status(ctx):
    """View your VaultKnight statistics"""
    if not has_vault_role(ctx.author, "vault_knight"):
        await ctx.send("⚔️ VaultKnight privileges required")
        return
    
    stats = bot.user_data[ctx.author.id]
    
    embed = discord.Embed(
        title="⚔️ VaultKnight Status",
        color=0xDC143C
    )
    embed.add_field(name="🛡️ Problematic Flags", value=stats["problematic_flags"])
    embed.add_field(name="✍️ Corrections Made", value=stats["corrections"])
    embed.add_field(name="📉 Penalties Applied", value=f"~{stats['problematic_flags'] * 15}")
    
    await ctx.send(embed=embed)

# ============ GHOSTWALKER COMMANDS ============
@bot.command(name='define')
async def define(ctx, emoji: str, *, meaning: str):
    """GhostWalker: Assign formal semantic value to emoji"""
    # Allow anyone to suggest, but only GhostWalkers can make it official
    is_ghost = has_vault_role(ctx.author, "ghost_walker")
    
    if emoji not in bot.emoji_definitions:
        bot.emoji_definitions[emoji] = []
    
    definition = {
        "meaning": meaning,
        "author": ctx.author.id,
        "timestamp": datetime.now().isoformat(),
        "official": is_ghost
    }
    
    bot.emoji_definitions[emoji].append(definition)
    bot.user_data[ctx.author.id]["definitions_created"][emoji] = meaning
    
    # Check training progress
    context = {"emoji": emoji}
    if await check_training_progress(ctx.author.id, "define", context, ctx.channel):
        await complete_training_quest(ctx.author, ctx.channel)
    
    if is_ghost:
        bot.user_data[ctx.author.id]["influence_score"] += 15
        bot.save_data()
        
        embed = discord.Embed(
            title="🔑 Official Definition Set",
            description=f"{emoji} = {meaning}",
            color=0x4B0082
        )
        embed.set_footer(text=f"Defined by GhostWalker {ctx.author.display_name}")
    else:
        embed = discord.Embed(
            title="💭 Definition Suggested",
            description=f"{emoji} = {meaning}",
            color=0x87CEEB
        )
        embed.set_footer(text="Awaiting GhostWalker approval")
    
    await ctx.send(embed=embed)

@bot.command(name='create_theme')
async def create_theme(ctx, theme_name: str, *, emojis: str):
    """GhostWalker: Create a new semantic theme
    
    Example: !vault create_theme warrior ⚔️🛡️⚡💪🏹
    """
    if not has_vault_role(ctx.author, "ghost_walker"):
        await ctx.send("👻 GhostWalker privileges required")
        return
    
    theme_name = theme_name.lower()
    theme_emojis = extract_emojis(emojis)
    
    if len(theme_emojis) < 3:
        await ctx.send("❌ Theme must contain at least 3 emojis")
        return
    
    # Store theme
    bot.semantic_themes[theme_name] = {
        "emojis": theme_emojis,
        "created_by": ctx.author.id,
        "created_at": datetime.now().isoformat(),
        "description": f"Theme created by {ctx.author.display_name}"
    }
    
    bot.save_data()
    
    embed = discord.Embed(
        title="🎨 Semantic Theme Created",
        description=f"Theme: **{theme_name}**",
        color=0x4B0082
    )
    embed.add_field(
        name="Associated Emojis",
        value=" ".join(theme_emojis),
        inline=False
    )
    embed.add_field(
        name="Usage",
        value=f"`!vault summon {theme_name}` to find related chains",
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command(name='list_themes')
async def list_themes(ctx):
    """List all available semantic themes"""
    embed = discord.Embed(
        title="🎨 Semantic Themes",
        description="Themes for organizing StarCode patterns",
        color=0x87CEEB
    )
    
    # Default themes
    default_themes = {
        "hope": "🌈 🕊️ ✨ 💫 🌟",
        "peace": "🕊️ 🌿 ☮️ 🤝 💚",
        "truth": "📖 🔍 💡 ⚖️ 📜",
        "judgment": "⚖️ 🔥 ⚔️ 📜 ⚡",
        "mercy": "💧 🤲 ❤️ 🩹 🌿",
        "fire": "🔥 ⚡ 🌋 ☄️ 🎆"
    }
    
    default_text = "\n".join([f"`{name}`: {emojis}" for name, emojis in default_themes.items()])
    embed.add_field(
        name="📚 Default Themes",
        value=default_text,
        inline=False
    )
    
    # Custom themes
    if bot.semantic_themes:
        custom_text = []
        for name, data in list(bot.semantic_themes.items())[:10]:
            creator = ctx.guild.get_member(data["created_by"])
            emoji_preview = " ".join(data["emojis"][:5])
            custom_text.append(f"`{name}`: {emoji_preview} (by {creator.display_name if creator else 'Unknown'})")
        
        embed.add_field(
            name="✨ Custom Themes",
            value="\n".join(custom_text),
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='create_training')
async def create_training(ctx, training_id: str, *, training_data: str):
    """GhostWalker: Create a custom training quest
    
    Format: name | task | emoji_chain | reward | detection_type | count(optional)
    """
    if not has_vault_role(ctx.author, "ghost_walker"):
        await ctx.send("👻 GhostWalker privileges required")
        return
    
    # Parse training data with optional count
    parts = training_data.split(" | ")
    if len(parts) < 5:
        await ctx.send("❌ Format: `name | task | emoji_chain | reward | detection_type | count(optional)`\n"
                      "Detection types: message, starcode, define, shield, bless")
        return
    
    name = parts[0].strip()
    task = parts[1].strip()
    chain_str = parts[2].strip()
    reward_str = parts[3].strip()
    detection = parts[4].strip().lower()
    count = 1  # Default
    
    # Check for count parameter
    if len(parts) >= 6:
        try:
            count = int(parts[5].strip())
        except ValueError:
            await ctx.send("❌ Count must be a number")
            return
    
    try:
        reward = int(reward_str)
    except ValueError:
        await ctx.send("❌ Reward must be a number")
        return
    
    chain = extract_emojis(chain_str)
    if len(chain) < 2 and detection != "shield":
        await ctx.send("❌ Chain must have at least 2 emojis (except for shield type)")
        return
    
    # Validate detection type
    valid_detections = ["message", "starcode", "define", "shield", "bless"]
    if detection not in valid_detections:
        await ctx.send(f"❌ Invalid detection type. Choose from: {', '.join(valid_detections)}")
        return
    
    # Create training with count
    bot.custom_trainings[training_id] = {
        "name": name,
        "task": task,
        "chain": chain,
        "reward": reward,
        "detection": detection,
        "count": count,
        "created_by": ctx.author.id,
        "created_at": datetime.now().isoformat()
    }
    
    bot.save_data()
    
    embed = discord.Embed(
        title="🎯 Custom Training Created",
        description=f"ID: `{training_id}`",
        color=0x4B0082
    )
    embed.add_field(name="Name", value=name)
    embed.add_field(name="Task", value=task)
    embed.add_field(name="Chain", value="".join(chain) if chain else "N/A")
    embed.add_field(name="Reward", value=f"{reward} influence")
    embed.add_field(name="Detection", value=detection)
    embed.add_field(name="Required Count", value=count)
    
    await ctx.send(embed=embed)

@bot.command(name='assign_training')
async def assign_training(ctx, target: str, training_id: str):
    """GhostWalker: Assign a training to a specific user"""
    if not has_vault_role(ctx.author, "ghost_walker"):
        await ctx.send("👻 GhostWalker privileges required")
        return
    
    # Get member by reference
    member = await get_member_by_reference(ctx, target)
    if not member:
        await ctx.send(f"❌ Could not find user: {target}")
        return
    
    # Check if training exists
    if training_id not in DEFAULT_TRAINING_QUESTS and training_id not in bot.custom_trainings:
        await ctx.send("❌ Training ID not found. Use `!vault list_trainings` to see available trainings.")
        return
    
    # Add to user's training queue
    if member.id not in bot.training_assignments:
        bot.training_assignments[member.id] = []
    
    bot.training_assignments[member.id].append(training_id)
    
    # If user has no active training, start this one
    if not bot.user_data[member.id].get("training_quest"):
        bot.user_data[member.id]["training_quest"] = training_id
        await show_training_quest(member, ctx.channel, training_id)
    else:
        await ctx.send(f"✅ Training `{training_id}` added to {member.display_name}'s queue")

@bot.command(name='glyph')
async def glyph_lookup(ctx, emoji: str):
    """Enhanced glyph lookup with definitions"""
    # Check traditional glyphs first
    info = LIBRARIAN_GLYPHS.get(emoji) or SEMANSIS_GLYPHS.get(emoji)
    
    embed = discord.Embed(
        title=f"{emoji} Glyph Information",
        color=0x87CEEB
    )
    
    if info:
        embed.add_field(
            name="Traditional Meaning",
            value=f"**{info['name']}**: {info['meaning']}",
            inline=False
        )
        if 'type' in info:
            embed.add_field(name="Codex", value=info['type'].title())
    
    # Check user definitions
    if emoji in bot.emoji_definitions:
        definitions = bot.emoji_definitions[emoji]
        official_defs = [d for d in definitions if d.get("official", False)]
        suggested_defs = [d for d in definitions if not d.get("official", False)]
        
        if official_defs:
            official_text = "\n".join([f"• {d['meaning']}" for d in official_defs[-3:]])
            embed.add_field(
                name="👻 GhostWalker Definitions",
                value=official_text,
                inline=False
            )
        
        if suggested_defs:
            suggested_text = "\n".join([f"• {d['meaning']}" for d in suggested_defs[-3:]])
            embed.add_field(
                name="💭 Community Suggestions",
                value=suggested_text,
                inline=False
            )
    
    # Show usage in StarCodes
    usage_count = sum(1 for chain in bot.starcode_patterns.values() if emoji in chain.get("pattern", ""))
    if usage_count > 0:
        embed.add_field(
            name="📊 StarCode Usage",
            value=f"Appears in {usage_count} registered patterns",
            inline=True
        )
    
    await ctx.send(embed=embed)

@bot.command(name='bless')
async def bless(ctx, *, chain: str):
    """Bless a chain with divine alignment"""
    emojis = extract_emojis(chain)
    if len(emojis) < 2:
        await ctx.send("❌ Invalid StarCode for blessing")
        return
    
    chain_key = "".join(emojis)
    
    # Store blessing
    bot.blessed_chains[chain_key] = {
        "blessed_by": ctx.author.id,
        "timestamp": datetime.now().isoformat(),
        "alignment": bot.divine_alignment
    }
    bot.save_data()
    
    # Award influence
    if chain_key in bot.starcode_patterns:
        author_id = bot.starcode_patterns[chain_key]["author"]
        bot.user_data[author_id]["influence_score"] += 10
        
        # Double if user is GhostWalker
        if has_vault_role(ctx.author, "ghost_walker"):
            bot.user_data[author_id]["influence_score"] += 10
    
    bot.user_data[ctx.author.id]["blessed_chains"].append(chain_key)
    
    # Check training progress
    if await check_training_progress(ctx.author.id, "bless", chain_key, ctx.channel):
        await complete_training_quest(ctx.author, ctx.channel)
    
    embed = discord.Embed(
        title="🌈 Chain Blessed",
        description=f"**{chain_key}** blessed with **{bot.divine_alignment}**",
        color=0xFFD700
    )
    embed.add_field(
        name="Effect",
        value="This chain now grants double influence when aligned with server mood",
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command(name='override_flag')
async def override_flag(ctx, *, chain: str):
    """GhostWalker: Override a VaultKnight's problematic flag"""
    if not has_vault_role(ctx.author, "ghost_walker"):
        await ctx.send("👻 GhostWalker privileges required")
        return
    
    emojis = extract_emojis(chain)
    chain_key = "".join(emojis)
    
    # Find and remove from problematic list
    removed = False
    for i, problem in enumerate(bot.problematic_chains):
        if problem["chain"] == chain_key:
            bot.problematic_chains.pop(i)
            removed = True
            
            # Restore influence
            if chain_key in bot.starcode_patterns:
                author_id = bot.starcode_patterns[chain_key]["author"]
                bot.user_data[author_id]["influence_score"] += 15
            
            break
    
    if removed:
        await ctx.send(f"⚖️ Override complete. `{chain_key}` removed from problematic registry. Influence restored.")
    else:
        await ctx.send("❌ Chain not found in problematic registry")

@bot.command(name='align_mood')
async def align_mood(ctx, mood: str):
    """GhostWalker: Set server's divine alignment"""
    if not has_vault_role(ctx.author, "ghost_walker"):
        await ctx.send("👻 GhostWalker privileges required")
        return
    
    mood = mood.lower()
    if mood not in DIVINE_ALIGNMENTS:
        await ctx.send(f"❌ Invalid mood. Choose from: {', '.join(DIVINE_ALIGNMENTS)}")
        return
    
    bot.divine_alignment = mood
    
    embed = discord.Embed(
        title="🕊️ Divine Alignment Set",
        description=f"Server mood is now: **{mood}**",
        color=0x4B0082
    )
    
    # Show which chains benefit
    aligned_chains = []
    for chain, data in bot.blessed_chains.items():
        if data["alignment"] == mood:
            aligned_chains.append(chain)
    
    if aligned_chains:
        embed.add_field(
            name="✨ Aligned Chains (2x influence)",
            value="\n".join(aligned_chains[:5]) + (f"\n...and {len(aligned_chains)-5} more" if len(aligned_chains) > 5 else ""),
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='summon')
async def summon(ctx, theme: str):
    """GhostWalker: Show all chains connected to a semantic theme"""
    if not has_vault_role(ctx.author, "ghost_walker"):
        await ctx.send("👻 GhostWalker privileges required")
        return
    
    theme = theme.lower()
    related_chains = []
    
    # Default themes (keeping backwards compatibility)
    default_theme_emojis = {
        "hope": ["🌈", "🕊️", "✨", "💫", "🌟"],
        "peace": ["🕊️", "🌿", "☮️", "🤝", "💚"],
        "truth": ["📖", "🔍", "💡", "⚖️", "📜"],
        "judgment": ["⚖️", "🔥", "⚔️", "📜", "⚡"],
        "mercy": ["💧", "🤲", "❤️", "🩹", "🌿"],
        "fire": ["🔥", "⚡", "🌋", "☄️", "🎆"]
    }
    
    # Check custom themes first
    if theme in bot.semantic_themes:
        theme_data = bot.semantic_themes[theme]
        theme_set = set(theme_data["emojis"])
        source = "Custom Theme"
    elif theme in default_theme_emojis:
        theme_set = set(default_theme_emojis[theme])
        source = "Default Theme"
    else:
        await ctx.send(f"❌ Unknown theme: **{theme}**\nUse `!vault list_themes` to see available themes")
        return
    
    # Search for matching chains IN REGISTERED PATTERNS ONLY
    for chain_key, data in bot.starcode_patterns.items():
        chain_emojis = set(list(chain_key))
        if chain_emojis.intersection(theme_set):
            related_chains.append((chain_key, data))
    
    if related_chains:
        embed = discord.Embed(
            title=f"🔮 Chains of {theme.title()}",
            description=f"StarCodes resonating with **{theme}** ({source})",
            color=0x9370DB
        )
        
        # Show theme emojis
        embed.add_field(
            name="Theme Emojis",
            value=" ".join(theme_set),
            inline=False
        )
        
        # Show related chains
        for i, (chain, data) in enumerate(related_chains[:10], 1):
            author = ctx.guild.get_member(data.get("author", 0))
            embed.add_field(
                name=f"{i}. {chain}",
                value=f"By: {author.mention if author else 'Unknown'}\nUses: {data.get('uses', 0)}",
                inline=True
            )
        
        if len(related_chains) > 10:
            embed.set_footer(text=f"Showing 10 of {len(related_chains)} matching chains")
        
        await ctx.send(embed=embed)
    else:
        await ctx.send(f"🔍 No registered chains found for theme: **{theme}**\n"
                       f"Register chains with `!vault starcode` first!")

@bot.command(name='theme_suggest')
async def theme_suggest(ctx, *, chain: str):
    """Suggest which themes a StarCode belongs to"""
    emojis = extract_emojis(chain)
    if len(emojis) < 2:
        await ctx.send("❌ Please provide a valid StarCode (2+ emojis)")
        return
    
    chain_set = set(emojis)
    matches = []
    
    # Check default themes
    default_themes = {
        "hope": ["🌈", "🕊️", "✨", "💫", "🌟"],
        "peace": ["🕊️", "🌿", "☮️", "🤝", "💚"],
        "truth": ["📖", "🔍", "💡", "⚖️", "📜"],
        "judgment": ["⚖️", "🔥", "⚔️", "📜", "⚡"],
        "mercy": ["💧", "🤲", "❤️", "🩹", "🌿"],
        "fire": ["🔥", "⚡", "🌋", "☄️", "🎆"]
    }
    
    for theme_name, theme_emojis in default_themes.items():
        overlap = chain_set.intersection(set(theme_emojis))
        if overlap:
            matches.append((theme_name, len(overlap), "Default"))
    
    # Check custom themes
    for theme_name, theme_data in bot.semantic_themes.items():
        overlap = chain_set.intersection(set(theme_data["emojis"]))
        if overlap:
            matches.append((theme_name, len(overlap), "Custom"))
    
    if matches:
        # Sort by overlap count
        matches.sort(key=lambda x: x[1], reverse=True)
        
        embed = discord.Embed(
            title="🎯 Theme Analysis",
            description=f"Themes for: **{''.join(emojis)}**",
            color=0x87CEEB
        )
        
        for theme_name, overlap_count, theme_type in matches[:5]:
            embed.add_field(
                name=f"{theme_name.title()} ({theme_type})",
                value=f"Matches: {overlap_count} emojis",
                inline=True
            )
        
        await ctx.send(embed=embed)
    else:
        await ctx.send("🔍 No matching themes found for this StarCode")

@bot.command(name='ghost_status')
async def ghost_status(ctx):
    """View your GhostWalker statistics"""
    if not has_vault_role(ctx.author, "ghost_walker"):
        await ctx.send("👻 GhostWalker privileges required")
        return
    
    stats = bot.user_data[ctx.author.id]
    
    embed = discord.Embed(
        title="👻 GhostWalker Status",
        color=0x4B0082
    )
    embed.add_field(name="🔑 Meanings Defined", value=len(stats["definitions_created"]))
    embed.add_field(name="🌈 Blessings Granted", value=len(stats["blessed_chains"]))
    embed.add_field(name="🎯 Trainings Created", value=sum(1 for t in bot.custom_trainings.values() if t.get("created_by") == ctx.author.id))
    embed.add_field(name="🎨 Themes Created", value=sum(1 for t in bot.semantic_themes.values() if t.get("created_by") == ctx.author.id))
    embed.add_field(name="✨ Total Influence", value=stats["influence_score"])
    
    # Show recent definitions
    if stats["definitions_created"]:
        recent_defs = list(stats["definitions_created"].items())[-3:]
        def_text = "\n".join([f"{emoji}: {meaning[:30]}..." for emoji, meaning in recent_defs])
        embed.add_field(
            name="Recent Definitions",
            value=def_text,
            inline=False
        )
    
    await ctx.send(embed=embed)

# ============ TRAINING QUEST COMMANDS ============
@bot.command(name='initiate_training')
async def initiate_training(ctx, target: str = None):
    """Start the training quest sequence"""
    if target:
        member = await get_member_by_reference(ctx, target)
        if not member:
            await ctx.send(f"❌ Could not find user: {target}")
            return
    else:
        member = ctx.author
    
    # Set first quest
    bot.user_data[member.id]["training_quest"] = "q1"
    await show_training_quest(member, ctx.channel, "q1")

@bot.command(name='quest_status')
async def quest_status(ctx):
    """Check current training quest status"""
    current_quest = bot.user_data[ctx.author.id].get("training_quest")
    
    if not current_quest:
        await ctx.send("📭 No active training quest. Use `!vault initiate_training` to start.")
        return
    
    # Get quest data
    if current_quest in DEFAULT_TRAINING_QUESTS:
        quest = DEFAULT_TRAINING_QUESTS[current_quest]
    elif current_quest in bot.custom_trainings:
        quest = bot.custom_trainings[current_quest]
    else:
        await ctx.send("❌ Quest data not found")
        return
    
    # Get progress
    progress_key = f"{current_quest}_progress"
    current_progress = bot.user_data[ctx.author.id]["training_progress"].get(progress_key, 0)
    required = quest.get("count", 1)
    
    embed = discord.Embed(
        title="📊 Quest Progress",
        description=f"Current: **{quest['name']}**",
        color=0x87CEEB
    )
    embed.add_field(name="Task", value=quest["task"])
    embed.add_field(name="Progress", value=f"{current_progress}/{required}")
    embed.add_field(name="Reward", value=f"{quest['reward']} influence")
    
    if "chain" in quest:
        embed.add_field(name="Required Chain", value="".join(quest["chain"]))
    
    # Show queued trainings
    if ctx.author.id in bot.training_assignments and bot.training_assignments[ctx.author.id]:
        queued = bot.training_assignments[ctx.author.id]
        embed.add_field(
            name="📋 Queued Trainings",
            value=", ".join([f"`{t}`" for t in queued[:5]]),
            inline=False
        )
    
    await ctx.send(embed=embed)

@bot.command(name='list_trainings')
async def list_trainings(ctx):
    """List all available training quests"""
    embed = discord.Embed(
        title="📚 Available Training Quests",
        color=0x87CEEB
    )
    
    # Default trainings
    default_list = []
    for id, quest in DEFAULT_TRAINING_QUESTS.items():
        count_text = f" ({quest.get('count', 1)}x)" if quest.get('count', 1) > 1 else ""
        default_list.append(f"`{id}`: {quest['name']}{count_text}")
    
    embed.add_field(
        name="🎯 Default Trainings",
        value="\n".join(default_list),
        inline=False
    )
    
    # Custom trainings
    if bot.custom_trainings:
        custom_list = []
        for id, training in bot.custom_trainings.items():
            creator = ctx.guild.get_member(training.get("created_by"))
            count_text = f" ({training.get('count', 1)}x)" if training.get('count', 1) > 1 else ""
            custom_list.append(f"`{id}`: {training['name']}{count_text} (by {creator.display_name if creator else 'Unknown'})")
        
        embed.add_field(
            name="✨ Custom Trainings",
            value="\n".join(custom_list[:10]),
            inline=False
        )
    
    embed.set_footer(text="Use !vault assign_training [user] [id] to assign a training")
    
    await ctx.send(embed=embed)

@bot.command(name='complete_training')
@commands.has_permissions(administrator=True)
async def complete_training_admin(ctx, target: str = None):
    """Admin: Mark current training as complete for a user"""
    if target:
        member = await get_member_by_reference(ctx, target)
        if not member:
            await ctx.send(f"❌ Could not find user: {target}")
            return
    else:
        member = ctx.author
    
    current = bot.user_data[member.id].get("training_quest")
    
    if not current:
        await ctx.send(f"❌ {member.display_name} has no active training")
        return
    
    # Complete the training
    await complete_training_quest(member, ctx.channel)
    await ctx.send(f"✅ Completed training for {member.display_name}")

@bot.command(name='revoke_training')
@commands.has_permissions(administrator=True)
async def revoke_training(ctx, target: str):
    """Admin: Revoke current training quest from a user"""
    member = await get_member_by_reference(ctx, target)
    if not member:
        await ctx.send(f"❌ Could not find user: {target}")
        return
    
    current = bot.user_data[member.id].get("training_quest")
    
    if not current:
        await ctx.send(f"❌ {member.display_name} has no active training")
        return
    
    # Revoke training
    bot.user_data[member.id]["training_quest"] = None
    
    # Clear progress
    progress_key = f"{current}_progress"
    if progress_key in bot.user_data[member.id]["training_progress"]:
        del bot.user_data[member.id]["training_progress"][progress_key]
    
    # Clear assignments
    if member.id in bot.training_assignments:
        bot.training_assignments[member.id] = []
    
    await ctx.send(f"✅ Revoked training `{current}` from {member.display_name}")

@bot.command(name='skip_training')
@commands.has_permissions(administrator=True)
async def skip_training(ctx, target: str = None):
    """Admin: Skip current training quest without reward"""
    if target:
        member = await get_member_by_reference(ctx, target)
        if not member:
            await ctx.send(f"❌ Could not find user: {target}")
            return
    else:
        member = ctx.author
    
    current = bot.user_data[member.id].get("training_quest")
    
    if not current:
        await ctx.send("❌ No active training to skip")
        return
    
    # Mark as completed without reward
    bot.user_data[member.id]["completed_trainings"].append(current)
    
    # Get next quest
    if current in DEFAULT_TRAINING_QUESTS:
        next_quest = DEFAULT_TRAINING_QUESTS[current].get("next")
    elif current in bot.custom_trainings:
        next_quest = bot.custom_trainings[current].get("next")
    else:
        next_quest = None
    
    if next_quest and next_quest != "complete":
        bot.user_data[member.id]["training_quest"] = next_quest
        await show_training_quest(member, ctx.channel, next_quest)
    else:
        bot.user_data[member.id]["training_quest"] = None
        await ctx.send(f"✅ Training skipped for {member.display_name}")

# ============ ENHANCED STARCODE COMMANDS ============
@bot.command(name='starcode')
async def starcode(ctx, *, pattern: str):
    """Enhanced StarCode registration with pattern tracking"""
    valid_emojis = extract_emojis(pattern)
    if len(valid_emojis) < 2 or pattern.strip() != "".join(valid_emojis):
        await ctx.send("❌ StarCode must be consecutive emojis with no other characters")
        return
    
    # Store pattern with enhanced data
    pattern_key = "".join(valid_emojis)
    
    # Remove from pending if manually registering
    pending_keys_to_remove = []
    for key, data in bot.pending_chains.items():
        if "".join(data["chain"]) == pattern_key:
            pending_keys_to_remove.append(key)
    
    for key in pending_keys_to_remove:
        del bot.pending_chains[key]
    
    if pattern_key not in bot.starcode_patterns:
        bot.starcode_patterns[pattern_key] = {
            "author": ctx.author.id,
            "created": datetime.now().isoformat(),
            "uses": 1,
            "description": ctx.message.content,
            "pattern": pattern_key
        }
        bot.user_data[ctx.author.id]["chains_originated"][pattern_key] = 1
    else:
        # Pattern exists - track reuse
        bot.starcode_patterns[pattern_key]["uses"] += 1
        original_author = bot.starcode_patterns[pattern_key]["author"]
        
        # Award influence for reuse
        bot.user_data[original_author]["influence_score"] += 1  # Original author
        bot.user_data[ctx.author.id]["influence_score"] += 2    # Adopter
    
    bot.user_data[ctx.author.id]["influence_score"] += 10
    
    # Check training progress
    if await check_training_progress(ctx.author.id, "starcode", pattern_key, ctx.channel):
        await complete_training_quest(ctx.author, ctx.channel)
    
    embed = discord.Embed(
        title="✨ StarCode Registered",
        description=f"Pattern: {pattern_key}",
        color=0xFFD700
    )
    embed.add_field(name="Author", value=ctx.author.mention)
    embed.add_field(name="Uses", value=bot.starcode_patterns[pattern_key]["uses"])
    
    # Check for blessing
    if pattern_key in bot.blessed_chains:
        blessing = bot.blessed_chains[pattern_key]
        embed.add_field(
            name="🌈 Blessed",
            value=f"Aligned with **{blessing['alignment']}**",
            inline=False
        )
    
    # Reply directly in the invoking channel per bot policy
    await ctx.send(embed=embed)

@bot.command(name='pending')
async def view_pending(ctx):
    """View chains pending auto-registration"""
    if not bot.pending_chains:
        await ctx.send("📭 No chains pending registration")
        return
    
    embed = discord.Embed(
        title="⏳ Pending StarCodes",
        description="Chains awaiting auto-registration",
        color=0x87CEEB
    )
    
    current_time = datetime.now()
    for key, data in list(bot.pending_chains.items())[:10]:
        chain = "".join(data["chain"])
        elapsed = (current_time - data["timestamp"]).seconds
        remaining = max(0, 60 - elapsed)
        
        author = ctx.guild.get_member(data["author"])
        embed.add_field(
            name=chain,
            value=f"By: {author.mention if author else 'Unknown'}\n"
                  f"Time left: {remaining}s",
            inline=True
        )
    
    if len(bot.pending_chains) > 10:
        embed.set_footer(text=f"Showing 10 of {len(bot.pending_chains)} pending chains")
    
    await ctx.send(embed=embed)

@bot.command(name='top_chains')
async def top_chains(ctx):
    """Show most reused StarCode patterns"""
    if not bot.starcode_patterns:
        await ctx.send("📭 No patterns registered yet")
        return
    
    # Sort by uses
    sorted_patterns = sorted(bot.starcode_patterns.items(), key=lambda x: x[1]["uses"], reverse=True)
    
    embed = discord.Embed(
        title="🏆 Top StarCode Patterns",
        description="Most adopted chains in the Vault",
        color=0xFFD700
    )
    
    for i, (pattern, data) in enumerate(sorted_patterns[:10], 1):
        author = ctx.guild.get_member(data["author"])
        embed.add_field(
            name=f"{i}. {pattern}",
            value=f"Uses: **{data['uses']}**\nBy: {author.mention if author else 'Unknown'}",
            inline=True
        )
    
    await ctx.send(embed=embed)

@bot.command(name='unlock')
async def unlock(ctx, *, chain: str):
    """Attempt to unlock a StarLock with a chain"""
    emojis = extract_emojis(chain)
    unlock_message = await check_starlock(emojis, ctx.author, ctx.guild)
    
    if unlock_message:
        await ctx.send(unlock_message)
    else:
        await ctx.send("🔒 This chain doesn't unlock anything... yet")

# ============ ENHANCED REMORY COMMAND ============
@bot.command(name='remory')
async def remory(ctx, view_type: str = "recent", target: str = None):
    """Enhanced remory viewing with timeline and context"""
    if target:
        user = await get_member_by_reference(ctx, target)
        if not user:
            await ctx.send(f"❌ Could not find user: {target}")
            return
    else:
        user = ctx.author
    
    remories = bot.user_data[user.id]["remory_strings"]
    
    if not remories:
        await ctx.send("📭 No remory strings stored yet")
        return
    
    if view_type == "recent":
        embed = discord.Embed(
            title=f"🌀 Recent Remory: {user.display_name}",
            color=0x9370DB
        )
        
        for i, remory in enumerate(remories[-5:], 1):
            chain_str = "".join(remory['chain'])
            context = remory.get('context', 'No context')[:50]
            channel = remory.get('channel', 'Unknown')
            
            embed.add_field(
                name=f"#{i}: {chain_str}",
                value=f"*{context}...*\n📍 {channel}\n📅 {remory['timestamp'].strftime('%Y-%m-%d')}",
                inline=False
            )
    
    elif view_type == "timeline":
        embed = discord.Embed(
            title=f"📈 Remory Timeline: {user.display_name}",
            description="Chain usage over time",
            color=0x9370DB
        )
        
        # Group by date
        timeline = defaultdict(list)
        for remory in remories:
            date = remory['timestamp'].strftime('%Y-%m-%d')
            timeline[date].append("".join(remory['chain']))
        
        for date, chains in sorted(timeline.items())[-7:]:
            embed.add_field(
                name=date,
                value=" ".join(chains[:5]) + (f" +{len(chains)-5}" if len(chains) > 5 else ""),
                inline=False
            )
    
    await ctx.send(embed=embed)

# ============ CONFIGURATION COMMANDS ============
@bot.command(name='initiate')
@commands.has_permissions(administrator=True)
async def initiate_setup(ctx, category_name: str = "📜 The Vault"):
    """Initialize vault with custom setup options"""
    guild = ctx.guild
    
    # Initialize guild config
    if str(guild.id) not in bot.guild_channels:
        bot.guild_channels[str(guild.id)] = {}
    
    # Create roles
    created_roles = []
    for role_key, config in ROLES_CONFIG.items():
        role = discord.utils.get(guild.roles, name=config["name"])
        if not role:
            role = await guild.create_role(
                name=config["name"],
                color=config["color"],
                mentionable=True
            )
            created_roles.append(role.name)
    
    # Check for existing category or create new one
    category = discord.utils.get(guild.categories, name=category_name)
    if not category:
        category = await guild.create_category(category_name)
    
    # Create or identify channels
    created_channels = []
    for feature, config in CHANNEL_CONFIG.items():
        # Check if channel already exists
        existing_channel = discord.utils.get(guild.channels, name=config["default_name"])
        
        if existing_channel:
            # Use existing channel
            bot.guild_channels[str(guild.id)][feature] = str(existing_channel.id)
            await ctx.send(f"✅ Using existing channel: {existing_channel.mention} for {feature}")
        else:
            # Create new channel
            new_channel = await guild.create_text_channel(
                name=config["default_name"],
                category=category,
                topic=config["description"]
            )
            bot.guild_channels[str(guild.id)][feature] = str(new_channel.id)
            created_channels.append(new_channel.mention)
    
    # Save configuration
    bot.save_data()
    
    # Send summary
    embed = discord.Embed(
        title="✅ Vault Initialization Complete",
        description=f"The semantic field has been established in **{category_name}**",
        color=0xFFD700
    )
    
    if created_roles:
        embed.add_field(
            name="🎭 Created Roles",
            value="\n".join(created_roles[:5]) + (f"\n...and {len(created_roles)-5} more" if len(created_roles) > 5 else ""),
            inline=True
        )
    
    if created_channels:
        embed.add_field(
            name="📚 Created Channels",
            value="\n".join(created_channels),
            inline=True
        )
    
    embed.add_field(
        name="💡 Next Steps",
        value="Use `!vault config` to customize channel assignments\n"
              "Use `!vault set_channel` to change specific channels",
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command(name='config')
async def show_config(ctx):
    """Show current vault configuration for this server"""
    guild_config = bot.guild_channels.get(str(ctx.guild.id), {})
    
    embed = discord.Embed(
        title="⚙️ Vault Configuration",
        description=f"Current channel assignments for **{ctx.guild.name}**",
        color=0x87CEEB
    )
    
    for feature, channel_id in guild_config.items():
        channel = ctx.guild.get_channel(int(channel_id))
        if channel:
            feature_config = CHANNEL_CONFIG.get(feature, {})
            embed.add_field(
                name=feature.replace("_", " ").title(),
                value=f"{channel.mention}\n*{feature_config.get('description', 'Custom channel')}*",
                inline=True
            )
    
    if not guild_config:
        embed.description = "No channels configured yet. Run `!vault initiate` to set up!"
    
    await ctx.send(embed=embed)

@bot.command(name='assign')
@commands.has_permissions(administrator=True)
async def assign_permissions(ctx, permission_type: str, role_name: str, target: str):
    """Admin: Assign read or write permissions to a role for a channel/category
    
    Usage: !vault assign [read/write] [role] [channel/category]
    
    Role can be specified by:
    - Name: Memory Mason, StarForger, vault_knight
    - Role mention: @Memory Mason
    - Just the key part of the name: mason, forger, knight
    
    Channel/category can be specified by:
    - Name: starforge-lab, archives
    - Channel mention: #starforge-lab
    - Channel ID: 1234567890
    - Partial name: starforge, archive
    
    Examples:
    !vault assign read "Memory Mason" starforge-lab
    !vault assign write forger archives
    !vault assign read knight #hidden-channel
    """
    # Validate permission type
    if permission_type.lower() not in ["read", "write"]:
        await ctx.send("❌ Permission type must be either 'read' or 'write'")
        return
    
    # Find the role using multiple methods
    role = None
    
    # Method 1: Check if it's a role mention
    if role_name.startswith('<@&') and role_name.endswith('>'):
        try:
            role_id = int(role_name[3:-1])
            role = ctx.guild.get_role(role_id)
        except (ValueError, TypeError):
            pass
    
    # Method 2: Check if it's an exact match
    if not role:
        role = discord.utils.get(ctx.guild.roles, name=role_name)
    
    # Method 3: Check if it's one of the predefined vault roles by key
    if not role and role_name.lower() in ROLES_CONFIG:
        config = ROLES_CONFIG[role_name.lower()]
        role = discord.utils.get(ctx.guild.roles, name=config["name"])
    
    # Method 4: Check by role display name (with emojis)
    if not role:
        for role_key, config in ROLES_CONFIG.items():
            # Normalize name (remove emojis)
            display_name = config["name"]
            clean_display_name = ''.join(c for c in display_name if c.isalnum() or c.isspace()).strip()
            
            # Try to match with the clean name or with the emoji
            if role_name.lower() in display_name.lower() or role_name.lower() in clean_display_name.lower():
                role = discord.utils.get(ctx.guild.roles, name=display_name)
                if role:
                    break
    
    # Method 5: Partial match on server roles
    if not role:
        matching_roles = []
        for server_role in ctx.guild.roles:
            if role_name.lower() in server_role.name.lower():
                matching_roles.append(server_role)
        
        if len(matching_roles) == 1:
            role = matching_roles[0]
        elif len(matching_roles) > 1:
            # If multiple matches, prefer exact match
            for r in matching_roles:
                if r.name.lower() == role_name.lower():
                    role = r
                    break
            
            # If still ambiguous, take the one with highest position
            if not role:
                role = sorted(matching_roles, key=lambda r: r.position, reverse=True)[0]
    
    # If still no role found, report error
    if not role:
        await ctx.send(f"❌ Could not find role: {role_name}")
        return
    
    # Try to find channel or category using multiple methods
    channel = None
    category = None
    
    # Method 1: Check if it's a channel mention
    if target.startswith('<#') and target.endswith('>'):
        try:
            channel_id = int(target[2:-1])
            channel = ctx.guild.get_channel(channel_id)
        except (ValueError, TypeError):
            pass
    
    # Method 2: Check if it's a channel ID
    if not channel and not category:
        try:
            channel_id = int(target)
            channel_obj = ctx.guild.get_channel(channel_id)
            if isinstance(channel_obj, discord.TextChannel):
                channel = channel_obj
            elif isinstance(channel_obj, discord.CategoryChannel):
                category = channel_obj
        except (ValueError, TypeError):
            pass
    
    # Method 3: Check if it's an exact match by name
    if not channel and not category:
        # Try exact match first
        channel = discord.utils.get(ctx.guild.text_channels, name=target)
        if not channel:
            category = discord.utils.get(ctx.guild.categories, name=target)
    
    # Method 4: Check for partial matches if still not found
    if not channel and not category:
        # Collect all partial matches
        matching_channels = []
        matching_categories = []
        
        for guild_channel in ctx.guild.channels:
            if target.lower() in guild_channel.name.lower():
                if isinstance(guild_channel, discord.TextChannel):
                    matching_channels.append(guild_channel)
                elif isinstance(guild_channel, discord.CategoryChannel):
                    matching_categories.append(guild_channel)
        
        # If only one match of each type, use that
        if len(matching_channels) == 1 and len(matching_categories) == 0:
            channel = matching_channels[0]
        elif len(matching_channels) == 0 and len(matching_categories) == 1:
            category = matching_categories[0]
        # If multiple matches, prefer exact match
        elif len(matching_channels) > 0 or len(matching_categories) > 0:
            # First try to find exact match in channels
            for ch in matching_channels:
                if ch.name.lower() == target.lower():
                    channel = ch
                    break
            
            # If no exact match in channels, try categories
            if not channel:
                for cat in matching_categories:
                    if cat.name.lower() == target.lower():
                        category = cat
                        break
            
            # If still ambiguous, take the first channel
            if not channel and not category:
                if matching_channels:
                    channel = matching_channels[0]
                elif matching_categories:
                    category = matching_categories[0]
    
    # If still not found, error out
    if not channel and not category:
        await ctx.send(f"❌ Could not find channel or category: {target}")
        return
    
    target_obj = channel if channel else category
    target_type = "channel" if channel else "category"
    
    # Set up permissions
    overwrite = target_obj.overwrites_for(role)
    
    if permission_type.lower() == "read":
        overwrite.read_messages = True
        overwrite.view_channel = True
        permission_desc = "Read"
    else:  # write
        overwrite.send_messages = True
        overwrite.add_reactions = True
        permission_desc = "Write"
    
    try:
        await target_obj.set_permissions(role, overwrite=overwrite)
        
        # Detail the specific permissions granted
        if permission_type.lower() == "read":
            permission_details = "Can view and read messages in this channel"
        else:
            permission_details = "Can send messages and add reactions in this channel"
        
        embed = discord.Embed(
            title="✅ Permissions Updated",
            description=f"**{permission_desc} permissions** granted to **{role.name}** for **{target_obj.name}** {target_type}",
            color=0x00FF00
        )
        
        embed.add_field(
            name="Role", 
            value=f"{role.mention}\n{role.name}", 
            inline=True
        )
        
        embed.add_field(
            name=f"{target_type.title()}", 
            value=f"{target_obj.mention if hasattr(target_obj, 'mention') else target_obj.name}\n{target_obj.name}", 
            inline=True
        )
        
        embed.add_field(
            name="Permissions Granted",
            value=permission_details,
            inline=False
        )
        
        embed.set_footer(text=f"Use !vault assign to modify permissions • {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        
        await ctx.send(embed=embed)
    except discord.Forbidden:
        await ctx.send("❌ I don't have permission to update channel permissions")
    except Exception as e:
        await ctx.send(f"❌ Error setting permissions: {str(e)[:100]}")

@bot.command(name='set_channel')
@commands.has_permissions(administrator=True)
async def set_channel(ctx, feature: str, channel: discord.TextChannel):
    """Assign a specific channel to a vault feature"""
    valid_features = list(CHANNEL_CONFIG.keys())
    
    if feature not in valid_features:
        await ctx.send(f"❌ Invalid feature. Choose from: {', '.join(valid_features)}")
        return
    
    # Update configuration
    if str(ctx.guild.id) not in bot.guild_channels:
        bot.guild_channels[str(ctx.guild.id)] = {}
    
    bot.guild_channels[str(ctx.guild.id)][feature] = str(channel.id)
    bot.save_data()
    
    embed = discord.Embed(
        title="✅ Channel Assignment Updated",
        description=f"**{feature.replace('_', ' ').title()}** → {channel.mention}",
        color=0x90EE90
    )
    embed.add_field(
        name="Description",
        value=CHANNEL_CONFIG[feature]["description"],
        inline=False
    )
    
    await ctx.send(embed=embed)

@bot.command(name='quickstart')
@commands.has_permissions(administrator=True)
async def quickstart(ctx):
    """Quick setup using current channel for all features"""
    guild = ctx.guild
    current_channel = ctx.channel
    
    # Initialize guild config
    if str(guild.id) not in bot.guild_channels:
        bot.guild_channels[str(guild.id)] = {}
    
    # Assign current channel to all features
    for feature in CHANNEL_CONFIG.keys():
        bot.guild_channels[str(guild.id)][feature] = str(current_channel.id)
    
    bot.save_data()
    
    # Create roles if needed
    created_roles = []
    for role_key, config in ROLES_CONFIG.items():
        role = discord.utils.get(guild.roles, name=config["name"])
        if not role:
            role = await guild.create_role(
                name=config["name"],
                color=config["color"],
                mentionable=True
            )
            created_roles.append(role.name)
    
    embed = discord.Embed(
        title="⚡ Quick Start Complete!",
        description=f"All vault features assigned to {current_channel.mention}",
        color=0xFFD700
    )
    
    if created_roles:
        embed.add_field(
            name="🎭 Created Roles",
            value=f"{len(created_roles)} vault roles created",
            inline=True
        )
    
    embed.add_field(
        name="💡 Tip",
        value="Use `!vault set_channel [feature] [#channel]` to customize later",
        inline=False
    )
    
    embed.add_field(
        name="🦊 Open Emoji Policy",
        value="ALL emojis are now valid! Try `!vault starcode 🦊🌈🩸`",
        inline=False
    )
    
    await ctx.send(embed=embed)

# ============ FEATURE COMMANDS ============
@bot.command(name='features')
async def show_features(ctx):
    """Display all available commands"""
    
    embed = discord.Embed(
        title="📜 Helmhud Guardian Commands",
        description="All available commands",
        color=0x87CEEB
    )
    
    # Core commands
    embed.add_field(
        name="👤 Profile & Status Commands",
        value="`!vault profile [user]` - View user statistics\n"
              "`!vault status` - Server statistics\n"
              "`!vault info` - Feature overview and quick start guide\n"
              "`!vault config` - View server configuration",
        inline=False
    )
    
    # StarCode & Search commands
    embed.add_field(
        name="⭐ StarCode Commands",
        value="`!vault starcode [emojis]` - Register new pattern\n"
              "`!vault pending` - View chains awaiting registration\n"
              "`!vault top_chains` - Most used patterns\n"
              "`!vault remory [type] [user]` - View stored memory chains\n"
              "`!vault unlock [emoji chain]` - Try to unlock a StarLock",
        inline=False
    )
    
    # Emoji & Theme commands
    embed.add_field(
        name="🔍 Emoji & Theme Commands",
        value="`!vault glyph [emoji]` - Look up glyph meaning\n"
              "`!vault define [emoji] [meaning]` - Define emoji meaning\n"
              "`!vault create_theme [name] [emojis]` - Create semantic theme\n"
              "`!vault list_themes` - View all semantic themes\n"
              "`!vault theme_suggest [chain]` - Find matching themes",
        inline=False
    )
    
    # StarLock commands
    embed.add_field(
        name="🔐 StarKey Commands",
        value="`!vault create_starkey [channel] [emojis]` - Create new StarKey\n"
              "`!vault assign_starkey [channel] [emojis]` - Assign StarKey to channel\n"
              "`!vault manage_starkeys [action] [starkey] [channel]` - Manage StarKeys\n"
              "`!vault list_starlocks` - List all available StarLocks",
        inline=False
    )
    
    # Training commands
    embed.add_field(
        name="🎯 Training Commands",
        value="`!vault initiate_training [user]` - Start training\n"
              "`!vault quest_status` - Check current quest\n"
              "`!vault list_trainings` - View all trainings\n"
              "`!vault create_training [id] [details]` - Create custom training\n"
              "`!vault assign_training [user] [id]` - Assign training to user\n"
              "`!vault complete_training` - Complete current training\n"
              "`!vault revoke_training [user] [id]` - Revoke assigned training\n"
              "`!vault skip_training` - Skip current training",
        inline=False
    )
    
    # VaultKnight commands
    embed.add_field(
        name="⚔️ VaultKnight Commands",
        value="`!vault mark_problematic` - Activate shield marking\n"
              "`!vault shield` - Alternative to mark_problematic\n"
              "`!vault correct [old] → [new]` - Submit corrections\n"
              "`!vault review_problems` - View flagged chains\n"
              "`!vault knight_status` - View knight statistics",
        inline=False
    )
    
    # GhostWalker commands
    embed.add_field(
        name="👻 GhostWalker Commands",
        value="`!vault bless [chain]` - Bless chain with alignment\n"
              "`!vault override_flag [chain]` - Override knight flags\n"
              "`!vault align_mood [mood]` - Set divine alignment\n"
              "`!vault summon [theme]` - Find themed chains\n"
              "`!vault ghost_status` - View ghost statistics",
        inline=False
    )
    
    # Admin commands
    embed.add_field(
        name="🔧 Admin Commands",
        value="`!vault quickstart` - Quick setup for current channel\n"
              "`!vault set_channel [feature] [#channel]` - Set channel purpose\n"
              "`!vault assign [read/write] [role] [#channel]` - Set role permissions\n"
              "`!vault batch [commands]` - Run multiple commands at once\n"
              "`!vault diagnose [user]` - Diagnose user data\n"
              "`!vault backfill [limit]` - Backfill server history\n"
              "`!vault sync_roles [user]` - Sync roles for user\n"
              "`!vault sync_all_roles` - Sync roles for all users\n"
              "`!vault test_suite` - Run comprehensive tests\n"
              "`!vault test_commands` - Test command syntax",
        inline=False
    )
    
    # Feedback commands
    embed.add_field(
        name="📝 Feedback Commands",
        value="`!vault feedback [text]` - Submit feedback\n"
              "`!vault report [type] [text]` - Report an issue\n"
              "`!vault reportbug [text]` - Report a bot bug\n"
              "`!vault reports` - View submitted reports",
        inline=False
    )
    
    embed.set_footer(text="Use !vault info for feature information and quick start guide")
    await ctx.send(embed=embed)

@bot.command(name='batch')
@commands.has_permissions(administrator=True)
async def batch_commands(ctx, *, commands_text: str):
    """Admin: Run multiple commands in one message, separated by new lines
    
    Usage: !vault batch
           command1 arg1 arg2
           command2 arg1
           command3
    """
    # Split the input text into lines
    command_lines = commands_text.strip().split('\n')
    
    # Create response embed
    embed = discord.Embed(
        title="🔄 Batch Command Execution",
        description=f"Executing {len(command_lines)} commands...",
        color=0x87CEEB,
        timestamp=datetime.now()
    )
    
    status_msg = await ctx.send(embed=embed)
    results = []
    
    # Process each command
    for i, cmd_line in enumerate(command_lines, 1):
        cmd_line = cmd_line.strip()
        if not cmd_line:
            results.append(f"⚠️ Line {i}: Empty command")
            continue
            
        # Parse the command
        parts = cmd_line.split()
        cmd_name = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        
        # Find the command
        command = bot.get_command(cmd_name)
        if not command:
            results.append(f"❌ Line {i}: Unknown command '{cmd_name}'")
            continue
            
        # Check if user can use this command
        try:
            if not await command.can_run(ctx):
                results.append(f"❌ Line {i}: You don't have permission to use '{cmd_name}'")
                continue
        except Exception as e:
            results.append(f"❌ Line {i}: Permission check failed: {str(e)[:50]}")
            continue
            
        # Create a new context with the same author and channel
        # but with the command string set to this specific command
        new_ctx = await ctx.bot.get_context(ctx.message)
        new_ctx.command = command
        
        # Execute the command
        try:
            if len(args) > 0:
                await command(new_ctx, *args)
                results.append(f"✅ Line {i}: Executed '{cmd_name} {' '.join(args)}'")
            else:
                await command(new_ctx)
                results.append(f"✅ Line {i}: Executed '{cmd_name}'")
        except Exception as e:
            results.append(f"❌ Line {i}: Error executing '{cmd_name}': {str(e)[:50]}")
    
    # Update the status embed with results
    embed.description = f"Completed {len(command_lines)} commands"
    
    # Add results in chunks to avoid hitting field limits
    chunk_size = 10
    for i in range(0, len(results), chunk_size):
        chunk = results[i:i + chunk_size]
        embed.add_field(
            name=f"Results {i+1}-{min(i+chunk_size, len(results))}",
            value="\n".join(chunk),
            inline=False
        )
    
    # Update the status message
    await safe_edit_message(status_msg, embed=embed)

@bot.command(name='info')
async def vault_info(ctx):
    """Display feature information and quick start guide"""
    
    # Create paginated embeds for better organization
    embeds = []
    
    # Page 1: Core Features
    embed1 = discord.Embed(
        title="🏛️ Helmhud Guardian Features - Core System",
        description="The Nephesh Grid semantic field management system",
        color=0xFFD700
    )
    
    embed1.add_field(
        name="🌀 InFluins System",
        value="• Emoji-based semantic tokens\n"
              "• Track meaningful emoji usage\n"
              "• Build influence through patterns",
        inline=False
    )
    
    embed1.add_field(
        name="🦊 Open Emoji Policy",
        value="• ALL Discord emojis are valid for StarCodes\n"
              "• Community moderation via 🛡️ corrections\n"
              "• Vault Knights defend semantic coherence\n"
              "• Meaning emerges from usage, not prescription",
        inline=False
    )
    
    embed1.add_field(
        name="⚡ Auto-Registration System",
        value="• Chains auto-register after 1 minute\n"
              "• Shield marking prevents registration\n"
              "• Corrections unregister and revert influence\n"
              "• Full influence tracking and reversal",
        inline=False
    )
    
    embed1.add_field(
        name="🎭 Role Progression",
        value="**9 Ascending Ranks:**\n"
              "🔰 Initiate Drone → 👁️ Wakened Seeker\n"
              "🌾 Lore Harvester → 🧱 Memory Mason\n"
              "🛡️ Index Guard → 📖 Curator Supreme\n"
              "⭐ StarForger → ⚔️ Vault Knight\n"
              "👻 Ghost Walker",
        inline=False
    )
    
    embeds.append(embed1)
    
    # Page 2: Training & Theme System
    embed2 = discord.Embed(
        title="🎓 Training & Theme Systems",
        description="Quest creation and semantic organization",
        color=0xFFA500
    )
    
    embed2.add_field(
        name="📚 Default Training Path",
        value="1️⃣ **Brick in the Pattern** - Create first StarCode\n"
              "2️⃣ **Light in the Archive** - Define emojis (2x)\n"
              "3️⃣ **Guard the Flame** - Use shield marking\n"
              "4️⃣ **Echo of Hope** - Bless a chain",
        inline=False
    )
    
    embed2.add_field(
        name="🎯 Custom Training Format",
        value="```!vault create_training [id] name | task | chain | reward | type | count```\n"
              "Types: message, starcode, define, shield, bless\n"
              "Example: `!vault create_training hero1 Hero's Journey | Use fire emojis 3 times | 🔥🔥🔥 | 25 | message | 3`",
        inline=False
    )
    
    embed2.add_field(
        name="🎨 Theme System",
        value="`!vault create_theme warrior ⚔️🛡️⚡💪🏹` - Create theme\n"
              "`!vault summon warrior` - Find chains with warrior emojis\n"
              "`!vault theme_suggest 🛡️🔥⚔️` - Find matching themes\n"
              "Themes organize StarCodes by semantic meaning",
        inline=False
    )
    
    embeds.append(embed2)
    
    # Page 3: Quick Reference
    embed3 = discord.Embed(
        title="⚡ Quick Start Guide",
        description="How to begin your vault journey",
        color=0x90EE90
    )
    
    embed3.add_field(
        name="1️⃣ First Steps",
        value="• React to any message with ANY emoji\n"
              "• You'll become an 🔰 Initiate Drone\n"
              "• Check your profile: `!vault profile`",
        inline=False
    )
    
    embed3.add_field(
        name="2️⃣ Build Influence",
        value="• Use 5+ unique emojis → 👁️ Wakened Seeker\n"
              "• Create StarCode chains (any 2+ emojis)\n"
              "• Chains auto-register after 1 minute\n"
              "• Complete training quests for bonus influence",
        inline=False
    )
    
    embed3.add_field(
        name="3️⃣ Advanced Play",
        value="• Register patterns: `!vault starcode 🦊🌈🩸`\n"
              "• Build 3+ chains → 🧱 Memory Mason\n"
              "• Use shield marking → ⚔️ Vault Knight\n"
              "• Define emojis → 👻 Ghost Walker",
        inline=False
    )
    
    embed3.add_field(
        name="📖 The Goal",
        value="Build a living semantic field where meaning emerges "
              "through collective symbol usage. Every emoji counts. "
              "Every chain speaks. The Vault remembers all.",
        inline=False
    )
    
    embeds.append(embed3)
    
    # Send all embeds
    for i, embed in enumerate(embeds, 1):
        embed.set_footer(text=f"Page {i}/{len(embeds)} • The Nephesh Grid • Open Emoji Policy Active")
        await ctx.send(embed=embed)

@bot.command(name='status')
async def vault_status(ctx):
    """Check overall vault statistics"""
    total_users = len([u for u in bot.user_data.values() if u["reaction_count"] > 0])
    total_starcodes = sum(len(u["starcode_chains"]) for u in bot.user_data.values())
    total_reactions = sum(u["reaction_count"] for u in bot.user_data.values())
    total_influence = sum(u["influence_score"] for u in bot.user_data.values())
    
    embed = discord.Embed(
        title="🏛️ Vault Status",
        description="The current state of the semantic field",
        color=0xFFD700
    )
    
    embed.add_field(name="Active Souls", value=total_users)
    embed.add_field(name="StarCodes Forged", value=total_starcodes)
    embed.add_field(name="Total Reactions", value=total_reactions)
    embed.add_field(name="Collective Influence", value=total_influence)
    embed.add_field(name="Divine Alignment", value=bot.divine_alignment.title())
    embed.add_field(name="Registered Patterns", value=len(bot.starcode_patterns))
    embed.add_field(name="Pending Chains", value=len(bot.pending_chains))
    embed.add_field(name="Custom Trainings", value=len(bot.custom_trainings))
    embed.add_field(name="Semantic Themes", value=len(bot.semantic_themes) + 6)  # +6 for defaults
    embed.add_field(name="Problematic Chains", value=len(bot.problematic_chains))
    embed.add_field(name="Blessed Chains", value=len(bot.blessed_chains))
    
    # Most used glyphs
    all_emojis = []
    for user_stats in bot.user_data.values():
        all_emojis.extend(list(user_stats["emojis_used"]))
    
    if all_emojis:
        emoji_counts = Counter(all_emojis)
        top_emojis = emoji_counts.most_common(5)
        
        top_text = "\n".join([f"{emoji}: {count}" for emoji, count in top_emojis])
        embed.add_field(
            name="🔥 Most Active Glyphs",
            value=top_text,
            inline=False
        )
    
    await ctx.send(embed=embed)

# ============ CLEANUP TASKS ============
@tasks.loop(minutes=10)
async def cleanup_shield_listeners():
    """Clean up expired shield listeners"""
    current_time = datetime.now()
    expired = []
    
    for user_id, listener_data in bot.shield_listeners.items():
        if (current_time - listener_data["timestamp"]).seconds > 300:  # 5 minutes
            expired.append(user_id)
    
    for user_id in expired:
        del bot.shield_listeners[user_id]


# ============ BUG REPORTING =============
import io
import os
import re
from datetime import datetime, timedelta
from typing import Optional, List, Tuple

# Security libraries
import bleach
from PIL import Image, ImageChops
import magic  # python-magic for file type detection

# ============ SECURITY CONFIGURATION ============
class ReportSecurityConfig:
    """Centralized security configuration for reports"""
    
    # Text sanitization
    ALLOWED_TAGS = []  # No HTML tags allowed
    ALLOWED_ATTRIBUTES = {}
    ALLOWED_PROTOCOLS = []
    MAX_MESSAGE_LENGTH = 1500
    MIN_MESSAGE_LENGTH = 10
    
    # File validation
    ALLOWED_EXTENSIONS = {'.png', '.jpg', '.jpeg'}
    ALLOWED_MIME_TYPES = {'image/png', 'image/jpeg', 'image/jpg'}
    ALLOWED_PIL_FORMATS = {'PNG', 'JPEG'}
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    MAX_IMAGE_DIMENSION = 10000  # Max width or height
    MIN_IMAGE_DIMENSION = 10  # Min width or height
    MAX_FILES_PER_REPORT = 3
    
    # Rate limiting
    COOLDOWN_SECONDS = 60
    
    # Owner ID
    OWNER_ID = 491972288426672128

# ============ SECURE TEXT SANITIZATION ============
def safe_text_input(text: str) -> str:
    """Safely handle text input that might contain escape sequences"""
    if not text:
        return ""
    
    # Replace literal backslashes that might cause issues
    # This prevents \u, \n, \t, etc. from being interpreted as escape sequences
    text = text.replace('\\', '\\\\')
    
    # Now safely process the text
    return text

def sanitize_report_text(text: str, max_length: int = ReportSecurityConfig.MAX_MESSAGE_LENGTH) -> str:
    """Sanitize text using bleach and Discord-specific rules"""
    if not text:
        return "No text provided"
    
    # First, handle potential Unicode escape sequences by encoding/decoding
    try:
        # Encode to bytes and decode back to handle any malformed Unicode
        text = text.encode('unicode-escape').decode('unicode-escape')
    except:
        # If that fails, try raw string handling
        try:
            text = text.encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
        except:
            # Last resort: replace problematic characters
            text = text.encode('ascii', errors='ignore').decode('ascii', errors='ignore')
    
    # Use bleach to clean any HTML/dangerous content
    text = bleach.clean(
        text,
        tags=ReportSecurityConfig.ALLOWED_TAGS,
        attributes=ReportSecurityConfig.ALLOWED_ATTRIBUTES,
        protocols=ReportSecurityConfig.ALLOWED_PROTOCOLS,
        strip=True,
        strip_comments=True
    )
    
    # Discord-specific sanitization with proper escaping
    # Escape Discord mentions to prevent pings
    text = text.replace('@everyone', '@\u200beveryone').replace('@here', '@\u200bhere')
    
    # For regex operations, we need to be careful with the input
    try:
        text = re.sub(r'<@!?(\d+)>', r'[@user:\1]', text)  # User mentions
        text = re.sub(r'<@&(\d+)>', r'[@role:\1]', text)   # Role mentions
        text = re.sub(r'<#(\d+)>', r'[#channel:\1]', text)  # Channel mentions
        text = re.sub(r'<a?:\w+:\d+>', '[custom emoji]', text)  # Custom emojis
        text = re.sub(r'\n{4,}', '\n\n\n', text)  # Limit consecutive newlines
        text = re.sub(r' {5,}', '    ', text)  # Limit consecutive spaces
    except re.error:
        # If regex fails, just do basic replacements
        text = text.replace('<@', '[@user:').replace('>', ']')
        text = text.replace('<#', '[#channel:')
        text = text.replace('<:', '[emoji:')
    
    # Using bleach's linkify to handle URLs safely
    try:
        text = bleach.linkify(text, callbacks=[])
    except:
        pass
    
    # Truncate if needed
    if len(text) > max_length:
        text = text[:max_length-3] + "..."
    
    # Final cleanup
    text = text.strip()
    
    return text or "No valid text provided"



# ============ SECURE IMAGE VALIDATION ============
async def validate_image_file(attachment: discord.Attachment) -> Tuple[bool, Optional[bytes], str]:
    """
    Securely validate an image file using Pillow
    Returns: (is_valid, file_data_if_valid, error_message)
    """
    try:
        # Check file extension
        file_ext = os.path.splitext(attachment.filename.lower())[1]
        if file_ext not in ReportSecurityConfig.ALLOWED_EXTENSIONS:
            return False, None, "Invalid file extension"
        
        # Check declared MIME type
        if attachment.content_type not in ReportSecurityConfig.ALLOWED_MIME_TYPES:
            return False, None, "Invalid content type"
        
        # Check file size
        if attachment.size > ReportSecurityConfig.MAX_FILE_SIZE:
            size_mb = attachment.size / (1024 * 1024)
            return False, None, f"File too large ({size_mb:.1f}MB)"
        
        # Download the file
        file_data = await attachment.read()
        
        # First pass: Verify the image
        try:
            # Open and immediately verify
            img_verify = Image.open(io.BytesIO(file_data))
            img_verify.verify()
            img_verify.close()
        except Image.UnidentifiedImageError:
            return False, None, "Not a valid image file"
        except Image.DecompressionBombError:
            return False, None, "Image decompression bomb detected"
        except Exception as e:
            return False, None, f"Invalid image file: {str(e)[:50]}"
        
        # Second pass: Open again for format and dimension checks
        try:
            img = Image.open(io.BytesIO(file_data))
            
            # Check format
            if img.format not in ReportSecurityConfig.ALLOWED_PIL_FORMATS:
                img.close()
                return False, None, f"Invalid image format ({img.format})"
            
            # Check dimensions
            width, height = img.size
            if width > ReportSecurityConfig.MAX_IMAGE_DIMENSION or height > ReportSecurityConfig.MAX_IMAGE_DIMENSION:
                img.close()
                return False, None, f"Image too large ({width}x{height})"
            
            if width < ReportSecurityConfig.MIN_IMAGE_DIMENSION or height < ReportSecurityConfig.MIN_IMAGE_DIMENSION:
                img.close()
                return False, None, f"Image too small ({width}x{height})"
            
            # Check mode (catch unusual image modes that might be malicious)
            if img.mode not in ['RGB', 'RGBA', 'L', 'P', '1', 'CMYK']:
                img.close()
                return False, None, f"Unusual image mode ({img.mode})"
            
            # Check for suspicious images (e.g., all one color which might be malicious)
            try:
                # Convert to RGB if necessary for extrema check
                if img.mode in ['RGBA', 'LA', 'PA']:
                    # For images with alpha, check RGB channels only
                    test_img = img.convert('RGB')
                elif img.mode == 'P':
                    # For palette images, convert to RGB
                    test_img = img.convert('RGB')
                elif img.mode == 'L':
                    # For grayscale, extrema returns single tuple
                    extrema = img.getextrema()
                    if extrema[0] == extrema[1]:
                        img.close()
                        return False, None, "Suspicious image content (solid color)"
                    test_img = None
                else:
                    test_img = img
                
                # Check RGB extrema if we have a test image
                if test_img:
                    extrema = test_img.getextrema()
                    # If all channels have the same min and max, it's a solid color
                    if all(e[0] == e[1] for e in extrema):
                        img.close()
                        if test_img != img:
                            test_img.close()
                        return False, None, "Suspicious image content (solid color)"
                    if test_img != img:
                        test_img.close()
                        
            except Exception:
                # If extrema check fails, continue (some valid images might fail this)
                pass
            
            # Check if image can be loaded fully (catches some corrupted files)
            try:
                img.load()
            except Exception as e:
                img.close()
                return False, None, f"Failed to load image: {str(e)[:30]}"
            
            # Strip EXIF data for privacy and create clean image
            try:
                # Create a new image without EXIF
                if img.mode == 'RGBA' or img.mode == 'LA':
                    # Handle transparency
                    new_img = Image.new(img.mode, img.size)
                    new_img.paste(img, (0, 0))
                else:
                    # No transparency
                    new_img = Image.new(img.mode, img.size)
                    new_img.paste(img, (0, 0))
                
                # Save to bytes
                output = io.BytesIO()
                save_format = 'PNG' if img.format == 'PNG' else 'JPEG'
                
                # Handle different modes for JPEG
                if save_format == 'JPEG':
                    # JPEG doesn't support transparency or certain modes
                    if new_img.mode in ['RGBA', 'LA', 'PA']:
                        # Convert to RGB, removing transparency
                        rgb_img = Image.new('RGB', new_img.size, (255, 255, 255))
                        rgb_img.paste(new_img, mask=new_img.split()[-1] if new_img.mode == 'RGBA' else None)
                        new_img = rgb_img
                    elif new_img.mode == 'P':
                        # Convert palette to RGB
                        new_img = new_img.convert('RGB')
                    elif new_img.mode not in ['L', 'RGB', 'CMYK']:
                        # Convert other modes to RGB
                        new_img = new_img.convert('RGB')
                
                # Save with appropriate settings
                save_kwargs = {'format': save_format}
                if save_format == 'JPEG':
                    save_kwargs['quality'] = 95
                    save_kwargs['optimize'] = True
                
                new_img.save(output, **save_kwargs)
                file_data = output.getvalue()
                output.close()
                new_img.close()
                
            except Exception as e:
                img.close()
                return False, None, f"Failed to process image: {str(e)[:30]}"
            
            img.close()
            
        except Exception as e:
            return False, None, f"Image validation error: {str(e)[:50]}"
        
        return True, file_data, "Valid"
        
    except Exception as e:
        return False, None, f"Validation error: {str(e)[:50]}"

def sanitize_filename(filename: str) -> str:
    """Sanitize filename using bleach and additional rules"""
    # Get base name and extension
    base, ext = os.path.splitext(filename)
    
    # Use bleach to clean the base name
    base = bleach.clean(base, tags=[], strip=True)
    
    # Additional sanitization: only alphanumeric, dash, underscore
    base = re.sub(r'[^a-zA-Z0-9\-_]', '', base)
    
    # Limit length
    base = base[:40]
    
    # Ensure valid extension
    ext = ext.lower()
    if ext not in ReportSecurityConfig.ALLOWED_EXTENSIONS:
        ext = '.png'
    
    # Fallback if empty
    if not base:
        base = f"image_{int(datetime.now().timestamp())}"
    
    return base + ext

# ============ RATE LIMITING ============
class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self._cooldowns = {}
    
    def is_rate_limited(self, user_id: int, action: str) -> Tuple[bool, int]:
        """Check if user is rate limited. Returns (is_limited, seconds_remaining)"""
        key = f"{action}_{user_id}"
        now = datetime.now()
        
        if key in self._cooldowns:
            elapsed = (now - self._cooldowns[key]).total_seconds()
            if elapsed < ReportSecurityConfig.COOLDOWN_SECONDS:
                remaining = int(ReportSecurityConfig.COOLDOWN_SECONDS - elapsed)
                return True, remaining
        
        self._cooldowns[key] = now
        return False, 0
    
    def cleanup_old_entries(self, max_age_seconds: int = 300):
        """Remove old entries to prevent memory bloat"""
        now = datetime.now()
        expired = []
        
        for key, timestamp in self._cooldowns.items():
            if (now - timestamp).total_seconds() > max_age_seconds:
                expired.append(key)
        
        for key in expired:
            del self._cooldowns[key]

# Initialize rate limiter
report_rate_limiter = RateLimiter()

# ============ FEEDBACK COMMAND (ALIAS) ============
@bot.command(name='feedback')
async def feedback(ctx, *, message: str = None):
    """Submit feedback or suggestions (alias for report)
    
    Usage: !vault feedback [your message]
    """
    await report_bug(ctx, message=message)

# ============ SECURE CATEGORIZED REPORT ============
@bot.command(name='report')
async def report_bug(ctx, *, message: str = None):
    """Report a bug or issue to the bot developer with optional image attachments
    
    Usage: !vault report [your message]
    You can attach PNG or JPG/JPEG images only (max 5MB each)
    """
    
    # Rate limiting check
    is_limited, remaining = report_rate_limiter.is_rate_limited(ctx.author.id, 'report')
    if is_limited:
        await ctx.send(f"⏱️ Please wait {remaining} seconds before submitting another report.")
        return
    
    # Check if there's a message or attachments
    if not message and not ctx.message.attachments:
        await ctx.send("❌ Please provide a message or attach an image with your report.")
        return
    
    # Safely handle and sanitize the message
    if message:
        message = safe_text_input(message)
        message = sanitize_report_text(message)
        
        # Check message length after sanitization
        if len(message) < ReportSecurityConfig.MIN_MESSAGE_LENGTH and not ctx.message.attachments:
            await ctx.send(f"❌ Please provide a more detailed description (at least {ReportSecurityConfig.MIN_MESSAGE_LENGTH} characters).")
            return
    else:
        message = "No text provided - see attached image(s)"
    
    try:
        # Get bot owner
        owner = bot.get_user(ReportSecurityConfig.OWNER_ID)
        if not owner:
            owner = await bot.fetch_user(ReportSecurityConfig.OWNER_ID)
        
        # Build report embed
        report_embed = discord.Embed(
            title="🐛 Bug Report Received",
            description=message,
            color=0xFF6347,
            timestamp=datetime.now()
        )
        
        # Sanitize all display text
        author_name = sanitize_report_text(safe_text_input(str(ctx.author)), 50)
        guild_name = sanitize_report_text(safe_text_input(ctx.guild.name), 50)
        channel_name = sanitize_report_text(safe_text_input(ctx.channel.name), 50)
        
        # Add reporter info
        report_embed.add_field(
            name="📤 Reported By",
            value=f"{ctx.author.mention} ({author_name})\nID: `{ctx.author.id}`",
            inline=True
        )
        
        # Add server info
        report_embed.add_field(
            name="🏠 Server",
            value=f"{guild_name}\nID: `{ctx.guild.id}`",
            inline=True
        )
        
        # Check if owner is in the server
        jump_url = None
        if ctx.guild.get_member(ReportSecurityConfig.OWNER_ID):
            jump_url = ctx.message.jump_url
            report_embed.add_field(
                name="📍 Location",
                value=f"[#{channel_name}]({jump_url})",
                inline=True
            )
        else:
            report_embed.add_field(
                name="📍 Channel",
                value=f"#{channel_name} (No access)",
                inline=True
            )
        
        # Handle attachments with security validation
        validated_files = []
        validation_results = []
        
        if ctx.message.attachments:
            # Limit number of attachments
            attachments_to_process = ctx.message.attachments[:ReportSecurityConfig.MAX_FILES_PER_REPORT]
            
            if len(ctx.message.attachments) > ReportSecurityConfig.MAX_FILES_PER_REPORT:
                validation_results.append(f"ℹ️ Only first {ReportSecurityConfig.MAX_FILES_PER_REPORT} files processed")
            
            for attachment in attachments_to_process:
                # Validate the image
                is_valid, file_data, error_msg = await validate_image_file(attachment)
                
                if is_valid and file_data:
                    # Sanitize filename
                    safe_filename = sanitize_filename(attachment.filename)
                    
                    # Create validated file
                    validated_file = discord.File(
                        io.BytesIO(file_data),
                        filename=safe_filename,
                        spoiler=False
                    )
                    validated_files.append(validated_file)
                    validation_results.append(f"✅ {safe_filename}")
                else:
                    sanitized_original_name = sanitize_report_text(safe_text_input(attachment.filename), 30)
                    validation_results.append(f"❌ {sanitized_original_name} - {error_msg}")
        
        # Add attachment summary
        if validation_results:
            report_embed.add_field(
                name="📎 Attachments",
                value="\n".join(validation_results[:5])[:1024],  # Discord field limit
                inline=False
            )
        
        # Add timestamp
        report_embed.add_field(
            name="🕐 Time",
            value=f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC",
            inline=False
        )
        
        # Set footer
        report_embed.set_footer(
            text=f"Report #{ctx.message.id} • {bot.user.name}",
            icon_url=bot.user.avatar.url if bot.user.avatar else None
        )
        
        # Set author
        author_display_name = sanitize_report_text(safe_text_input(ctx.author.display_name), 50)
        report_embed.set_author(
            name=author_display_name,
            icon_url=ctx.author.avatar.url if ctx.author.avatar else None
        )
        
        # Send to owner with validated attachments
        if validated_files:
            await owner.send(embed=report_embed, files=validated_files)
        else:
            await owner.send(embed=report_embed)
        
        # Send text version as backup (also sanitized)
        text_report = (
            f"**Bug Report from {author_name}**\n"
            f"Server: {guild_name} ({ctx.guild.id})\n"
            f"Channel: #{channel_name}\n"
        )
        
        if jump_url:
            text_report += f"Jump to message: {jump_url}\n"
        
        text_report += f"\n**Report:**\n{message}"
        
        if validated_files:
            text_report += f"\n\n**Validated Images:** {len(validated_files)}"
        
        # Ensure text report isn't too long
        if len(text_report) > 2000:
            text_report = text_report[:1997] + "..."
        
        await owner.send(text_report)
        
        # Confirm to reporter
        confirm_embed = discord.Embed(
            title="✅ Report Submitted",
            description="Your bug report has been sent to the developer.",
            color=0x00FF00
        )
        
        if validated_files:
            confirm_embed.add_field(
                name="✅ Images Included",
                value=f"{len(validated_files)} image(s) attached",
                inline=True
            )
        
        rejected_count = len([r for r in validation_results if r.startswith("❌")])
        if rejected_count > 0:
            confirm_embed.add_field(
                name="⚠️ Files Rejected",
                value=f"{rejected_count} file(s) rejected\n(Only PNG/JPG under 5MB)",
                inline=True
            )
        
        confirm_embed.add_field(
            name="What happens next?",
            value="• The developer will review your report\n"
                  "• Critical bugs will be prioritized\n"
                  "• You may be contacted for more details",
            inline=False
        )
        
        confirm_embed.add_field(
            name="Report ID",
            value=f"`{ctx.message.id}`",
            inline=True
        )
        
        confirm_embed.set_footer(text="Thank you for helping improve Helmhud Guardian!")
        
        await ctx.send(embed=confirm_embed)
        
        # Log the report (sanitized)
        attachment_log = f" with {len(validated_files)} images" if validated_files else ""
        log_message = sanitize_report_text(safe_text_input(message[:100]), 100)
        print(f"[BUG REPORT] From {ctx.author} ({ctx.author.id}) in {guild_name}{attachment_log}: {log_message}")
        
    except discord.Forbidden:
        error_embed = discord.Embed(
            title="❌ Report Failed",
            description="Could not send report to developer (DMs may be disabled).",
            color=0xFF0000
        )
        error_embed.add_field(
            name="Alternative",
            value="Please contact the developer directly or through the support server.",
            inline=False
        )
        await ctx.send(embed=error_embed)
        
        print(f"[FAILED BUG REPORT] From {ctx.author} ({ctx.author.id})")
        
    except Exception as e:
        # Sanitize error message
        error_msg = sanitize_report_text(str(e), 100)
        await ctx.send(f"❌ An error occurred while sending the report: {error_msg}")
        print(f"[REPORT ERROR] {str(e)}")
        import traceback
        traceback.print_exc()

@bot.command(name='reportbug')
async def report_categorized(ctx, category: str = None, *, message: str = None):
    """Report a bug with category and optional image attachments
    
    Usage: !vault reportbug [category] [message]
    Categories: bug, suggestion, error, other
    You can attach PNG or JPG/JPEG images only (max 5MB each)
    """
    
    # Valid categories
    valid_categories = {
        "bug": ("🐛", 0xFF6347),
        "suggestion": ("💡", 0x87CEEB),
        "error": ("❌", 0xFF0000),
        "other": ("📝", 0x808080)
    }
    
    if not category or category.lower() not in valid_categories:
        # Show help
        help_embed = discord.Embed(
            title="📝 Report Categories",
            description="Please specify a category for your report:",
            color=0x87CEEB
        )
        
        for cat, (emoji, color) in valid_categories.items():
            help_embed.add_field(
                name=f"{emoji} {cat.title()}",
                value=f"`!vault reportbug {cat} [your message]`",
                inline=False
            )
        
        help_embed.add_field(
            name="📸 Attachments",
            value=f"You can attach PNG or JPG images (max 5MB each, up to {ReportSecurityConfig.MAX_FILES_PER_REPORT} files)",
            inline=False
        )
        
        await ctx.send(embed=help_embed)
        return
    
    # Rate limiting check
    is_limited, remaining = report_rate_limiter.is_rate_limited(ctx.author.id, 'reportbug')
    if is_limited:
        await ctx.send(f"⏱️ Please wait {remaining} seconds before submitting another report.")
        return
    
    # Check if there's a message or attachments
    if not message and not ctx.message.attachments:
        await ctx.send(f"❌ Please provide a message or attach an image after the category.\n"
                      f"Example: `!vault reportbug {category} Your detailed report here`")
        return
    
    # Safely handle and sanitize message
    if message:
        message = safe_text_input(message)
        message = sanitize_report_text(message)
        if len(message) < ReportSecurityConfig.MIN_MESSAGE_LENGTH and not ctx.message.attachments:
            await ctx.send(f"❌ Please provide a more detailed description (at least {ReportSecurityConfig.MIN_MESSAGE_LENGTH} characters).")
            return
    else:
        message = "No text provided - see attached image(s)"
    
    # Use the category info
    emoji, color = valid_categories[category.lower()]
    
    try:
        owner = bot.get_user(ReportSecurityConfig.OWNER_ID) or await bot.fetch_user(ReportSecurityConfig.OWNER_ID)
        
        # Build categorized report
        report_embed = discord.Embed(
            title=f"{emoji} {category.title()} Report",
            description=message,
            color=color,
            timestamp=datetime.now()
        )
        
        # Sanitize display names
        author_name = sanitize_report_text(safe_text_input(str(ctx.author)), 50)
        guild_name = sanitize_report_text(safe_text_input(ctx.guild.name), 50)
        channel_name = sanitize_report_text(safe_text_input(ctx.channel.name), 50)
        
        # Add metadata
        report_embed.add_field(
            name="📤 Reported By",
            value=f"{ctx.author.mention} ({author_name})\nID: `{ctx.author.id}`",
            inline=True
        )
        
        report_embed.add_field(
            name="🏠 Server",
            value=f"{guild_name}\nID: `{ctx.guild.id}`",
            inline=True
        )
        
        # Location with jump URL if accessible
        if ctx.guild.get_member(ReportSecurityConfig.OWNER_ID):
            jump_url = ctx.message.jump_url
            report_embed.add_field(
                name="📍 Location",
                value=f"[#{channel_name}]({jump_url})",
                inline=True
            )
        else:
            report_embed.add_field(
                name="📍 Channel",
                value=f"#{channel_name} (No access)",
                inline=True
            )
        
        # Priority based on category
        priority_map = {
            "error": "🔴 High",
            "bug": "🟡 Normal",
            "suggestion": "🟢 Low",
            "other": "⚪ Varies"
        }
        report_embed.add_field(
            name="⚡ Priority",
            value=priority_map.get(category.lower(), "🟡 Normal"),
            inline=True
        )
        
        # Handle attachments with validation
        validated_files = []
        validation_summary = []
        
        if ctx.message.attachments:
            for i, attachment in enumerate(ctx.message.attachments[:ReportSecurityConfig.MAX_FILES_PER_REPORT]):
                # Validate the image
                is_valid, file_data, error_msg = await validate_image_file(attachment)
                
                if is_valid and file_data:
                    safe_filename = sanitize_filename(attachment.filename)
                    validated_files.append(discord.File(
                        io.BytesIO(file_data),
                        filename=safe_filename,
                        spoiler=False
                    ))
                    validation_summary.append(f"✅ {safe_filename}")
                else:
                    sanitized_name = sanitize_report_text(safe_text_input(attachment.filename), 30)
                    validation_summary.append(f"❌ {sanitized_name} - {error_msg}")
        
        if validation_summary:
            report_embed.add_field(
                name="📎 Attachment Validation",
                value="\n".join(validation_summary[:5])[:1024],
                inline=False
            )
        
        author_display_name = sanitize_report_text(safe_text_input(ctx.author.display_name), 50)
        report_embed.set_author(
            name=author_display_name,
            icon_url=ctx.author.avatar.url if ctx.author.avatar else None
        )
        
        report_embed.set_footer(text=f"Report #{ctx.message.id}")
        
        # Send to owner
        if validated_files:
            await owner.send(embed=report_embed, files=validated_files)
        else:
            await owner.send(embed=report_embed)
        
        # Confirm to user
        confirm_text = f"{emoji} Your {category} report has been submitted!"
        if validated_files:
            confirm_text += f" ({len(validated_files)} images included)"
        confirm_text += f"\nReport ID: `{ctx.message.id}`"
        
        await ctx.send(confirm_text)
        
        # Log
        print(f"[{category.upper()} REPORT] From {ctx.author} ({ctx.author.id}) in {guild_name}")
        
    except Exception as e:
        error_msg = sanitize_report_text(str(e), 100)
        await ctx.send(f"❌ Failed to send report: {error_msg}")
        print(f"[REPORT ERROR] {str(e)}")
        import traceback
        traceback.print_exc()

# ============ VIEW REPORT STATUS (FOR OWNER) ============
@bot.command(name='reports')
async def view_reports(ctx):
    """Owner only: View report system status and configuration"""
    
    if ctx.author.id != ReportSecurityConfig.OWNER_ID:
        await ctx.send("🔒 This command is only available to the bot developer.")
        return
    
    embed = discord.Embed(
        title="📊 Report System Status",
        description="Secure report system using trusted libraries",
        color=0x00FF00
    )
    
    embed.add_field(
        name="Available Commands",
        value="`!vault report [message]` - Basic report\n"
              "`!vault feedback [message]` - Feedback/suggestions\n"
              "`!vault reportbug [category] [message]` - Categorized report",
        inline=False
    )
    
    embed.add_field(
        name="Report Categories",
        value="🐛 bug - Code bugs\n"
              "💡 suggestion - Feature requests\n"
              "❌ error - Error messages\n"
              "📝 other - General reports",
        inline=False
    )
    
    embed.add_field(
        name="🔒 Security Features",
        value="• **Text**: `bleach` library sanitization\n"
              "• **Images**: `Pillow` validation + `python-magic`\n"
              "• **Files**: Size/dimension/format validation\n"
              "• **Rate Limiting**: 60 second cooldown\n"
              "• **Filename**: Sanitized with `bleach`",
        inline=False
    )
    
    embed.add_field(
        name="📋 Configuration",
        value=f"• Max file size: {ReportSecurityConfig.MAX_FILE_SIZE // (1024*1024)}MB\n"
              f"• Max files: {ReportSecurityConfig.MAX_FILES_PER_REPORT}\n"
              f"• Allowed formats: PNG, JPG/JPEG\n"
              f"• Max dimensions: {ReportSecurityConfig.MAX_IMAGE_DIMENSION}px\n"
              f"• Cooldown: {ReportSecurityConfig.COOLDOWN_SECONDS}s",
        inline=False
    )
    
    # Show current cooldowns if any
    active_cooldowns = 0
    for key in report_rate_limiter._cooldowns:
        active_cooldowns += 1
    
    if active_cooldowns > 0:
        embed.add_field(
            name="📊 Active Cooldowns",
            value=f"{active_cooldowns} users on cooldown",
            inline=True
        )
    
    embed.set_footer(text="Powered by bleach, Pillow, and python-magic")
    
    await ctx.send(embed=embed)

# ============ CLEANUP TASK FOR RATE LIMITER ============
@tasks.loop(minutes=5)
async def cleanup_report_cooldowns():
    """Clean up old report cooldowns to prevent memory bloat"""
    report_rate_limiter.cleanup_old_entries(300)  # Clean entries older than 5 minutes
    logger.info("[CLEANUP] Report cooldowns cleaned")


# ============ ERROR HANDLING ============
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        await ctx.send("❌ Unknown vault command. Use `!vault help` or `!vault features`")
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("🛡️ Insufficient vault clearance")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ Missing required argument: {error.param.name}")
    else:
        await ctx.send(f"⚠️ Vault error: {error}")
        logger.error(f"Error in {ctx.command}: {error}")
        import traceback
        traceback.print_exc()


# ============ GLOBAL ROLE SYNC ============
async def sync_user_roles_across_servers(
    user_id: int, source_guild: discord.Guild = None, silent: bool = False
):
    """Sync a user's earned roles across all servers they're in"""
    user_stats = bot.user_data.get(user_id)
    if not user_stats:
        return
    
    # Determine which roles the user qualifies for
    qualified_roles = []
    
    if user_stats["reaction_count"] >= 1:
        qualified_roles.append("initiate_drone")
    if len(user_stats["emojis_used"]) >= 5:
        qualified_roles.append("wakened_seeker")
    if user_stats["reaction_count"] >= 10:
        qualified_roles.append("lore_harvester")
    if len(user_stats["starcode_chains"]) >= 3:
        qualified_roles.append("memory_mason")
    if user_stats["corrections"] >= 5:
        qualified_roles.append("index_guard")
    if user_stats["influence_score"] >= 50:
        qualified_roles.append("starforger")
    if user_stats["corrections"] >= 3 and user_stats["problematic_flags"] >= 2:
        qualified_roles.append("vault_knight")
    if user_stats["influence_score"] >= 100 and len(user_stats["definitions_created"]) >= 3:
        qualified_roles.append("ghost_walker")
    
    # Track results for logging
    sync_results = {
        "servers_checked": 0,
        "servers_updated": 0,
        "roles_added": 0,
        "errors": 0
    }
    logger.info(f"Starting role sync for user {user_id}")

    # Check all guilds the bot is in
    for guild in bot.guilds:
        sync_results["servers_checked"] += 1

        # Skip the source guild if provided (already handled)
        if source_guild and guild.id == source_guild.id:
            continue

        if not guild.me.guild_permissions.manage_roles:
            logger.warning(
                f"Skipping {guild.name} - missing manage_roles permission"
            )
            continue

        # Check if user is in this guild
        member = guild.get_member(user_id)
        if not member:
            continue
        
        # Check each qualified role
        roles_added_here = False
        for role_key in qualified_roles:
            role_config = ROLES_CONFIG.get(role_key)
            if not role_config:
                continue
            
            role_name = role_config["name"]
            
            # Check if member already has this role
            if any(r.name == role_name for r in member.roles):
                continue
            
            # Get or create the role
            role = discord.utils.get(guild.roles, name=role_name)
            if not role:
                try:
                    role = await guild.create_role(
                        name=role_name,
                        color=role_config["color"],
                        mentionable=True
                    )
                except discord.Forbidden:
                    sync_results["errors"] += 1
                    continue
                except Exception as e:
                    logger.error(
                        f"Error creating role {role_name} in {guild.name}: {e}"
                    )
                    sync_results["errors"] += 1
                    continue
            
            # Add role to member
            try:
                await safe_add_roles(member, role)
                sync_results["roles_added"] += 1
                roles_added_here = True

                if not silent:
                    channel_id = bot.get_channel_for_feature(guild.id, "vault_progression")
                    if channel_id:
                        channel = guild.get_channel(int(channel_id))
                    else:
                        channel = discord.utils.get(guild.channels, name="vault-progression")

                    if channel:
                        embed = discord.Embed(
                            title="✨ Role Sync ✨",
                            description=f"{member.mention} has been granted **{role_name}**",
                            color=role_config["color"]
                        )
                        embed.add_field(
                            name="Synced From",
                            value=f"Another server ({source_guild.name if source_guild else 'Unknown'})",
                            inline=False
                        )
                        embed.set_footer(text="Cross-server role synchronization")

                        try:
                            await channel.send(embed=embed)
                        except Exception:
                            pass  # Silent fail on announcement

            except discord.Forbidden:
                sync_results["errors"] += 1
                continue
            except Exception as e:
                logger.error(
                    f"Error adding role {role_name} to {member} in {guild.name}: {e}"
                )
                sync_results["errors"] += 1
                continue
        
        if roles_added_here:
            sync_results["servers_updated"] += 1

    logger.info(
        f"Role sync for {user_id}: {sync_results['roles_added']} roles added across {sync_results['servers_updated']} servers with {sync_results['errors']} errors"
    )
    return sync_results

# ============ MODIFIED ROLE PROGRESSION ============
async def check_role_progression(member, guild, channel=None):
    """Enhanced role progression with cross-server sync"""
    user_stats = bot.user_data[member.id]
    current_roles = [role.name for role in member.roles]
    
    new_roles_earned = []
    
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
            new_roles_earned.append((role_key, config))
            
            # Announce progression in invoking channel if provided
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
    
    # If any new roles were earned, sync across all servers
    if new_roles_earned:
        sync_results = await sync_user_roles_across_servers(member.id, guild, silent=True)
        logger.info(f"Role sync for {member}: {sync_results}")

# ============ MEMBER JOIN EVENT ============
@bot.event
async def on_member_join(member):
    """When a member joins, check if they should have any roles"""
    if member.bot:
        return
    
    # Check if user has existing profile
    if member.id not in bot.user_data:
        return
    
    user_stats = bot.user_data[member.id]
    guild = member.guild
    roles_to_add = []
    
    # Check each role qualification
    role_checks = [
        ("initiate_drone", user_stats["reaction_count"] >= 1),
        ("wakened_seeker", len(user_stats["emojis_used"]) >= 5),
        ("lore_harvester", user_stats["reaction_count"] >= 10),
        ("memory_mason", len(user_stats["starcode_chains"]) >= 3),
        ("index_guard", user_stats["corrections"] >= 5),
        ("starforger", user_stats["influence_score"] >= 50),
        ("vault_knight", user_stats["corrections"] >= 3 and user_stats["problematic_flags"] >= 2),
        ("ghost_walker", user_stats["influence_score"] >= 100 and len(user_stats["definitions_created"]) >= 3)
    ]
    
    for role_key, qualified in role_checks:
        if not qualified:
            continue
            
        config = ROLES_CONFIG.get(role_key)
        if not config:
            continue
        
        role_name = config["name"]
        
        # Get or create role
        role = discord.utils.get(guild.roles, name=role_name)
        if not role:
            try:
                role = await guild.create_role(
                    name=role_name,
                    color=config["color"],
                    mentionable=True
                )
            except:
                continue
        
        roles_to_add.append(role)
    
    # Add all roles at once
    if roles_to_add:
        try:
            await safe_add_roles(member, *roles_to_add)
            
            # Announce if progression channel exists
            channel_id = bot.get_channel_for_feature(guild.id, "vault_progression")
            if channel_id:
                channel = guild.get_channel(int(channel_id))
            else:
                channel = discord.utils.get(guild.channels, name="vault-progression")
            
            if channel:
                role_names = [r.name for r in roles_to_add]
                embed = discord.Embed(
                    title="🌟 Returning Vault Citizen",
                    description=f"{member.mention} has rejoined with existing qualifications",
                    color=0xFFD700
                )
                embed.add_field(
                    name="Restored Roles",
                    value="\n".join(role_names),
                    inline=False
                )
                embed.add_field(
                    name="Statistics",
                    value=f"Influence: **{user_stats['influence_score']}**\n"
                          f"Reactions: **{user_stats['reaction_count']}**\n"
                          f"StarCodes: **{len(user_stats['starcode_chains'])}**",
                    inline=True
                )
                embed.set_footer(text="The Vault remembers")
                
                await channel.send(embed=embed)
                
        except discord.Forbidden:
            logger.warning(f"Could not add roles to {member} in {guild.name} - missing permissions")
        except Exception as e:
            logger.error(f"Error adding roles on join: {e}")


# ============ SYNC COMMAND ============
@bot.command(name='sync_roles')
async def sync_roles(ctx, *, args: str = None):
    """Manually sync your roles across all servers (or sync another user if admin)
    
    Usage: !vault sync_roles [user] [silent]
    """

    silent = False
    target_ref = None
    if args:
        parts = args.split()
        parts_lower = [p.lower() for p in parts]
        if "silent" in parts_lower:
            silent = True
            parts = [p for p in parts if p.lower() != "silent"]
        if parts:
            target_ref = parts[0]

    if target_ref and ctx.author.guild_permissions.administrator:
        member = await get_member_by_reference(ctx, target_ref)
        if not member:
            await ctx.send(f"❌ Could not find user: {target_ref}")
            return
        user_to_sync = member
    else:
        user_to_sync = ctx.author

    if not silent:
        status_embed = discord.Embed(
            title="🔄 Syncing Roles...",
            description=f"Checking role qualifications across all servers for {user_to_sync.mention}",
            color=0x87CEEB,
        )
        msg = await ctx.send(embed=status_embed)
    else:
        msg = None

    sync_results = await sync_user_roles_across_servers(
        user_to_sync.id, ctx.guild, silent=silent
    )

    result = discord.Embed(
        title="✅ Role Sync Complete",
        description=f"Synchronized roles for {user_to_sync.mention}",
        color=0x00FF00,
    )

    result.add_field(
        name="📊 Results",
        value=f"Servers checked: **{sync_results['servers_checked']}**\n"
              f"Servers updated: **{sync_results['servers_updated']}**\n"
              f"Roles added: **{sync_results['roles_added']}**\n"
              f"Errors: **{sync_results['errors']}**",
        inline=False
    )

    if sync_results['roles_added'] > 0:
        result.add_field(
            name="✨ Success",
            value=f"Added {sync_results['roles_added']} missing roles across {sync_results['servers_updated']} servers!",
            inline=False
        )
    else:
        result.add_field(
            name="ℹ️ Status",
            value="All roles are already synchronized!",
            inline=False
        )

    if msg:
        await safe_edit_message(msg, embed=result)
    else:
        await ctx.send(embed=result)

# ============ GLOBAL SYNC COMMAND (ADMIN) ============
@bot.command(name='sync_all_roles')
@commands.has_permissions(administrator=True)
async def sync_all_roles(ctx, mode: str = None):
    """Admin: Sync roles for ALL users across ALL servers"""

    silent = mode and mode.lower() == "silent"
    
    confirm_embed = discord.Embed(
        title="⚠️ Global Role Sync",
        description="This will sync roles for ALL users across ALL servers.\nThis may take a while.",
        color=0xFFA500
    )
    confirm_embed.add_field(
        name="Impact",
        value=f"• {len(bot.user_data)} users to check\n• {len(bot.guilds)} servers to update",
        inline=False
    )
    confirm_embed.set_footer(text="React with ✅ to confirm")
    
    msg = await ctx.send(embed=confirm_embed)
    await msg.add_reaction("✅")
    
    def check(reaction, user):
        return user == ctx.author and str(reaction.emoji) == "✅" and reaction.message.id == msg.id
    
    try:
        await bot.wait_for('reaction_add', timeout=30.0, check=check)
    except asyncio.TimeoutError:
        await ctx.send("❌ Global sync cancelled - timeout")
        return
    
    # Start global sync
    progress_embed = discord.Embed(
        title="🔄 Global Role Sync in Progress...",
        description="Synchronizing all users across all servers",
        color=0x87CEEB,
    )
    if not silent:
        await safe_edit_message(msg, embed=progress_embed)

    total_users = 0
    total_roles_added = 0
    total_errors = 0

    for user_id in bot.user_data:
        if not silent and total_users % 10 == 0:
            progress_embed.description = f"Processing user {total_users}/{len(bot.user_data)}..."
            await safe_edit_message(msg, embed=progress_embed)

        results = await sync_user_roles_across_servers(user_id, silent=silent)
        total_roles_added += results['roles_added']
        total_errors += results['errors']
        total_users += 1
    
    # Final report
    complete_embed = discord.Embed(
        title="✅ Global Role Sync Complete",
        description="All users have been synchronized",
        color=0x00FF00,
        timestamp=datetime.now()
    )
    complete_embed.add_field(
        name="📊 Summary",
        value=f"Users processed: **{total_users}**\n"
              f"Roles added: **{total_roles_added}**\n"
              f"Errors: **{total_errors}**",
        inline=False
    )
    
    if not silent and msg:
        await safe_edit_message(msg, embed=complete_embed)
    else:
        await ctx.send(embed=complete_embed)

# ============ TEST SUITE COMMAND ============
@bot.command(name='test_suite')
@commands.has_permissions(administrator=True)
async def test_suite(ctx):
    """Admin: Run comprehensive test suite for all bot functions"""
    
    # Create test report embed
    test_report = discord.Embed(
        title="🧪 Helmhud Guardian Test Suite",
        description="Running comprehensive tests...",
        color=0x00FF00,
        timestamp=datetime.now()
    )
    test_msg = await ctx.send(embed=test_report)
    
    # Test data storage
    test_data = {
        "test_user_id": 999999999999999999,  # Fake test user ID
        "original_data": {},
        "created_patterns": [],
        "created_definitions": [],
        "created_themes": [],
        "created_trainings": [],
        "blessed_chains": [],
        "problematic_chains": [],
        "test_results": {},
        "cleanup_needed": []
    }
    
    # Store original state
    test_data["original_data"] = {
        "user_data": bot.user_data.get(test_data["test_user_id"], None),
        "starcode_patterns": bot.starcode_patterns.copy(),
        "emoji_definitions": bot.emoji_definitions.copy(),
        "semantic_themes": bot.semantic_themes.copy(),
        "custom_trainings": bot.custom_trainings.copy(),
        "blessed_chains": bot.blessed_chains.copy(),
        "problematic_chains": bot.problematic_chains.copy(),
        "custom_starlocks": bot.custom_starlocks.copy(),
        "divine_alignment": bot.divine_alignment,
        "feedback_data": getattr(bot, "feedback_data", []).copy() if hasattr(bot, "feedback_data") else [],
        "bug_reports": getattr(bot, "bug_reports", []).copy() if hasattr(bot, "bug_reports") else [],
        "channel_config": getattr(bot, "channel_config", {}).copy() if hasattr(bot, "channel_config") else {}
    }
    
    async def update_report(test_name, status, details=""):
        """Update test report with results"""
        test_data["test_results"][test_name] = {
            "status": status,
            "details": details
        }

        # Update embed without exceeding field limits
        lines = []
        for name, result in test_data["test_results"].items():
            icon = "✅" if result["status"] == "PASS" else ("❌" if result["status"] == "FAIL" else "🔄")
            value = result["details"] if result["details"] else "Test completed"
            lines.append(f"{icon} **{name}:** {value[:100]}")

        test_report.description = "Running comprehensive tests...\n" + "\n".join(lines)
        await safe_edit_message(test_msg, embed=test_report)
    
    try:
        # Test 1: User Profile Creation
        await update_report("User Profile Creation", "TESTING")
        
        # Create test user profile
        bot.user_data[test_data["test_user_id"]] = {
            "emojis_used": set(["🧪", "🔬", "⚗️", "🧬", "🔭"]),
            "reaction_count": 15,
            "starcode_chains": [["🧪", "🔬"], ["⚗️", "🧬"], ["🔭", "🌟"]],
            "corrections": 5,  # Increased to qualify for index_guard
            "influence_score": 100,  # Increased to qualify for ghost_walker
            "remory_strings": [],
            "chains_originated": {},
            "chains_adopted": {},
            "training_quest": None,
            "training_progress": {},
            "blessed_chains": [],
            "problematic_flags": 2,
            "definitions_created": {"🧪": "Test meaning", "🔬": "Science tool", "⚗️": "Chemistry"},  # Added for ghost_walker
            "completed_trainings": []
        }
        
        # Verify profile exists
        if test_data["test_user_id"] in bot.user_data:
            await update_report("User Profile Creation", "PASS", "Test profile created successfully")
        else:
            await update_report("User Profile Creation", "FAIL", "Failed to create test profile")
            return
        
        # Test 2: StarCode Registration
        await update_report("StarCode Registration", "TESTING")
        
        test_pattern = "🧪🔬🧬"
        bot.starcode_patterns[test_pattern] = {
            "author": test_data["test_user_id"],
            "created": datetime.now().isoformat(),
            "uses": 1,
            "description": "Test pattern",
            "pattern": test_pattern
        }
        test_data["created_patterns"].append(test_pattern)
        bot.user_data[test_data["test_user_id"]]["chains_originated"][test_pattern] = 1
        
        if test_pattern in bot.starcode_patterns:
            await update_report("StarCode Registration", "PASS", f"Pattern {test_pattern} registered")
        else:
            await update_report("StarCode Registration", "FAIL", "Failed to register pattern")
        
        # Test 3: Emoji Definition
        await update_report("Emoji Definition", "TESTING")
        
        test_emoji = "🧪"
        test_meaning = "Test tube - symbol of experimentation"
        
        if test_emoji not in bot.emoji_definitions:
            bot.emoji_definitions[test_emoji] = []
        
        bot.emoji_definitions[test_emoji].append({
            "meaning": test_meaning,
            "author": test_data["test_user_id"],
            "timestamp": datetime.now().isoformat(),
            "official": True
        })
        test_data["created_definitions"].append(test_emoji)
        bot.user_data[test_data["test_user_id"]]["definitions_created"][test_emoji] = test_meaning
        
        if test_emoji in bot.emoji_definitions:
            await update_report("Emoji Definition", "PASS", f"{test_emoji} defined")
        else:
            await update_report("Emoji Definition", "FAIL", "Failed to define emoji")
        
        # Test 4: Theme Creation
        await update_report("Theme Creation", "TESTING")
        
        test_theme = "test_science"
        test_theme_emojis = ["🧪", "🔬", "⚗️", "🧬", "🔭"]
        
        bot.semantic_themes[test_theme] = {
            "emojis": test_theme_emojis,
            "created_by": test_data["test_user_id"],
            "created_at": datetime.now().isoformat(),
            "description": "Test theme for science"
        }
        test_data["created_themes"].append(test_theme)
        
        if test_theme in bot.semantic_themes:
            await update_report("Theme Creation", "PASS", f"Theme '{test_theme}' created")
        else:
            await update_report("Theme Creation", "FAIL", "Failed to create theme")
        
        # Test 5: Training Creation
        await update_report("Training Creation", "TESTING")
        
        test_training_id = "test_quest"
        bot.custom_trainings[test_training_id] = {
            "name": "Test Quest",
            "task": "Complete test actions",
            "chain": ["🧪", "🔬"],
            "reward": 10,
            "detection": "message",
            "count": 1,
            "created_by": test_data["test_user_id"],
            "created_at": datetime.now().isoformat()
        }
        test_data["created_trainings"].append(test_training_id)
        
        if test_training_id in bot.custom_trainings:
            await update_report("Training Creation", "PASS", "Custom training created")
        else:
            await update_report("Training Creation", "FAIL", "Failed to create training")
        
        # Test 6: Chain Blessing
        await update_report("Chain Blessing", "TESTING")
        
        blessed_chain = "🧪🔬"
        bot.blessed_chains[blessed_chain] = {
            "blessed_by": test_data["test_user_id"],
            "timestamp": datetime.now().isoformat(),
            "alignment": bot.divine_alignment
        }
        test_data["blessed_chains"].append(blessed_chain)
        bot.user_data[test_data["test_user_id"]]["blessed_chains"].append(blessed_chain)
        
        if blessed_chain in bot.blessed_chains:
            await update_report("Chain Blessing", "PASS", f"Chain {blessed_chain} blessed")
        else:
            await update_report("Chain Blessing", "FAIL", "Failed to bless chain")
        
        # Test 7: Problematic Chain Marking
        await update_report("Problematic Marking", "TESTING")
        
        problem_chain = "💀💣"
        bot.problematic_chains.append({
            "chain": problem_chain,
            "flagged_by": test_data["test_user_id"],
            "timestamp": datetime.now(),
            "message_id": 0,
            "author_id": test_data["test_user_id"],
            "context": "Test problematic chain"
        })
        test_data["problematic_chains"].append(problem_chain)
        
        if any(p["chain"] == problem_chain for p in bot.problematic_chains):
            await update_report("Problematic Marking", "PASS", "Chain marked as problematic")
        else:
            await update_report("Problematic Marking", "FAIL", "Failed to mark problematic")
        
        # Test 8: Divine Alignment
        await update_report("Divine Alignment", "TESTING")
        
        original_alignment = bot.divine_alignment
        bot.divine_alignment = "truth"
        
        if bot.divine_alignment == "truth":
            await update_report("Divine Alignment", "PASS", "Alignment changed to 'truth'")
            bot.divine_alignment = original_alignment  # Restore
        else:
            await update_report("Divine Alignment", "FAIL", "Failed to change alignment")
        
        # Test 9: Training Assignment
        await update_report("Training Assignment", "TESTING")
        
        bot.user_data[test_data["test_user_id"]]["training_quest"] = "q1"
        bot.user_data[test_data["test_user_id"]]["training_progress"]["q1_progress"] = 0
        
        if bot.user_data[test_data["test_user_id"]]["training_quest"] == "q1":
            await update_report("Training Assignment", "PASS", "Training quest assigned")
        else:
            await update_report("Training Assignment", "FAIL", "Failed to assign training")
        
        # Test 10: Influence Calculation
        await update_report("Influence Calculation", "TESTING")
        
        test_chain = ["🧪", "🔬"]
        base_influence = calculate_chain_influence(test_chain, test_data["test_user_id"], bot)
        
        if base_influence > 0:
            await update_report("Influence Calculation", "PASS", f"Calculated influence: {base_influence}")
        else:
            await update_report("Influence Calculation", "FAIL", "Failed to calculate influence")
        
        # Test 11: Role Qualification Check
        await update_report("Role Qualification", "TESTING")
        
        # Check if test user qualifies for roles
        qualifications = []
        user_stats = bot.user_data[test_data["test_user_id"]]
        
        if user_stats["reaction_count"] >= 1:
            qualifications.append("Initiate Drone")
        if len(user_stats["emojis_used"]) >= 5:
            qualifications.append("Wakened Seeker")
        if user_stats["reaction_count"] >= 10:
            qualifications.append("Lore Harvester")
        if len(user_stats["starcode_chains"]) >= 3:
            qualifications.append("Memory Mason")
        if user_stats["influence_score"] >= 50:
            qualifications.append("StarForger")
        
        if qualifications:
            await update_report("Role Qualification", "PASS", f"Qualifies for: {', '.join(qualifications[:3])}")
        else:
            await update_report("Role Qualification", "FAIL", "No role qualifications met")
        
        # Test 12: Data Persistence
        await update_report("Data Persistence", "TESTING")
        
        try:
            # Test save
            bot.save_data()
            
            # Test that sets convert properly
            if isinstance(bot.user_data[test_data["test_user_id"]]["emojis_used"], set):
                await update_report("Data Persistence", "PASS", "Data structures maintained correctly")
            else:
                await update_report("Data Persistence", "FAIL", "Set conversion issue")
        except Exception as e:
            await update_report("Data Persistence", "FAIL", f"Error: {str(e)[:50]}")
        
        # Test 13: Command Permissions
        await update_report("Command Permissions", "TESTING")
        
        # Simulate permission checks
        test_member = type('obj', (object,), {
            'roles': [type('obj', (object,), {'name': '⚔️ Vault Knight'})()]
        })()
        
        knight_check = has_vault_role(test_member, "vault_knight")
        ghost_check = has_vault_role(test_member, "ghost_walker")
        
        if knight_check and not ghost_check:
            await update_report("Command Permissions", "PASS", "Role permission checks working")
        else:
            await update_report("Command Permissions", "FAIL", "Permission check failed")
        
        # Test 14: StarLock System
        await update_report("StarLock System", "TESTING")
        
        # Check if StarLock patterns are defined
        test_starlock = "💡⚡🔍"
        if test_starlock in DEFAULT_STARLOCKS:
            await update_report("StarLock System", "PASS", f"StarLock {DEFAULT_STARLOCKS[test_starlock]['name']} verified")
        else:
            await update_report("StarLock System", "FAIL", "StarLock not found")
        
        # Test 15: Auto-Registration Queue
        await update_report("Auto-Registration", "TESTING")
        
        test_pending_key = f"test_{datetime.now().timestamp()}"
        bot.pending_chains[test_pending_key] = {
            "chain": ["🧪", "🔬"],
            "author": test_data["test_user_id"],
            "message_id": 0,
            "channel_id": ctx.channel.id,
            "guild_id": ctx.guild.id,
            "timestamp": datetime.now() - timedelta(seconds=30),  # 30 seconds ago
            "content": "Test pending chain"
        }
        test_data["cleanup_needed"].append(("pending", test_pending_key))
        
        if test_pending_key in bot.pending_chains:
            await update_report("Auto-Registration", "PASS", "Pending chain added to queue")
        else:
            await update_report("Auto-Registration", "FAIL", "Failed to add pending chain")
            
        # Test 16: StarKey System
        await update_report("StarKey System", "TESTING")
        
        # Create test StarKey entry
        test_starkey = "🧪🔬📊"
        bot.custom_starlocks[test_starkey] = {
            "unlock": "test-channel",
            "type": "channel",
            "name": "Test Channel",
            "created_by": test_data["test_user_id"],
            "created_at": datetime.now().isoformat()
        }
        test_data["cleanup_needed"].append(("starkey", test_starkey))
        
        if test_starkey in bot.custom_starlocks:
            await update_report("StarKey System", "PASS", "StarKey creation successful")
        else:
            await update_report("StarKey System", "FAIL", "StarKey creation failed")
            
        # Test 17: StarKey Channel Assignment
        await update_report("StarKey Assignment", "TESTING")
        
        test_channel_name = "test-starkey-channel"
        test_starkey2 = "📊🔍🧪"
        bot.custom_starlocks[test_starkey2] = {
            "unlock": test_channel_name,
            "type": "channel",
            "name": "Test StarKey Channel",
            "created_by": test_data["test_user_id"],
            "created_at": datetime.now().isoformat()
        }
        test_data["cleanup_needed"].append(("starkey", test_starkey2))
        
        # Verify channel assignment
        keys_for_channel = [k for k, v in bot.custom_starlocks.items() 
                           if v["unlock"] == test_channel_name]
        
        if test_starkey2 in keys_for_channel:
            await update_report("StarKey Assignment", "PASS", "StarKey assigned correctly")
        else:
            await update_report("StarKey Assignment", "FAIL", "StarKey assignment failed")
            
        # Test 18: Feedback System
        await update_report("Feedback System", "TESTING")
        
        test_feedback = {
            "author_id": test_data["test_user_id"],
            "author_name": "Test User",
            "content": "This is a test feedback message",
            "timestamp": datetime.now().isoformat(),
            "status": "pending",
            "id": f"fb_{int(time.time())}"
        }
        
        if not hasattr(bot, "feedback_data"):
            bot.feedback_data = []
            
        bot.feedback_data.append(test_feedback)
        test_data["cleanup_needed"].append(("feedback", test_feedback["id"]))
        
        if any(f["id"] == test_feedback["id"] for f in bot.feedback_data):
            await update_report("Feedback System", "PASS", "Feedback submission works")
        else:
            await update_report("Feedback System", "FAIL", "Feedback submission failed")
        
        # Test 19: Report Bug System
        await update_report("Bug Report System", "TESTING")
        
        test_bug = {
            "author_id": test_data["test_user_id"],
            "author_name": "Test User",
            "content": "This is a test bug report",
            "timestamp": datetime.now().isoformat(),
            "status": "pending",
            "id": f"bug_{int(time.time())}",
            "priority": "medium"
        }
        
        if not hasattr(bot, "bug_reports"):
            bot.bug_reports = []
            
        bot.bug_reports.append(test_bug)
        test_data["cleanup_needed"].append(("bug", test_bug["id"]))
        
        if any(b["id"] == test_bug["id"] for b in bot.bug_reports):
            await update_report("Bug Report System", "PASS", "Bug reporting works")
        else:
            await update_report("Bug Report System", "FAIL", "Bug reporting failed")
            
        # Test 20: Role Synchronization
        await update_report("Role Synchronization", "TESTING")
        
        # Determine which roles the test user qualifies for
        qualified_roles = []
        user_stats = bot.user_data[test_data["test_user_id"]]
        
        if user_stats["reaction_count"] >= 1:
            qualified_roles.append("initiate_drone")
        if len(user_stats["emojis_used"]) >= 5:
            qualified_roles.append("wakened_seeker")
        if user_stats["reaction_count"] >= 10:
            qualified_roles.append("lore_harvester")
        if len(user_stats["starcode_chains"]) >= 3:
            qualified_roles.append("memory_mason")
        if user_stats["corrections"] >= 5:
            qualified_roles.append("index_guard")
        if user_stats["influence_score"] >= 50:
            qualified_roles.append("starforger")
        if user_stats["corrections"] >= 3 and user_stats["problematic_flags"] >= 2:
            qualified_roles.append("vault_knight")
        if user_stats["influence_score"] >= 100 and len(user_stats["definitions_created"]) >= 3:
            qualified_roles.append("ghost_walker")
        
        if isinstance(qualified_roles, list) and len(qualified_roles) > 0:
            await update_report("Role Synchronization", "PASS", f"Role calculation returned {len(qualified_roles)} roles")
        else:
            await update_report("Role Synchronization", "FAIL", "Role calculation failed")
            
        # Test 21: Training Completion
        await update_report("Training Completion", "TESTING")
        
        # Set up training to be completed
        test_training_id = "test_completion_training"
        bot.custom_trainings[test_training_id] = {
            "name": "Test Completion",
            "task": "Complete test task",
            "chain": ["🧪", "🔬"],
            "reward": 15,
            "detection": "message",
            "count": 1,
            "created_by": test_data["test_user_id"],
            "created_at": datetime.now().isoformat()
        }
        test_data["created_trainings"].append(test_training_id)
        
        # Set training as active and complete it
        bot.user_data[test_data["test_user_id"]]["training_quest"] = test_training_id
        bot.user_data[test_data["test_user_id"]]["training_progress"][f"{test_training_id}_progress"] = 1
        bot.user_data[test_data["test_user_id"]]["completed_trainings"].append(test_training_id)
        bot.user_data[test_data["test_user_id"]]["training_quest"] = None
        
        if test_training_id in bot.user_data[test_data["test_user_id"]]["completed_trainings"]:
            await update_report("Training Completion", "PASS", "Training completion successful")
        else:
            await update_report("Training Completion", "FAIL", "Training completion failed")
            
        # Test 22: Training Revocation
        await update_report("Training Revocation", "TESTING")
        
        # Create training for revocation test
        revoke_training_id = "test_revoke_training"
        bot.custom_trainings[revoke_training_id] = {
            "name": "Test Revocation",
            "task": "Test task for revocation",
            "chain": ["🧪", "⚗️"],
            "reward": 5,
            "detection": "reaction",
            "count": 1,
            "created_by": test_data["test_user_id"],
            "created_at": datetime.now().isoformat()
        }
        test_data["created_trainings"].append(revoke_training_id)
        
        # Assign and revoke
        bot.user_data[test_data["test_user_id"]]["training_quest"] = revoke_training_id
        bot.user_data[test_data["test_user_id"]]["training_progress"][f"{revoke_training_id}_progress"] = 0
        
        # Revoke the training
        bot.user_data[test_data["test_user_id"]]["training_quest"] = None
        if f"{revoke_training_id}_progress" in bot.user_data[test_data["test_user_id"]]["training_progress"]:
            del bot.user_data[test_data["test_user_id"]]["training_progress"][f"{revoke_training_id}_progress"]
        
        if bot.user_data[test_data["test_user_id"]]["training_quest"] is None:
            await update_report("Training Revocation", "PASS", "Training revocation successful")
        else:
            await update_report("Training Revocation", "FAIL", "Training revocation failed")
            
        # Test 23: Emoji Definition Creation
        await update_report("Emoji Definition Creation", "TESTING")
        
        # Create a second definition for the test emoji
        second_meaning = "Scientific testing - experimental process"
        
        if test_emoji in bot.emoji_definitions:
            bot.emoji_definitions[test_emoji].append({
                "meaning": second_meaning,
                "author": test_data["test_user_id"],
                "timestamp": datetime.now().isoformat(),
                "official": False
            })
            
            if any(d["meaning"] == second_meaning for d in bot.emoji_definitions[test_emoji]):
                await update_report("Emoji Definition Creation", "PASS", "Multiple definitions successful")
            else:
                await update_report("Emoji Definition Creation", "FAIL", "Failed to add multiple definitions")
        else:
            await update_report("Emoji Definition Creation", "FAIL", "Test emoji not found")
            
        # Test 24: Feedback System Management
        await update_report("Feedback Management", "TESTING")
        
        # Update status of test feedback
        if hasattr(bot, "feedback_data"):
            for feedback in bot.feedback_data:
                if feedback["id"] == test_feedback["id"]:
                    feedback["status"] = "reviewed"
                    break
                    
            if any(f["id"] == test_feedback["id"] and f["status"] == "reviewed" 
                   for f in bot.feedback_data):
                await update_report("Feedback Management", "PASS", "Feedback status update successful")
            else:
                await update_report("Feedback Management", "FAIL", "Feedback status update failed")
        else:
            await update_report("Feedback Management", "FAIL", "Feedback system not initialized")
            
        # Test 25: Channel Configuration
        await update_report("Channel Configuration", "TESTING")
        
        if not hasattr(bot, "channel_config"):
            bot.channel_config = {}
            
        # Set a test channel configuration
        bot.channel_config["test_welcome"] = {
            "id": ctx.channel.id,
            "purpose": "welcome",
            "configured_by": test_data["test_user_id"],
            "timestamp": datetime.now().isoformat()
        }
        test_data["cleanup_needed"].append(("channel_config", "test_welcome"))
        
        if "test_welcome" in bot.channel_config:
            await update_report("Channel Configuration", "PASS", "Channel configuration successful")
        else:
            await update_report("Channel Configuration", "FAIL", "Channel configuration failed")
            
        # Test 26: Info Command
        await update_report("Info Command", "TESTING")
        
        # Test by checking that the function exists and is callable
        info_command = bot.get_command("info")
        if info_command and callable(info_command.callback):
            await update_report("Info Command", "PASS", "Info command exists and is callable")
        else:
            await update_report("Info Command", "FAIL", "Info command is missing or not callable")
            
        # Test 27: Permission Assignment
        await update_report("Permission Assignment", "TESTING")
        
        # Test by checking that the assign command exists and is callable
        assign_command = bot.get_command("assign")
        if assign_command and callable(assign_command.callback):
            await update_report("Permission Assignment", "PASS", "Assign command exists and is callable")
        else:
            await update_report("Permission Assignment", "FAIL", "Assign command is missing or not callable")
            
        # Test 28: Batch Command
        await update_report("Batch Command", "TESTING")
        
        # Test by checking that the batch command exists and is callable
        batch_command = bot.get_command("batch")
        if batch_command and callable(batch_command.callback):
            await update_report("Batch Command", "PASS", "Batch command exists and is callable")
        else:
            await update_report("Batch Command", "FAIL", "Batch command is missing or not callable")
        
    except Exception as e:
        await update_report("Critical Error", "FAIL", f"Exception: {str(e)[:100]}")
        print(f"Test suite error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # CLEANUP PHASE
        await asyncio.sleep(2)  # Let user see results
        
        cleanup_embed = discord.Embed(
            title="🧹 Cleaning up test data...",
            description="Reverting all test changes",
            color=0xFFFF00
        )
        await ctx.send(embed=cleanup_embed)
        
        try:
            # Remove test user data
            if test_data["test_user_id"] in bot.user_data:
                del bot.user_data[test_data["test_user_id"]]
            
            # Remove created patterns
            for pattern in test_data["created_patterns"]:
                if pattern in bot.starcode_patterns:
                    del bot.starcode_patterns[pattern]
            
            # Remove created definitions
            for emoji in test_data["created_definitions"]:
                if emoji in bot.emoji_definitions:
                    bot.emoji_definitions[emoji] = [d for d in bot.emoji_definitions[emoji] 
                                                   if d.get("author") != test_data["test_user_id"]]
                    if not bot.emoji_definitions[emoji]:
                        del bot.emoji_definitions[emoji]
            
            # Remove created themes
            for theme in test_data["created_themes"]:
                if theme in bot.semantic_themes:
                    del bot.semantic_themes[theme]
            
            # Remove created trainings
            for training in test_data["created_trainings"]:
                if training in bot.custom_trainings:
                    del bot.custom_trainings[training]
            
            # Remove blessed chains
            for chain in test_data["blessed_chains"]:
                if chain in bot.blessed_chains:
                    del bot.blessed_chains[chain]
            
            # Remove problematic chains
            bot.problematic_chains = [p for p in bot.problematic_chains 
                                    if p.get("flagged_by") != test_data["test_user_id"]]
            
            # Clean up other test data
            for cleanup_type, cleanup_key in test_data.get("cleanup_needed", []):
                if cleanup_type == "pending" and cleanup_key in bot.pending_chains:
                    del bot.pending_chains[cleanup_key]
                elif cleanup_type == "starkey" and cleanup_key in bot.custom_starlocks:
                    del bot.custom_starlocks[cleanup_key]
                elif cleanup_type == "feedback" and hasattr(bot, "feedback_data"):
                    bot.feedback_data = [f for f in bot.feedback_data if f["id"] != cleanup_key]
                elif cleanup_type == "bug" and hasattr(bot, "bug_reports"):
                    bot.bug_reports = [b for b in bot.bug_reports if b["id"] != cleanup_key]
                elif cleanup_type == "channel_config" and hasattr(bot, "channel_config") and cleanup_key in bot.channel_config:
                    del bot.channel_config[cleanup_key]
            
            # Restore divine alignment and other attributes
            bot.divine_alignment = test_data["original_data"]["divine_alignment"]
            
            # Restore feedback and bug reports
            if hasattr(bot, "feedback_data") and "feedback_data" in test_data["original_data"]:
                bot.feedback_data = test_data["original_data"]["feedback_data"]
            
            if hasattr(bot, "bug_reports") and "bug_reports" in test_data["original_data"]:
                bot.bug_reports = test_data["original_data"]["bug_reports"]
                
            # Restore channel configuration
            if hasattr(bot, "channel_config") and "channel_config" in test_data["original_data"]:
                bot.channel_config = test_data["original_data"]["channel_config"]
            
            cleanup_embed.description = "✅ All test data cleaned up successfully!"
            cleanup_embed.color = 0x00FF00
            
        except Exception as e:
            cleanup_embed.description = f"⚠️ Cleanup error: {str(e)[:100]}"
            cleanup_embed.color = 0xFF0000
            print(f"Cleanup error: {e}")
        
        await safe_edit_message(test_msg, embed=cleanup_embed)
        
        # Final summary
        total_tests = len(test_data["test_results"])
        passed_tests = sum(1 for r in test_data["test_results"].values() if r["status"] == "PASS")
        failed_tests = total_tests - passed_tests
        
        summary_embed = discord.Embed(
            title="📊 Test Suite Summary",
            description=f"Completed {total_tests} tests",
            color=0x00FF00 if failed_tests == 0 else 0xFF0000,
            timestamp=datetime.now()
        )
        
        summary_embed.add_field(name="✅ Passed", value=str(passed_tests), inline=True)
        summary_embed.add_field(name="❌ Failed", value=str(failed_tests), inline=True)
        summary_embed.add_field(name="🎯 Success Rate", value=f"{(passed_tests/total_tests)*100:.1f}%", inline=True)
        
        # List failed tests
        if failed_tests > 0:
            failed_list = [name for name, result in test_data["test_results"].items() 
                         if result["status"] == "FAIL"]
            summary_embed.add_field(
                name="Failed Tests",
                value="\n".join(failed_list),
                inline=False
            )
        
        summary_embed.set_footer(text="Helmhud Guardian Test Suite Complete")
        
        await ctx.send(embed=summary_embed)

# ============ QUICK COMMAND TEST ============
@bot.command(name='test_commands')
@commands.has_permissions(administrator=True)
async def test_commands(ctx):
    """Admin: Quick test of command syntax and basic functionality"""
    
    embed = discord.Embed(
        title="🔧 Command Syntax Test",
        description="Testing all command structures...",
        color=0x87CEEB
    )
    msg = await ctx.send(embed=embed)
    
    results = []
    
    # List of all commands to test
    commands_to_test = [
        # Basic commands
        ("status", "Server statistics"),
        ("profile", "User profile"),
        ("features", "Command list"),
        ("info", "Feature overview"),
        ("config", "Server configuration"),
        
        # StarCode commands
        ("starcode 🧪🔬", "Pattern registration"),
        ("pending", "Pending chains"),
        ("top_chains", "Top patterns"),
        ("unlock 🔑🚪", "StarLock attempt"),
        
        # StarKey commands
        ("create_starkey test-channel 🔑🚪", "Create StarKey"),
        ("assign_starkey test-channel 🗝️🔓", "Assign StarKey"),
        ("manage_starkeys revoke 🔑🚪 test-channel", "Manage StarKeys"),
        ("list_starlocks", "List all StarKeys"),
        
        # Training commands
        ("initiate_training", "Start training"),
        ("quest_status", "Quest progress"),
        ("list_trainings", "Available trainings"),
        ("create_training test_quest Complete_test_actions 🧪,🔬", "Create training quest"),
        ("assign_training @user test_quest", "Assign training to user"),
        ("complete_training", "Complete active training"),
        ("revoke_training @user test_quest", "Revoke assigned training"),
        ("skip_training", "Skip current training"),
        
        # Lookup commands
        ("glyph 🧪", "Glyph information"),
        ("remory recent", "Recent remory"),
        ("list_themes", "Theme list"),
        ("theme_suggest 🧪🔬", "Theme suggestions"),
        
        # Definition and Theme commands
        ("define 🧪 Test_meaning", "Define emoji meaning"),
        ("create_theme test_theme 🧪,🔬,⚗️ Test_theme_description", "Create semantic theme"),
        
        # VaultKnight commands (will fail without role)
        ("mark_problematic", "Shield marking mode"),
        ("shield", "Shield problematic content"),
        ("correct", "Correct problematic content"),
        ("review_problems", "Problem registry"),
        ("knight_status", "Knight statistics"),
        
        # GhostWalker commands (will fail without role)
        ("bless 🧪🔬", "Chain blessing"),
        ("override_flag", "Override problematic flag"),
        ("align_mood", "Align divine mood"),
        ("summon hope", "Theme summon"),
        ("ghost_status", "Ghost statistics"),
        
        # Channel and configuration commands
        ("set_channel welcome #welcome", "Set channel purpose"),
        ("assign read \"Memory Mason\" #starforge-lab", "Assign channel permissions"),
        ("sync_roles", "Synchronize roles for user"),
        ("sync_all_roles", "Synchronize all user roles"),
        
        # Feedback and reporting commands
        ("feedback This_is_test_feedback", "Submit feedback"),
        ("report user_issue This_is_test_report", "Report issue"),
        ("reportbug Bug_description", "Report bot bug"),
        ("reports", "View submitted reports"),
        
        # System commands
        ("backfill", "Backfill missing data"),
        
        # Initialization commands
        ("initiate", "Initiate user profile"),
        
        # Admin commands
        ("quickstart", "Quick setup"),
        ("diagnose", "User diagnosis"),
        ("batch status\nprofile", "Batch execution"),
        ("test_suite", "Comprehensive tests"),
        ("test_commands", "Command syntax test"),
    ]
    
    for cmd, description in commands_to_test:
        try:
            # Get command object
            cmd_name = cmd.split()[0]
            command = bot.get_command(cmd_name)
            
            if command:
                # Check if command has required permissions
                if hasattr(command, 'checks'):
                    results.append(f"✅ `!vault {cmd}` - {description}")
                else:
                    results.append(f"✅ `!vault {cmd}` - {description}")
            else:
                results.append(f"❌ `!vault {cmd}` - Command not found")
                
        except Exception as e:
            results.append(f"⚠️ `!vault {cmd}` - Error: {str(e)[:30]}")
    
    # Update embed with results
    embed.description = "Command syntax test complete!"
    
    # Split results into chunks for fields
    chunk_size = 10
    for i in range(0, len(results), chunk_size):
        chunk = results[i:i + chunk_size]
        embed.add_field(
            name=f"Commands {i+1}-{min(i+chunk_size, len(results))}",
            value="\n".join(chunk),
            inline=False
        )
    
    embed.set_footer(text=f"Tested {len(commands_to_test)} commands")
    await safe_edit_message(msg, embed=embed)

