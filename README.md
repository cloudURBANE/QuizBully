# IT Support & Knowledge Quiz Bot 🤖

A Discord bot for interactive IT quizzes, with timers, leaderboards, hints, and AI explanations.

- **Language**: Python 3.11+
- **Libraries**: `discord.py`, `pymongo`, `openai`

## Badges

- CI: GitHub Actions runs lint and tests on every PR.

## Features
- Interactive quiz flows in DMs
- Timed questions per difficulty
- Real-time leaderboard and metrics
- Hints and AI-powered explanations (OpenAI)
- Optional MongoDB topics source; works without DB

## Getting Started

### 1) Clone
```bash
git clone https://github.com/your-username/quiz-bot.git
cd quiz-bot
```

### 2) Configure
Copy `.env.example` to `.env` and fill values:
```
DISCORD_TOKEN=your_discord_bot_token
OPENAI_API_KEY=your_openai_api_key
MONGO_URI=your_mongodb_connection_uri # optional
```

### 3) Install
```bash
pip3 install -r requirements.txt
```

### 4) Run
```bash
python3 bot.py
```

Or with Docker:
```bash
docker build -t quiz-bot:latest .
docker run --rm \
  -e DISCORD_TOKEN=$DISCORD_TOKEN \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e MONGO_URI=$MONGO_URI \
  quiz-bot:latest
```

## Usage
In a DM with your bot, send `!q` and follow on-screen reactions to choose difficulty and question source.

## Development
- Lint and format: `make lint` / `make format`
- Tests: `make test`
- Common tasks: `make help` (see Makefile)

## Contributing
See `CONTRIBUTING.md` and `CODE_OF_CONDUCT.md`.

## License
MIT — see `LICENSE`.
