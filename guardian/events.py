import discord
from discord.ext import tasks
from .bot import bot
from .utils import *
from .config import *
from .commands import cleanup_shield_listeners, cleanup_report_cooldowns
import asyncio
import re
from .llm import ensure_model_downloaded

# ============ EVENT HANDLERS ============
@bot.event
async def on_ready():
    print(f'✠ {bot.user} has connected to the Vault')
    print(f'✠ Serving {len(bot.guilds)} guild(s)')
    print(f'✠ The semantic field awaits...')
    ensure_model_downloaded()

    # Start tasks only if they're not already running
    if not cleanup_shield_listeners.is_running():
        cleanup_shield_listeners.start()
    if not auto_register_chains.is_running():
        auto_register_chains.start()
    if not auto_register_reaction_chains.is_running():
        auto_register_reaction_chains.start()
    if not cleanup_report_cooldowns.is_running():
        cleanup_report_cooldowns.start()

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    
    # Check if this is a shield marking reaction
    if str(reaction.emoji) == "🛡️" and user.id in bot.shield_listeners:
        # This is a marking action
        message = reaction.message
        sequences = find_contiguous_emoji_chains(message.content)
        if sequences:
            emojis = sequences[0]
            chain_key = "".join(emojis)
            
            # Remove from pending chains immediately
            pending_keys_to_remove = []
            for key, data in bot.pending_chains.items():
                if data["message_id"] == message.id:
                    pending_keys_to_remove.append(key)
            
            for key in pending_keys_to_remove:
                del bot.pending_chains[key]
            
            # Unregister if already registered
            if chain_key in bot.starcode_patterns:
                await unregister_chain(chain_key, "problematic", user.id)
            
            # Add to problematic registry
            bot.problematic_chains.append({
                "chain": chain_key,
                "flagged_by": user.id,
                "timestamp": datetime.now(),
                "message_id": message.id,
                "author_id": message.author.id,
                "context": message.content[:100]
            })
            
            # Apply influence penalty
            bot.user_data[message.author.id]["influence_score"] -= 15
            bot.user_data[user.id]["problematic_flags"] += 1
            
            # Send confirmation
            channel = bot.shield_listeners[user.id]["channel"]
            embed = discord.Embed(
                title="⚠️ StarCode Marked Problematic",
                color=0xFF6347
            )
            embed.add_field(name="Chain", value=chain_key)
            embed.add_field(name="Author", value=f"<@{message.author.id}>")
            embed.add_field(name="Effect", value="Chain unregistered\nInfluence reverted\n-15 penalty applied")
            embed.add_field(name="Context", value=message.content[:100], inline=False)
            embed.add_field(name="Location", value=f"[Jump to message]({message.jump_url})", inline=False)
            
            await channel.send(embed=embed)
            
            # Remove listener
            del bot.shield_listeners[user.id]
            
            # Check training progress for shield action
            if await check_training_progress(user.id, "shield", None, channel):
                await complete_training_quest(user, channel)
        
        return
    
    # Normal reaction tracking
    emoji = str(reaction.emoji)
    bot.user_data[user.id]["emojis_used"].add(emoji)
    bot.user_data[user.id]["reaction_count"] += 1
    
    # Check for StarCode chains in message reactions, preserving duplicates
    message_reactions = get_reaction_emojis(reaction.message)

    if detect_starcode_chain(message_reactions):
        # Calculate influence with reuse bonus
        influence = calculate_chain_influence(message_reactions, user.id, bot)
        bot.user_data[user.id]["influence_score"] += influence
        bot.user_data[user.id]["starcode_chains"].append(message_reactions)

        # Track chain adoption
        chain_key = "".join(message_reactions)
        if chain_key in bot.user_data[user.id]["chains_adopted"]:
            bot.user_data[user.id]["chains_adopted"][chain_key] += 1
        else:
            bot.user_data[user.id]["chains_adopted"][chain_key] = 1


        # Visual indicator the chain is being tracked
        # Add a sparkle reaction only once to indicate tracking
        try:
            if all(str(r.emoji) != "✨" for r in reaction.message.reactions):
                await reaction.message.add_reaction("✨")
        except Exception:
            pass

        # Track the message for potential reaction chain auto-registration.
        # The timestamp is updated on each reaction so the chain must persist
        # for a full minute without changes.
        # Track message for potential reaction chain auto-registration

        bot.pending_reaction_chains[reaction.message.id] = {
            "channel_id": reaction.message.channel.id,
            "guild_id": reaction.message.guild.id,
            "author": reaction.message.author.id,

            "chain": message_reactions,
            "timestamp": datetime.now(),
        }
    
    # Check role progression and announce in the configured progression channel
    await check_role_progression(user, reaction.message.guild)

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    emoji_sequences = find_contiguous_emoji_chains(message.content)
    for emojis in emoji_sequences:
        chain_key = "".join(emojis)

        bot.pending_chains[f"{message.id}_{chain_key}"] = {
            "chain": emojis,
            "author": message.author.id,
            "message_id": message.id,
            "channel_id": message.channel.id,
            "guild_id": message.guild.id,
            "timestamp": datetime.now(),
            "content": message.content
        }

        await message.add_reaction("✨")

        remory_text = strip_all_mentions(message.content)
        remory = {
            "author": message.author.id,
            "chain": emojis,
            "timestamp": datetime.now(),
            "context": remory_text[:100],
            "channel": message.channel.name,
            "message_id": message.id
        }
        bot.user_data[message.author.id]["remory_strings"].append(remory)
        from .llm import invalidate_index
        invalidate_index()

        unlock_message = await check_starlock(emojis, message.author, message.guild)
        if unlock_message:
            await message.channel.send(unlock_message)

        if await check_training_progress(message.author.id, "message", message.content, message.channel):
            await complete_training_quest(message.author, message.channel)
    if not emoji_sequences:
        remory_text = strip_all_mentions(message.content)
        if remory_text.strip():
            remory = {
                "author": message.author.id,
                "chain": [],
                "timestamp": datetime.now(),
                "context": remory_text[:100],
                "channel": message.channel.name,
                "message_id": message.id,
            }
            bot.user_data[message.author.id]["remory_strings"].append(remory)
            from .llm import invalidate_index
            invalidate_index()

    # LLM chat when the bot is mentioned
    if bot.user in message.mentions:
        query = strip_bot_mentions(message.content)

        # Gather recent context excluding the bot's own messages
        recent_lines = []
        async for msg in message.channel.history(limit=5, before=message):
            if msg.author.bot:
                continue
            clean_text = strip_all_mentions(msg.clean_content)
            recent_lines.append(f"{msg.author.display_name}: {clean_text}")
        recent_lines.reverse()
        recent_context = "\n".join(recent_lines)

        from .llm import get_similar, generate_reply
        memories = get_similar(query, k=5)
        unique_memories = []
        seen = set()
        for mem in memories:
            if mem not in seen:
                unique_memories.append(mem)
                seen.add(mem)
        memory_block = "\n".join(strip_all_mentions(mem) for mem in unique_memories)

        prompt = (
            "You are Helmhud Guardian, a helpful Discord bot. "
            "Respond to the user based on the conversation and memories.\n\n"
            "### Recent Conversation:\n" + recent_context +
            "\n\n### Influential Memories:\n" + memory_block +
            "\n\n### User Query:\n" + query +
            "\n\n### Reply:\n"
        )
        reply = await asyncio.to_thread(generate_reply, prompt)
        # Remove any bot mentions the model produced
        reply = re.sub(rf"<@!?{bot.user.id}>", "", reply)
        reply = reply.replace(f"@{bot.user.display_name}", "")
        reply = reply.replace(f"@{bot.user.name}", "")
        reply = reply.strip()

        # Prepend the author's mention and avoid double mention
        reply = f"{message.author.mention} {reply}".strip()
        await message.reply(reply, mention_author=False)
        return
    await bot.process_commands(message)

async def complete_training_quest(user, channel):
    """Complete a training quest and progress to next"""
    user_data = bot.user_data[user.id]
    current_training = user_data.get("training_quest")
    
    if not current_training:
        return
        
    # Get quest data
    if current_training in DEFAULT_TRAINING_QUESTS:
        quest = DEFAULT_TRAINING_QUESTS[current_training]
    elif current_training in bot.custom_trainings:
        quest = bot.custom_trainings[current_training]
    else:
        return
    
    # Award reward
    user_data["influence_score"] += quest["reward"]
    user_data["completed_trainings"].append(current_training)
    
    # Notify completion
    embed = discord.Embed(
        title="✅ Quest Complete!",
        description=f"**{quest['name']}** completed!",
        color=0x90EE90
    )
    embed.add_field(name="Reward", value=f"+{quest['reward']} influence")
    
    await channel.send(f"{user.mention}", embed=embed)
    
    # Progress to next quest
    next_quest = quest.get("next")
    if next_quest == "complete":
        user_data["training_quest"] = None
        await channel.send("🎓 **Training Complete!** You're now a true Vault citizen!")
        # Check for more assigned trainings
        if user.id in bot.training_assignments and bot.training_assignments[user.id]:
            next_assigned = bot.training_assignments[user.id].pop(0)
            user_data["training_quest"] = next_assigned
            await show_training_quest(user, channel, next_assigned)
    elif next_quest:
        user_data["training_quest"] = next_quest
        await show_training_quest(user, channel, next_quest)

async def show_training_quest(user, channel, quest_id):
    """Display a training quest to user"""
    if quest_id in DEFAULT_TRAINING_QUESTS:
        quest = DEFAULT_TRAINING_QUESTS[quest_id]
    elif quest_id in bot.custom_trainings:
        quest = bot.custom_trainings[quest_id]
    else:
        return
    
    embed = discord.Embed(
        title=f"🎯 New Quest: {quest['name']}",
        description=quest.get("description", quest["task"]),
        color=0x87CEEB
    )
    
    if "chain" in quest:
        embed.add_field(name="🔗 Required Chain", value="".join(quest["chain"]))
    
    embed.add_field(name="📋 Task", value=quest["task"])
    embed.add_field(name="🎁 Reward", value=f"+{quest['reward']} influence")
    
    count = quest.get("count", 1)
    if count > 1:
        embed.add_field(name="📊 Required", value=f"{count} times")
    
    # Show current progress if any
    progress_key = f"{quest_id}_progress"
    current_progress = bot.user_data[user.id]["training_progress"].get(progress_key, 0)
    if current_progress > 0:
        embed.add_field(name="Current Progress", value=f"{current_progress}/{count}")
    
    await channel.send(f"{user.mention}", embed=embed)

# ============ AUTO-REGISTRATION SYSTEM ============
@tasks.loop(seconds=30)
async def auto_register_chains():
    """Auto-register chains that have persisted for 1 minute"""
    current_time = datetime.now()
    to_register = []
    
    for key, chain_data in list(bot.pending_chains.items()):
        # Check if 1 minute has passed
        if (current_time - chain_data["timestamp"]).seconds >= 60:
            to_register.append((key, chain_data))
    
    for key, chain_data in to_register:
        chain_key = "".join(chain_data["chain"])
        
        # Check if already registered
        if chain_key not in bot.starcode_patterns:
            # Auto-register
            bot.starcode_patterns[chain_key] = {
                "author": chain_data["author"],
                "created": datetime.now().isoformat(),
                "uses": 1,
                "description": f"Auto-registered from: {chain_data['content'][:50]}...",
                "pattern": chain_key,
                "message_id": chain_data["message_id"],
                "auto_registered": True
            }

            # Persist the new registration immediately
            bot.save_data()
            
            # Track original author's chain
            bot.user_data[chain_data["author"]]["chains_originated"][chain_key] = 1
            
            # Award influence and track it
            influence_gain = 10
            bot.user_data[chain_data["author"]]["influence_score"] += influence_gain
            
            # Track influence history for potential reversal
            bot.influence_history[chain_data["author"]].append({
                "amount": influence_gain,
                "reason": "auto_register",
                "chain": chain_key,
                "timestamp": datetime.now(),
                "reversible": True
            })
            
            # Notify in vault channel if possible
            try:
                vault_id = bot.get_channel_for_feature(chain_data['guild_id'], 'remory_archive')
                if vault_id:
                    channel = bot.get_channel(int(vault_id))
                else:
                    guild = bot.get_guild(chain_data['guild_id'])
                    default_name = CHANNEL_CONFIG['remory_archive']['default_name']
                    channel = discord.utils.get(guild.channels, name=default_name) if guild else None

                if channel:
                    embed = discord.Embed(
                        title='✨ StarCode Auto-Registered',
                        description=f'Pattern **{chain_key}** has been registered',
                        color=0x90EE90
                    )
                    embed.add_field(name='Author', value=f'<@{chain_data["author"]}>')
                    embed.set_footer(text='Chain persisted for 1 minute without correction')
                    await safe_send(channel, embed=embed)
            except Exception:
                pass
        del bot.pending_chains[key]

# ============ REACTION AUTO-REGISTRATION ============
@tasks.loop(seconds=30)
async def auto_register_reaction_chains():
    """Auto-register reaction chains that persist for 1 minute"""
    current_time = datetime.now()
    to_register = []

    for msg_id, data in list(bot.pending_reaction_chains.items()):
        if (current_time - data["timestamp"]).seconds >= 60:
            to_register.append((msg_id, data))

    for msg_id, data in to_register:
        channel = bot.get_channel(data["channel_id"])
        if not channel:
            del bot.pending_reaction_chains[msg_id]
            continue

        try:
            message = await channel.fetch_message(msg_id)
        except Exception:
            del bot.pending_reaction_chains[msg_id]
            continue
            
        # Get reaction emojis including duplicates and ignoring the sparkle indicator
        message_reactions = get_reaction_emojis(message)

        if detect_starcode_chain(message_reactions):
            chain_key = "".join(message_reactions)

            if chain_key not in bot.starcode_patterns:
                bot.starcode_patterns[chain_key] = {
                    "author": data["author"],
                    "created": datetime.now().isoformat(),
                    "uses": 1,
                    "description": "Auto-registered from reactions",
                    "pattern": chain_key,
                    "message_id": msg_id,
                    "auto_registered": True,
                }

                bot.save_data()

                bot.user_data[data["author"]]["chains_originated"][chain_key] = 1

                influence_gain = 10
                bot.user_data[data["author"]]["influence_score"] += influence_gain

                bot.influence_history[data["author"]].append({
                    "amount": influence_gain,
                    "reason": "auto_register_reaction",
                    "chain": chain_key,
                    "timestamp": datetime.now(),
                    "reversible": True,
                })

                try:
                    vault_id = bot.get_channel_for_feature(data["guild_id"], "remory_archive")
                    if vault_id:
                        notify_channel = bot.get_channel(int(vault_id))
                    else:
                        guild = bot.get_guild(data["guild_id"])
                        default_name = CHANNEL_CONFIG["remory_archive"]["default_name"]
                        notify_channel = discord.utils.get(guild.channels, name=default_name) if guild else None

                    if notify_channel:
                        embed = discord.Embed(
                            title="✨ StarCode Auto-Registered",
                            description=f"Pattern **{chain_key}** has been registered",
                            color=0x90EE90,
                        )
                        embed.add_field(name="Author", value=f"<@{data['author']}>")
                        embed.set_footer(text="Chain persisted for 1 minute without correction")
                        await safe_send(notify_channel, embed=embed)
                except Exception:
                    pass

        del bot.pending_reaction_chains[msg_id]
