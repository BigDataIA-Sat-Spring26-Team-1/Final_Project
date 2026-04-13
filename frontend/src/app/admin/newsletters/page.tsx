import { 
  Newspaper, 
  Calendar, 
  Search, 
  TrendingUp,
  Mail,
  MoreVertical,
  Eye,
  CheckCircle2
} from 'lucide-react';
import { PageWrapper } from '@/components/PageWrapper';

export default function AdminNewslettersPage() {
  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex items-end justify-between">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold tracking-tight">Global Distribution Archive</h1>
            <p className="text-dim text-lg">Central repository for the "Top 20 Common" daily tech briefs.</p>
          </div>
          <button className="bg-secondary hover:bg-secondary/90 text-white px-6 py-3 rounded-2xl text-sm font-bold transition-all flex items-center gap-2">
             <Mail className="w-5 h-5" />
             Trigger Force Sync
          </button>
        </header>

        {/* Global Stats for Newsletters */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
           <div className="glass rounded-[2rem] p-8 border border-white/5 space-y-2">
              <p className="text-[10px] font-black text-dim uppercase tracking-widest leading-none">Total Distribution</p>
              <h3 className="text-3xl font-black">1.2M+</h3>
              <p className="text-xs text-emerald-400 font-bold">+18k today</p>
           </div>
           <div className="glass rounded-[2rem] p-8 border border-white/5 space-y-2 bg-secondary/5">
              <p className="text-[10px] font-black text-secondary uppercase tracking-widest leading-none">Global Open Rate</p>
              <h3 className="text-3xl font-black">42.8%</h3>
              <p className="text-xs text-dim">Benchmark: 22.4%</p>
           </div>
           <div className="glass rounded-[2rem] p-8 border border-white/5 space-y-2">
              <p className="text-[10px] font-black text-dim uppercase tracking-widest leading-none">Agent Accuracy</p>
              <h3 className="text-3xl font-black">98.4%</h3>
              <p className="text-xs text-dim font-bold tracking-tighter">LLM-Verification Passed</p>
           </div>
        </div>

        <div className="space-y-6">
           <h2 className="text-xl font-bold flex items-center gap-2">
              <Calendar className="w-5 h-5 text-secondary" />
              Daily Common Archives (Top 20)
           </h2>
           
           <div className="space-y-4">
              <HistoryItem 
                date="April 11, 2026"
                title="The Pulse: Silicon Dawn & Agentic Shift"
                deliveries="122,400"
                status="SENT"
                relevance={94}
              />
              <HistoryItem 
                date="April 10, 2026"
                title="The Pulse: LLM Security & HNSW Scaling"
                deliveries="118,900"
                status="SENT"
                relevance={96}
              />
              <HistoryItem 
                date="April 09, 2026"
                title="The Pulse: EU Policy & Edge Compute"
                deliveries="114,200"
                status="SENT"
                relevance={91}
              />
              <HistoryItem 
                date="April 08, 2026"
                title="The Pulse: Quantum Leap & Vector ROI"
                deliveries="125,100"
                status="ARCHIVED"
                relevance={89}
              />
           </div>
        </div>
      </div>
    </PageWrapper>
  );
}

function HistoryItem({ date, title, deliveries, status, relevance }: any) {
  return (
    <div className="glass rounded-3xl p-6 border border-white/5 flex items-center justify-between hover:bg-white/[0.02] group cursor-pointer transition-all active:scale-[0.99]">
       <div className="flex items-center gap-6 flex-1">
          <div className="w-14 h-14 rounded-2xl bg-white/5 flex flex-col items-center justify-center border border-white/5 text-center px-2">
             <p className="text-[8px] font-black uppercase text-dim leading-none">APR</p>
             <p className="text-xl font-black leading-none mt-1">{date.split(' ')[1].replace(',', '')}</p>
          </div>
          <div className="space-y-1">
             <h4 className="text-lg font-bold group-hover:text-secondary transition-colors">{title}</h4>
             <div className="flex items-center gap-4 text-xs text-dim font-medium">
                <span className="flex items-center gap-1.5">
                   <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                   {deliveries} Delivered
                </span>
                <span className="w-1 h-1 rounded-full bg-white/10" />
                <span>Score: {relevance}%</span>
             </div>
          </div>
       </div>
       <div className="flex items-center gap-6">
          <span className="px-3 py-1 rounded-full bg-white/5 text-[10px] font-black tracking-widest border border-white/10 text-dim">
             {status}
          </span>
          <div className="flex gap-2">
             <button className="p-2.5 rounded-xl hover:bg-white/5 text-dim hover:text-white transition-all"><Eye className="w-5 h-5" /></button>
             <button className="p-2.5 rounded-xl hover:bg-white/5 text-dim hover:text-white transition-all"><MoreVertical className="w-5 h-5" /></button>
          </div>
       </div>
    </div>
  );
}
