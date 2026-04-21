// Unit tests for the typed API client.
//
// These cover the contract every page relies on: correct method + path,
// correct handling of JSON bodies, multipart uploads, querystring encoding,
// and error normalisation through `ApiError`.

import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';

import {
  ApiError,
  API_BASE_URL,
  extractPersonas,
  generateB2BReport,
  generateB2CNewsletter,
  getHealth,
  getPersona,
  getRecommendations,
  getTopTrends,
  pingLiveness,
  rankDailyTrends,
  submitArticleFeedback,
  triggerRssIngestion,
} from '@/lib/api';

import { server } from '../mocks/server';

describe('API_BASE_URL', () => {
  it('defaults to http://localhost:8000 when no env var is set', () => {
    expect(API_BASE_URL).toBe('http://localhost:8000');
  });
});

describe('System probes', () => {
  it('pingLiveness hits /livez', async () => {
    const res = await pingLiveness();
    expect(res.status).toBe('alive');
  });

  it('getHealth returns shape matching HealthResponse', async () => {
    const res = await getHealth();
    expect(res).toMatchObject({
      status: 'healthy',
      app_name: 'Curate AI',
      version: '1.0.0',
      environment: 'dev',
    });
    expect(res.snowflake_version).toMatch(/^\d+\./);
  });
});

describe('Personas', () => {
  it('getPersona returns the stored persona for an existing user', async () => {
    const persona = await getPersona('user-demo-001');
    expect(persona.user_id).toBe('user-demo-001');
    expect(persona.persona_archetype).toBe('ML_RESEARCHER');
    expect(persona.explicit_category_weights.llms).toBeCloseTo(0.9);
  });

  it('getPersona throws ApiError(404) for a missing user', async () => {
    await expect(getPersona('missing')).rejects.toMatchObject({
      name: 'ApiError',
      status: 404,
    });
  });

  it('extractPersonas builds FormData with user_id + files', async () => {
    const file = new File(['resume bytes'], 'resume.pdf', { type: 'application/pdf' });
    const res = await extractPersonas('user-42', [file]);
    expect(res.user_id).toBe('user-42');
    expect(res.results).toHaveLength(1);
    expect(res.results[0].is_success).toBe(true);
    expect(res.results[0].data?.job_title).toBe('Senior ML Engineer');
  });

  it('submitArticleFeedback echoes the feedback signal in the response', async () => {
    const res = await submitArticleFeedback({
      user_id: 'user-42',
      article_categories: { llms: 0.8 },
      feedback: 'like',
    });
    expect(res.message).toContain("'like'");
    expect(res.updated_categories).toHaveProperty('llms');
  });
});

describe('Newsletter', () => {
  it('generateB2CNewsletter returns HTML with user context', async () => {
    const res = await generateB2CNewsletter({ user_id: 'user-42', execution_mode: 'polished' });
    expect(res.status).toBe('SUCCESS');
    expect(res.html_content).toContain('user-42');
    expect(res.execution_path_taken).toContain('editor_review');
  });

  it('fast mode skips editor_review in the execution path', async () => {
    const res = await generateB2CNewsletter({ user_id: 'user-42', execution_mode: 'fast' });
    expect(res.execution_path_taken).not.toContain('editor_review');
  });
});

describe('B2B', () => {
  it('generateB2BReport returns Markdown keyed by user_id', async () => {
    const res = await generateB2BReport({ user_id: 'acme-co' });
    expect(res.user_id).toBe('acme-co');
    expect(res.report).toContain('# Executive Intelligence Briefing');
  });
});

describe('Search / recommendations', () => {
  it('getRecommendations encodes querystring and returns ranked articles', async () => {
    const res = await getRecommendations('user-42', 3);
    expect(res.results.length).toBeGreaterThan(0);
    expect(res.results[0].score).toBeGreaterThan(0);
  });

  it('raises ApiError on backend 404 with the detail preserved', async () => {
    await expect(getRecommendations('missing')).rejects.toSatisfy(
      (err: unknown) =>
        err instanceof ApiError && err.status === 404 && /User persona not found/.test(err.detail ?? ''),
    );
  });
});

describe('Trends', () => {
  it('getTopTrends returns the ranked cluster list', async () => {
    const res = await getTopTrends(5);
    expect(res.total).toBeGreaterThan(0);
    expect(res.results[0].trend_status).toBeDefined();
  });

  it('getTopTrends respects the limit parameter', async () => {
    const res = await getTopTrends(1);
    expect(res.results).toHaveLength(1);
  });

  it('rankDailyTrends posts and returns the accepted payload', async () => {
    const res = (await rankDailyTrends()) as { status: string };
    expect(res.status).toBe('success');
  });
});

describe('Ingestion', () => {
  it('triggerRssIngestion returns IngestionBatchResponse', async () => {
    const res = await triggerRssIngestion();
    expect(res.total_found).toBeGreaterThan(0);
    expect(res.saved_count).toBeGreaterThan(0);
    expect(res.start_time).toMatch(/^\d{4}-/);
  });
});

describe('Error handling', () => {
  it('wraps non-2xx responses in ApiError with status + detail', async () => {
    server.use(
      http.get('http://localhost:8000/api/v1/personas/:id', () =>
        HttpResponse.json({ detail: 'nope' }, { status: 500 }),
      ),
    );
    await expect(getPersona('whatever')).rejects.toSatisfy(
      (err: unknown) => err instanceof ApiError && err.status === 500 && err.detail === 'nope',
    );
  });

  it('falls back to raw text when the error body is not JSON', async () => {
    server.use(
      http.get('http://localhost:8000/livez', () =>
        HttpResponse.text('plain text oops', { status: 503 }),
      ),
    );
    await expect(pingLiveness()).rejects.toSatisfy(
      (err: unknown) =>
        err instanceof ApiError && err.status === 503 && err.detail === 'plain text oops',
    );
  });
});
