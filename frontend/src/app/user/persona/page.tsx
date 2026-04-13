import { 
  Settings, 
  User, 
  Brain, 
  Target, 
  Zap,
  ShieldCheck,
  RefreshCw,
  Plus
} from 'lucide-react';
import { PageWrapper } from '@/components/PageWrapper';

export default function UserPersonaPage() {
  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex items-end justify-between">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold tracking-tight">Persona Intelligence</h1>
            <p className="text-dim text-lg">Deep technical profile and behavior refinement for <strong>Aakash</strong>.</p>
          </div>
          <button className="bg-primary hover:bg-primary/90 text-primary-foreground px-6 py-3 rounded-2xl text-sm font-bold transition-all flex items-center gap-2">
             <RefreshCw className="w-4 h-4" />
             Re-verify Background
          </button>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
           <div className="lg:col-span-2 space-y-8">
              <div className="glass rounded-[2rem] p-10 border border-white/5 space-y-8">
                 <div className="space-y-2">
                    <h3 className="text-2xl font-bold">Dynamic Persona Logic</h3>
                    <p className="text-sm text-dim">Your persona is automatically evolved based on search intent and article interactions.</p>
                 </div>
                 
                 <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    <div className="space-y-4">
                       <h4 className="text-xs font-black uppercase tracking-widest text-secondary">Extracted Core Roles</h4>
                       <div className="space-y-3">
                          <RoleItem title="Tech Strategist" score={98} />
                          <RoleItem title="Data Architect" score={85} />
                          <RoleItem title="ML Engineer" score={72} />
                       </div>
                    </div>
                    <div className="space-y-4">
                       <h4 className="text-xs font-black uppercase tracking-widest text-secondary">Interest Clusters</h4>
                       <div className="flex flex-wrap gap-2">
                          {['Vector Search', 'RAG Patterns', 'Postgres', 'Distributed Systems', 'EU AI Policy', 'Startup ROI'].map(tag => (
                            <span key={tag} className="px-3 py-1.5 rounded-xl bg-white/5 border border-white/10 text-xs font-bold text-white">
                                {tag}
                            </span>
                          ))}
                       </div>
                    </div>
                 </div>
              </div>

              <div className="glass rounded-[2rem] p-10 border border-white/5 space-y-4">
                 <h3 className="text-xl font-bold">Behavioral Refinement</h3>
                 <p className="text-sm text-dim">The agent has noted a high preference for technical whitepapers over general news. Adjusting curation weights accordingly.</p>
                 <div className="flex items-center gap-4 pt-4">
                    <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden">
                       <div className="h-full bg-primary w-[85%]" />
                    </div>
                    <span className="text-xs font-bold text-primary">85% Technical Depth</span>
                 </div>
              </div>
           </div>

           <div className="space-y-6">
              <div className="glass rounded-3xl p-8 border border-white/5 space-y-6">
                 <h3 className="text-lg font-bold flex items-center gap-2">
                    <Zap className="w-5 h-5 text-amber-400" />
                    Agentic Hooks
                 </h3>
                 <div className="space-y-4">
                    <HookItem title="Linkedin Sync" active />
                    <HookItem title="GitHub Analyzer" active />
                    <HookItem title="X/Twitter Insights" />
                 </div>
                 <button className="w-full py-4 glass border-dashed border-white/10 rounded-2xl flex items-center justify-center gap-2 text-xs font-bold text-dim hover:text-white transition-all">
                    <Plus className="w-4 h-4" />
                    Add Integration
                 </button>
              </div>
           </div>
        </div>
      </div>
    </PageWrapper>
  );
}

function RoleItem({ title, score }: any) {
  return (
    <div className="flex items-center justify-between">
       <span className="text-sm font-bold text-white">{title}</span>
       <span className="text-xs font-bold text-primary">{score}%</span>
    </div>
  );
}

function HookItem({ title, active }: any) {
  return (
    <div className="flex items-center justify-between p-3 rounded-xl bg-white/[0.02] border border-white/5">
       <span className="text-sm font-medium text-white">{title}</span>
       <span className={cn(
           "px-2 py-0.5 rounded-md text-[10px] font-black uppercase tracking-tighter",
           active ? "bg-emerald-500/10 text-emerald-500" : "text-dim"
       )}>
           {active ? 'Linked' : 'Offline'}
       </span>
    </div>
  );
}

function cn(...inputs: any[]) {
  return inputs.filter(Boolean).join(' ');
}
