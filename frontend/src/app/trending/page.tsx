import { 
  Search, 
  Activity,
  Globe,
  Flame
} from 'lucide-react';
import { PageWrapper } from '@/components/PageWrapper';
import { TrendFeatureCard, EntityItem } from '@/components/DashboardComponents';

export default function TrendingPage() {
  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex items-end justify-between">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold tracking-tight">Trend Intelligence</h1>
            <p className="text-muted-foreground text-lg">Cross-source signals and topic velocity tracking.</p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center glass rounded-xl px-4 py-2 border border-white/5 focus-within:border-primary/50 transition-all">
              <Search className="w-4 h-4 text-muted-foreground mr-2" />
              <input 
                type="text" 
                placeholder="Filter topics..." 
                className="bg-transparent border-none outline-none text-sm w-48 placeholder:text-muted-foreground"
              />
            </div>
            <button className="bg-primary hover:bg-primary/90 text-primary-foreground px-6 py-2 rounded-xl text-sm font-semibold transition-all">
              Export Report
            </button>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
          <div className="lg:col-span-3 space-y-6">
            <div className="glass rounded-3xl p-8 border border-white/5 h-[400px] flex flex-col items-center justify-center text-center relative overflow-hidden group">
              <div className="absolute inset-x-0 bottom-0 h-48 flex items-end gap-1 px-8">
                {[40, 60, 45, 90, 65, 80, 55, 100, 75, 40, 60, 85, 95, 120, 80, 60, 40, 50, 70, 90].map((h, i) => (
                  <div 
                    key={i} 
                    className="flex-1 bg-primary/20 hover:bg-primary/40 transition-all rounded-t-sm" 
                    style={{ height: `${h}%` }} 
                  />
                ))}
              </div>
              <div className="z-10 bg-background/80 backdrop-blur-md p-6 rounded-2xl border border-white/10 shadow-2xl">
                <Activity className="w-10 h-10 text-primary mx-auto mb-4" />
                <h3 className="text-xl font-bold mb-2">Real-time Velocity Index</h3>
                <p className="text-muted-foreground text-sm max-w-sm">
                  Aggregated signal across 30+ sources. Currently tracking <span className="text-white font-bold">12 high-velocity clusters</span> in the last 24 hours.
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <TrendFeatureCard 
                title="Global Sentiment" 
                value="82% Positive" 
                icon={Globe}
                detail="Sector: Artificial Intelligence"
              />
              <TrendFeatureCard 
                title="Blue Ocean Score" 
                value="Low Competition" 
                icon={Flame}
                detail="Topic: HNSW Query Optimization"
                isPrimary
              />
            </div>
          </div>

          <div className="space-y-6">
            <h2 className="text-xl font-bold">Emerging Entities</h2>
            <div className="space-y-4">
              <EntityItem name="LLM Security" score={9.4} delta={12} />
              <EntityItem name="OpenAI Search" score={8.8} delta={24} />
              <EntityItem name="Nvidia B200" score={8.2} delta={8} />
              <EntityItem name="Apple Intelligence" score={7.9} delta={45} />
              <EntityItem name="Claude 3.5 Sonnet" score={7.5} delta={15} />
            </div>
          </div>
        </div>
      </div>
    </PageWrapper>
  );
}
