import { 
  TrendingUp, 
  Target, 
  BarChart3, 
  Flame,
  Globe,
  Briefcase,
  Search,
  ArrowUpRight
} from 'lucide-react';
import { PageWrapper } from '@/components/PageWrapper';

export default function CompanyTrendsPage() {
  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex items-end justify-between">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold tracking-tight">Keyword Velocity</h1>
            <p className="text-dim text-lg">Authority-weighted trend signals for <strong>Cloud Infrastructure Corp</strong>.</p>
          </div>
          <div className="flex items-center gap-3">
             <div className="flex items-center glass rounded-xl px-4 py-2 border border-white/5">
                <Search className="w-4 h-4 text-dim mr-2" />
                <input type="text" placeholder="Filter company keywords..." className="bg-transparent border-none outline-none text-sm w-48" />
             </div>
          </div>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
           <div className="glass rounded-3xl p-8 border border-white/5 space-y-4">
              <h3 className="text-xs font-black uppercase tracking-widest text-secondary">Dominant Authority Cluster</h3>
              <h4 className="text-3xl font-black">Vector DB Security</h4>
              <p className="text-dim">You currently hold a 0.82 alignment score in this emerging tech segment.</p>
              <div className="flex items-center gap-2 text-emerald-400 text-sm font-bold">
                 <ArrowUpRight className="w-4 h-4" />
                 +14% Growth this month
              </div>
           </div>
           <div className="glass rounded-3xl p-8 border border-white/5 space-y-4 bg-gradient-to-br from-primary/5 to-transparent">
              <h3 className="text-xs font-black uppercase tracking-widest text-primary">Blue Ocean Opportunity</h3>
              <h4 className="text-3xl font-black">HNSW Distribution</h4>
              <p className="text-dim">High search velocity with low competitor authority overlap detected.</p>
              <button className="text-xs font-black text-primary hover:underline uppercase tracking-widest">Generate Strategy Brief</button>
           </div>
        </div>

        <div className="glass rounded-[2.5rem] border border-white/5 overflow-hidden">
           <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                 <thead>
                    <tr className="bg-white/5 text-[10px] font-black uppercase tracking-widest text-dim border-b border-white/5">
                       <th className="px-8 py-5">Strategic Keyword</th>
                       <th className="px-8 py-5">Company Status</th>
                       <th className="px-8 py-5 text-center">Market Vol</th>
                       <th className="px-8 py-5 text-center">Our Authority</th>
                       <th className="px-8 py-5 text-right">Momentum</th>
                    </tr>
                 </thead>
                 <tbody className="divide-y divide-white/5">
                    <CompanyTrendRow name="Vector Embedding Security" status="LEADER" vol="12.4k" auth="0.94" delta="+22%" />
                    <CompanyTrendRow name="Edge-First Telemetry" status="EMERGING" vol="8.1k" auth="0.45" delta="+8%" />
                    <CompanyTrendRow name="Distributed HNSW" status="OPPORTUNITY" vol="4.2k" auth="0.12" delta="+1100%" isHot />
                    <CompanyTrendRow name="Semantic Deduplication" status="MATURE" vol="45.2k" auth="0.88" delta="-2%" isNegative />
                 </tbody>
              </table>
           </div>
        </div>
      </div>
    </PageWrapper>
  );
}

function CompanyTrendRow({ name, status, vol, auth, delta, isHot, isNegative }: any) {
  return (
    <tr className="hover:bg-white/[0.02] transition-colors group cursor-pointer">
       <td className="px-8 py-6 font-bold text-white group-hover:text-primary transition-colors">{name}</td>
       <td className="px-8 py-6">
          <span className={cn(
             "px-3 py-1 rounded-full text-[10px] font-black tracking-widest border",
             status === 'OPPORTUNITY' ? "bg-primary/10 text-primary border-primary/20" : "bg-white/5 text-dim border-white/10"
          )}>
             {status}
          </span>
       </td>
       <td className="px-8 py-6 text-center text-dim font-medium">{vol}</td>
       <td className="px-8 py-6 text-center">
          <div className="flex flex-col items-center">
             <span className="text-xs font-bold text-white leading-none">{auth}</span>
             <div className="w-12 h-1 bg-white/5 rounded-full mt-1">
                <div className="h-full bg-secondary rounded-full" style={{ width: `${parseFloat(auth) * 100}%` }} />
             </div>
          </div>
       </td>
       <td className={cn(
          "px-8 py-6 text-right font-black",
          isNegative ? "text-red-500" : "text-emerald-500"
       )}>
          {delta} {isNegative ? '↓' : '↑'}
       </td>
    </tr>
  );
}

function cn(...inputs: any[]) {
  return inputs.filter(Boolean).join(' ');
}
