'use client';

// StrategicBriefCard — renders a single structured SEO brief in the exact
// card layout from Temp/SEO_Prototype/UI/index.html. Layout:
//   • Top meta bar: "Strategic Brief #NN-NN" + opportunity score + urgency
//   • Two-column grid:
//       LEFT  — Blue Ocean Strategic Angle, Primary Keyword Velocity,
//               Internal Linking Strategy
//       RIGHT — Suggested Editorial Titles, Detailed Content Structure,
//               Reference Sources
// The component is purely presentational — data comes pre-structured from
// `content_briefs.structured_brief` (populated by the B2B agent).

import {
  ArrowDownRight,
  ArrowUpRight,
  ArrowRight,
  Compass,
  Link2,
} from 'lucide-react';

import type { StrategicBriefEnvelope } from '@/lib/api';
import { cn } from '@/lib/utils';

function formatVolume(n?: number | null): string {
  if (n == null) return '—';
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

function urgencyClass(tier?: string): string {
  switch (tier) {
    case 'HIDDEN_GEM':
      return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
    case 'ACT_NOW':
      return 'bg-rose-500/10 text-rose-400 border-rose-500/20';
    case 'MONITOR':
      return 'bg-amber-500/10 text-amber-400 border-amber-500/20';
    default:
      return 'bg-white/5 text-dim border-white/10';
  }
}

function briefNumber(briefId: string | undefined, date: string): string {
  // "#04-88" style identifier. Deterministic from id+date so it's stable.
  const month = date?.slice(5, 7) || '00';
  let hash = 0;
  for (const ch of briefId || date || '') {
    hash = ((hash << 5) - hash + ch.charCodeAt(0)) & 0xffff;
  }
  const suffix = String(Math.abs(hash) % 100).padStart(2, '0');
  return `#${month}-${suffix}`;
}

export function StrategicBriefCard({
  envelope,
  briefDate,
  briefId,
}: {
  envelope: StrategicBriefEnvelope;
  briefDate: string;
  briefId?: string;
}) {
  const { brief, reference_sources: references = [] } = envelope;
  const score = brief.opportunity_score?.toFixed(1) ?? '—';
  const priorityLabel =
    brief.opportunity_score >= 85
      ? 'Critical Priority'
      : brief.opportunity_score >= 70
      ? 'High Priority'
      : brief.opportunity_score >= 50
      ? 'Moderate Priority'
      : 'Low Priority';

  return (
    <div className="space-y-6">
      {/* Meta card */}
      <div className="relative glass rounded-2xl border border-white/5 px-7 py-6 overflow-hidden">
        <div className="absolute left-0 top-0 bottom-0 w-1 bg-secondary" />
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="space-y-2">
            <div className="text-[11px] font-black uppercase tracking-[0.18em] text-secondary">
              Strategic Brief {briefNumber(briefId, briefDate)}
            </div>
            <h2 className="text-2xl md:text-3xl font-bold tracking-tight text-white">
              {brief.headline}
            </h2>
            <div className="text-sm text-dim">
              Opportunity Score:{' '}
              <span className="text-emerald-400 font-bold">{score}</span>
              <span className="ml-1 text-dim">({priorityLabel})</span>
            </div>
          </div>
          <span
            className={cn(
              'px-3 py-1.5 rounded-full text-[10px] font-black tracking-widest border uppercase',
              urgencyClass(brief.urgency_tier),
            )}
          >
            {brief.urgency_tier?.replace(/_/g, ' ')}
          </span>
        </div>
      </div>

      {/* Two-column body */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* LEFT column */}
        <div className="space-y-6">
          {/* Blue Ocean Strategic Angle */}
          <section className="glass rounded-2xl border border-white/5 p-7 bg-gradient-to-br from-primary/[0.05] via-transparent to-secondary/[0.05]">
            <h3 className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.16em] text-primary mb-4">
              <Compass className="w-4 h-4" />
              Blue Ocean Strategic Angle
            </h3>
            <p className="text-sm leading-relaxed text-white/85">
              {brief.blue_ocean_angle}
            </p>
          </section>

          {/* Primary Keyword Velocity */}
          <section className="glass rounded-2xl border border-white/5 p-7">
            <h3 className="text-xs font-black uppercase tracking-[0.16em] text-primary mb-5">
              Primary Keyword Velocity
            </h3>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left border-b border-white/10">
                  <th className="pb-3 text-dim font-semibold">Keyword</th>
                  <th className="pb-3 text-dim font-semibold text-right">
                    Monthly Volume
                  </th>
                  <th className="pb-3 text-dim font-semibold text-right">
                    Velocity
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {brief.primary_keywords.map((k) => {
                  const pos = (k.velocity_pct ?? 0) >= 0;
                  return (
                    <tr key={k.keyword} className="hover:bg-white/[0.02]">
                      <td className="py-3 text-white">{k.keyword}</td>
                      <td className="py-3 text-primary text-right font-mono">
                        {formatVolume(k.monthly_volume)}
                      </td>
                      <td
                        className={cn(
                          'py-3 text-right font-mono',
                          k.velocity_pct == null
                            ? 'text-dim'
                            : pos
                            ? 'text-emerald-400'
                            : 'text-rose-400',
                        )}
                      >
                        {k.velocity_pct == null ? (
                          '—'
                        ) : (
                          <span className="inline-flex items-center gap-1 justify-end">
                            {pos ? (
                              <ArrowUpRight className="w-3.5 h-3.5" />
                            ) : (
                              <ArrowDownRight className="w-3.5 h-3.5" />
                            )}
                            {pos ? '+' : ''}
                            {k.velocity_pct.toFixed(1)}%
                          </span>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </section>

          {/* Internal Linking Strategy */}
          <section className="glass rounded-2xl border border-white/5 p-7">
            <h3 className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.16em] text-primary mb-4">
              <Link2 className="w-4 h-4" />
              Internal Linking Strategy
            </h3>
            <p className="text-sm leading-relaxed text-white/85">
              {brief.internal_linking_strategy}
            </p>
          </section>
        </div>

        {/* RIGHT column */}
        <div className="space-y-6">
          {/* Suggested Editorial Titles */}
          <section className="glass rounded-2xl border border-white/5 p-7">
            <h3 className="text-xs font-black uppercase tracking-[0.16em] text-primary mb-5">
              Suggested Editorial Titles
            </h3>
            <ul className="space-y-3 text-sm">
              {brief.editorial_titles.map((title) => (
                <li key={title} className="flex items-start gap-3 text-white/85">
                  <ArrowRight className="w-4 h-4 mt-0.5 shrink-0 text-primary" />
                  <span>&ldquo;{title}&rdquo;</span>
                </li>
              ))}
            </ul>
          </section>

          {/* Detailed Content Structure */}
          <section className="glass rounded-2xl border border-white/5 p-7">
            <h3 className="text-xs font-black uppercase tracking-[0.16em] text-primary mb-5">
              Detailed Content Structure
            </h3>
            <ol className="space-y-4">
              {brief.content_structure.map((section) => (
                <li key={section.step} className="flex gap-4">
                  <div className="text-secondary font-black tabular-nums text-lg leading-none pt-1">
                    {String(section.step).padStart(2, '0')}
                  </div>
                  <div className="space-y-1">
                    <div className="text-white font-bold text-sm">
                      {section.title}
                    </div>
                    <div className="text-dim text-xs leading-relaxed">
                      {section.description}
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          </section>

          {/* Reference Sources */}
          {references.length > 0 && (
            <section className="glass rounded-2xl border border-primary/20 p-7">
              <h3 className="text-xs font-black uppercase tracking-[0.16em] text-primary mb-5">
                Reference Sources
              </h3>
              <ul className="space-y-3 text-sm">
                {references.map((ref, idx) => (
                  <li key={`${ref.url}-${idx}`} className="flex items-start gap-3">
                    <ArrowRight className="w-4 h-4 mt-0.5 shrink-0 text-primary" />
                    <a
                      href={ref.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-secondary hover:text-primary underline underline-offset-2 transition-colors"
                    >
                      Reference {String(idx + 1).padStart(2, '0')}: {ref.title}
                      {ref.source_name ? ` (${ref.source_name})` : ''}
                    </a>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
