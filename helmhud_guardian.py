# -*- coding: utf-8 -*-
"""Entry point for Helmhud Guardian bot"""

import os
import logging
from dotenv import load_dotenv
from guardian import bot
from guardian.llm import ensure_model_downloaded

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s:%(name)s: %(message)s",
)

load_dotenv()

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not isinstance(token, str) or not token:
        raise RuntimeError(
            "DISCORD_TOKEN not set. Create a .env file with DISCORD_TOKEN=your_token"
        )
    ensure_model_downloaded()
    bot.run(token)
