# MEV Strategy Lab — convenience targets.

.PHONY: install test lint typecheck fmt api frontend docker docker-down clean

install:
	pip install -e ./engine -e ./api
	cd frontend && npm install --no-audit --no-fund

test:
	cd engine && python -m pytest --timeout=15 -q
	cd api && python -m pytest --timeout=15 -q

lint:
	cd engine && ruff check .
	cd api && ruff check . || true
	cd frontend && npx eslint src --ext ts,tsx || true

typecheck:
	cd engine && mypy mevlab || true
	cd frontend && npx tsc -b --noEmit

fmt:
	cd engine && ruff format .
	cd api && ruff format .

api:
	cd api && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

frontend:
	cd frontend && npm run dev -- --host 0.0.0.0

docker:
	docker compose up --build -d

docker-down:
	docker compose down

clean:
	find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	rm -rf engine/.pytest_cache engine/.ruff_cache engine/.mypy_cache
	rm -rf api/.pytest_cache api/.ruff_cache
	rm -rf frontend/node_modules frontend/dist
