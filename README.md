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
   If the model is gated, authenticate with Hugging Face:
   ```bash
   huggingface-cli login
   ```
3. Copy `.env.example` to `.env` and fill in `DISCORD_TOKEN` with your bot token.
4. Start the bot:
   ```bash
   python helmhud_guardian.py
   ```

The first run checks whether the Apriel-5B model is cached locally and downloads
it if necessary. Mention `@Helmhud Guardian` in any channel to chat with the LLM.
The bot replies using context from recent messages and influential memories.
Mentions are stripped from the text before sending prompts to the model so it
doesn't see `@Helmhud Guardian` and only your reply tag includes it.


The bot stores its JSON data files in the directory specified by the `HELMHUD_DATA_DIR` environment variable. If not set, files are saved in the project root.
