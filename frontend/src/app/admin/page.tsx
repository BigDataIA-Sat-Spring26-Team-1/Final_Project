import { 
  Users, 
  Building2, 
  Zap, 
  ShieldCheck,
  TrendingUp,
  AlertCircle
} from 'lucide-react';
import { PageWrapper } from '@/components/PageWrapper';
import { StatCard, ActivityItem } from '@/components/DashboardComponents';

export default function AdminDashboard() {
  return (
    <PageWrapper>
      <div className="space-y-10">
        <header>
          <h1 className="text-4xl font-bold tracking-tight">System Administration</h1>
          <p className="text-dim text-lg">Global infrastructure overview and cross-sector metrics.</p>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <StatCard 
            title="Total B2C Users" 
            value="12,540" 
            change="+4.2%" 
            description="Active personal personas"
            icon={Users}
          />
          <StatCard 
            title="Total B2B Entities" 
            value="482" 
            change="+1.8%" 
            description="Enterprise accounts"
            icon={Building2}
          />
          <StatCard 
            title="Today's Newsletters" 
            value="24" 
            change="Common Set" 
            description="Global distribution drafts"
            icon={Zap}
          />
          <StatCard 
            title="System Status" 
            value="Operational" 
            change="100%" 
            description="All services online"
            icon={ShieldCheck}
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Admin specific activity */}
          <div className="space-y-6">
            <h2 className="text-xl font-bold flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-secondary" />
              High Velocity Clusters
            </h2>
            <div className="space-y-4">
              <ActivityItem 
                title="Hugging Face / LLM Hub"
                source="OPEN SOURCE"
                time="Global"
                status="SURGING"
                relevancy={100}
              />
              <ActivityItem 
                title="Chain-of-Thought Reasoning"
                source="RESEARCH"
                time="Global"
                status="TRENDING"
                relevancy={98}
              />
            </div>
          </div>

          <div className="space-y-6">
            <h2 className="text-xl font-bold flex items-center gap-2 text-amber-400">
              <AlertCircle className="w-5 h-5" />
              Pending Admin Reviews
            </h2>
            <div className="glass rounded-3xl p-6 border border-white/5 space-y-4">
              <p className="text-sm text-dim italic">No critical policy updates required today. All agent scoring thresholds are within nominal range.</p>
            </div>
          </div>
        </div>
      </div>
    </PageWrapper>
  );
}
