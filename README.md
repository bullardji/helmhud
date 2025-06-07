# Helmhud Guardian

Helmhud Guardian is a Discord bot. To run it you need Python 3.11+ and to install its dependencies.

## Setup

1. Create a virtual environment (optional but recommended):
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
2. Install requirements (includes LLM dependencies):
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in `DISCORD_TOKEN` with your bot token.
4. Start the bot:
   ```bash
   python helmhud_guardian.py
   ```

When running, mention `@Helmhud Guardian` in any channel to chat with the local LLM. The bot will reply using context from recent messages and influential memories.

The bot stores its JSON data files in the directory specified by the `HELMHUD_DATA_DIR` environment variable. If not set, files are saved in the project root.
