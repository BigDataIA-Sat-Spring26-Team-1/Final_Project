import { 
  TrendingUp, 
  Target, 
  BarChart3, 
  ChevronRight,
  Flame,
  Globe,
  Briefcase
} from 'lucide-react';
import { PageWrapper } from '@/components/PageWrapper';
import { TrendFeatureCard, EntityItem } from '@/components/DashboardComponents';

export default function CompanyDashboard() {
  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex flex-col gap-2">
          <div className="flex items-center gap-2 text-secondary font-bold text-sm uppercase tracking-widest">
            <Briefcase className="w-4 h-4" />
            Enterprise Console
          </div>
          <h1 className="text-4xl font-bold tracking-tight">Market Intelligence Hub</h1>
          <p className="text-dim text-lg">Authority tracking and competitor blue ocean opportunities for <strong>Cloud Infrastructure Corp</strong>.</p>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
           <div className="lg:col-span-3 space-y-8">
              {/* Main Analysis Chart Placeholder */}
              <div className="glass rounded-[2rem] p-10 border border-white/5 space-y-6 relative overflow-hidden group">
                 <div className="flex items-center justify-between relative z-10">
                    <div>
                       <h3 className="text-2xl font-bold">Keyword Velocity Index</h3>
                       <p className="text-sm text-dim">Aggregated visibility across primary clusters.</p>
                    </div>
                    <div className="flex items-center gap-4">
                       <div className="text-right">
                          <p className="text-[10px] font-black text-dim uppercase tracking-widest">Global Rank</p>
                          <p className="text-xl font-bold text-emerald-400">#42 (+12)</p>
                       </div>
                    </div>
                 </div>
                 
                 <div className="h-64 flex items-end gap-1.5 px-2 relative z-10">
                    {[30, 45, 35, 70, 55, 90, 85, 120, 110, 140, 130, 160, 120, 100, 80, 110].map((h, i) => (
                      <div 
                        key={i} 
                        className="flex-1 bg-gradient-to-t from-secondary/40 to-secondary/10 rounded-t-lg transition-all hover:from-secondary/60" 
                        style={{ height: `${h / 2}%` }} 
                      />
                    ))}
                 </div>

                 {/* Decorative background circle */}
                 <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-secondary/5 blur-[120px] rounded-full z-0" />
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                 <TrendFeatureCard 
                    title="Authority Overlap" 
                    value="12% Strategic" 
                    icon={Target}
                    detail="Competitor: HashiCorp"
                 />
                 <TrendFeatureCard 
                    title="Traffic Opportunity" 
                    value="High (9.2)" 
                    icon={Flame}
                    detail="Cluster: Vector Security"
                    isPrimary
                 />
              </div>
           </div>

           <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h2 className="text-xl font-bold">Signal Feed</h2>
                <button className="text-xs font-bold text-secondary flex items-center gap-1 hover:underline">
                    View Matrix
                    <ChevronRight className="w-3 h-3" />
                </button>
              </div>
              <div className="space-y-4">
                <EntityItem name="HNSW Latency" score={9.8} delta={32} />
                <EntityItem name="Qdrant Cloud" score={8.2} delta={15} />
                <EntityItem name="Distributed RAG" score={7.9} delta={45} />
                <EntityItem name="LLM Proxy" score={6.5} delta={-12} />
                <EntityItem name="Semantic Cache" score={9.1} delta={28} />
              </div>
           </div>
        </div>
      </div>
    </PageWrapper>
  );
}
