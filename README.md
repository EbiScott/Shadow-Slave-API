# Shadow Slave Quote API

A small FastAPI service for short, explicitly attributed dialogue from *Shadow Slave* by Guiltythree. It serves quotes, not book text.

The generated SQLite database is committed so the service can run without the source EPUBs. The EPUB files themselves are ignored.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Database and dataset status |
| GET | `/v1/characters` | Character list with quote counts and aliases |
| GET | `/v1/characters/{character}` | Character summary and first/last quote |
| GET | `/v1/quotes/random` | Random quote; filter by character, volume, length |
| GET | `/v1/quotes` | Quote search with character, volume, confidence, paging |
| GET | `/v1/quotes/{quote_id}` | One quote by ID |
| GET | `/docs` | OpenAPI documentation |

Example:

```text
GET /v1/quotes/random?character=Sunless&min_words=6&max_chars=220
```

Aliases resolve to canonical names, so `Sunny`, `Lord of Shadows`, and `Lost from Light` all resolve to `Sunless`.

## Local setup

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install and run:

```bash
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs`.

## Rebuild the quote database

Place the EPUBs in the project root, then run:

```bash
python scripts/build_quotes.py
```

The script extracts dialogue with a nearby attribution, canonicalises character names, deduplicates by character and quote, and writes `data/quotes.db`.

The parser supports the Chapter title layouts used across all 12 volumes, including `h1`, `h2`, and `h3` chapter headings.

## Tests

```bash
python -m pytest -q
```

The suite checks extraction, chapter parsing, alias resolution, every-volume coverage, API responses, random Sunless quotes, character filtering, and 404s.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `SHADOW_SLAVE_DB` | `data/quotes.db` | Override database path |
| `ALLOWED_ORIGINS` | `https://0xk4m1.vercel.app` plus local dev ports | Comma-separated CORS origins |

## Deploy on Render

Render is the recommended host for this service. It supports a normal Python web process and the database is read-only inside the repo, so no persistent disk is required.

1. Push this repository to GitHub.
2. Create a new Render Blueprint or Web Service from the repo.
3. Use the included `render.yaml`, or set:
   - Build command: `pip install -r requirements.txt`
   - Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Health check path: `/health`
4. Set `ALLOWED_ORIGINS` to your portfolio origin if it differs from `https://0xk4m1.vercel.app`.

The free plan spins down after inactivity, so the first request after idle may be slower.

### Why not Vercel

Vercel is built around serverless functions and a read-only deployment bundle. This service uses a normal Python ASGI process and SQLite. Vercel would require a separate database (such as Turso or Postgres), rewritten database access, and Python function configuration. Render is simpler and keeps the committed SQLite artifact working as-is.

## Data notes

- Source EPUBs are not committed.
- The database contains short quoted excerpts with attribution, not full chapters.
- Extraction keeps explicitly or action-attributed dialogue; narration is not included.
- This is an unofficial fan project and is not affiliated with the author or publisher.
