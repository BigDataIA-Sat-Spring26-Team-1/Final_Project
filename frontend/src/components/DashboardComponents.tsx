import { 
  ArrowUpRight, 
  Clock, 
  Zap, 
  CheckCircle2, 
  Newspaper,
  TrendingUp,
  Brain,
  Search,
  Activity,
  Globe,
  Flame,
  Plus,
  Send,
  Eye,
  Trash2,
  Mail,
  Users,
  Calendar,
  ShieldCheck,
  Target,
  FileText,
  MousePointer2
} from 'lucide-react';
import { cn } from '@/lib/utils';

// --- Global Stat Card ---
export function StatCard({ title, value, change, description, icon: Icon, isWarning }: any) {
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
export function ActivityItem({ title, source, time, status, relevancy }: any) {
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
export function TrendTag({ name, count, velocity }: any) {
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
export function TrendFeatureCard({ title, value, icon: Icon, detail, isPrimary }: any) {
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
export function EntityItem({ name, score, delta }: any) {
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
export function DraftCard({ title, status, persona, date, recipients }: any) {
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

// --- SEO Opportunity Item ---
export function OpportunityItem({ topic, relevance, competition, category }: any) {
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
