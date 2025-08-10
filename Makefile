PY=python3
PIP=pip3

.PHONY: install dev lint format test run docker-build docker-run

install:
	$(PIP) install -r requirements.txt

dev:
	$(PIP) install -r requirements.txt
	$(PIP) install ruff pre-commit pytest
	pre-commit install || true

lint:
	ruff check .

format:
	ruff format .

test:
	pytest -q

run:
	$(PY) bot.py

docker-build:
	docker build -t quiz-bot:latest .

docker-run:
	docker run --rm -e DISCORD_TOKEN=$$DISCORD_TOKEN -e OPENAI_API_KEY=$$OPENAI_API_KEY -e MONGO_URI=$$MONGO_URI quiz-bot:latest