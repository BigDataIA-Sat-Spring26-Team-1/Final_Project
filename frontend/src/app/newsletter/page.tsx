import { 
  Plus, 
  Mail
} from 'lucide-react';
import { PageWrapper } from '@/components/PageWrapper';
import { DraftCard } from '@/components/DashboardComponents';

export default function NewsletterPage() {
  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex items-end justify-between">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold tracking-tight">Agentic Newsletters</h1>
            <p className="text-muted-foreground text-lg">Manage your automated curation cycles and drafts.</p>
          </div>
          <button className="flex items-center gap-2 bg-primary hover:bg-primary/90 text-primary-foreground px-6 py-3 rounded-2xl text-sm font-bold transition-all shadow-lg shadow-primary/20">
            <Plus className="w-5 h-5" />
            Generate New Draft
          </button>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <DraftCard 
            title="The AI Weekly: GPT-5, RAG Patterns & EU Policy"
            status="DRAFT"
            persona="Tech Professional"
            date="Oct 24, 2024"
            recipients={1240}
          />
          <DraftCard 
            title="Deep Learning Observer: October Edition"
            status="SCHEDULED"
            persona="Researcher"
            date="Oct 28, 2024"
            recipients={850}
          />
          <DraftCard 
            title="Venture Insights: AI Unicorns to Watch"
            status="SENT"
            persona="Investor"
            date="Oct 20, 2024"
            recipients={2100}
          />
        </div>

        <div className="glass rounded-3xl p-10 border border-dashed border-white/20 text-center space-y-4">
          <div className="w-16 h-16 bg-white/5 rounded-full flex items-center justify-center mx-auto mb-6">
            <Mail className="w-8 h-8 text-muted-foreground" />
          </div>
          <h3 className="text-xl font-bold">No active agent triggers</h3>
          <p className="text-muted-foreground max-w-sm mx-auto">
            Configure cross-source triggers to automatically generate drafts based on custom score thresholds.
          </p>
          <button className="text-primary font-bold text-sm hover:underline">Manage Triggers</button>
        </div>
      </div>
    </PageWrapper>
  );
}
