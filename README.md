# BTG News Tracker (v0)

Initial version of a topic-driven news agent with:
- FastAPI backend
- LangGraph orchestration (`search -> summarize_sources -> summarize`)
- Brave Search API for latest web results (last 7 days)
- OpenAI GPT-5 mini for synthesis
- React frontend

## Architecture

- Frontend: `frontend/`
- Backend: `backend/`

Backend flow:
1. Accept topic (`POST /api/news`)
2. Query Brave Search with `freshness=pw` (past week)
3. Strictly keep only parseable sources published within the last 7 days
4. Dedupe by canonical URL and normalized title
5. Generate per-source mini summaries
6. Build final global summary from mini summaries + source snippets
7. Return summary + source list

## Keys

This project reads keys from either env vars or files in `./secrets/`:
- `BRAVE_API_KEY` or `./secrets/bravesearchapi.key`
- `OPENAI_API_KEY` or `./secrets/openai.key`
- `SLACK_WEBHOOK_URL` or `./secrets/slackwebhook.key`

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

- "Last 7 days" is enforced twice: Brave's weekly freshness filter and strict backend date filtering.
- Date filtering keeps only sources with parseable timestamps that fall inside the rolling 7-day window.
- Current tradeoff: strict filtering may return fewer results for topics where many pages have missing/ambiguous publish dates.
- On successful generation, the backend sends the topic summary and source mini-summaries to Slack via webhook.
