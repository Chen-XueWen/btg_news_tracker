import { useMemo, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
const MAX_METRICS = 5
const CUSTOM_OPTION = 'custom'
const VIDEO_DURATION_OPTIONS = [4, 8, 12]
const DEFAULT_VIDEO_SECONDS = 12
const VIDEO_POLL_INTERVAL_MS = 5000
const VIDEO_POLL_MAX_ATTEMPTS = 180

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
  const [videoLoading, setVideoLoading] = useState(false)
  const [videoError, setVideoError] = useState('')
  const [videoJob, setVideoJob] = useState(null)
  const [videoSeconds, setVideoSeconds] = useState(DEFAULT_VIDEO_SECONDS)

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
      setVideoJob(null)
      setVideoError('')
    } catch (err) {
      setError(err.message || 'Unexpected error')
      setResult(null)
    } finally {
      setLoading(false)
    }
  }

  async function pollVideoJob(videoId) {
    for (let attempt = 0; attempt < VIDEO_POLL_MAX_ATTEMPTS; attempt += 1) {
      const response = await fetch(`${API_BASE}/api/videos/${videoId}`)
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to fetch video job status')
      }

      setVideoJob(data)
      const status = String(data.status || '').toLowerCase()
      if (status === 'completed' || status === 'failed' || status === 'cancelled') {
        return data
      }

      await new Promise((resolve) => {
        setTimeout(resolve, VIDEO_POLL_INTERVAL_MS)
      })
    }

    throw new Error('Video generation timed out while waiting for completion (15 minutes).')
  }

  function extractVideoErrorText(job) {
    if (!job || !job.error) {
      return ''
    }

    if (typeof job.error === 'string') {
      return job.error
    }

    if (typeof job.error === 'object') {
      const message = job.error.message || job.error.detail
      if (message) {
        return String(message)
      }
      return JSON.stringify(job.error)
    }

    return String(job.error)
  }

  async function handleGenerateVideo() {
    if (!result || videoLoading) {
      return
    }

    const requestedSeconds = Number(videoSeconds)
    const safeSeconds = VIDEO_DURATION_OPTIONS.includes(requestedSeconds)
      ? requestedSeconds
      : DEFAULT_VIDEO_SECONDS
    setVideoLoading(true)
    setVideoError('')

    try {
      const response = await fetch(`${API_BASE}/api/videos`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          topic: result.topic,
          summary: result.summary,
          seconds: safeSeconds,
          size: '1280x720'
        })
      })

      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to start video generation')
      }

      setVideoJob(data)

      const status = String(data.status || '').toLowerCase()
      if (status !== 'completed' && status !== 'failed' && status !== 'cancelled') {
        const finalJob = await pollVideoJob(data.id)
        setVideoJob(finalJob)
        const finalStatus = String(finalJob.status || '').toLowerCase()
        if (finalStatus === 'failed' || finalStatus === 'cancelled') {
          const text = extractVideoErrorText(finalJob)
          setVideoError(text || `Video job ${finalStatus}.`)
        }
      } else if (status === 'failed' || status === 'cancelled') {
        const text = extractVideoErrorText(data)
        setVideoError(text || `Video job ${status}.`)
      } else if (status === 'completed') {
        const completedJob = await pollVideoJob(data.id)
        setVideoJob(completedJob)
      }
    } catch (err) {
      setVideoError(err.message || 'Unexpected error while generating video')
    } finally {
      setVideoLoading(false)
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

          <section className="video-panel">
            <h3>Video Narration</h3>
            <p className="video-help">
              Generates a short video narration using <code>sora-2</code> (cost-optimized option) with a
              neutral news-anchor voice. Duration options are 4, 8, or 12 seconds.
            </p>
            <label htmlFor="video-seconds">Duration (seconds)</label>
            <select
              id="video-seconds"
              value={videoSeconds}
              onChange={(e) => setVideoSeconds(Number(e.target.value))}
            >
              {VIDEO_DURATION_OPTIONS.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
            <button type="button" onClick={handleGenerateVideo} disabled={videoLoading}>
              {videoLoading ? 'Generating video...' : 'Generate video'}
            </button>
            {videoError && <p className="error">{videoError}</p>}
            {videoJob && (
              <p className="video-status">
                Status: <strong>{videoJob.status || 'unknown'}</strong>
                {videoJob.progress !== null && videoJob.progress !== undefined
                  ? ` (${Number(videoJob.progress).toFixed(0)}%)`
                  : ''}
              </p>
            )}
            {videoJob && String(videoJob.status || '').toLowerCase() === 'failed' && videoJob.error && (
              <pre className="video-error-detail">{extractVideoErrorText(videoJob)}</pre>
            )}
            {videoJob && String(videoJob.status || '').toLowerCase() === 'completed' && (
              <>
                <video
                  key={videoJob.id}
                  className="video-player"
                  controls
                  preload="metadata"
                  src={`${API_BASE}/api/videos/${videoJob.id}/content`}
                />
                <p className="video-download">
                  <a
                    href={`${API_BASE}/api/videos/${videoJob.id}/content?download=true`}
                    target="_blank"
                    rel="noreferrer"
                  >
                    Download video (.mp4)
                  </a>
                </p>
              </>
            )}
          </section>

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
