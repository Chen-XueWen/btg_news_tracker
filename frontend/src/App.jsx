import { useMemo, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export default function App() {
  const [topic, setTopic] = useState('Quantum Computing')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  const canSubmit = useMemo(() => topic.trim().length >= 2 && !loading, [topic, loading])

  async function fetchNews(event) {
    event.preventDefault()
    if (!canSubmit) {
      return
    }

    setLoading(true)
    setError('')

    try {
      const response = await fetch(`${API_BASE}/api/news`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ topic: topic.trim() })
      })

      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to fetch news')
      }

      setResult(data)
    } catch (err) {
      setError(err.message || 'Unexpected error')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="container">
      <h1>BTG News Tracker</h1>
      <p className="subtitle">Get a 7-day news brief on any topic.</p>

      <form onSubmit={fetchNews} className="form">
        <label htmlFor="topic">Topic of interest</label>
        <div className="row">
          <input
            id="topic"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="Agentic AI, Quantum Computing, etc."
          />
          <button type="submit" disabled={!canSubmit}>
            {loading ? 'Searching...' : 'Run agent'}
          </button>
        </div>
      </form>

      {error && <p className="error">{error}</p>}

      {result && (
        <section className="results">
          <h2>Summary for {result.topic}</h2>
          <pre className="summary">{result.summary}</pre>

          <h3>Sources</h3>
          <ul className="articles">
            {result.articles.map((article) => (
              <li key={article.url}>
                <a href={article.url} target="_blank" rel="noreferrer">
                  {article.title}
                </a>
                <p>{article.description}</p>
                <small>
                  {article.source || 'Unknown source'} {article.published ? `| ${article.published}` : ''}
                </small>
              </li>
            ))}
          </ul>
        </section>
      )}
    </main>
  )
}
