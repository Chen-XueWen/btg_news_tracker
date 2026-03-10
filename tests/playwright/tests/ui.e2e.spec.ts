import { expect, test } from '@playwright/test'

test('can submit topic and render summary using mocked news API', async ({ page }) => {
  await page.route('**/api/news', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        topic: 'Quantum Computing',
        summary: 'Quantum teams reported progress in error mitigation and hardware scaling.',
        generated_at: '2026-03-10T00:00:00Z',
        articles: [
          {
            title: 'Quantum update',
            url: 'https://example.com/quantum-update',
            description: 'A relevant update',
            source: 'example.com',
            published: '1 day ago',
            mini_summary: 'A concise summary',
            source_metric_scores: [{ variable: 'Source Credibility', score: 4.4 }]
          }
        ]
      })
    })
  })

  await page.goto('/')
  await page.getByRole('button', { name: 'Run agent' }).click()

  await expect(page.getByText('Summary for Quantum Computing')).toBeVisible()
  await expect(page.getByText('A concise summary')).toBeVisible()
})

test('can trigger video generation flow and show completed status with mocked video APIs', async ({ page }) => {
  await page.route('**/api/news', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        topic: 'Quantum Computing',
        summary: 'This summary is long enough to generate a video in the UI flow.',
        generated_at: '2026-03-10T00:00:00Z',
        articles: [
          {
            title: 'Quantum update',
            url: 'https://example.com/quantum-update',
            description: 'A relevant update',
            source: 'example.com',
            published: '1 day ago',
            mini_summary: 'A concise summary',
            source_metric_scores: []
          }
        ]
      })
    })
  })

  await page.route('**/api/videos', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'vid-qa-001',
        status: 'completed',
        progress: 100,
        seconds: 12,
        size: '1280x720',
        model: 'sora-2'
      })
    })
  })

  await page.route('**/api/videos/vid-qa-001', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'vid-qa-001',
        status: 'completed',
        progress: 100,
        seconds: 12,
        size: '1280x720',
        model: 'sora-2'
      })
    })
  })

  await page.goto('/')
  await page.getByRole('button', { name: 'Run agent' }).click()
  await page.getByRole('button', { name: 'Generate video' }).click()

  await expect(page.getByText('Status:')).toBeVisible()
  await expect(page.getByText('completed')).toBeVisible()
  await expect(page.getByRole('link', { name: 'Download video (.mp4)' })).toBeVisible()
})
