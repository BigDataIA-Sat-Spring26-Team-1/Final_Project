import { 
  Clock, 
  Zap, 
  CheckCircle2, 
  Newspaper,
  TrendingUp,
  Brain
} from 'lucide-react';
import { PageWrapper } from '@/components/PageWrapper';
import { StatCard, ActivityItem, TrendTag } from '@/components/DashboardComponents';

export default function Home() {
  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex flex-col gap-2">
          <h1 className="text-4xl font-bold tracking-tight">Intelligence Overview</h1>
          <p className="text-muted-foreground text-lg">System heartbeat and content curation metrics.</p>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard 
            title="Daily Ingestion" 
            value="3,129" 
            change="+12%" 
            description="Articles processed today"
            icon={Zap}
          />
          <StatCard 
            title="Avg. Relevancy" 
            value="94.2%" 
            change="+2.4%" 
            description="Personalization score"
            icon={CheckCircle2}
          />
          <StatCard 
            title="Agent Cycles" 
            value="158" 
            change="+8" 
            description="LangGraph executions"
            icon={Brain}
          />
          <StatCard 
            title="Drafts Ready" 
            value="12" 
            change="0" 
            description="Pending human review"
            icon={Newspaper}
            isWarning
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold flex items-center gap-2">
                <Clock className="w-5 h-5 text-primary" />
                Recent Ingestion Stream
              </h2>
              <button className="text-sm font-medium text-primary hover:underline">View All</button>
            </div>
            
            <div className="space-y-4">
              <ActivityItem 
                title="OpenAI Releases GPT-5 Preliminary Safety Report"
                source="OpenAI Blog"
                time="12m ago"
                status="QUALIFIED"
                relevancy={98}
              />
              <ActivityItem 
                title="New HNSW Optimization in Qdrant 1.9"
                source="Qdrant Technical"
                time="45m ago"
                status="VECTORIZED"
                relevancy={82}
              />
              <ActivityItem 
                title="EU AI Act: Final Vote Results and Implementation Timeline"
                source="Reuters Tech"
                time="1h ago"
                status="TRENDING"
                relevancy={95}
              />
              <ActivityItem 
                title="State of LLM Evaluation 2024: Benchmarks vs Reality"
                source="ArXiv cs.CL"
                time="3h ago"
                status="RESEARCH"
                relevancy={89}
              />
            </div>
          </div>

          <div className="space-y-6">
            <h2 className="text-xl font-bold flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-primary" />
              Active Trends
            </h2>
            <div className="glass rounded-2xl p-6 space-y-5 border border-white/5">
              <TrendTag name="LLM Safety" count={42} velocity="High" />
              <TrendTag name="HNSW Indexing" count={18} velocity="Stable" />
              <TrendTag name="EU AI Policy" count={31} velocity="Surging" />
              <TrendTag name="RAG Architectures" count={56} velocity="Peak" />
              <button className="w-full py-3 rounded-xl bg-secondary text-secondary-foreground font-medium text-sm hover:bg-secondary/80 transition-colors">
                Configure Thresholds
              </button>
            </div>
          </div>
        </div>
      </div>
    </PageWrapper>
  );
}
