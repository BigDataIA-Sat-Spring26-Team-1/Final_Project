import {
  ArrowUpRight,
  Send,
  Eye,
  Trash2,
  Users,
  Calendar,
  ThumbsUp,
  ThumbsDown,
  EyeOff,
  Loader2,
} from 'lucide-react';
import { useState } from 'react';

import {
  ApiError,
  submitArticleFeedback,
  type FeedbackType,
  type RankedArticle,
} from '@/lib/api';
import { cn } from '@/lib/utils';

// ---- Shared prop shapes -----------------------------------------------------
// Any icon from lucide-react satisfies this shape — we only render it and
// forward a className, so the narrow signature is enough.
type IconType = React.ComponentType<{ className?: string }>;

// --- Global Stat Card ---
type StatCardProps = {
  title: string;
  /** Accepts a ReactNode so callers can pass a <Spinner/> while loading. */
  value: React.ReactNode;
  /** "+12%", "-2%", or "0" — the + / - / 0 prefix drives the colour. */
  change: string;
  description: string;
  icon: IconType;
  isWarning?: boolean;
};
export function StatCard({ title, value, change, description, icon: Icon, isWarning }: StatCardProps) {
  return (
    <div className="glass rounded-2xl p-6 border border-white/5 space-y-4 hover:border-white/10 transition-all cursor-default group">
      <div className="flex items-center justify-between">
        <div className={cn(
          "p-2.5 rounded-xl",
          isWarning ? "bg-amber-500/10 text-amber-500" : "bg-primary/10 text-primary"
        )}>
          <Icon className="w-6 h-6" />
        </div>
        <div className={cn(
          "flex items-center gap-1 text-sm font-medium",
          change.startsWith('+') ? "text-emerald-500" : change === '0' ? "text-muted-foreground" : "text-amber-500"
        )}>
          {change !== '0' && <ArrowUpRight className="w-4 h-4" />}
          {change}
        </div>
      </div>
      <div>
        <p className="text-sm font-medium text-muted-foreground">{title}</p>
        <h3 className="text-3xl font-bold mt-1">{value}</h3>
      </div>
      <p className="text-xs text-muted-foreground">{description}</p>
    </div>
  );
}

// --- Home Activity Item ---
type ActivityItemProps = {
  title: string;
  source: string;
  time: string;
  status: string;
  relevancy: number;
};
export function ActivityItem({ title, source, time, status, relevancy }: ActivityItemProps) {
  return (
    <div className="glass rounded-2xl p-5 border border-white/5 flex items-center justify-between hover:bg-white/[0.02] active:scale-[0.99] transition-all cursor-pointer">
      <div className="space-y-1 max-w-[70%]">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold tracking-widest uppercase text-primary/80">{source}</span>
          <span className="w-1 h-1 rounded-full bg-white/20" />
          <span className="text-xs text-muted-foreground">{time}</span>
        </div>
        <h4 className="text-base font-semibold truncate leading-tight">{title}</h4>
      </div>
      <div className="flex items-center gap-4">
        <div className="text-right flex flex-col items-end">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/5 border border-white/5">
            <div className={cn(
              "w-1.5 h-1.5 rounded-full",
              relevancy > 90 ? "bg-emerald-500" : "bg-amber-500"
            )} />
            <span className="text-xs font-bold">{relevancy}%</span>
          </div>
          <p className="text-[10px] text-muted-foreground mt-1 font-bold tracking-widest uppercase">{status}</p>
        </div>
      </div>
    </div>
  );
}

// --- Home Trend Tag ---
type TrendTagProps = {
  name: string;
  count: number;
  velocity: 'Surging' | 'High' | 'Peak' | 'Stable' | string;
};
export function TrendTag({ name, count, velocity }: TrendTagProps) {
  return (
    <div className="flex items-center justify-between group cursor-pointer">
      <div className="space-y-0.5">
        <p className="text-sm font-bold group-hover:text-primary transition-colors">{name}</p>
        <p className="text-[10px] text-muted-foreground uppercase tracking-widest font-bold font-mono">{count} MENTIONS</p>
      </div>
      <div className={cn(
        "text-[10px] font-black uppercase px-2 py-0.5 rounded border tracking-tighter",
        velocity === 'Surging' ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" :
        velocity === 'High' ? "bg-primary/10 text-primary border-primary/20" :
        velocity === 'Peak' ? "bg-purple-500/10 text-purple-500 border-purple-500/20" :
        "bg-white/5 text-muted-foreground border-white/10"
      )}>
        {velocity}
      </div>
    </div>
  );
}

// --- Trending Feature Card ---
// Accepts a ReactNode value so callers can render a <Spinner/> while loading.
type TrendFeatureCardProps = {
  title: string;
  value: React.ReactNode;
  icon: IconType;
  detail: string;
  isPrimary?: boolean;
};
export function TrendFeatureCard({ title, value, icon: Icon, detail, isPrimary }: TrendFeatureCardProps) {
  return (
    <div className={cn(
      "glass rounded-2xl p-6 border border-white/5 space-y-3",
      isPrimary && "bg-primary/5 border-primary/20"
    )}>
      <div className="flex items-center gap-3">
        <Icon className={cn("w-5 h-5", isPrimary ? "text-primary" : "text-muted-foreground")} />
        <span className="text-sm font-medium text-muted-foreground">{title}</span>
      </div>
      <div className="space-y-1">
        <h4 className="text-2xl font-extrabold tracking-tight">{value}</h4>
        <p className="text-xs text-muted-foreground font-medium uppercase tracking-widest">{detail}</p>
      </div>
    </div>
  );
}

// --- Trending Entity Item ---
type EntityItemProps = { name: string; score: number; delta: number };
export function EntityItem({ name, score, delta }: EntityItemProps) {
  return (
    <div className="glass rounded-xl p-4 border border-white/5 flex items-center justify-between hover:bg-white/5 transition-colors">
      <div className="space-y-1">
        <p className="text-sm font-bold truncate max-w-[120px]">{name}</p>
        <p className="text-[10px] text-muted-foreground font-bold">RELIABILITY: {(score*10).toFixed(0)}%</p>
      </div>
      <div className="text-right">
        <div className="flex items-center gap-1 text-emerald-500 text-xs font-bold">
          <ArrowUpRight className="w-3 h-3" />
          +{delta}%
        </div>
      </div>
    </div>
  );
}

// --- Newsletter Draft Card ---
type DraftStatus = 'DRAFT' | 'SCHEDULED' | 'SENT' | string;
type DraftCardProps = {
  title: string;
  status: DraftStatus;
  persona: string;
  date: string;
  recipients: number;
};
export function DraftCard({ title, status, persona, date, recipients }: DraftCardProps) {
  const isSent = status === 'SENT';
  const isScheduled = status === 'SCHEDULED';

  return (
    <div className="glass rounded-3xl border border-white/5 overflow-hidden flex flex-col hover:border-white/10 transition-all group">
      <div className="p-8 flex-1 space-y-6">
        <div className="flex items-center justify-between">
          <div className={cn(
            "px-3 py-1 rounded-full text-[10px] font-black tracking-widest uppercase border",
            isSent ? "bg-emerald-500/10 text-emerald-500 border-emerald-500/20" :
            isScheduled ? "bg-primary/10 text-primary border-primary/20" :
            "bg-amber-500/10 text-amber-500 border-amber-500/20"
          )}>
            {status}
          </div>
          <div className="flex items-center gap-2 text-muted-foreground text-xs font-medium">
            <Calendar className="w-3.5 h-3.5" />
            {date}
          </div>
        </div>

        <div className="space-y-3">
          <h3 className="text-2xl font-bold leading-tight group-hover:text-primary transition-colors">{title}</h3>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1.5 text-sm text-muted-foreground">
              <Users className="w-4 h-4" />
              {persona}
            </div>
            <div className="w-1 h-1 rounded-full bg-white/10" />
            <div className="text-sm font-semibold text-white">
              {recipients.toLocaleString()} Readers
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white/[0.02] p-4 border-t border-white/5 flex items-center justify-between">
        <div className="flex gap-2">
          <button className="p-2.5 rounded-xl hover:bg-white/5 transition-colors text-muted-foreground hover:text-white" title="Preview">
            <Eye className="w-5 h-5" />
          </button>
          <button className="p-2.5 rounded-xl hover:bg-white/5 transition-colors text-muted-foreground hover:text-white" title="Delete">
            <Trash2 className="w-5 h-5" />
          </button>
        </div>
        <button className={cn(
          "px-5 py-2 rounded-xl text-sm font-bold flex items-center gap-2 transition-all",
          isSent ? "text-muted-foreground bg-white/5 cursor-not-allowed" : "bg-white text-black hover:bg-zinc-200"
        )}>
          {isSent ? 'Sent Successfully' : (
            <>
              <Send className="w-4 h-4" />
              Commit & Send
            </>
          )}
        </button>
      </div>
    </div>
  );
}

// --- Feedable Article Row ---
// Wraps an article row with like / dislike / skip buttons that post through
// the persona feedback endpoint. Parent owns state — we just surface the
// user's intent via onFeedback so pages can update the list (remove on skip,
// etc.). Disables itself after one acknowledgement so a single article can't
// double-register like+dislike.
export function FeedableArticleRow({
  article,
  userId,
  onFeedback,
}: {
  article: RankedArticle;
  userId: string;
  onFeedback?: (type: FeedbackType, article: RankedArticle) => void;
}) {
  const [busy, setBusy] = useState<FeedbackType | null>(null);
  const [acknowledged, setAcknowledged] = useState<FeedbackType | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFeedback = async (type: FeedbackType) => {
    if (!userId) {
      setError('Set a user id on the page before rating articles.');
      return;
    }
    setBusy(type);
    setError(null);
    try {
      await submitArticleFeedback({
        user_id: userId,
        article_categories: article.categories ?? {},
        feedback: type,
      });
      setAcknowledged(type);
      onFeedback?.(type, article);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? `${err.status}: ${err.detail ?? err.message}`
          : (err as Error).message,
      );
    } finally {
      setBusy(null);
    }
  };

  const relevancy = Math.round((article.score ?? 0) * 100);

  return (
    <div className="glass rounded-2xl p-5 border border-white/5 space-y-3 hover:bg-white/[0.02] transition-all">
      <div className="flex items-center justify-between gap-4">
        <div className="space-y-1 flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-[10px] font-bold tracking-widest uppercase text-primary/80">
              {article.trend_status ?? 'RECOMMENDED'}
            </span>
            {(article.source_name || article.sources?.[0]) && (
              <>
                <span className="w-1 h-1 rounded-full bg-white/20" />
                <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">
                  {article.source_name ?? article.sources?.[0]}
                </span>
              </>
            )}
            {article.cluster_size && article.cluster_size > 1 && (
              <>
                <span className="w-1 h-1 rounded-full bg-white/20" />
                <span className="text-xs text-muted-foreground">
                  +{article.cluster_size - 1} source{article.cluster_size > 2 ? 's' : ''}
                </span>
              </>
            )}
          </div>
          {article.url ? (
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-base font-semibold leading-tight hover:text-primary transition-colors block truncate"
              title="Open source article in a new tab"
            >
              {article.title}
            </a>
          ) : (
            <h4 className="text-base font-semibold truncate leading-tight">{article.title}</h4>
          )}
          {article.summary && (
            <p className="text-xs text-muted-foreground line-clamp-2">{article.summary}</p>
          )}
        </div>
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/5 border border-white/5 shrink-0">
          <div
            className={cn(
              'w-1.5 h-1.5 rounded-full',
              relevancy > 90 ? 'bg-emerald-500' : relevancy > 70 ? 'bg-amber-500' : 'bg-zinc-500',
            )}
          />
          <span className="text-xs font-bold">{relevancy}%</span>
        </div>
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FeedbackButton
            onClick={() => handleFeedback('like')}
            disabled={busy !== null || acknowledged !== null}
            busy={busy === 'like'}
            acknowledged={acknowledged === 'like'}
            label="Like"
            icon={ThumbsUp}
          />
          <FeedbackButton
            onClick={() => handleFeedback('dislike')}
            disabled={busy !== null || acknowledged !== null}
            busy={busy === 'dislike'}
            acknowledged={acknowledged === 'dislike'}
            label="Dislike"
            icon={ThumbsDown}
          />
          <FeedbackButton
            onClick={() => handleFeedback('skip')}
            disabled={busy !== null || acknowledged !== null}
            busy={busy === 'skip'}
            acknowledged={acknowledged === 'skip'}
            label="Skip"
            icon={EyeOff}
          />
        </div>
        {acknowledged && (
          <span className="text-[10px] uppercase tracking-widest font-black text-emerald-500">
            {acknowledged} recorded
          </span>
        )}
        {error && !acknowledged && (
          <span className="text-[10px] uppercase tracking-widest font-black text-rose-400 truncate max-w-[240px]">
            {error}
          </span>
        )}
      </div>
    </div>
  );
}

function FeedbackButton({
  onClick,
  disabled,
  busy,
  acknowledged,
  label,
  icon: Icon,
}: {
  onClick: () => void;
  disabled: boolean;
  busy: boolean;
  acknowledged: boolean;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      className={cn(
        'p-2 rounded-xl border text-xs font-bold transition-all flex items-center gap-1.5',
        'border-white/5 bg-white/[0.02]',
        acknowledged && 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400',
        !acknowledged && !disabled && 'hover:bg-white/5 hover:border-white/10',
        disabled && !acknowledged && 'opacity-40 cursor-not-allowed',
      )}
    >
      {busy ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Icon className="w-3.5 h-3.5" />}
      <span className="sr-only">{label}</span>
    </button>
  );
}

// --- SEO Opportunity Item ---
type OpportunityItemProps = {
  topic: string;
  relevance: number;
  competition: string;
  category: string;
};
export function OpportunityItem({ topic, relevance, competition, category }: OpportunityItemProps) {
  return (
    <div className="glass rounded-2xl p-6 border border-white/5 flex items-center justify-between hover:border-primary/20 transition-all cursor-pointer group">
      <div className="space-y-1.5 flex-1">
        <div className="flex items-center gap-2">
          <div className="text-[10px] font-black uppercase text-primary/80 tracking-widest">{competition} COMPETITION</div>
          <span className="w-1 h-1 rounded-full bg-white/20" />
          <span className="text-[10px] font-bold text-muted-foreground uppercase tracking-widest">{category}</span>
        </div>
        <h4 className="text-lg font-bold group-hover:text-primary transition-colors">{topic}</h4>
      </div>
      <div className="text-right">
        <p className="text-sm font-black text-white">{relevance}%</p>
        <p className="text-[10px] text-muted-foreground font-bold tracking-tighter uppercase">RELEVANCE</p>
      </div>
    </div>
  );
}
