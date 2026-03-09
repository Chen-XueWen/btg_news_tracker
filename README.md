# BTG News Tracker (v0)

Initial version of a topic-driven news agent with:
- FastAPI backend
- LangGraph orchestration (`search -> summarize`)
- Brave Search API for latest web results (last 7 days)
- OpenAI GPT-5 mini for synthesis
- React frontend

## Architecture

- Frontend: `frontend/`
- Backend: `backend/`

Backend flow:
1. Accept topic (`POST /api/news`)
2. Query Brave Search with `freshness=pw` (past week)
3. Summarize results with GPT-5 mini
4. Return summary + source list

## Keys

This project reads keys from either env vars or root key files:
- `BRAVE_API_KEY` or `./bravesearchapi.key`
- `OPENAI_API_KEY` or `./openai.key`

## Run backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Health check:

```bash
curl http://localhost:8000/api/health
```

## Run frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend default API base is `http://localhost:8000`.
Override with:

```bash
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

## Sample API call

```bash
curl -X POST http://localhost:8000/api/news \
  -H "Content-Type: application/json" \
  -d '{"topic":"Agentic AI"}'
```

## Notes

- "Last 7 days" is currently implemented via Brave's weekly freshness filter (`freshness=pw`).
- Next expansion ideas: multi-source ranking, dedupe, citation confidence, scheduled tracking, persistence.
