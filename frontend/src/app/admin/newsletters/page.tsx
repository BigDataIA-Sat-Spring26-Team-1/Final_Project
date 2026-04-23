'use client';

// Global Archive — separate B2C + B2B surfaces driven by admin archive
// endpoints. Tab 1 (B2C) lets admins pick any user and read their latest +
// past newsletters. Tab 2 (B2B) does the same for companies with content
// briefs. Both tabs share a simple layout: selector → archive list → viewer.

import { Calendar, FileText, Mail, Newspaper, TriangleAlert, Users } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

import { CompanySwitcher } from '@/components/CompanySwitcher';
import { PageWrapper } from '@/components/PageWrapper';
import { Spinner } from '@/components/Spinner';
import { UserSwitcher } from '@/components/UserSwitcher';
import {
  ApiError,
  getBriefArchive,
  getNewsletterArchive,
  type BriefArchiveItem,
  type NewsletterArchiveItem,
} from '@/lib/api';
import { cn } from '@/lib/utils';

type Mode = 'B2C' | 'B2B';

export default function GlobalArchivePage() {
  const [mode, setMode] = useState<Mode>('B2C');

  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="space-y-3">
          <h1 className="text-4xl font-bold tracking-tight">Global Archive</h1>
          <p className="text-dim text-lg">
            Browse the full archive of newsletters and briefs, per tenant.
          </p>
        </header>

        <div className="flex items-center gap-1 p-1 glass rounded-2xl w-fit border border-white/5">
          <TabButton
            active={mode === 'B2C'}
            onClick={() => setMode('B2C')}
            icon={Users}
            label="B2C User Newsletters"
          />
          <TabButton
            active={mode === 'B2B'}
            onClick={() => setMode('B2B')}
            icon={FileText}
            label="B2B Company Briefs"
          />
        </div>

        {mode === 'B2C' ? <B2CArchive /> : <B2BArchive />}
      </div>
    </PageWrapper>
  );
}

function TabButton({
  active,
  onClick,
  icon: Icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'px-6 py-2 rounded-xl text-sm font-bold transition-all flex items-center gap-2',
        active
          ? 'bg-secondary text-white shadow-lg shadow-secondary/20'
          : 'text-dim hover:text-white',
      )}
    >
      <Icon className="w-4 h-4" />
      {label}
    </button>
  );
}

function B2CArchive() {
  const [userId, setUserId] = useState<string>('');
  const [items, setItems] = useState<NewsletterArchiveItem[]>([]);
  const [selected, setSelected] = useState<NewsletterArchiveItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (id: string, signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    setItems([]);
    setSelected(null);
    try {
      const res = await getNewsletterArchive(id, undefined, 50, signal);
      setItems(res.results);
      setSelected(res.results[0] ?? null);
    } catch (err) {
      if ((err as Error).name === 'AbortError') return;
      setError(
        err instanceof ApiError
          ? `${err.status}: ${err.detail ?? err.message}`
          : (err as Error).message,
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!userId) return;
    const controller = new AbortController();
    load(userId, controller.signal);
    return () => controller.abort();
  }, [userId, load]);

  return (
    <div className="space-y-6">
      <div className="glass rounded-3xl p-6 border border-white/5 flex items-center gap-4 flex-wrap">
        <Mail className="w-5 h-5 text-secondary" />
        <span className="text-sm font-bold">Select a user</span>
        <UserSwitcher currentUserId={userId || null} onSelect={(id) => setUserId(id)} />
      </div>

      {error && (
        <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-6 flex items-start gap-3">
          <TriangleAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <p className="text-sm text-rose-200">{error}</p>
        </div>
      )}

      {!userId ? (
        <div className="glass rounded-3xl p-10 border border-dashed border-white/20 text-center text-dim">
          Pick a user to load their newsletter history.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <aside className="glass rounded-3xl border border-white/5 p-6 space-y-3 h-fit">
            <h3 className="text-xs font-black uppercase tracking-widest text-dim flex items-center gap-2">
              <Calendar className="w-4 h-4" /> Editions
            </h3>
            {loading ? (
              <Spinner label="Loading archive" />
            ) : items.length === 0 ? (
              <p className="text-sm text-dim italic">No newsletters stored for this user yet.</p>
            ) : (
              <ul className="space-y-2">
                {items.map((n) => (
                  <li key={n.id}>
                    <button
                      onClick={() => setSelected(n)}
                      className={cn(
                        'w-full text-left px-3 py-2 rounded-xl text-sm transition',
                        selected?.id === n.id
                          ? 'bg-primary/10 border border-primary/20 text-white'
                          : 'hover:bg-white/5 text-dim',
                      )}
                    >
                      <p className="font-mono text-xs">{n.edition_date}</p>
                      <p className="text-[10px] uppercase tracking-widest text-dim mt-0.5">
                        {n.status}
                      </p>
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </aside>

          <div className="lg:col-span-3 glass rounded-3xl border border-white/5 p-8">
            {loading && !selected ? (
              <Spinner label="Loading newsletter" />
            ) : !selected ? (
              <div className="flex flex-col items-center justify-center py-12 text-dim">
                <Newspaper className="w-12 h-12 mb-4" />
                <p>Pick an edition on the left.</p>
              </div>
            ) : selected.final_content || selected.draft_content ? (
              <article
                className="newsletter-preview rounded-2xl border border-white/10 bg-white/[0.02] p-8 max-h-[70vh] overflow-auto prose prose-invert max-w-none"
                dangerouslySetInnerHTML={{
                  __html: selected.final_content || selected.draft_content || '',
                }}
              />
            ) : (
              <p className="text-dim italic">No content stored for this edition.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function B2BArchive() {
  const [companyId, setCompanyId] = useState<string>('');
  const [items, setItems] = useState<BriefArchiveItem[]>([]);
  const [selected, setSelected] = useState<BriefArchiveItem | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (id: string, signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    setItems([]);
    setSelected(null);
    try {
      const res = await getBriefArchive(id, undefined, 50, signal);
      setItems(res.results);
      setSelected(res.results[0] ?? null);
    } catch (err) {
      if ((err as Error).name === 'AbortError') return;
      setError(
        err instanceof ApiError
          ? `${err.status}: ${err.detail ?? err.message}`
          : (err as Error).message,
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!companyId) return;
    const controller = new AbortController();
    load(companyId, controller.signal);
    return () => controller.abort();
  }, [companyId, load]);

  return (
    <div className="space-y-6">
      <div className="glass rounded-3xl p-6 border border-white/5 flex items-center gap-4 flex-wrap">
        <FileText className="w-5 h-5 text-secondary" />
        <span className="text-sm font-bold">Select a company</span>
        <CompanySwitcher currentCompanyId={companyId || null} onSelect={(id) => setCompanyId(id)} />
      </div>

      {error && (
        <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-6 flex items-start gap-3">
          <TriangleAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
          <p className="text-sm text-rose-200">{error}</p>
        </div>
      )}

      {!companyId ? (
        <div className="glass rounded-3xl p-10 border border-dashed border-white/20 text-center text-dim">
          Pick a company to load its brief history.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          <aside className="glass rounded-3xl border border-white/5 p-6 space-y-3 h-fit">
            <h3 className="text-xs font-black uppercase tracking-widest text-dim flex items-center gap-2">
              <Calendar className="w-4 h-4" /> Briefs
            </h3>
            {loading ? (
              <Spinner label="Loading archive" />
            ) : items.length === 0 ? (
              <p className="text-sm text-dim italic">No briefs stored for this company yet.</p>
            ) : (
              <ul className="space-y-2">
                {items.map((b) => (
                  <li key={b.id}>
                    <button
                      onClick={() => setSelected(b)}
                      className={cn(
                        'w-full text-left px-3 py-2 rounded-xl text-sm transition',
                        selected?.id === b.id
                          ? 'bg-primary/10 border border-primary/20 text-white'
                          : 'hover:bg-white/5 text-dim',
                      )}
                    >
                      <p className="font-mono text-xs">{b.brief_date}</p>
                      {b.urgency_tier && (
                        <p className="text-[10px] uppercase tracking-widest text-dim mt-0.5">
                          {b.urgency_tier.replace(/_/g, ' ')}
                        </p>
                      )}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </aside>

          <div className="lg:col-span-3 glass rounded-3xl border border-white/5 p-8">
            {loading && !selected ? (
              <Spinner label="Loading brief" />
            ) : !selected ? (
              <div className="flex flex-col items-center justify-center py-12 text-dim">
                <FileText className="w-12 h-12 mb-4" />
                <p>Pick a brief on the left.</p>
              </div>
            ) : selected.brief_content ? (
              <pre className="whitespace-pre-wrap text-sm leading-relaxed text-white/90 font-mono bg-white/[0.02] rounded-2xl border border-white/10 p-6 max-h-[70vh] overflow-auto">
                {selected.brief_content}
              </pre>
            ) : (
              <p className="text-dim italic">No content stored for this brief.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
