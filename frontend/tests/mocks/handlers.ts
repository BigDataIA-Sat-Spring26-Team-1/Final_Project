// Default MSW handlers. One entry per backend endpoint exposed by
// src/lib/api.ts, returning a realistic-but-minimal payload. Tests that care
// about error paths override with `server.use(http.get(...))`.
//
// The BASE_URL must match what api.ts resolves at test time. Tests set
// NEXT_PUBLIC_API_URL via vi.stubEnv or rely on the default localhost:8000.

import { http, HttpResponse } from 'msw';

const API = 'http://localhost:8000';

export const mockCategoryWeights = {
  llms: 0.9,
  ai_agents: 0.7,
  computer_vision: 0.2,
  security: 0.15,
  hardware: 0.05,
  software_engineering: 0.6,
  ai_policy: 0.1,
  general_ai: 0.5,
  data_engineering: 0.4,
  startups: 0.3,
};

export const mockPersonaResult = {
  name: 'Aakash Belide',
  job_title: 'Senior ML Engineer',
  seniority: 'senior',
  primary_interests: ['LLMs', 'Vector Search'],
  technical_skills: ['Python', 'PyTorch', 'Snowflake'],
  bio_summary: 'Builds intelligent content pipelines.',
  persona_archetype: 'ML_RESEARCHER',
  category_weights: mockCategoryWeights,
  source_type: 'LinkedIn PDF',
  extraction_latency_seconds: 1.2,
};

export const mockStoredPersona = {
  user_id: 'user-demo-001',
  job_title: 'Senior ML Engineer',
  seniority: 'senior',
  persona_archetype: 'ML_RESEARCHER',
  bio_summary: 'Builds intelligent content pipelines.',
  explicit_category_weights: mockCategoryWeights,
  behavioral_category_weights: { llms: 0.4, ai_agents: 0.2 },
};

export const mockTrends = [
  {
    cluster_id: 'c-001',
    title: 'GPT-5 Safety Report Released',
    summary: 'New benchmarks published.',
    trend_status: 'BREAKING',
    final_trend_score: 124.5,
    cluster_size: 6,
    social_popularity_score: 420,
    categories: { llms: 0.9, ai_policy: 0.3 },
    created_at: '2026-04-20T12:00:00Z',
  },
  {
    cluster_id: 'c-002',
    title: 'Qdrant 1.17 HNSW Optimization',
    summary: '12% memory reduction.',
    trend_status: 'TRENDING',
    final_trend_score: 68.0,
    cluster_size: 3,
    social_popularity_score: 150,
    categories: { data_engineering: 0.7 },
    created_at: '2026-04-20T10:00:00Z',
  },
];

export const mockRecommendations = [
  {
    cluster_id: 'c-001',
    title: 'GPT-5 Safety Report Released',
    summary: 'New benchmarks published.',
    score: 0.95,
    cluster_size: 6,
    categories: { llms: 0.9 },
    trend_status: 'BREAKING',
  },
  {
    cluster_id: 'c-002',
    title: 'Qdrant 1.17 HNSW Optimization',
    summary: '12% memory reduction.',
    score: 0.82,
    cluster_size: 3,
    categories: { data_engineering: 0.7 },
    trend_status: 'TRENDING',
  },
];

export const handlers = [
  // ---- System ----
  http.get(`${API}/livez`, () => HttpResponse.json({ status: 'alive' })),
  http.get(`${API}/api/v1/health`, () =>
    HttpResponse.json({
      status: 'healthy',
      app_name: 'Curate AI',
      version: '1.0.0',
      environment: 'dev',
      snowflake_version: '10.13.104',
    }),
  ),

  // ---- Personas ----
  http.get(`${API}/api/v1/personas/:userId`, ({ params }) => {
    if (params.userId === 'missing') {
      return HttpResponse.json(
        { detail: `No persona found for user_id '${params.userId}'.` },
        { status: 404 },
      );
    }
    return HttpResponse.json({ ...mockStoredPersona, user_id: String(params.userId) });
  }),

  // Note: we deliberately don't read `request.formData()` here — MSW's
  // formData parser hangs intermittently in Node/jsdom, and for test purposes
  // we only care that *something* was POSTed to this path.
  http.post(`${API}/api/v1/personas/extract`, () =>
    HttpResponse.json({
      user_id: 'user-42',
      results: [
        {
          filename: 'resume.pdf',
          is_success: true,
          data: mockPersonaResult,
          error: null,
        },
      ],
      overall_latency_seconds: 1.8,
    }),
  ),

  http.post(`${API}/api/v1/personas/feedback`, async ({ request }) => {
    const body = (await request.json()) as {
      user_id: string;
      feedback: string;
      article_categories: Record<string, number>;
    };
    return HttpResponse.json({
      user_id: body.user_id,
      updated_categories: { llms: 0.75 },
      message: `Behavioral weights updated based on '${body.feedback}' signal.`,
    });
  }),

  // ---- Newsletter ----
  http.post(`${API}/api/v1/newsletter/b2c`, async ({ request }) => {
    const body = (await request.json()) as { user_id: string; execution_mode?: string };
    const mode = body.execution_mode ?? 'polished';
    return HttpResponse.json({
      status: 'SUCCESS',
      html_content: `<h1>Daily Brief for ${body.user_id}</h1><p>Mode: ${mode}</p>`,
      execution_path_taken:
        mode === 'fast' ? ['init', 'curate', 'write'] : ['init', 'curate', 'write', 'editor_review'],
    });
  }),

  // ---- B2B ----
  http.post(`${API}/api/v1/b2b/report`, async ({ request }) => {
    const body = (await request.json()) as { user_id: string };
    return HttpResponse.json({
      user_id: body.user_id,
      report: `# Executive Intelligence Briefing\n\n## Key Opportunity Signals\n- Vector search gap detected.\n`,
      status: 'SUCCESS',
    });
  }),

  // ---- Search / Recommendations ----
  http.get(`${API}/api/v1/search/recommendations`, ({ request }) => {
    const url = new URL(request.url);
    if (url.searchParams.get('user_id') === 'missing') {
      return HttpResponse.json({ detail: 'User persona not found' }, { status: 404 });
    }
    return HttpResponse.json({
      status: 'SUCCESS',
      results: mockRecommendations,
      semantic_basis: 'llms,vector_search',
    });
  }),

  // ---- Trend ----
  http.get(`${API}/api/v1/trend/top`, ({ request }) => {
    const url = new URL(request.url);
    const limit = Number(url.searchParams.get('limit') ?? 20);
    return HttpResponse.json({
      total: mockTrends.length,
      results: mockTrends.slice(0, limit),
    });
  }),

  http.post(`${API}/api/v1/trend/rank`, () =>
    HttpResponse.json(
      { status: 'success', message: 'Ranked 12 story clusters.', latency_seconds: 1.4 },
      { status: 202 },
    ),
  ),

  // ---- Ingestion / Dedup ----
  http.post(`${API}/api/v1/ingestion/fetch-rss`, () =>
    HttpResponse.json({
      status: 'OK',
      total_found: 3129,
      saved_count: 2987,
      start_time: '2026-04-20T12:00:00Z',
      end_time: '2026-04-20T14:00:00Z',
      processing_time_seconds: 42.5,
    }),
  ),

  http.post(`${API}/api/v1/deduplication/process`, () =>
    HttpResponse.json({ status: 'OK', merged: 42 }),
  ),
];
