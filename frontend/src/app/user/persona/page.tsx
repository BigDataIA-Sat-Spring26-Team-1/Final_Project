'use client';

// Persona dashboard. Reads from /auth/me to know which user we're editing —
// no manual id input. The "Update Interests" button is a toggle: clicking it
// switches the page into edit mode (bio becomes editable, chips become
// selectable), and clicking "Save Interests" commits both to Snowflake in
// one shot.

import { CheckCircle2, Loader2, Pencil, Save, TriangleAlert, X } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { PageWrapper } from '@/components/PageWrapper';
import { useAuth } from '@/components/AuthProvider';
import {
  ApiError,
  getPersona,
  updatePersonaCategories,
  updateUserProfile,
  type StoredPersona,
} from '@/lib/api';
import { cn } from '@/lib/utils';

// Hardcoded taxonomy — mirrors the onboarding manual flow. The classification
// DAG writes values into this same namespace, so everything the user picks
// here lines up with how articles are tagged downstream.
const CATEGORY_OPTIONS: string[] = [
  'llms',
  'ai_agents',
  'computer_vision',
  'security',
  'hardware',
  'software_engineering',
  'ai_policy',
  'general_ai',
  'data_engineering',
  'startups',
];

export default function UserPersonaPage() {
  const { user } = useAuth();
  const userId = user?.id ?? '';

  const [persona, setPersona] = useState<StoredPersona | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Edit state is off by default — the page is read-only until the user
  // clicks "Update Interests". Clicking again (the save button) commits.
  const [editing, setEditing] = useState(false);
  const [selectedCategories, setSelectedCategories] = useState<Set<string>>(new Set());
  const [bioDraft, setBioDraft] = useState('');
  const [saving, setSaving] = useState(false);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);

  const loadPersona = useCallback(async (id: string, signal?: AbortSignal) => {
    setLoading(true);
    setError(null);
    try {
      const data = await getPersona(id, signal);
      setPersona(data);
    } catch (err) {
      if ((err as Error).name === 'AbortError') return;
      setPersona(null);
      setError(
        err instanceof ApiError
          ? err.status === 404
            ? 'No persona found — run onboarding first.'
            : `${err.status}: ${err.detail ?? err.message}`
          : (err as Error).message,
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!userId) return;
    const controller = new AbortController();
    loadPersona(userId, controller.signal);
    return () => controller.abort();
  }, [userId, loadPersona]);

  // Seed the editable state whenever the persona loads.
  useEffect(() => {
    if (!persona) {
      setSelectedCategories(new Set());
      setBioDraft('');
      return;
    }
    setSelectedCategories(new Set(Object.keys(persona.explicit_category_weights || {})));
    setBioDraft(persona.bio_summary || '');
  }, [persona]);

  const toggleCategory = (cat: string) => {
    if (!editing) return;
    setSelectedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(cat)) {
        next.delete(cat);
      } else {
        next.add(cat);
      }
      return next;
    });
    setSavedMsg(null);
  };

  const handleToggleEdit = () => {
    if (!editing) {
      setEditing(true);
      setSavedMsg(null);
      setError(null);
      return;
    }
    // `editing` was true → commit.
    void handleSave();
  };

  const handleCancel = () => {
    if (persona) {
      setSelectedCategories(new Set(Object.keys(persona.explicit_category_weights || {})));
      setBioDraft(persona.bio_summary || '');
    }
    setEditing(false);
    setSavedMsg(null);
    setError(null);
  };

  const handleSave = async () => {
    if (!userId) return;
    setSaving(true);
    setError(null);
    setSavedMsg(null);
    try {
      const picks = Array.from(selectedCategories);
      const weight = picks.length ? 1 / picks.length : 0;
      const payload: Record<string, number> = {};
      picks.forEach((p) => {
        payload[p] = Number(weight.toFixed(4));
      });
      // Commit bio first so a category-save failure doesn't leave the bio
      // dirty; then the category weights. Both go to the admin surface which
      // the backend trusts on a Bearer token.
      if (bioDraft.trim() !== (persona?.bio_summary || '').trim()) {
        await updateUserProfile(userId, undefined, undefined, undefined, bioDraft.trim() || undefined);
      }
      await updatePersonaCategories(userId, payload);
      setSavedMsg('Profile updated — your feed will reflect the new interests on the next run.');
      setEditing(false);
      await loadPersona(userId);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail ?? err.message : (err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  const topInterests = useMemo(() => {
    if (!persona) return [];
    return Object.entries(persona.explicit_category_weights)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 6)
      .map(([cat]) => cat);
  }, [persona]);

  const topBehavioral = useMemo(() => {
    if (!persona) return [];
    return Object.entries(persona.behavioral_category_weights)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 3);
  }, [persona]);

  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex items-end justify-between gap-6 flex-wrap">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold tracking-tight">Persona Intelligence</h1>
            <p className="text-dim text-lg">
              Deep technical profile and behavioral refinement
              {persona?.job_title ? ` for ${persona.job_title}` : ''}.
            </p>
          </div>
        </header>

        {error && (
          <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-6 flex items-start gap-3">
            <TriangleAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <p className="text-sm text-rose-200">{error}</p>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-8">
            <div className="glass rounded-[2rem] p-10 border border-white/5 space-y-8">
              <div className="space-y-2">
                <h3 className="text-2xl font-bold">Dynamic Persona Logic</h3>
                <p className="text-sm text-dim">
                  Explicit weights come from onboarding (LinkedIn PDF extraction or the manual
                  picker). Interest clusters are the highest-weighted categories from the same
                  source — they drive your personalized article ranking.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="space-y-4">
                  <h4 className="text-xs font-black uppercase tracking-widest text-secondary">
                    Explicit Category Weights
                  </h4>
                  <div className="space-y-3">
                    {loading ? (
                      <EmptyHint loading hint="" />
                    ) : persona ? (
                      Object.entries(persona.explicit_category_weights)
                        .sort(([, a], [, b]) => b - a)
                        .slice(0, 5)
                        .map(([cat, weight]) => (
                          <RoleItem
                            key={cat}
                            title={humanize(cat)}
                            score={Math.round(weight * 100)}
                          />
                        ))
                    ) : (
                      <EmptyHint loading={loading} hint="no persona loaded" />
                    )}
                  </div>
                </div>

                <div className="space-y-4">
                  <h4 className="text-xs font-black uppercase tracking-widest text-secondary">
                    Interest Clusters
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {persona ? (
                      topInterests.map((tag) => (
                        <span
                          key={tag}
                          className="px-3 py-1.5 rounded-xl bg-white/5 border border-white/10 text-xs font-bold text-white"
                        >
                          {humanize(tag)}
                        </span>
                      ))
                    ) : (
                      <EmptyHint loading={loading} hint="—" />
                    )}
                  </div>
                </div>
              </div>
            </div>

            <div className="glass rounded-[2rem] p-10 border border-white/5 space-y-4">
              <h3 className="text-xl font-bold">Behavioral Refinement</h3>
              <p className="text-sm text-dim">
                Weights learned from your like / dislike / skip feedback. These layer on top of
                the onboarding profile.
              </p>
              {persona ? (
                topBehavioral.length === 0 ? (
                  <p className="text-sm text-dim italic">
                    No behavioral signals yet — interact with articles to start shaping this.
                  </p>
                ) : (
                  topBehavioral.map(([cat, weight]) => (
                    <div key={cat} className="flex items-center gap-4 pt-2">
                      <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-primary"
                          style={{ width: `${Math.round(weight * 100)}%` }}
                        />
                      </div>
                      <span className="text-xs font-bold text-primary min-w-[160px] text-right">
                        {Math.round(weight * 100)}% · {humanize(cat)}
                      </span>
                    </div>
                  ))
                )
              ) : (
                <EmptyHint loading={loading} hint="—" />
              )}
            </div>
          </div>

          <div className="space-y-6">
            <div className="glass rounded-3xl p-8 border border-white/5 space-y-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-lg font-bold">Your Profile</h3>
                  <p className="text-xs text-dim mt-1">
                    Click <em>Update Interests</em> to edit your bio and category picks. Click
                    again to save.
                  </p>
                </div>
                {editing && (
                  <button
                    type="button"
                    onClick={handleCancel}
                    disabled={saving}
                    title="Cancel without saving"
                    className="p-2 rounded-xl text-dim hover:text-white hover:bg-white/5 transition"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>

              <label className="space-y-1.5 block">
                <span className="text-[10px] font-black uppercase tracking-widest text-dim">Bio</span>
                <textarea
                  value={bioDraft}
                  onChange={(e) => setBioDraft(e.target.value)}
                  disabled={!editing || saving}
                  rows={4}
                  placeholder="A short professional summary"
                  className="w-full rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm outline-none focus:border-primary/40 disabled:opacity-70 disabled:cursor-not-allowed"
                />
              </label>

              <div className="space-y-2">
                <span className="text-[10px] font-black uppercase tracking-widest text-dim">
                  Interest Categories
                </span>
                <div className="flex flex-wrap gap-2">
                  {CATEGORY_OPTIONS.map((cat) => {
                    const active = selectedCategories.has(cat);
                    return (
                      <button
                        key={cat}
                        type="button"
                        onClick={() => toggleCategory(cat)}
                        disabled={!editing || saving}
                        className={cn(
                          'px-3 py-1.5 rounded-xl border text-xs font-bold transition-all uppercase',
                          active
                            ? 'bg-primary/10 text-primary border-primary/30'
                            : 'bg-white/5 text-dim border-white/10 hover:border-white/20',
                          !editing && 'cursor-default opacity-80',
                          editing && !saving && 'cursor-pointer',
                        )}
                      >
                        {humanize(cat)}
                      </button>
                    );
                  })}
                </div>
              </div>

              <button
                onClick={handleToggleEdit}
                disabled={!userId || saving || (!persona && !editing)}
                className="w-full flex items-center justify-center gap-2 bg-primary hover:bg-primary/90 disabled:opacity-40 text-primary-foreground px-4 py-2.5 rounded-xl text-sm font-bold transition-all"
              >
                {saving ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : editing ? (
                  <Save className="w-4 h-4" />
                ) : (
                  <Pencil className="w-4 h-4" />
                )}
                {saving ? 'Saving…' : editing ? 'Save Changes' : 'Update Interests'}
              </button>

              {savedMsg && (
                <div className="flex items-center gap-2 text-xs text-emerald-400">
                  <CheckCircle2 className="w-4 h-4" />
                  {savedMsg}
                </div>
              )}
            </div>

            {persona?.persona_archetype && (
              <div className="glass rounded-3xl p-8 border border-white/5 space-y-3">
                <h3 className="text-lg font-bold">Archetype</h3>
                <p className="text-xs font-mono uppercase tracking-widest text-primary">
                  {persona.persona_archetype}
                </p>
                <p className="text-xs text-dim leading-relaxed">
                  Assigned during onboarding. Swapping interests above won&apos;t re-tag the
                  archetype; re-run onboarding if your core role changes.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </PageWrapper>
  );
}

// ---- Small presentational helpers -------------------------------------------

/** Turn `ai_agents` into `AI Agents` — the backend taxonomy uses snake_case. */
function humanize(key: string): string {
  return key
    .split('_')
    .map((w) => (w === 'ai' || w === 'llms' ? w.toUpperCase() : w[0]?.toUpperCase() + w.slice(1)))
    .join(' ');
}

function RoleItem({ title, score }: { title: string; score: number }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm font-bold text-white">{title}</span>
      <span className="text-xs font-bold text-primary">{score}%</span>
    </div>
  );
}

function EmptyHint({ loading, hint }: { loading: boolean; hint: string }) {
  return <p className="text-xs text-dim italic">{loading ? 'Loading...' : hint}</p>;
}
