'use client';

// Company profile — mirrors the user persona page. Auto-loads the logged-in
// tenant's row (no dropdown), renders a read-only view by default, and
// flips to edit mode on "Update Profile". All fields are mandatory; we
// block save on the frontend and the backend rejects partial payloads with
// a 422 so downstream DAGs never see empty values.

import { CheckCircle2, Loader2, Pencil, Save, TriangleAlert, X } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

import { PageWrapper } from '@/components/PageWrapper';
import { useAuth } from '@/components/AuthProvider';
import {
  ApiError,
  getCompanyProfile,
  updateCompanyProfile,
  type CompanyDetail,
} from '@/lib/api';
import { cn } from '@/lib/utils';

const COMPANY_SIZE_OPTIONS: { value: string; label: string }[] = [
  { value: 'EARLY_STAGE', label: 'Early Stage (1–50)' },
  { value: 'GROWTH', label: 'Growth (51–500)' },
  { value: 'MID_MARKET', label: 'Mid Market (501–5,000)' },
  { value: 'ENTERPRISE', label: 'Enterprise (5,000+)' },
];

const TONE_OPTIONS: { value: string; label: string }[] = [
  { value: 'AUTHORITATIVE', label: 'Authoritative' },
  { value: 'CONVERSATIONAL', label: 'Conversational' },
  { value: 'TECHNICAL', label: 'Technical' },
  { value: 'VISIONARY', label: 'Visionary' },
  { value: 'PLAYFUL', label: 'Playful' },
];

type Draft = {
  name: string;
  domain: string;
  industry: string;
  description: string;
  company_size: string;
  target_audience: string;
  key_products: string;
  content_pillars: string;
  competitors: string;
  tone_of_voice: string;
};

const EMPTY_DRAFT: Draft = {
  name: '',
  domain: '',
  industry: '',
  description: '',
  company_size: '',
  target_audience: '',
  key_products: '',
  content_pillars: '',
  competitors: '',
  tone_of_voice: '',
};

function toDraft(c: CompanyDetail | null): Draft {
  if (!c) return { ...EMPTY_DRAFT };
  return {
    name: c.name ?? '',
    domain: c.domain ?? '',
    industry: c.industry ?? '',
    description: c.description ?? '',
    company_size: c.company_size ?? '',
    target_audience: c.target_audience ?? '',
    key_products: c.key_products ?? '',
    content_pillars: c.content_pillars ?? '',
    competitors: c.competitors ?? '',
    tone_of_voice: c.tone_of_voice ?? '',
  };
}

function validate(draft: Draft): string | null {
  const missing: string[] = [];
  if (!draft.name.trim()) missing.push('Company Name');
  if (!draft.domain.trim()) missing.push('Website Domain');
  if (!draft.industry.trim()) missing.push('Industry');
  if (!draft.description.trim()) missing.push('Description');
  if (!draft.company_size.trim()) missing.push('Company Size');
  if (!draft.target_audience.trim()) missing.push('Target Audience');
  if (!draft.key_products.trim()) missing.push('Key Products');
  if (!draft.content_pillars.trim()) missing.push('Content Pillars');
  if (!draft.competitors.trim()) missing.push('Competitors');
  if (!draft.tone_of_voice.trim()) missing.push('Tone of Voice');
  if (missing.length) return `Please fill in: ${missing.join(', ')}.`;
  if (draft.description.trim().length < 20) {
    return 'Description must be at least 20 characters.';
  }
  if (draft.target_audience.trim().length < 10) {
    return 'Target Audience must be at least 10 characters.';
  }
  return null;
}

export default function CompanyProfilePage() {
  const { user, markCompanyProfileComplete } = useAuth();
  const companyId = user?.company_id ?? '';

  const [company, setCompany] = useState<CompanyDetail | null>(null);
  const [draft, setDraft] = useState<Draft>({ ...EMPTY_DRAFT });
  // Start in a loading state so the first paint shows a spinner instead of
  // the empty placeholder form while the company fetch is in flight.
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const loadCompany = useCallback(
    async (id: string, signal?: AbortSignal) => {
      setLoading(true);
      setError(null);
      try {
        const res = await getCompanyProfile(id, signal);
        setCompany(res);
        setDraft(toDraft(res));
      } catch (err) {
        if ((err as Error).name === 'AbortError') return;
        setError(
          err instanceof ApiError
            ? err.detail ?? err.message
            : (err as Error).message,
        );
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    if (!companyId) return;
    const controller = new AbortController();
    loadCompany(companyId, controller.signal);
    return () => controller.abort();
  }, [companyId, loadCompany]);

  const handleFieldChange = <K extends keyof Draft>(key: K, value: Draft[K]) => {
    setDraft((prev) => ({ ...prev, [key]: value }));
    setSuccess(null);
  };

  const handleToggleEdit = () => {
    if (!editing) {
      setEditing(true);
      setError(null);
      setSuccess(null);
      return;
    }
    void handleSave();
  };

  const handleCancel = () => {
    setDraft(toDraft(company));
    setEditing(false);
    setError(null);
    setSuccess(null);
  };

  const handleSave = async () => {
    if (!companyId) return;
    const validationError = validate(draft);
    if (validationError) {
      setError(validationError);
      return;
    }
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      await updateCompanyProfile(companyId, {
        name: draft.name.trim(),
        domain: draft.domain.trim(),
        industry: draft.industry.trim(),
        description: draft.description.trim(),
        company_size: draft.company_size.trim(),
        target_audience: draft.target_audience.trim(),
        key_products: draft.key_products.trim(),
        content_pillars: draft.content_pillars.trim(),
        competitors: draft.competitors.trim(),
        tone_of_voice: draft.tone_of_voice.trim(),
      });
      setSuccess('Company profile saved.');
      setEditing(false);
      await loadCompany(companyId);
      // Release the AuthProvider gate so the rest of the company surfaces
      // (drafts, trends) become reachable without a full reload.
      markCompanyProfileComplete();
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.detail ?? err.message
          : (err as Error).message,
      );
    } finally {
      setSaving(false);
    }
  };

  if (!companyId) {
    return (
      <PageWrapper>
        <div className="glass rounded-3xl p-10 border border-dashed border-white/20 text-center">
          <p className="text-dim">
            Your account isn&apos;t linked to a company yet. Contact an admin.
          </p>
        </div>
      </PageWrapper>
    );
  }

  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex items-end justify-between gap-6 flex-wrap">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold tracking-tight">Company Profile</h1>
            <p className="text-dim text-lg">
              Manage the tenant metadata your strategic briefs are generated
              against. Click <em>Update Profile</em> to edit, then save.
            </p>
          </div>
          {editing && (
            <button
              type="button"
              onClick={handleCancel}
              disabled={saving}
              className="p-2.5 rounded-xl text-dim hover:text-white hover:bg-white/5 transition"
              title="Cancel without saving"
            >
              <X className="w-5 h-5" />
            </button>
          )}
        </header>

        {error && (
          <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-4 flex items-start gap-2 text-sm text-rose-200">
            <TriangleAlert className="w-4 h-4 mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        )}
        {success && (
          <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-4 flex items-start gap-2 text-sm text-emerald-200">
            <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" />
            <span>{success}</span>
          </div>
        )}

        {loading && !company ? (
          <div className="glass rounded-3xl p-10 border border-dashed border-white/20 text-center space-y-4">
            <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto" />
            <p className="text-dim">Loading company profile…</p>
          </div>
        ) : (
          <div className="glass rounded-[2rem] p-10 border border-white/5 space-y-8">
            <AffinityChips weights={company?.content_affinity_weights ?? null} />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Field
                label="Company Name"
                required
                editing={editing}
                value={draft.name}
                onChange={(v) => handleFieldChange('name', v)}
                placeholder="e.g., Acme Corporation"
                saving={saving}
              />
              <Field
                label="Website Domain"
                required
                editing={editing}
                value={draft.domain}
                onChange={(v) => handleFieldChange('domain', v)}
                placeholder="e.g., acme.com"
                saving={saving}
              />
              <Field
                label="Industry"
                required
                editing={editing}
                value={draft.industry}
                onChange={(v) => handleFieldChange('industry', v)}
                placeholder="e.g., Technology, Finance, Healthcare"
                saving={saving}
              />
              <SelectField
                label="Company Size"
                required
                editing={editing}
                value={draft.company_size}
                onChange={(v) => handleFieldChange('company_size', v)}
                options={COMPANY_SIZE_OPTIONS}
                saving={saving}
                placeholder="Select company size"
              />
            </div>

            <Field
              label="Description"
              required
              editing={editing}
              value={draft.description}
              onChange={(v) => handleFieldChange('description', v)}
              placeholder="What does the company do? Audience, product, positioning."
              multiline
              saving={saving}
              helper="Minimum 20 characters — powers the strategic brief prompts."
            />

            <div className="border-t border-white/5 pt-6 space-y-6">
              <div>
                <h3 className="text-sm font-bold text-white">
                  Strategic Brief Context
                </h3>
                <p className="text-xs text-dim mt-1">
                  Used by the Strategic Brief LLM to anchor the blue-ocean
                  angle and editorial titles on your actual business.
                </p>
              </div>

              <Field
                label="Target Audience"
                required
                editing={editing}
                value={draft.target_audience}
                onChange={(v) => handleFieldChange('target_audience', v)}
                placeholder="e.g., CISOs at Fortune 500 financial institutions."
                multiline
                saving={saving}
                helper="Who are the articles written for? Minimum 10 characters."
              />

              <Field
                label="Key Products / Services"
                required
                editing={editing}
                value={draft.key_products}
                onChange={(v) => handleFieldChange('key_products', v)}
                placeholder="e.g., Zero-Trust LLM gateway, prompt-injection firewall."
                multiline
                saving={saving}
                helper="Comma-separated list or short paragraph."
              />

              <Field
                label="Content Pillars"
                required
                editing={editing}
                value={draft.content_pillars}
                onChange={(v) => handleFieldChange('content_pillars', v)}
                placeholder="e.g., LLM security, compliance, enterprise AI adoption."
                saving={saving}
                helper="3–6 themes your SEO content should cluster around."
              />

              <Field
                label="Key Competitors"
                required
                editing={editing}
                value={draft.competitors}
                onChange={(v) => handleFieldChange('competitors', v)}
                placeholder="e.g., Lakera, Protect AI, Robust Intelligence."
                saving={saving}
                helper="Comma-separated. Informs the competition-gap analysis."
              />

              <SelectField
                label="Tone of Voice"
                required
                editing={editing}
                value={draft.tone_of_voice}
                onChange={(v) => handleFieldChange('tone_of_voice', v)}
                options={TONE_OPTIONS}
                saving={saving}
                placeholder="Select tone"
              />
            </div>

            <div className="flex flex-wrap gap-3 justify-end pt-2">
              <button
                onClick={handleToggleEdit}
                disabled={saving || loading}
                className="flex items-center gap-2 bg-primary hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed text-primary-foreground px-6 py-3 rounded-2xl text-sm font-bold transition-all shadow-lg shadow-primary/20"
              >
                {saving ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" /> Saving…
                  </>
                ) : editing ? (
                  <>
                    <Save className="w-4 h-4" /> Save Profile
                  </>
                ) : (
                  <>
                    <Pencil className="w-4 h-4" /> Update Profile
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </PageWrapper>
  );
}

// ---- Presentational field helpers ------------------------------------------

function Field({
  label,
  value,
  onChange,
  editing,
  placeholder,
  multiline = false,
  required = false,
  saving = false,
  helper,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  editing: boolean;
  placeholder?: string;
  multiline?: boolean;
  required?: boolean;
  saving?: boolean;
  helper?: string;
}) {
  const sharedClass = cn(
    'w-full rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm outline-none focus:border-primary/40 transition',
    (!editing || saving) && 'opacity-80 cursor-not-allowed',
  );
  return (
    <label className="space-y-1.5 block">
      <span className="text-[10px] font-black uppercase tracking-widest text-dim flex items-center gap-1">
        {label}
        {required && <span className="text-rose-400">*</span>}
      </span>
      {multiline ? (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={!editing || saving}
          placeholder={placeholder}
          rows={5}
          className={sharedClass}
        />
      ) : (
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={!editing || saving}
          placeholder={placeholder}
          className={sharedClass}
        />
      )}
      {helper && <span className="text-[10px] text-dim">{helper}</span>}
    </label>
  );
}

function SelectField({
  label,
  value,
  onChange,
  editing,
  options,
  required = false,
  saving = false,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  editing: boolean;
  options: { value: string; label: string }[];
  required?: boolean;
  saving?: boolean;
  placeholder?: string;
}) {
  return (
    <label className="space-y-1.5 block">
      <span className="text-[10px] font-black uppercase tracking-widest text-dim flex items-center gap-1">
        {label}
        {required && <span className="text-rose-400">*</span>}
      </span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={!editing || saving}
        className={cn(
          'w-full rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm outline-none focus:border-primary/40 transition',
          (!editing || saving) && 'opacity-80 cursor-not-allowed',
        )}
      >
        <option value="" className="bg-slate-900">
          {placeholder ?? 'Select an option'}
        </option>
        {options.map((opt) => (
          <option key={opt.value} value={opt.value} className="bg-slate-900">
            {opt.label}
          </option>
        ))}
      </select>
    </label>
  );
}

function humanizeCategory(key: string): string {
  return key
    .split('_')
    .map((w) =>
      w === 'ai' || w === 'llms'
        ? w.toUpperCase()
        : w[0]?.toUpperCase() + w.slice(1),
    )
    .join(' ');
}

function AffinityChips({
  weights,
}: {
  weights: Record<string, number> | null;
}) {
  // Read-only banner — the backend re-extracts this vector every time
  // the profile is saved, so there's nothing to edit here. Showing it
  // makes it obvious to the tenant operator why their Strategic Briefs
  // emphasise one vocabulary set over another.
  if (!weights || Object.keys(weights).length === 0) {
    return (
      <div className="rounded-xl border border-dashed border-white/10 bg-white/[0.02] p-5 space-y-2">
        <div className="text-[10px] font-black uppercase tracking-widest text-dim">
          Content Affinity
        </div>
        <p className="text-xs text-dim italic">
          Not yet extracted. Save this profile to have the LLM derive the
          10-dim category weights that drive your Strategic Brief agent.
        </p>
      </div>
    );
  }
  const top = Object.entries(weights)
    .filter(([, v]) => v > 0.03)
    .sort(([, a], [, b]) => b - a);
  return (
    <div className="rounded-xl border border-secondary/20 bg-gradient-to-br from-secondary/[0.06] via-transparent to-primary/[0.06] p-5 space-y-3">
      <div className="flex items-center justify-between">
        <div className="text-[10px] font-black uppercase tracking-widest text-secondary">
          Content Affinity (10-dim taxonomy)
        </div>
        <div className="text-[10px] text-dim font-mono">
          re-extracted on every profile save
        </div>
      </div>
      <p className="text-xs text-dim">
        Vocabulary distribution your Strategic Brief agent uses as a hard
        constraint. Top-3 dominate headlines and keywords; categories
        &lt;5% are forbidden from appearing.
      </p>
      <div className="flex flex-wrap gap-2 pt-1">
        {top.map(([cat, w]) => (
          <span
            key={cat}
            className={cn(
              'px-3 py-1.5 rounded-xl text-xs font-bold border',
              w >= 0.2
                ? 'bg-primary/15 text-primary border-primary/30'
                : w >= 0.1
                  ? 'bg-secondary/10 text-secondary border-secondary/25'
                  : 'bg-white/5 text-dim border-white/10',
            )}
          >
            {humanizeCategory(cat)}
            <span className="ml-2 text-[10px] opacity-75 tabular-nums">
              {(w * 100).toFixed(0)}%
            </span>
          </span>
        ))}
      </div>
    </div>
  );
}
