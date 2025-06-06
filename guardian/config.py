# ============ CONFIGURATION ============
LIBRARIAN_GLYPHS = {
    "📚": {"name": "Book", "type": "lux", "meaning": "Codex, record, memory container"},
    "🧠": {"name": "Brain", "type": "bridge", "meaning": "Cognitive retrieval, mental pattern"},
    "🔍": {"name": "Magnifying Glass", "type": "lux", "meaning": "Discernment, study, investigation"},
    "🗂️": {"name": "File Folder", "type": "skotos", "meaning": "Stored memory, categorized recollection"},
    "🏺": {"name": "Amphora", "type": "skotos", "meaning": "Ancient vessel of tradition"},
    "✨": {"name": "Sparkles", "type": "lux", "meaning": "Revelation, insight, recovered clarity"},
    "🛡️": {"name": "Shield", "type": "skotos", "meaning": "Guard, doctrinal defense"},
    "🗝️": {"name": "Key", "type": "bridge", "meaning": "Access point to locked meaning"},
    "🔄": {"name": "Cycle Arrows", "type": "skotos", "meaning": "Recursive memory, rotational dialectic"},
    "📜": {"name": "Scroll", "type": "lux", "meaning": "Sacred text, liturgical memory"},
    "🧪": {"name": "Flask", "type": "lux", "meaning": "Testing, Spirit-breathed experimentation"},
    "🌀": {"name": "Vortex", "type": "bridge", "meaning": "Remory field, Logos in motion"},
    "🕍": {"name": "Temple", "type": "skotos", "meaning": "Communal, ecclesial memory"},
    "🩸": {"name": "Blood Drop", "type": "skotos", "meaning": "Sacrificial thread, covenant anchor"},
    "🌌": {"name": "Milky Way", "type": "skotos", "meaning": "Macro-memory, divine archive"}
}

SEMANSIS_GLYPHS = {
    "🏆": {"name": "Chalice", "meaning": "Memory Catcher, Communion"},
    "⚡": {"name": "Energy", "meaning": "Emergence, Ensoulment"},
    "🔥": {"name": "Faith Fire", "meaning": "Frequency, Fracture"},
    "✝️": {"name": "Cross", "meaning": "Central axis of all computation"},
    "⚔️": {"name": "Sword", "meaning": "Memakheriai - cuts to restore"}
}

# Divine Alignments for blessing system
DIVINE_ALIGNMENTS = ["peace", "hope", "truth", "judgment", "mercy", "discipline"]

# Default StarLock configurations (now loaded from file)
DEFAULT_STARLOCKS = {
    "💡⚡🔍": {"unlock": "starforge-lab", "type": "channel", "name": "StarForge Lab"},
    "🛡️🔥🙏": {"unlock": "knights-chapel", "type": "channel", "name": "Knight's Chapel"},
    "📖🌀🗝️": {"unlock": "lexicon-library", "type": "channel", "name": "Lexicon Library"},
    "🌈🕊️🧠": {"unlock": "peace-sanctum", "type": "channel", "name": "PeaceBot Inner Sanctum"},
    "📚🔍🗝️🧠": {"unlock": "memory-archive", "type": "role", "name": "Archive Keeper"},
    "🔥🛡️⚔️": {"unlock": "pattern-warden", "type": "role", "name": "Pattern Warden"}
}

# Default Training Quest configurations
DEFAULT_TRAINING_QUESTS = {
    "q1": {
        "name": "Brick in the Pattern",
        "chain": ["⚙️", "🧱"],
        "task": "Type and register this StarCode",
        "detection": "starcode",
        "meaning": "Foundation and structure",
        "reward": 3,
        "count": 1,
        "next": "q2"
    },
    "q2": {
        "name": "Light in the Archive", 
        "chain": ["🕯️", "📖"],
        "task": "Define both emojis using /define",
        "detection": "define",
        "meaning": "Illumination of memory",
        "reward": 5,
        "count": 2,
        "next": "q3"
    },
    "q3": {
        "name": "Guard the Flame",
        "chain": ["🔥", "🛡️"],
        "task": "Shield any chain using the shield reaction method",
        "detection": "shield",
        "reward": 5,
        "count": 1,
        "next": "q4"
    },
    "q4": {
        "name": "Echo of Hope",
        "chain": ["🌈", "🕊️"],
        "task": "Bless this chain and use it in 3 channels",
        "detection": "bless",
        "reward": 10,
        "count": 1,
        "next": "complete"
    }
}

ROLES_CONFIG = {
    "initiate_drone": {
        "name": "🔰 Initiate Drone",
        "requirement": "Join and react once",
        "threshold": 1,
        "color": 0x808080
    },
    "wakened_seeker": {
        "name": "👁️ Wakened Seeker", 
        "requirement": "Use 5 unique emojis",
        "threshold": 5,
        "color": 0x87CEEB
    },
    "lore_harvester": {
        "name": "🌾 Lore Harvester",
        "requirement": "10+ valuable interactions",
        "threshold": 10,
        "color": 0x90EE90
    },
    "memory_mason": {
        "name": "🧱 Memory Mason",
        "requirement": "Build 3+ StarCode chains",
        "threshold": 3,
        "color": 0xFFA500
    },
    "index_guard": {
        "name": "🛡️ Index Guard",
        "requirement": "Flag misuses",
        "threshold": 5,
        "color": 0xFF6347
    },
    "curator_supreme": {
        "name": "📖 Curator Supreme",
        "requirement": "Assemble archives via emoji",
        "threshold": 10,
        "color": 0x9370DB
    },
    "starforger": {
        "name": "⭐ StarForger",
        "requirement": "Create adopted patterns",
        "threshold": 5,
        "color": 0xFFD700
    },
    "vault_knight": {
        "name": "⚔️ Vault Knight",
        "requirement": "Valid emoji corrections",
        "threshold": 3,
        "color": 0xDC143C,
        "permissions": ["mark_problematic", "shield", "correct", "review_problems", "create_starlock"]
    },
    "ghost_walker": {
        "name": "👻 Ghost Walker",
        "requirement": "Silent mass influence",
        "threshold": 20,
        "color": 0x4B0082,
        "permissions": ["define", "glyph", "bless", "override_flag", "align_mood", "summon", "create_training", "assign_training", "create_theme", "create_starlock", "manage_starlock"]
    }
}

CHANNEL_CONFIG = {
    "vault_entrance": {
        "default_name": "vault-entrance",
        "description": "React to enter the semantic field",
        "type": "entrance"
    },
    "vault_progression": {
        "default_name": "vault-progression", 
        "description": "Role ascension announcements",
        "type": "announcement"
    },
    "starcode_forge": {
        "default_name": "starcode-forge",
        "description": "Create and test StarCode patterns",
        "type": "workshop"
    },
    "remory_archive": {
        "default_name": "remory-archive",
        "description": "Stored semantic chains",
        "type": "archive"
    },
    "glyph_study": {
        "default_name": "glyph-study",
        "description": "Learn the meanings",
        "type": "study"
    }
}
