import { 
  Plus, 
  Search, 
  Clock, 
  ArrowUpRight,
  Eye,
  Settings2,
  Brain,
  Zap
} from 'lucide-react';
import { PageWrapper } from '@/components/PageWrapper';
import { DraftCard } from '@/components/DashboardComponents';

export default function CompanyDraftsPage() {
  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex items-end justify-between">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold tracking-tight">Enterprise Draft Cycles</h1>
            <p className="text-dim text-lg">Agentic brief generation and editorial review loops.</p>
          </div>
          <button className="bg-primary hover:bg-primary/90 text-primary-foreground px-8 py-3 rounded-2xl text-sm font-black transition-all flex items-center gap-2 shadow-2xl shadow-primary/20">
             <Plus className="w-5 h-5" />
             Trigger Strategy Agent
          </button>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
           <div className="glass rounded-[2rem] p-10 border border-white/5 space-y-6 bg-gradient-to-br from-secondary/10 to-transparent">
              <div className="flex items-center gap-3 text-secondary">
                 <Brain className="w-6 h-6" />
                 <h3 className="font-bold uppercase tracking-widest text-xs">Strategy Context</h3>
              </div>
              <div className="space-y-4">
                 <div className="space-y-1">
                    <p className="text-[10px] font-black text-dim uppercase tracking-widest leading-none">Primary Authority</p>
                    <p className="text-xl font-bold text-white">Cloud Systems / Vector Security</p>
                 </div>
                 <div className="space-y-1">
                    <p className="text-[10px] font-black text-dim uppercase tracking-widest leading-none">Target Sentiment</p>
                    <p className="text-xl font-bold text-emerald-400">Thought Leadership / Innovation</p>
                 </div>
              </div>
              <button className="flex items-center gap-2 text-xs font-bold text-dim hover:text-white transition-colors">
                 <Settings2 className="w-4 h-4" />
                 Configure Multi-Agent Tuning
              </button>
           </div>

           <div className="glass rounded-[2rem] p-10 border border-white/5 flex flex-col items-center justify-center text-center space-y-5">
              <div className="w-16 h-16 rounded-full bg-white/5 flex items-center justify-center animate-pulse">
                 <Zap className="w-8 h-8 text-primary/40" />
              </div>
              <div className="space-y-1">
                 <h3 className="text-lg font-bold">Real-time Brief Monitoring</h3>
                 <p className="text-xs text-dim max-w-[240px] leading-relaxed">Agent is currently analyzing 14 Emerging Entity matches for your Authority Profile.</p>
              </div>
           </div>
        </div>

        <div className="space-y-6">
           <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold flex items-center gap-2">
                 <Clock className="w-5 h-5 text-secondary" />
                 Recent Brief Outputs
              </h2>
           </div>
           
           <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              <DraftCard 
                 title="Blue Ocean Strategy: Zero-Trust Vector Scaling"
                 status="DRAFT"
                 persona="C-Level Execs"
                 date="Apr 11, 2026"
                 recipients={1240}
              />
              <DraftCard 
                 title="Whitepaper: The HNSW Memory Optimization Gap"
                 status="ARCHIVED"
                 persona="Solutions Architects"
                 date="Apr 08, 2026"
                 recipients={2100}
              />
           </div>
        </div>
      </div>
    </PageWrapper>
  );
}
