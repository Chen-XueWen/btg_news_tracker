# BTG News Tracker Architecture

```mermaid
flowchart LR
    user["User"]
    ui["React Frontend (Vite)\nfrontend/src/App.jsx"]

    user --> ui

    ui -->|"POST /api/news"| newsApi
    ui -->|"POST /api/videos"| videoCreateApi
    ui -->|"GET /api/videos/{id}"| videoStatusApi
    ui -->|"GET /api/videos/{id}/content"| videoContentApi

    subgraph backend["FastAPI Backend (backend/app/main.py)"]
        newsApi["/api/news"]
        videoCreateApi["/api/videos"]
        videoStatusApi["/api/videos/{id}"]
        videoContentApi["/api/videos/{id}/content"]
        healthApi["/api/health"]

        startup["Startup: load_settings() + build_news_agent()"]
        memState["In-memory app.state\nvideo_topics + notified_video_ids"]
    end

    subgraph agent["LangGraph News Agent (backend/app/agent/graph.py)"]
        searchNode["search"]
        summarizeSourcesNode["summarize_sources"]
        summarizeNode["summarize"]
        scoreNode["score"]
        searchNode --> summarizeSourcesNode --> summarizeNode --> scoreNode
    end

    subgraph integrations["External Integrations"]
        brave["Brave Search API"]
        openaiResp["OpenAI Responses API\n(gpt-5-mini)"]
        openaiVideo["OpenAI Video API\n(sora-2)"]
        slackWebhook["Slack Webhook"]
        slackFiles["Slack Files API"]
    end

    subgraph config["Configuration"]
        env["Environment Variables"]
        secrets["./secrets/*.key files"]
    end

    env --> startup
    secrets --> startup

    newsApi --> agent
    agent -->|"search_brave_news"| brave
    agent -->|"summarize_sources + summarize_news + score_news"| openaiResp
    newsApi -->|"send_news_to_slack"| slackWebhook

    videoCreateApi -->|"create_video_job + build_video_prompt"| openaiVideo
    videoCreateApi --> memState

    videoStatusApi -->|"get_video_job"| openaiVideo
    videoStatusApi --> memState
    videoStatusApi -->|"on completed: upload_video_file_to_slack"| slackFiles
    videoStatusApi -->|"fallback/notification: send_video_to_slack"| slackWebhook

    videoContentApi -->|"download_video_content"| openaiVideo
```

## Notes
- The news workflow is a strict linear LangGraph pipeline: `search -> summarize_sources -> summarize -> score`.
- There is no database; runtime video-tracking metadata is kept in FastAPI `app.state`.
- Source recency is enforced in backend search filtering (parseable published date within last 7 days).
