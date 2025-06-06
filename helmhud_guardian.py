# -*- coding: utf-8 -*-
"""Entry point for Helmhud Guardian bot"""

import os
from dotenv import load_dotenv
from guardian import bot

load_dotenv()

if __name__ == "__main__":
    bot.run(os.getenv("DISCORD_TOKEN"))
