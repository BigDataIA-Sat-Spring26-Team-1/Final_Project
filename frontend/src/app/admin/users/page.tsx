'use client';

// User management. The list view requires a backend endpoint that doesn't
// exist yet (no GET /api/v1/users), so this page acts as a single-record
// inspector instead: the admin types in a user_id and we pull the persona via
// the existing /personas/{user_id} read. The placeholder list rows are kept
// to communicate the intended UX once the list endpoint lands.

import {
  ChevronRight,
  Filter,
  Loader2,
  Mail,
  Search,
  TriangleAlert,
} from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';

import { PageWrapper } from '@/components/PageWrapper';
import { ApiError, getPersona, type StoredPersona } from '@/lib/api';
import { cn } from '@/lib/utils';

export default function AdminUsersPage() {
  const [userId, setUserId] = useState('');
  const [persona, setPersona] = useState<StoredPersona | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Auto-load when the input contains a non-empty id (debounced via abort).
  useEffect(() => {
    if (!userId.trim()) {
      setPersona(null);
      setError(null);
      return;
    }
    const controller = new AbortController();
    (async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getPersona(userId.trim(), controller.signal);
        setPersona(data);
      } catch (err) {
        if ((err as Error).name === 'AbortError') return;
        setPersona(null);
        setError(
          err instanceof ApiError
            ? err.status === 404
              ? `No persona found for "${userId.trim()}".`
              : `${err.status}: ${err.detail ?? err.message}`
            : (err as Error).message,
        );
      } finally {
        setLoading(false);
      }
    })();
    return () => controller.abort();
  }, [userId]);

  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex items-end justify-between gap-4 flex-wrap">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold tracking-tight">User Management</h1>
            <p className="text-dim text-lg">
              Inspect personas and behavioral weights for any individual user.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center glass rounded-xl px-4 py-2 border border-white/5 focus-within:border-primary/40">
              <Search className="w-4 h-4 text-dim mr-2" />
              <input
                type="text"
                value={userId}
                onChange={(e) => setUserId(e.target.value)}
                placeholder="Lookup by user id..."
                className="bg-transparent border-none outline-none text-sm w-56 placeholder:text-dim font-mono"
              />
            </div>
            <button
              type="button"
              title="Filtering needs the list endpoint."
              disabled
              className="p-2.5 glass rounded-xl border border-white/5 opacity-50 cursor-not-allowed"
            >
              <Filter className="w-5 h-5 text-dim" />
            </button>
          </div>
        </header>

        {/* Inspector card — populated by the lookup form above. */}
        <div className="glass rounded-3xl border border-white/5 p-8">
          {!userId.trim() ? (
            <p className="text-sm text-dim italic">
              Type a user id to look up that user&apos;s persona profile.
            </p>
          ) : loading ? (
            <div className="flex items-center gap-3 text-dim">
              <Loader2 className="w-4 h-4 animate-spin" /> Loading {userId}…
            </div>
          ) : error ? (
            <div className="flex items-start gap-3 text-rose-200">
              <TriangleAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              <p className="text-sm">{error}</p>
            </div>
          ) : persona ? (
            <UserInspector persona={persona} />
          ) : null}
        </div>

        {/* Bulk listing placeholder — kept visible so reviewers see the intended
            UX. Once /api/v1/users lands the rows below get replaced by a real
            paginated table mirroring the schema. */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-black uppercase tracking-widest text-dim">
              Full User Roster
            </h2>
            <span className="text-[10px] uppercase tracking-widest font-bold text-amber-400">
              pending /api/v1/users endpoint
            </span>
          </div>
          <div className="glass rounded-3xl border border-dashed border-white/10 p-12 text-center text-sm text-dim italic">
            The bulk roster will render here once Abhinav&apos;s list endpoint is
            available. Use the lookup field above to inspect users by id in
            the meantime.
          </div>
        </div>
      </div>
    </PageWrapper>
  );
}

function UserInspector({ persona }: { persona: StoredPersona }) {
  const topExplicit = Object.entries(persona.explicit_category_weights)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5);
  const topBehavioral = Object.entries(persona.behavioral_category_weights)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5);

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4 flex-wrap">
        <div className="w-14 h-14 rounded-full bg-secondary/20 flex items-center justify-center text-secondary font-bold text-lg">
          {(persona.user_id?.charAt(0) ?? '?').toUpperCase()}
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-xl font-bold">{persona.job_title ?? 'Unknown role'}</p>
          <p className="text-sm text-dim">
            {persona.seniority ?? '—'}
            {persona.persona_archetype ? ` · ${persona.persona_archetype}` : ''}
          </p>
          <p className="text-xs text-dim font-mono mt-1">{persona.user_id}</p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href={`/newsletter`}
            className="p-2 hover:bg-white/5 rounded-lg text-dim hover:text-white"
            title="Generate newsletter for this user"
          >
            <Mail className="w-4 h-4" />
          </Link>
          <Link
            href={`/user/persona`}
            className="p-2 hover:bg-white/5 rounded-lg text-dim hover:text-white"
            title="Open persona editor"
          >
            <ChevronRight className="w-4 h-4" />
          </Link>
        </div>
      </div>

      {persona.bio_summary && (
        <p className="text-sm text-dim leading-relaxed border-l-2 border-secondary/40 pl-4">
          {persona.bio_summary}
        </p>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <WeightsBlock title="Explicit weights" entries={topExplicit} />
        <WeightsBlock title="Behavioral weights" entries={topBehavioral} />
      </div>
    </div>
  );
}

function WeightsBlock({
  title,
  entries,
}: {
  title: string;
  entries: [string, number][];
}) {
  return (
    <div className="space-y-3">
      <p className="text-[10px] font-black uppercase tracking-widest text-dim">{title}</p>
      {entries.length === 0 ? (
        <p className="text-xs text-dim italic">No weights recorded.</p>
      ) : (
        <ul className="space-y-2">
          {entries.map(([cat, weight]) => (
            <li key={cat} className="flex items-center justify-between gap-3">
              <span className="text-sm font-bold text-white">
                {cat.replace(/_/g, ' ')}
              </span>
              <div className="flex items-center gap-2">
                <div className="w-24 h-1.5 bg-white/5 rounded-full">
                  <div
                    className={cn('h-full rounded-full', 'bg-primary')}
                    style={{ width: `${Math.round(weight * 100)}%` }}
                  />
                </div>
                <span className="text-xs font-mono w-10 text-right">
                  {(weight * 100).toFixed(0)}%
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
