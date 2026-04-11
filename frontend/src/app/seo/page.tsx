import { 
  Target, 
  FileText,
  MousePointer2,
  ShieldCheck
} from 'lucide-react';
import { PageWrapper } from '@/components/PageWrapper';
import { OpportunityItem } from '@/components/DashboardComponents';

export default function SEOStrategyPage() {
  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex flex-col gap-2">
          <h1 className="text-4xl font-bold tracking-tight">Enterprise SEO Intelligence</h1>
          <p className="text-muted-foreground text-lg">Cross-company authority matching and blue ocean discovery.</p>
        </header>

        <div className="flex items-center gap-6 p-8 glass rounded-3xl border border-white/5 bg-gradient-to-r from-primary/5 to-transparent">
          <div className="w-16 h-16 rounded-2xl bg-primary flex items-center justify-center shadow-2xl shadow-primary/20">
            <ShieldCheck className="w-8 h-8 text-primary-foreground" />
          </div>
          <div className="flex-1 space-y-1 border-r border-white/10 pr-10">
            <p className="text-sm font-semibold text-primary uppercase tracking-widest">Active Authority Profile</p>
            <h2 className="text-2xl font-bold">Cloud Infrastructure Corp</h2>
          </div>
          <div className="flex-1 space-y-1 px-10 border-r border-white/10">
            <p className="text-xs text-muted-foreground uppercase font-bold tracking-tighter">Vector Alignment</p>
            <div className="flex items-center gap-3">
              <h3 className="text-2xl font-black">0.89</h3>
              <div className="w-24 h-2 bg-white/10 rounded-full overflow-hidden">
                <div className="w-[89%] h-full bg-primary" />
              </div>
            </div>
          </div>
          <div className="flex-1 space-y-1 pl-10">
            <p className="text-xs text-muted-foreground uppercase font-bold tracking-tighter">Top Keyword Cluster</p>
            <h3 className="text-xl font-bold">HNSW Indexing</h3>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
          <div className="space-y-6">
            <h2 className="text-xl font-bold flex items-center gap-2">
              <Target className="w-5 h-5 text-primary" />
              Strategic Opportunities
            </h2>
            <div className="space-y-4">
              <OpportunityItem 
                topic="Vector Search Optimization"
                relevance={94}
                competition="LOW"
                category="Technical SEO"
              />
              <OpportunityItem 
                topic="Distributed HNSW Performance"
                relevance={88}
                competition="LOW"
                category="Industry Whitepaper"
              />
              <OpportunityItem 
                topic="Enterprise RAG Compliance"
                relevance={82}
                competition="MEDIUM"
                category="Case Study"
              />
            </div>
          </div>

          <div className="space-y-6">
            <h2 className="text-xl font-bold flex items-center gap-2">
              <FileText className="w-5 h-5 text-primary" />
              Ready Content Briefs
            </h2>
            <div className="glass rounded-3xl p-8 border border-white/5 space-y-6">
              <div className="bg-white/5 rounded-2xl p-5 border border-white/5 space-y-4">
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <h4 className="text-lg font-bold">Scaling Vectors for Enterprise</h4>
                    <p className="text-sm text-muted-foreground">Strategic angles for Cloud Admin audience.</p>
                  </div>
                  <button className="p-2 rounded-xl bg-white/5 hover:bg-white/10 text-muted-foreground hover:text-white transition-all">
                    <MousePointer2 className="w-4 h-4" />
                  </button>
                </div>
                <div className="flex gap-2">
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-primary/20 text-primary border border-primary/20 uppercase">Primary</span>
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-white/5 text-muted-foreground border border-white/10 uppercase">HNSW</span>
                </div>
              </div>
              <button className="w-full py-4 rounded-2xl bg-white text-black font-bold text-sm hover:bg-zinc-200 transition-all">
                Initialize Agentic Brief Generation
              </button>
            </div>
          </div>
        </div>
      </div>
    </PageWrapper>
  );
}
