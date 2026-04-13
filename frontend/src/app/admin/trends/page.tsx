import { 
  BarChart3, 
  TrendingUp, 
  Search,
  ArrowUpRight,
  ShieldCheck,
  Globe
} from 'lucide-react';
import { PageWrapper } from '@/components/PageWrapper';
import { cn } from '@/lib/utils';

export default function AdminTrendsPage() {
  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex items-end justify-between">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold tracking-tight">Global Market Sentiment</h1>
            <p className="text-dim text-lg">Aggregated signals across all monitored tech clusters and newsletters.</p>
          </div>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
           <div className="glass rounded-3xl p-8 border border-white/5 space-y-4 shadow-2xl">
              <div className="flex items-center gap-3 text-emerald-400 mb-2">
                <Globe className="w-6 h-6" />
                <h3 className="font-bold uppercase tracking-widest text-xs">Primary Signal</h3>
              </div>
              <h4 className="text-3xl font-black">Agentic Orchestration</h4>
              <p className="text-dim">Currently surfacing in 84% of all generated B2B drafts this week.</p>
           </div>
           
           <div className="glass rounded-3xl p-8 border border-white/5 space-y-4 bg-gradient-to-br from-primary/5 to-transparent">
              <div className="flex items-center gap-3 text-primary mb-2">
                <ShieldCheck className="w-6 h-6" />
                <h3 className="font-bold uppercase tracking-widest text-xs">Data Reliability</h3>
              </div>
              <h4 className="text-3xl font-black">99.2% Nominal</h4>
              <p className="text-dim">Average cross-source verification score across 12,000+ articles.</p>
           </div>
        </div>

        {/* Prototype Keyword Table Implementation */}
        <div className="glass rounded-[2.5rem] border border-white/5 overflow-hidden">
           <div className="p-8 border-b border-white/5 flex items-center justify-between bg-white/[0.01]">
              <h3 className="text-xl font-bold">Emerging Topics & Entity Velocity</h3>
              <div className="flex items-center gap-4">
                 <div className="flex items-center glass rounded-xl px-4 py-2 border border-white/5">
                    <Search className="w-4 h-4 text-dim mr-2" />
                    <input type="text" placeholder="Filter entities..." className="bg-transparent border-none outline-none text-sm w-48" />
                 </div>
              </div>
           </div>

           <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                 <thead>
                    <tr className="bg-white/5 text-[10px] font-black uppercase tracking-widest text-dim border-b border-white/5">
                       <th className="px-8 py-5">Entity / Signal</th>
                       <th className="px-8 py-5">Status</th>
                       <th className="px-8 py-5 text-center">Prev Window</th>
                       <th className="px-8 py-5 text-center">Current</th>
                       <th className="px-8 py-5 text-right">Velocity</th>
                    </tr>
                 </thead>
                 <tbody className="divide-y divide-white/5">
                    <TrendRow name="Hugging Face / LLM Hub" sub="Open Source Infrastructure" status="SURGING" prev={34} curr={117} delta="+244.1%" />
                    <TrendRow name="NVIDIA / H100 Supply" sub="Compute & Hardware" status="SURGING" prev={11} curr={64} delta="+481.8%" isHot />
                    <TrendRow name="Amazon Bedrock / SageMaker" sub="Enterprise Orchestration" status="BREAKOUT" prev={1} curr={12} delta="+1100.0%" isHot />
                    <TrendRow name="LLM / RAG Architecture" sub="Application Frameworks" status="SURGING" prev={40} curr={107} delta="+167.5%" />
                    <TrendRow name="Intel / Optimum Intel" sub="Edge Optimization" status="SURGING" prev={11} curr={31} delta="+181.8%" />
                    <TrendRow name="OpenAI / GPT-4o API" sub="Proprietary Models" status="DECLINING" prev={219} curr={9} delta="-95.9%" isNegative />
                 </tbody>
              </table>
           </div>
        </div>
      </div>
    </PageWrapper>
  );
}

function TrendRow({ name, sub, status, prev, curr, delta, isHot, isNegative }: any) {
  return (
    <tr className="hover:bg-white/[0.02] transition-colors group cursor-pointer">
       <td className="px-8 py-6">
          <p className="font-bold text-white group-hover:text-primary transition-colors">{name}</p>
          <p className="text-xs text-dim">{sub}</p>
       </td>
       <td className="px-8 py-6">
          <span className={cn(
             "px-3 py-1 rounded-full text-[10px] font-black tracking-widest border",
             isNegative ? "bg-red-500/10 text-red-500 border-red-500/20" : "bg-emerald-500/10 text-emerald-500 border-emerald-500/20"
          )}>
             {status}
          </span>
       </td>
       <td className="px-8 py-6 text-center text-dim font-medium">{prev}</td>
       <td className="px-8 py-6 text-center font-bold">{curr}</td>
       <td className={cn(
          "px-8 py-6 text-right font-black",
          isNegative ? "text-red-500" : "text-emerald-500"
       )}>
          {delta} {isNegative ? '↓' : '↑'}
       </td>
    </tr>
  );
}
