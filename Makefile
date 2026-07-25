# AI IELTS Tutor — common developer tasks.
# Windows users without `make` can run the underlying commands directly.

PY ?= python

.PHONY: help install run test compile migrate migrate-down docker-build docker-up docker-down clean

help:  ## List available targets
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  %-14s %s\n", $$1, $$2}'

install:  ## Install backend dependencies
	cd backend && pip install -r requirements.txt

run:  ## Run the backend with autoreload on :8000
	cd backend && uvicorn main:app --reload --port 8000

test:  ## Run all backend smoke suites
	cd backend && $(PY) tests/run_smoke.py

compile:  ## Byte-compile the backend (fast sanity check)
	cd backend && $(PY) -m compileall -q .

migrate:  ## Apply all Alembic migrations (needs DATABASE_URL for Postgres)
	cd backend && alembic upgrade head

migrate-down:  ## Roll back all Alembic migrations
	cd backend && alembic downgrade base

docker-build:  ## Build the backend Docker image
	docker build -t ai-ielts-backend ./backend

docker-up:  ## Start the full stack (API + PostgreSQL) via compose
	docker compose up --build

docker-down:  ## Stop the compose stack
	docker compose down

clean:  ## Remove local SQLite DBs and Python caches
	cd backend && rm -f *.db && find . -type d -name __pycache__ -exec rm -rf {} +
