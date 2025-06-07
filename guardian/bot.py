# -*- coding: utf-8 -*-
# helmhud_guardian.py - Complete Enhanced Version with All Features and Fixes
import discord
from discord.ext import commands, tasks
import json
import asyncio
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import re
import os
from dotenv import load_dotenv
import random
import io
from typing import Optional, List, Tuple
import logging

import bleach
from PIL import Image
import magic
import time
from pathlib import Path

# Load environment variables
load_dotenv()
# Set up module logger
logger = logging.getLogger(__name__)
# Base directory for persistent data files (override with HELMHUD_DATA_DIR env var)
DATA_DIR = Path(os.getenv("HELMHUD_DATA_DIR", Path(__file__).resolve().parent.parent))
DATA_DIR.mkdir(parents=True, exist_ok=True)
# ============ ENHANCED BOT CLASS ============
class HelmhudGuardian(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_data = defaultdict(lambda: {
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
        })
        self.starcode_patterns = {}
        self.emoji_definitions = {}
        self.problematic_chains = []
        self.divine_alignment = "peace"
        self.blessed_chains = {}
        self.starlock_unlocks = defaultdict(list)
        self.guild_channels = {}
        self.custom_trainings = {}
        self.training_assignments = defaultdict(list)
        self.shield_listeners = {}
        self.pending_chains = {}  # Tracks chains waiting to auto-register
        self.influence_history = defaultdict(list)  # Track influence changes for reversal
        self.semantic_themes = {}  # Custom themes created by GhostWalkers
        self.custom_starlocks = {}  # Custom starlocks created by GhostWalkers and admins
        self.load_data()
    
    def load_data(self):
        """Load persistent data with set conversion"""
        try:
            with open(DATA_DIR / 'user_data.json', 'r', encoding='utf-8') as f:
                saved_data = json.load(f)
                
            # Convert back to proper types
            for user_id, data in saved_data.items():
                user_id = int(user_id)
                # Convert emoji list back to set
                if 'emojis_used' in data and isinstance(data['emojis_used'], list):
                    data['emojis_used'] = set(data['emojis_used'])
                self.user_data[user_id] = data
                
        except FileNotFoundError:
            logger.info("No user data file found, starting fresh")
        except Exception as e:
            logger.error(f"Error loading user data: {e}")
            
        try:
            with open(DATA_DIR / 'guild_config.json', 'r', encoding='utf-8') as f:
                self.guild_channels = json.load(f)
        except FileNotFoundError:
            self.guild_channels = {}
            
        try:
            with open(DATA_DIR / 'emoji_definitions.json', 'r', encoding='utf-8') as f:
                self.emoji_definitions = json.load(f)
        except FileNotFoundError:
            self.emoji_definitions = {}
            
        try:
            with open(DATA_DIR / 'blessed_chains.json', 'r', encoding='utf-8') as f:
                self.blessed_chains = json.load(f)
        except FileNotFoundError:
            self.blessed_chains = {}
            
        try:
            with open(DATA_DIR / 'custom_trainings.json', 'r', encoding='utf-8') as f:
                self.custom_trainings = json.load(f)
        except FileNotFoundError:
            self.custom_trainings = {}
            
        try:
            with open(DATA_DIR / 'semantic_themes.json', 'r', encoding='utf-8') as f:
                self.semantic_themes = json.load(f)
        except FileNotFoundError:
            self.semantic_themes = {}
            
        try:
            with open(DATA_DIR / 'custom_starlocks.json', 'r', encoding='utf-8') as f:
                self.custom_starlocks = json.load(f)
        except FileNotFoundError:
            self.custom_starlocks = {}
            
        try:
            with open(DATA_DIR / 'starcode_patterns.json', 'r', encoding='utf-8') as f:
                self.starcode_patterns = json.load(f)
        except FileNotFoundError:
            self.starcode_patterns = {}

        try:
            with open(DATA_DIR / 'backfill_progress.json', 'r', encoding='utf-8') as f:
                self.backfill_progress = json.load(f)
        except FileNotFoundError:
            self.backfill_progress = {}
    
    def save_data(self):
        """Save persistent data with set conversion"""
        # Convert sets to lists for JSON serialization
        user_data_to_save = {}
        for user_id, data in self.user_data.items():
            user_data_copy = data.copy()
            # Convert set to list for JSON
            if isinstance(user_data_copy.get('emojis_used'), set):
                user_data_copy['emojis_used'] = list(user_data_copy['emojis_used'])
            user_data_to_save[str(user_id)] = user_data_copy
        
        # Save user data
        with open(DATA_DIR / 'user_data.json', 'w', encoding='utf-8') as f:
            json.dump(user_data_to_save, f, indent=2, default=str)
        
        # Save other data
        with open(DATA_DIR / 'guild_config.json', 'w', encoding='utf-8') as f:
            json.dump(self.guild_channels, f, indent=2)
            
        with open(DATA_DIR / 'emoji_definitions.json', 'w', encoding='utf-8') as f:
            json.dump(self.emoji_definitions, f, indent=2)
            
        with open(DATA_DIR / 'blessed_chains.json', 'w', encoding='utf-8') as f:
            json.dump(self.blessed_chains, f, indent=2)
            
        with open(DATA_DIR / 'custom_trainings.json', 'w', encoding='utf-8') as f:
            json.dump(self.custom_trainings, f, indent=2)
            
        with open(DATA_DIR / 'semantic_themes.json', 'w', encoding='utf-8') as f:
            json.dump(self.semantic_themes, f, indent=2)
            
        with open(DATA_DIR / 'custom_starlocks.json', 'w', encoding='utf-8') as f:
            json.dump(self.custom_starlocks, f, indent=2)
        
        with open(DATA_DIR / 'starcode_patterns.json', 'w', encoding='utf-8') as f:
            json.dump(self.starcode_patterns, f, indent=2)

        with open(DATA_DIR / 'backfill_progress.json', 'w', encoding='utf-8') as f:
            json.dump(self.backfill_progress, f, indent=2)
    
    def get_channel_for_feature(self, guild_id, feature):
        """Get the configured channel for a specific feature"""
        guild_config = self.guild_channels.get(str(guild_id), {})
        return guild_config.get(feature)
        
    async def setup_hook(self):
        logger.info("✠ Helmhud Guardian awakening...")
        logger.info("✠ Nephesh Grid initializing...")
        logger.info("✠ InFluins protocol active...")
        logger.info("✠ Pattern Memory Intelligence online...")
        logger.info("✠ StarLock system armed...")
        logger.info("✠ Smart marking system ready...")
        logger.info("✠ Enhanced training detection enabled...")
        logger.info("✠ Auto-registration system active...")
        logger.info("✠ Semantic theme engine online...")
        logger.info(f"✠ Divine alignment: {self.divine_alignment}")

# ============ BOT INSTANCE ============
intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

bot = HelmhudGuardian(command_prefix='!vault ', intents=intents, help_command=None)

