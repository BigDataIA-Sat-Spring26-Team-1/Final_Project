/**
 * CurateAI backend API client.
 *
 * One place that knows how to talk to FastAPI. Every page / component should
 * import the typed functions below instead of calling `fetch` directly — that
 * way the base URL, error shape, and request headers stay in lockstep.
 *
 * Design notes:
 *   - `NEXT_PUBLIC_API_URL` is baked in at build time by Next.js. Set it in
 *     `.env.local` for dev and via the Cloud Run build step for production.
 *   - All request helpers accept an optional `AbortSignal` so pages can cancel
 *     in-flight calls when the user navigates away (avoids the "update on
 *     unmounted component" warning).
 *   - Errors are normalised to `ApiError` with both the HTTP status and the
 *     server's `detail` payload, so UI code can render friendly messages
 *     without re-parsing the response.
 */

// ---- Base URL ---------------------------------------------------------------
// Backends typically bind to :8000 via `uv run uvicorn ...` or :8080 inside
// Docker/Cloud Run. Either works — override with NEXT_PUBLIC_API_URL when
// needed. No trailing slash (we always prefix paths with a leading /).
export const API_BASE_URL: string =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, '') ?? 'http://localhost:8000';

// ---- Error type -------------------------------------------------------------
/**
 * Thrown for any non-2xx response. Callers can `instanceof ApiError` to branch
 * on transport-level failures vs. their own validation errors.
 */
export class ApiError extends Error {
  public readonly status: number;
  public readonly detail?: string;

  constructor(message: string, status: number, detail?: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

// ---- Internal fetch helper --------------------------------------------------
type RequestOptions = Omit<RequestInit, 'body'> & {
  /** JSON-serialisable body for POST/PUT/PATCH. */
  json?: unknown;
  /** Pre-built FormData (for file uploads). Takes precedence over `json`. */
  formData?: FormData;
  /** Pre-built querystring as a plain object; values are URL-encoded. */
  query?: Record<string, string | number | boolean | undefined>;
  /** Optional abort signal for request cancellation. */
  signal?: AbortSignal;
};

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { json, formData, query, headers, signal, ...rest } = options;

  const qs = query
    ? '?' +
      Object.entries(query)
        .filter(([, v]) => v !== undefined && v !== null)
        .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
        .join('&')
    : '';

  // FormData sets its own Content-Type (including the multipart boundary), so
  // we only set application/json when sending a JSON body.
  const finalHeaders: HeadersInit = {
    Accept: 'application/json',
    ...(json !== undefined && !formData ? { 'Content-Type': 'application/json' } : {}),
    ...(headers ?? {}),
  };

  const res = await fetch(`${API_BASE_URL}${path}${qs}`, {
    ...rest,
    headers: finalHeaders,
    body: formData ?? (json !== undefined ? JSON.stringify(json) : undefined),
    signal,
  });

  // 204 No Content is perfectly valid — don't try to parse an empty body.
  if (res.status === 204) {
    return undefined as T;
  }

  const rawText = await res.text();
  const parsed = rawText ? tryParseJson(rawText) : undefined;

  if (!res.ok) {
    const detail =
      typeof parsed === 'object' && parsed !== null && 'detail' in parsed
        ? String((parsed as { detail: unknown }).detail)
        : typeof parsed === 'object' && parsed !== null && 'message' in parsed
        ? String((parsed as { message: unknown }).message)
        : rawText;
    throw new ApiError(
      `API ${res.status} on ${path}`,
      res.status,
      detail || undefined,
    );
  }

  return parsed as T;
}

function tryParseJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

// ============================================================================
// Types — mirror backend/app/core/schemas.py. Kept flat on purpose so pages
// can destructure without chasing nested imports.
// ============================================================================

/** 10-category taxonomy from `CategoryWeights`. */
export interface CategoryWeights {
  llms: number;
  ai_agents: number;
  computer_vision: number;
  security: number;
  hardware: number;
  software_engineering: number;
  ai_policy: number;
  general_ai: number;
  data_engineering: number;
  startups: number;
}

/** Result from the LLM persona extractor. */
export interface PersonaExtractionResult {
  name: string;
  job_title: string;
  seniority: string;
  primary_interests: string[];
  technical_skills: string[];
  bio_summary: string;
  persona_archetype: string;
  category_weights: CategoryWeights;
  source_type: string;
  extraction_latency_seconds: number;
}

export interface SinglePersonaExtractionResponse {
  filename: string;
  is_success: boolean;
  data?: PersonaExtractionResult | null;
  error?: string | null;
}

export interface BatchPersonaResponse {
  user_id: string;
  results: SinglePersonaExtractionResponse[];
  overall_latency_seconds: number;
}

export type FeedbackType = 'like' | 'dislike' | 'skip';

export interface ArticleFeedbackRequest {
  user_id: string;
  /** Map of category name → weight in [0, 1]. Comes from the article itself. */
  article_categories: Record<string, number>;
  feedback: FeedbackType;
}

export interface ArticleFeedbackResponse {
  user_id: string;
  updated_categories: Record<string, number>;
  message: string;
}

export type NewsletterExecutionMode = 'fast' | 'polished';

export interface B2CNewsletterRequest {
  user_id: string;
  execution_mode?: NewsletterExecutionMode;
}

export interface B2CNewsletterResponse {
  status: string;
  html_content: string;
  execution_path_taken: string[];
  /** True when the backend returned a cached draft rather than regenerating. */
  already_generated?: boolean;
  /** ISO timestamp of the persisted draft. */
  generated_at?: string | null;
  /** Edition date (YYYY-MM-DD) the draft belongs to. */
  edition_date?: string | null;
}

export interface B2BReportRequest {
  user_id: string;
}

export interface B2BReportResponse {
  user_id: string;
  report: string;
  status: string;
  already_generated?: boolean;
  generated_at?: string | null;
  brief_date?: string | null;
}

export interface IngestionBatchResponse {
  status: string;
  total_found: number;
  saved_count: number;
  start_time: string;
  end_time: string;
  processing_time_seconds: number;
}

/** Shape of a single ranked article returned by the search endpoint. */
export interface RankedArticle {
  cluster_id: string;
  title: string;
  summary?: string;
  /** Source URL of the representative article in the cluster. */
  url?: string;
  score: number;
  cluster_size?: number;
  categories?: Record<string, number>;
  trend_status?: string | null;
  [key: string]: unknown;
}

export interface RecommendationsResponse {
  status: string;
  results: RankedArticle[];
  semantic_basis?: string;
}

export interface HealthResponse {
  status: string;
  app_name: string;
  version: string;
  environment: string;
  snowflake_version: string;
}

/** A single ranked story cluster as returned by GET /api/v1/trend/top. */
export interface TrendCluster {
  cluster_id: string;
  title: string;
  summary: string | null;
  /** BREAKING / TRENDING / VIRAL / COMMUNITY-PICK / REGULAR / ... */
  trend_status: string | null;
  final_trend_score: number;
  cluster_size: number;
  social_popularity_score: number;
  categories: Record<string, number>;
  created_at: string | null;
  /** Articles that rolled into this cluster on the queried day. */
  curr_day_count: number;
  /** Articles that rolled into this cluster the day before. */
  prev_day_count: number;
}

export interface TrendTopResponse {
  total: number;
  results: TrendCluster[];
}

/** Returned by GET /api/v1/personas/{user_id}. */
export interface StoredPersona {
  user_id: string;
  job_title: string | null;
  seniority: string | null;
  persona_archetype: string | null;
  bio_summary: string | null;
  /** Weights captured at onboarding. */
  explicit_category_weights: Record<string, number>;
  /** Weights refined by like/dislike/skip feedback. */
  behavioral_category_weights: Record<string, number>;
}

export interface UserListItem {
  id: string;
  email: string;
  full_name: string | null;
  created_at: string;
}

export interface UserListResponse {
  total: number;
  results: UserListItem[];
}

export interface CompanyListItem {
  id: string;
  name: string;
  domain: string | null;
  industry: string | null;
  created_at: string;
}

export interface CompanyListResponse {
  total: number;
  results: CompanyListItem[];
}

export interface NewsletterArchiveItem {
  id: string;
  user_id: string;
  edition_date: string;
  status: string;
  generated_at: string | null;
  execution_path_taken: string | null;
  final_content: string | null;
  draft_content: string | null;
}

export interface NewsletterArchiveResponse {
  total: number;
  results: NewsletterArchiveItem[];
}

export interface BriefArchiveItem {
  id: string;
  company_id: string;
  brief_date: string;
  brief_content: string;
  urgency_tier: string;
  created_at: string;
  generated_at?: string;
}

export interface BriefArchiveResponse {
  total: number;
  results: BriefArchiveItem[];
}

/** Shared response for every endpoint that kicks off an Airflow DAG. */
export interface DAGTriggerResponse {
  status: string;
  message: string;
  dag_id: string;
  dag_run_id: string;
  state?: string | null;
}

/**
 * Back-compat alias — the admin UI still imports this name. The underlying
 * shape is the DAG trigger response.
 */
export type IngestionTriggerResponse = DAGTriggerResponse;

// ============================================================================
// System endpoints
// ============================================================================

export function pingLiveness(signal?: AbortSignal) {
  return request<{ status: string }>('/livez', { method: 'GET', signal });
}

export function getHealth(signal?: AbortSignal) {
  return request<HealthResponse>('/api/v1/health', { method: 'GET', signal });
}

// ============================================================================
// Prometheus metrics (pre-aggregated JSON for dashboard UI)
// ============================================================================

export interface MetricsHistogramEntry {
  count: number;
  sum: number;
  avg_seconds: number;
}

export interface MetricsSummary {
  llm: {
    requests_by_status: Record<string, number>;
    tokens_by_type: Record<string, number>;
    cost_usd_by_model: Record<string, number>;
  };
  agents: {
    newsletter_rejections: number;
    node_latency: Record<string, MetricsHistogramEntry>;
  };
  http: {
    endpoint_latency: Record<string, MetricsHistogramEntry>;
  };
  dags: {
    triggers_by_outcome: Record<string, number>;
    trigger_latency: Record<string, MetricsHistogramEntry>;
  };
}

export function getMetricsSummary(signal?: AbortSignal) {
  return request<MetricsSummary>('/api/v1/metrics/summary', { method: 'GET', signal });
}

// ============================================================================
// Personas
// ============================================================================

/** Fetch the stored persona (explicit + behavioral weights) for a user. */
export function getPersona(userId: string, signal?: AbortSignal): Promise<StoredPersona> {
  return request<StoredPersona>(`/api/v1/personas/${encodeURIComponent(userId)}`, {
    method: 'GET',
    signal,
  });
}

/**
 * Upload one or more PDFs (LinkedIn export, resume, etc.) and receive a
 * structured persona back. The backend persists the winning persona to
 * Snowflake as a side effect.
 */
export function extractPersonas(
  userId: string,
  files: File[],
  signal?: AbortSignal,
): Promise<BatchPersonaResponse> {
  const fd = new FormData();
  fd.append('user_id', userId);
  for (const file of files) fd.append('files', file);
  return request<BatchPersonaResponse>('/api/v1/personas/extract', {
    method: 'POST',
    formData: fd,
    signal,
  });
}

export interface ManualPersonaRequest {
  user_id: string;
  job_title: string;
  seniority: string;
  bio_summary?: string;
  persona_archetype?: string;
  linkedin_url?: string | null;
  explicit_category_weights: Record<string, number>;
}

/** Skip the PDF extractor and set persona weights by hand. */
export function createManualPersona(
  payload: ManualPersonaRequest,
  signal?: AbortSignal,
): Promise<{ user_id: string; persona_id: string; status: string }> {
  return request('/api/v1/personas/manual', {
    method: 'POST',
    json: payload,
    signal,
  });
}

/** Record a like / dislike / skip signal against an article. */
export function submitArticleFeedback(
  payload: ArticleFeedbackRequest,
  signal?: AbortSignal,
): Promise<ArticleFeedbackResponse> {
  return request<ArticleFeedbackResponse>('/api/v1/personas/feedback', {
    method: 'POST',
    json: payload,
    signal,
  });
}

// ============================================================================
// Newsletter (B2C)
// ============================================================================

/** Trigger the B2C LangGraph and return the rendered HTML newsletter. */
export function generateB2CNewsletter(
  payload: B2CNewsletterRequest,
  signal?: AbortSignal,
): Promise<B2CNewsletterResponse> {
  return request<B2CNewsletterResponse>('/api/v1/newsletter/b2c', {
    method: 'POST',
    json: payload,
    signal,
  });
}

// ============================================================================
// B2B Intelligence
// ============================================================================

export function generateB2BReport(
  payload: B2BReportRequest,
  signal?: AbortSignal,
): Promise<B2BReportResponse> {
  return request<B2BReportResponse>('/api/v1/b2b/report', {
    method: 'POST',
    json: payload,
    signal,
  });
}

// ============================================================================
// Search / recommendations
// ============================================================================

export function getRecommendations(
  userId: string,
  limit: number = 5,
  signal?: AbortSignal,
): Promise<RecommendationsResponse> {
  return request<RecommendationsResponse>('/api/v1/search/recommendations', {
    method: 'GET',
    query: { user_id: userId, limit },
    signal,
  });
}

// ============================================================================
// Ingestion / Dedup / Trend — admin / ops surface. Most app users never call
// these; they're here so admin pages can fire off pipeline runs.
// ============================================================================

export function triggerRssIngestion(signal?: AbortSignal): Promise<DAGTriggerResponse> {
  return request<DAGTriggerResponse>('/api/v1/ingestion/fetch-rss', {
    method: 'POST',
    signal,
  });
}

export function runDeduplication(signal?: AbortSignal): Promise<DAGTriggerResponse> {
  return request<DAGTriggerResponse>('/api/v1/deduplication/process', {
    method: 'POST',
    signal,
  });
}

export function rankDailyTrends(signal?: AbortSignal): Promise<DAGTriggerResponse> {
  return request<DAGTriggerResponse>('/api/v1/trend/rank', { method: 'POST', signal });
}

/** Read the latest ranked trend snapshot for the frontend. */
export function getTopTrends(
  limit: number = 20,
  status?: string,
  signal?: AbortSignal,
  date?: string,
): Promise<TrendTopResponse> {
  return request<TrendTopResponse>('/api/v1/trend/top', {
    method: 'GET',
    query: { limit, status, date },
    signal,
  });
}

// ============================================================================
// Admin — User/Company management
// ============================================================================

export function updateUserProfile(
  userId: string,
  fullName?: string,
  jobTitle?: string,
  seniority?: string,
  bioSummary?: string,
  linkedinUrl?: string,
  signal?: AbortSignal,
): Promise<{ user_id: string; status: string }> {
  return request<{ user_id: string; status: string }>(
    `/api/v1/admin/personas/${encodeURIComponent(userId)}`,
    {
      method: 'PUT',
      json: {
        full_name: fullName,
        job_title: jobTitle,
        seniority,
        bio_summary: bioSummary,
        linkedin_url: linkedinUrl,
      },
      signal,
    },
  );
}

export function updateCompanyProfile(
  companyId: string,
  name?: string,
  domain?: string,
  industry?: string,
  description?: string,
  companySize?: string,
  signal?: AbortSignal,
): Promise<{ company_id: string; status: string }> {
  return request<{ company_id: string; status: string }>(
    `/api/v1/admin/companies/${encodeURIComponent(companyId)}`,
    {
      method: 'PUT',
      json: {
        name,
        domain,
        industry,
        description,
        company_size: companySize,
      },
      signal,
    },
  );
}

export function createUser(
  email: string,
  fullName?: string,
  signal?: AbortSignal,
): Promise<{ id: string; email: string; status: string }> {
  return request<{ id: string; email: string; status: string }>('/api/v1/admin/users', {
    method: 'POST',
    json: { email, full_name: fullName },
    signal,
  });
}

export function createCompany(
  name: string,
  domain?: string,
  industry?: string,
  description?: string,
  companySize?: string,
  signal?: AbortSignal,
): Promise<{ id: string; name: string; status: string }> {
  return request<{ id: string; name: string; status: string }>('/api/v1/admin/companies', {
    method: 'POST',
    json: { name, domain, industry, description, company_size: companySize },
    signal,
  });
}

export function listUsers(
  limit: number = 50,
  offset: number = 0,
  signal?: AbortSignal,
): Promise<UserListResponse> {
  return request<UserListResponse>('/api/v1/admin/users', {
    method: 'GET',
    query: { limit, offset },
    signal,
  });
}

export function listCompanies(
  limit: number = 50,
  offset: number = 0,
  signal?: AbortSignal,
): Promise<CompanyListResponse> {
  return request<CompanyListResponse>('/api/v1/admin/companies', {
    method: 'GET',
    query: { limit, offset },
    signal,
  });
}

export interface CrossTenantNewsletterItem {
  id: string;
  user_id: string;
  edition_date: string;
  status: string;
  generated_at: string | null;
  execution_path_taken: string | null;
  user_email: string | null;
  user_full_name: string | null;
}

export interface CrossTenantNewslettersResponse {
  date: string;
  total: number;
  results: CrossTenantNewsletterItem[];
}

export function listGlobalNewsletters(
  date?: string,
  limit: number = 50,
  signal?: AbortSignal,
): Promise<CrossTenantNewslettersResponse> {
  return request<CrossTenantNewslettersResponse>('/api/v1/admin/newsletters/all', {
    method: 'GET',
    query: { date, limit },
    signal,
  });
}

export interface CrossTenantBriefItem {
  id: string;
  company_id: string;
  brief_date: string;
  urgency_tier: string | null;
  generated_at: string | null;
  content_length: number;
  company_name: string | null;
  company_domain: string | null;
}

export interface CrossTenantBriefsResponse {
  date: string;
  total: number;
  results: CrossTenantBriefItem[];
}

export function listGlobalBriefs(
  date?: string,
  limit: number = 50,
  signal?: AbortSignal,
): Promise<CrossTenantBriefsResponse> {
  return request<CrossTenantBriefsResponse>('/api/v1/admin/briefs/all', {
    method: 'GET',
    query: { date, limit },
    signal,
  });
}

export function getNewsletterArchive(
  userId: string,
  date?: string,
  limit: number = 10,
  signal?: AbortSignal,
): Promise<NewsletterArchiveResponse> {
  return request<NewsletterArchiveResponse>('/api/v1/admin/newsletters/archive', {
    method: 'GET',
    query: { user_id: userId, date, limit },
    signal,
  });
}

export function getBriefArchive(
  companyId: string,
  date?: string,
  limit: number = 10,
  signal?: AbortSignal,
): Promise<BriefArchiveResponse> {
  return request<BriefArchiveResponse>('/api/v1/admin/briefs/archive', {
    method: 'GET',
    query: { company_id: companyId, date, limit },
    signal,
  });
}

export function triggerAdminIngestion(signal?: AbortSignal): Promise<DAGTriggerResponse> {
  return request<DAGTriggerResponse>('/api/v1/admin/ingestion/trigger', {
    method: 'POST',
    signal,
  });
}
