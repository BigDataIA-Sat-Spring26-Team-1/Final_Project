'use client';

// Enterprise draft cycles — the primary "Generate B2B Intelligence Report"
// page. Calls the B2B LangGraph with a corporate client id, renders the
// returned Markdown, and caches it in sessionStorage so sibling pages
// (/seo, /company, /company/trends) can read the same report without
// re-paying the LLM latency.

import {
  Brain,
  Clock,
  FileText,
  Loader2,
  Plus,
  Settings2,
  TriangleAlert,
  Zap,
} from 'lucide-react';
import { useEffect, useState } from 'react';

import { PageWrapper } from '@/components/PageWrapper';
import {
  ApiError,
  generateB2BReport,
  type B2BReportResponse,
} from '@/lib/api';
import {
  getLastCompanyId,
  loadReport,
  saveReport,
  setLastCompanyId,
} from '@/lib/b2b-cache';
import { cn } from '@/lib/utils';

export default function CompanyDraftsPage() {
  const [companyId, setCompanyId] = useState('');
  const [report, setReport] = useState<B2BReportResponse | null>(null);
  const [generatedAt, setGeneratedAt] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Hydrate from cache on mount so returning users see their last report.
  useEffect(() => {
    const lastId = getLastCompanyId();
    if (lastId) {
      setCompanyId(lastId);
      const cached = loadReport(lastId);
      if (cached) {
        setReport(cached.payload);
        setGeneratedAt(cached.generated_at);
      }
    }
  }, []);

  const handleGenerate = async () => {
    if (!companyId.trim()) {
      setError('Enter a corporate client id before triggering the agent.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const response = await generateB2BReport({ user_id: companyId.trim() });
      setReport(response);
      const now = Date.now();
      setGeneratedAt(now);
      saveReport(companyId.trim(), response);
      setLastCompanyId(companyId.trim());
    } catch (err) {
      setError(
        err instanceof ApiError
          ? `${err.status}: ${err.detail ?? err.message}`
          : (err as Error).message,
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex items-end justify-between gap-6 flex-wrap">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold tracking-tight">Enterprise Draft Cycles</h1>
            <p className="text-dim text-lg">Agentic brief generation and editorial review loops.</p>
          </div>
          <button
            onClick={handleGenerate}
            disabled={loading || !companyId}
            className="bg-primary hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed text-primary-foreground px-8 py-3 rounded-2xl text-sm font-black transition-all flex items-center gap-2 shadow-2xl shadow-primary/20"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" /> Generating...
              </>
            ) : (
              <>
                <Plus className="w-5 h-5" /> Trigger Strategy Agent
              </>
            )}
          </button>
        </header>

        {/* Corporate client id — the B2B agent keys every retrieval off this. */}
        <div className="glass rounded-3xl p-6 border border-white/5">
          <label className="block space-y-2">
            <span className="text-xs uppercase tracking-widest text-dim font-bold">
              Corporate Client ID
            </span>
            <input
              type="text"
              value={companyId}
              onChange={(e) => setCompanyId(e.target.value)}
              placeholder="e.g. company-acme-001"
              className="w-full rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm outline-none focus:border-primary/40 font-mono"
            />
          </label>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <div className="glass rounded-[2rem] p-10 border border-white/5 space-y-6 bg-gradient-to-br from-secondary/10 to-transparent">
            <div className="flex items-center gap-3 text-secondary">
              <Brain className="w-6 h-6" />
              <h3 className="font-bold uppercase tracking-widest text-xs">Strategy Context</h3>
            </div>
            <div className="space-y-4">
              <div className="space-y-1">
                <p className="text-[10px] font-black text-dim uppercase tracking-widest leading-none">
                  Active Client
                </p>
                <p className="text-xl font-bold text-white">{companyId || '— not set —'}</p>
              </div>
              <div className="space-y-1">
                <p className="text-[10px] font-black text-dim uppercase tracking-widest leading-none">
                  Last Generation
                </p>
                <p className="text-xl font-bold text-emerald-400">
                  {generatedAt ? new Date(generatedAt).toLocaleString() : '—'}
                </p>
              </div>
            </div>
            <button
              type="button"
              title="Future hook — currently reads from backend defaults."
              className="flex items-center gap-2 text-xs font-bold text-dim hover:text-white transition-colors"
            >
              <Settings2 className="w-4 h-4" />
              Configure Multi-Agent Tuning
            </button>
          </div>

          <div className="glass rounded-[2rem] p-10 border border-white/5 flex flex-col items-center justify-center text-center space-y-5">
            <div
              className={cn(
                'w-16 h-16 rounded-full bg-white/5 flex items-center justify-center',
                loading && 'animate-pulse',
              )}
            >
              <Zap className="w-8 h-8 text-primary/40" />
            </div>
            <div className="space-y-1">
              <h3 className="text-lg font-bold">
                {loading
                  ? 'Agent in flight'
                  : report
                  ? 'Brief ready'
                  : 'Awaiting first generation'}
              </h3>
              <p className="text-xs text-dim max-w-[240px] leading-relaxed">
                {loading
                  ? 'LangGraph is scoring opportunities and drafting the Markdown report.'
                  : report
                  ? 'Scroll to view the most recent brief for this client.'
                  : 'Trigger the agent to produce a cross-cluster intelligence brief.'}
              </p>
            </div>
          </div>
        </div>

        {error && (
          <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-6 flex items-start gap-3">
            <TriangleAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <p className="text-sm text-rose-200">{error}</p>
          </div>
        )}

        {report && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold flex items-center gap-2">
                <Clock className="w-5 h-5 text-secondary" />
                Latest Brief Output
              </h2>
              <span
                className={cn(
                  'px-3 py-1 rounded-full text-[10px] font-black tracking-widest uppercase border',
                  report.status === 'SUCCESS'
                    ? 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20'
                    : 'bg-amber-500/10 text-amber-500 border-amber-500/20',
                )}
              >
                {report.status}
              </span>
            </div>

            <div className="glass rounded-3xl p-8 border border-white/5 space-y-4">
              <div className="flex items-center gap-2 text-dim text-xs font-bold uppercase tracking-widest">
                <FileText className="w-4 h-4" />
                Markdown Brief · {companyId}
              </div>
              {/* Markdown from the agent — rendered as preformatted text. For a
                  richer render we could drop in react-markdown; keeping it raw
                  keeps the demo free of extra deps. */}
              <pre className="whitespace-pre-wrap text-sm leading-relaxed text-white/90 font-mono bg-white/[0.02] rounded-2xl border border-white/10 p-6 max-h-[70vh] overflow-auto">
                {report.report || 'Empty report — no intelligence signals for this client yet.'}
              </pre>
            </div>
          </div>
        )}
      </div>
    </PageWrapper>
  );
}
