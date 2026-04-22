'use client';

// Onboarding is the first real API call most users will make against CurateAI:
// upload a LinkedIn PDF / resume → the backend extracts a structured persona
// and persists it to Snowflake. We need browser state + the File API, which
// means this page has to be a client component.

import {
  ArrowRight,
  CheckCircle2,
  FileText,
  FileUp,
  Link,
  Loader2,
  ShieldCheck,
  Sparkles,
  TriangleAlert,
} from 'lucide-react';
import { useRef, useState } from 'react';

import { PageWrapper } from '@/components/PageWrapper';
import {
  ApiError,
  createManualPersona,
  extractPersonas,
  type BatchPersonaResponse,
  type PersonaExtractionResult,
  type SinglePersonaExtractionResponse,
} from '@/lib/api';
import { cn } from '@/lib/utils';

// Three ways to land a persona. LinkedIn + Resume share the extract endpoint —
// the backend parser doesn't actually care about the label. Manual is the
// click-path that avoids the LLM extractor entirely.
type OnboardingMode = 'linkedin' | 'resume' | 'manual';

const CATEGORY_TAXONOMY: { key: string; label: string }[] = [
  { key: 'llms', label: 'LLMs' },
  { key: 'ai_agents', label: 'AI Agents' },
  { key: 'computer_vision', label: 'Computer Vision' },
  { key: 'security', label: 'Security' },
  { key: 'hardware', label: 'Hardware' },
  { key: 'software_engineering', label: 'Software Engineering' },
  { key: 'ai_policy', label: 'AI Policy' },
  { key: 'general_ai', label: 'General AI' },
  { key: 'data_engineering', label: 'Data Engineering' },
  { key: 'startups', label: 'Startups' },
];

// 10 MB matches the copy under the drop zone. We check client-side so the user
// gets instant feedback instead of waiting for a 413 round-trip.
const MAX_FILE_BYTES = 10 * 1024 * 1024;

export default function UserOnboarding() {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [mode, setMode] = useState<OnboardingMode>('linkedin');
  const [userId, setUserId] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [result, setResult] = useState<BatchPersonaResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Manual-mode state — only read when mode === 'manual'.
  const [manualJobTitle, setManualJobTitle] = useState('');
  const [manualSeniority, setManualSeniority] = useState('mid');
  const [manualBio, setManualBio] = useState('');
  const [manualWeights, setManualWeights] = useState<Record<string, number>>(
    Object.fromEntries(CATEGORY_TAXONOMY.map(({ key }) => [key, 0])),
  );
  const [manualSuccess, setManualSuccess] = useState<string | null>(null);

  const handleManualSubmit = async () => {
    if (!userId.trim()) {
      setError('Enter a user id first.');
      return;
    }
    if (!manualJobTitle.trim()) {
      setError('Job title is required for a manual persona.');
      return;
    }
    setIsSubmitting(true);
    setError(null);
    setManualSuccess(null);
    try {
      const out = await createManualPersona({
        user_id: userId.trim(),
        job_title: manualJobTitle.trim(),
        seniority: manualSeniority,
        bio_summary: manualBio.trim(),
        explicit_category_weights: manualWeights,
      });
      setManualSuccess(`Persona ${out.persona_id.slice(0, 8)}… saved for ${out.user_id}.`);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? `${err.status}: ${err.detail ?? err.message}`
          : (err as Error).message,
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleFilesPicked = (picked: FileList | null) => {
    if (!picked || picked.length === 0) return;
    const rejected: string[] = [];
    const accepted: File[] = [];
    for (const file of Array.from(picked)) {
      if (file.size > MAX_FILE_BYTES) {
        rejected.push(`${file.name} (>${MAX_FILE_BYTES / 1024 / 1024}MB)`);
      } else {
        accepted.push(file);
      }
    }
    if (rejected.length > 0) {
      setError(`Skipped ${rejected.length} file(s): ${rejected.join(', ')}`);
    } else {
      setError(null);
    }
    setFiles(accepted);
    setResult(null);
  };

  const handleSubmit = async () => {
    if (!userId.trim()) {
      setError('Enter a user id before uploading.');
      return;
    }
    if (files.length === 0) {
      setError('Pick at least one PDF to extract from.');
      return;
    }

    setIsSubmitting(true);
    setError(null);
    setResult(null);

    try {
      const response = await extractPersonas(userId.trim(), files);
      setResult(response);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? `${err.status}: ${err.detail ?? err.message}`
          : (err as Error).message || 'Unknown error',
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const firstSuccessful = result?.results.find((r) => r.is_success && r.data);

  return (
    <PageWrapper>
      <div className="max-w-4xl mx-auto space-y-12 py-10">
        <header className="text-center space-y-4">
          <div className="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center mx-auto mb-6 border border-primary/20">
            <Sparkles className="text-primary w-8 h-8" />
          </div>
          <h1 className="text-5xl font-extrabold tracking-tight">Define Your Intelligence Persona</h1>
          <p className="text-dim text-xl max-w-2xl mx-auto">
            Choose how you&apos;d like CurateAI to personalize your content loops and agentic research.
          </p>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <OnboardingOption
            title="LinkedIn PDF"
            description="Upload your exported LinkedIn profile to automatically extract entities and skills."
            icon={Link}
            selected={mode === 'linkedin'}
            primary
            onClick={() => setMode('linkedin')}
          />
          <OnboardingOption
            title="Resume / CV"
            description="Upload a standard PDF resume for deep scanning of your professional background."
            icon={FileText}
            selected={mode === 'resume'}
            onClick={() => setMode('resume')}
          />
          <OnboardingOption
            title="Manual Setup"
            description="Hand-pick your interest clusters, technical focus areas, and industry sectors."
            icon={ArrowRight}
            selected={mode === 'manual'}
            onClick={() => setMode('manual')}
          />
          <div className="glass rounded-3xl p-8 border border-white/5 flex flex-col items-center justify-center space-y-4 text-center">
            <div className="p-3 bg-white/5 rounded-full">
              <ShieldCheck className="w-6 h-6 text-emerald-400" />
            </div>
            <p className="text-xs text-dim lowercase font-mono">End-to-end encrypted storage of profile data.</p>
          </div>
        </div>

        <div className="glass rounded-[2.5rem] p-12 border border-white/5 flex flex-col items-center text-center space-y-8 bg-gradient-to-b from-white/[0.02] to-transparent">
          <div className="space-y-2">
            <h3 className="text-2xl font-bold">
              {mode === 'manual' ? 'Manual Persona Setup' : mode === 'resume' ? 'Resume Upload' : 'LinkedIn Upload'}
            </h3>
            <p className="text-dim">
              {mode === 'manual'
                ? 'Fill in your role and dial the category weights to tell CurateAI what to surface.'
                : mode === 'resume'
                ? 'Drop a standard PDF resume here; the extractor pulls role, seniority, and interest weights.'
                : 'Drop your LinkedIn-exported PDF here; the extractor turns it into a structured persona.'}
            </p>
          </div>

          {/* Minimal user_id input — swap for real auth once login is in place. */}
          <label className="w-full max-w-md space-y-2 text-left">
            <span className="text-xs uppercase tracking-widest text-dim font-bold">User ID</span>
            <input
              type="text"
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
              placeholder="e.g. user-demo-001"
              disabled={isSubmitting}
              className="w-full rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm outline-none focus:border-primary/40"
            />
          </label>

          {mode !== 'manual' && (
            <>
          {/* Hidden file input triggered by the styled drop zone label. */}
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf,.pdf"
            multiple
            className="sr-only"
            onChange={(e) => handleFilesPicked(e.target.files)}
          />

          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={isSubmitting}
            className={cn(
              'w-full max-w-md aspect-video border-2 border-dashed border-white/10 rounded-3xl',
              'flex flex-col items-center justify-center gap-4',
              'hover:border-primary/40 hover:bg-primary/5 transition-all group',
              isSubmitting && 'opacity-60 cursor-not-allowed',
            )}
          >
            <div className="p-4 bg-white/5 rounded-2xl group-hover:scale-110 transition-transform">
              <FileUp className="w-8 h-8 text-dim group-hover:text-primary" />
            </div>
            <p className="text-sm font-bold text-dim">
              {files.length > 0
                ? `${files.length} file${files.length > 1 ? 's' : ''} ready`
                : 'Click to browse or drag file'}
            </p>
          </button>

          {files.length > 0 && (
            <ul className="w-full max-w-md space-y-1 text-left text-xs text-dim">
              {files.map((f) => (
                <li key={f.name} className="flex items-center justify-between">
                  <span className="truncate">{f.name}</span>
                  <span className="font-mono text-zinc-600">{(f.size / 1024).toFixed(0)} KB</span>
                </li>
              ))}
            </ul>
          )}

          <button
            type="button"
            onClick={handleSubmit}
            disabled={isSubmitting || files.length === 0}
            className={cn(
              'px-8 py-3 rounded-xl font-bold bg-primary text-primary-foreground',
              'flex items-center gap-2',
              'disabled:opacity-40 disabled:cursor-not-allowed hover:opacity-90 transition',
            )}
          >
            {isSubmitting ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" /> Extracting persona...
              </>
            ) : (
              <>
                Run Extraction <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>

          <p className="text-[10px] text-zinc-600 uppercase tracking-widest font-black">Supported formats: PDF (Max 10MB)</p>
            </>
          )}

          {mode === 'manual' && (
            <div className="w-full max-w-2xl space-y-6 text-left">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <label className="space-y-2">
                  <span className="text-xs uppercase tracking-widest text-dim font-bold">Job title</span>
                  <input
                    type="text"
                    value={manualJobTitle}
                    onChange={(e) => setManualJobTitle(e.target.value)}
                    placeholder="Senior Data Engineer"
                    className="w-full rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm outline-none focus:border-primary/40"
                  />
                </label>
                <label className="space-y-2">
                  <span className="text-xs uppercase tracking-widest text-dim font-bold">Seniority</span>
                  <select
                    value={manualSeniority}
                    onChange={(e) => setManualSeniority(e.target.value)}
                    className="w-full rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm outline-none focus:border-primary/40"
                  >
                    {['entry', 'mid', 'senior', 'lead', 'executive'].map((s) => (
                      <option key={s} value={s} className="bg-zinc-900">{s}</option>
                    ))}
                  </select>
                </label>
              </div>
              <label className="block space-y-2">
                <span className="text-xs uppercase tracking-widest text-dim font-bold">Bio (optional)</span>
                <textarea
                  value={manualBio}
                  onChange={(e) => setManualBio(e.target.value)}
                  rows={3}
                  placeholder="Two-sentence summary of what you work on."
                  className="w-full rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm outline-none focus:border-primary/40 resize-none"
                />
              </label>

              <div className="space-y-3">
                <p className="text-xs uppercase tracking-widest text-dim font-bold">Category weights</p>
                <p className="text-xs text-dim">
                  Slide each category between 0 and 1 to tell the recommender which topics you care about. Start at 0.
                </p>
                <div className="space-y-3">
                  {CATEGORY_TAXONOMY.map(({ key, label }) => (
                    <div key={key} className="flex items-center gap-4">
                      <span className="text-sm font-bold w-44 shrink-0">{label}</span>
                      <input
                        type="range"
                        min={0}
                        max={1}
                        step={0.05}
                        value={manualWeights[key] ?? 0}
                        onChange={(e) =>
                          setManualWeights((prev) => ({
                            ...prev,
                            [key]: parseFloat(e.target.value),
                          }))
                        }
                        className="flex-1 accent-primary"
                      />
                      <span className="text-xs font-mono w-10 text-right text-dim">
                        {(manualWeights[key] ?? 0).toFixed(2)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <button
                type="button"
                onClick={handleManualSubmit}
                disabled={isSubmitting || !userId.trim() || !manualJobTitle.trim()}
                className={cn(
                  'w-full px-8 py-3 rounded-xl font-bold bg-primary text-primary-foreground',
                  'flex items-center justify-center gap-2',
                  'disabled:opacity-40 disabled:cursor-not-allowed hover:opacity-90 transition',
                )}
              >
                {isSubmitting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" /> Saving persona…
                  </>
                ) : (
                  <>
                    Save persona <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>

              {manualSuccess && (
                <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/5 p-4 flex items-start gap-3">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
                  <p className="text-sm text-emerald-200">{manualSuccess}</p>
                </div>
              )}
            </div>
          )}

          {error && (
            <div className="w-full max-w-md rounded-xl border border-rose-500/20 bg-rose-500/5 p-4 flex items-start gap-3 text-left">
              <TriangleAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
              <p className="text-sm text-rose-200">{error}</p>
            </div>
          )}

          {result && (
            <ExtractionResult
              data={firstSuccessful?.data ?? null}
              allResults={result.results}
              totalLatency={result.overall_latency_seconds}
            />
          )}
        </div>
      </div>
    </PageWrapper>
  );
}

// ---- Presentational children -------------------------------------------------

type OnboardingOptionProps = {
  title: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  primary?: boolean;
  selected?: boolean;
  onClick?: () => void;
};

function OnboardingOption({
  title,
  description,
  icon: Icon,
  primary,
  selected,
  onClick,
}: OnboardingOptionProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'text-left glass rounded-3xl p-8 border transition-all group relative overflow-hidden',
        selected
          ? 'border-primary/60 ring-2 ring-primary/30'
          : 'border-white/5 hover:border-white/20',
        primary && !selected && 'bg-gradient-to-br from-primary/5 to-transparent border-primary/20',
      )}
    >
      {primary && (
        <div className="absolute top-4 right-4 px-2 py-0.5 rounded-md bg-primary text-primary-foreground text-[10px] font-black uppercase">
          Recommended
        </div>
      )}
      <div
        className={cn(
          'w-12 h-12 rounded-xl flex items-center justify-center mb-6 transition-transform group-hover:scale-110',
          primary ? 'bg-primary text-primary-foreground shadow-lg shadow-primary/20' : 'bg-white/5 text-dim border border-white/10',
        )}
      >
        <Icon className="w-6 h-6" />
      </div>
      <h3 className="text-xl font-bold mb-2 group-hover:text-primary transition-colors">{title}</h3>
      <p className="text-sm text-dim leading-relaxed">{description}</p>
    </button>
  );
}

function ExtractionResult({
  data,
  allResults,
  totalLatency,
}: {
  data: PersonaExtractionResult | null;
  allResults: SinglePersonaExtractionResponse[];
  totalLatency: number;
}) {
  return (
    <div className="w-full max-w-md space-y-4 text-left rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-6">
      <div className="flex items-center gap-2">
        <CheckCircle2 className="w-5 h-5 text-emerald-400" />
        <h4 className="font-bold">Extraction complete</h4>
        <span className="ml-auto text-xs font-mono text-dim">{totalLatency.toFixed(1)}s</span>
      </div>

      {data ? (
        <div className="space-y-3 text-sm">
          <Field label="Name" value={data.name} />
          <Field label="Role" value={`${data.job_title} (${data.seniority})`} />
          <Field label="Archetype" value={data.persona_archetype} mono />
          <Field label="Bio" value={data.bio_summary} />
          <div>
            <p className="text-xs uppercase tracking-widest text-dim font-bold mb-2">Category Weights</p>
            <ul className="space-y-1 text-xs">
              {Object.entries(data.category_weights)
                .sort(([, a], [, b]) => b - a)
                .slice(0, 5)
                .map(([cat, weight]) => (
                  <li key={cat} className="flex items-center justify-between">
                    <span className="text-dim">{cat.replace(/_/g, ' ')}</span>
                    <span className="font-mono">{(weight * 100).toFixed(0)}%</span>
                  </li>
                ))}
            </ul>
          </div>
        </div>
      ) : (
        <p className="text-sm text-dim">No successful extractions in this batch.</p>
      )}

      {allResults.some((r) => !r.is_success) && (
        <details className="text-xs text-dim">
          <summary className="cursor-pointer">Failed files</summary>
          <ul className="mt-2 space-y-1">
            {allResults
              .filter((r) => !r.is_success)
              .map((r) => (
                <li key={r.filename}>
                  <span className="font-mono">{r.filename}</span> — {r.error ?? 'unknown error'}
                </li>
              ))}
          </ul>
        </details>
      )}
    </div>
  );
}

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-widest text-dim font-bold">{label}</p>
      <p className={cn('text-sm', mono && 'font-mono')}>{value}</p>
    </div>
  );
}
