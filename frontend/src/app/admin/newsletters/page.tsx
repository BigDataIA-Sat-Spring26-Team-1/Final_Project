'use client';

// Global Distribution Archive (admin view of newsletter drafts).
//
// Two real wires:
//   1. "Trigger Force Sync" runs the ingestion endpoint to pull fresh articles.
//   2. The "Review" jump-link kicks the user into /admin/newsletters/review
//      with a chosen user_id + execution mode.
//
// The archive list itself depends on a draft-history endpoint that doesn't
// exist (GET /api/v1/admin/newsletters/archive). Until that lands, the list
// shows a clearly-labelled placeholder and a single "queue a review" form.

import {
  Calendar,
  CheckCircle2,
  Eye,
  Loader2,
  Mail,
  TriangleAlert,
} from 'lucide-react';
import { useState } from 'react';

import { PageWrapper } from '@/components/PageWrapper';
import {
  ApiError,
  triggerRssIngestion,
  type DAGTriggerResponse,
} from '@/lib/api';

export default function AdminNewslettersPage() {
  const [reviewUser, setReviewUser] = useState('');
  const [mode, setMode] = useState<'fast' | 'polished'>('polished');

  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<DAGTriggerResponse | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);

  const handleForceSync = async () => {
    setSyncing(true);
    setSyncResult(null);
    setSyncError(null);
    try {
      const res = await triggerRssIngestion();
      setSyncResult(res);
    } catch (err) {
      setSyncError(
        err instanceof ApiError
          ? `${err.status}: ${err.detail ?? err.message}`
          : (err as Error).message,
      );
    } finally {
      setSyncing(false);
    }
  };

  const reviewHref = reviewUser.trim()
    ? `/admin/newsletters/review?user_id=${encodeURIComponent(reviewUser.trim())}&mode=${mode}`
    : '#';

  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex items-end justify-between gap-4 flex-wrap">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold tracking-tight">Global Distribution Archive</h1>
            <p className="text-dim text-lg">
              Trigger ingestion runs and queue draft reviews from one console.
            </p>
          </div>
          <button
            onClick={handleForceSync}
            disabled={syncing}
            className="bg-secondary hover:bg-secondary/90 disabled:opacity-40 disabled:cursor-not-allowed text-white px-6 py-3 rounded-2xl text-sm font-bold transition-all flex items-center gap-2"
          >
            {syncing ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" /> Syncing...
              </>
            ) : (
              <>
                <Mail className="w-5 h-5" /> Trigger Force Sync
              </>
            )}
          </button>
        </header>

        {syncError && (
          <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-6 flex items-start gap-3">
            <TriangleAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <p className="text-sm text-rose-200">{syncError}</p>
          </div>
        )}

        {/* Trigger handoff — the pipeline runs on Airflow, so the only fields
            we have synchronously are the run id + status. Article counts land
            in the scheduler logs once the DAG finishes. */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="glass rounded-[2rem] p-8 border border-white/5 space-y-2">
            <p className="text-[10px] font-black text-dim uppercase tracking-widest leading-none">
              Last Trigger · Status
            </p>
            <h3 className="text-3xl font-black">{syncResult?.status ?? '—'}</h3>
            <p className="text-xs text-emerald-400 font-bold">
              {syncResult ? 'handed off to scheduler' : 'no trigger this session'}
            </p>
          </div>
          <div className="glass rounded-[2rem] p-8 border border-white/5 space-y-2 bg-secondary/5">
            <p className="text-[10px] font-black text-secondary uppercase tracking-widest leading-none">
              DAG · Run State
            </p>
            <h3 className="text-3xl font-black">{syncResult?.state ?? '—'}</h3>
            <p className="text-xs text-dim font-mono truncate">
              {syncResult?.dag_id ?? 'ingestion_dag'}
            </p>
          </div>
          <div className="glass rounded-[2rem] p-8 border border-white/5 space-y-2">
            <p className="text-[10px] font-black text-dim uppercase tracking-widest leading-none">
              Run ID
            </p>
            <h3 className="text-xl font-black break-all">
              {syncResult?.dag_run_id ?? '—'}
            </h3>
            <p className="text-xs text-dim font-bold tracking-tighter">
              Follow progress in the Airflow UI
            </p>
          </div>
        </div>

        {/* Review queue — real, simple form that hands off to the review page. */}
        <div className="space-y-6">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <h2 className="text-xl font-bold flex items-center gap-2">
              <Calendar className="w-5 h-5 text-secondary" />
              Queue Editorial Review
            </h2>
            <span className="text-[10px] uppercase tracking-widest font-bold text-amber-400">
              archive list pending /admin/newsletters/archive
            </span>
          </div>

          <div className="glass rounded-3xl p-8 border border-white/5 space-y-4">
            <p className="text-sm text-dim">
              Until the draft archive endpoint ships, manually review a draft by
              entering a user id below. The review page will trigger a fresh
              generation and load it into the editor.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <input
                type="text"
                value={reviewUser}
                onChange={(e) => setReviewUser(e.target.value)}
                placeholder="user id"
                className="rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm outline-none focus:border-primary/40 font-mono md:col-span-2"
              />
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value as 'fast' | 'polished')}
                className="rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm outline-none focus:border-primary/40"
              >
                <option value="polished">polished (full editor loop)</option>
                <option value="fast">fast (skip editor)</option>
              </select>
            </div>
            <a
              href={reviewHref}
              aria-disabled={!reviewUser.trim()}
              className={
                'inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-primary text-primary-foreground text-sm font-bold ' +
                (reviewUser.trim() ? 'hover:opacity-90' : 'opacity-40 cursor-not-allowed pointer-events-none')
              }
            >
              <Eye className="w-4 h-4" />
              Open Review Editor
            </a>
          </div>
        </div>

        {/* Placeholder rows — kept so reviewers see the eventual shape. */}
        <div className="space-y-4">
          <h2 className="text-xs font-black uppercase tracking-widest text-dim">
            Daily Common Archives (placeholder)
          </h2>
          {[1, 2, 3].map((i) => (
            <PlaceholderRow key={i} index={i} />
          ))}
        </div>
      </div>
    </PageWrapper>
  );
}

function PlaceholderRow({ index }: { index: number }) {
  return (
    <div className="glass rounded-3xl p-6 border border-dashed border-white/10 flex items-center justify-between">
      <div className="flex items-center gap-6 flex-1">
        <div className="w-14 h-14 rounded-2xl bg-white/5 border border-white/5 flex items-center justify-center">
          <CheckCircle2 className="w-5 h-5 text-dim" />
        </div>
        <div>
          <p className="text-sm font-bold text-dim">Placeholder draft #{index}</p>
          <p className="text-xs text-dim italic">
            Will populate once the draft archive endpoint is wired.
          </p>
        </div>
      </div>
    </div>
  );
}

