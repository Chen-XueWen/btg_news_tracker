import { useMemo, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const MAX_METRICS = 5
const CUSTOM_OPTION = 'custom'

const PRESET_METRICS = [
  {
    key: 'source_credibility',
    variable: 'Source Credibility',
    description: 'Higher score when sources are reputable, authoritative, and consistent across outlets.'
  },
  {
    key: 'relevance',
    variable: 'Topical Relevance',
    description: 'Higher score when the summary and sources stay tightly focused on the requested topic.'
  },
  {
    key: 'actionability',
    variable: 'Actionability',
    description: 'Higher score when the output provides clear, practical takeaways for next steps.'
  }
]

function metricFromPreset(preset) {
  return {
    presetKey: preset.key,
    variable: preset.variable,
    description: preset.description
  }
}

function emptyMetric() {
  return { presetKey: CUSTOM_OPTION, variable: '', description: '' }
}

export default function App() {
  const [topic, setTopic] = useState('Quantum Computing')
  const [metrics, setMetrics] = useState(PRESET_METRICS.map(metricFromPreset))
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  const canSubmit = useMemo(() => topic.trim().length >= 2 && !loading, [topic, loading])

  function updateMetric(index, key, value) {
    setMetrics((prev) => prev.map((metric, i) => (i === index ? { ...metric, [key]: value } : metric)))
  }

  function updatePreset(index, selectedKey) {
    const preset = PRESET_METRICS.find((item) => item.key === selectedKey)

    setMetrics((prev) =>
      prev.map((metric, i) => {
        if (i !== index) {
          return metric
        }

        if (!preset) {
          return { ...metric, presetKey: CUSTOM_OPTION, variable: metric.variable || '' }
        }

        return {
          ...metric,
          presetKey: preset.key,
          variable: preset.variable,
          description: preset.description
        }
      })
    )
  }

  function addMetric() {
    setMetrics((prev) => {
      if (prev.length >= MAX_METRICS) {
        return prev
      }
      return [...prev, emptyMetric()]
    })
  }

  function removeMetric(index) {
    setMetrics((prev) => {
      const next = prev.filter((_, i) => i !== index)
      return next.length ? next : [emptyMetric()]
    })
  }

  function normalizeMetrics() {
    const normalized = []

    for (const metric of metrics) {
      const variable = metric.variable.trim()
      const description = metric.description.trim()

      if (!variable && !description) {
        continue
      }
      if (!variable || !description) {
        return { error: 'Each scoring metric must include both Variable and Description.' }
      }
      normalized.push({ variable, description })
    }

    if (normalized.length > MAX_METRICS) {
      return { error: `You can add up to ${MAX_METRICS} metrics.` }
    }

    return { metrics: normalized }
  }

  async function fetchNews(event) {
    event.preventDefault()
    if (!canSubmit) {
      return
    }

    const normalized = normalizeMetrics()
    if (normalized.error) {
      setError(normalized.error)
      return
    }

    setLoading(true)
    setError('')

    try {
      const response = await fetch(`${API_BASE}/api/news`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: topic.trim(),
          scoring_metrics: normalized.metrics
        })
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

        <section className="metric-section">
          <div className="metric-head">
            <h3>Scoring Metrics</h3>
            <button
              type="button"
              className="button-secondary"
              onClick={addMetric}
              disabled={metrics.length >= MAX_METRICS}
            >
              Add metric
            </button>
          </div>
          <p className="metric-help">
            Up to {MAX_METRICS} metrics. Pick a variable preset or choose Custom, then adjust the description.
          </p>

          <div className="metric-list">
            {metrics.map((metric, index) => {
              const isCustom = metric.presetKey === CUSTOM_OPTION

              return (
                <div className="metric-row" key={`metric-${index}`}>
                  <select
                    value={metric.presetKey}
                    onChange={(e) => updatePreset(index, e.target.value)}
                    aria-label="Variable preset"
                  >
                    {PRESET_METRICS.map((preset) => (
                      <option key={preset.key} value={preset.key}>
                        {preset.variable}
                      </option>
                    ))}
                    <option value={CUSTOM_OPTION}>Custom variable</option>
                  </select>

                  {isCustom ? (
                    <input
                      value={metric.variable}
                      onChange={(e) => updateMetric(index, 'variable', e.target.value)}
                      placeholder="Custom variable"
                    />
                  ) : (
                    <input value={metric.variable} readOnly className="readonly-field" />
                  )}

                  <input
                    value={metric.description}
                    onChange={(e) => updateMetric(index, 'description', e.target.value)}
                    placeholder="Description (how to score this metric)"
                  />

                  <button type="button" className="button-danger" onClick={() => removeMetric(index)}>
                    Remove
                  </button>
                </div>
              )
            })}
          </div>
        </section>
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
                {Array.isArray(article.source_metric_scores) && article.source_metric_scores.length > 0 && (
                  <p className="source-metric-line">
                    {article.source_metric_scores
                      .map(
                        (metric, metricIndex) =>
                          `${metric.variable}: ${Number(metric.score).toFixed(2)} / 5${
                            metricIndex < article.source_metric_scores.length - 1 ? ' | ' : ''
                          }`
                      )
                      .join('')}
                  </p>
                )}
                {article.mini_summary && <p><strong>tldr:</strong> {article.mini_summary}</p>}
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
