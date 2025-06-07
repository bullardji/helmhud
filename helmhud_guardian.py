# -*- coding: utf-8 -*-
"""Entry point for Helmhud Guardian bot"""

import os
import logging
from dotenv import load_dotenv
from guardian import bot

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s:%(name)s: %(message)s",
)

load_dotenv()

if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_TOKEN"))
