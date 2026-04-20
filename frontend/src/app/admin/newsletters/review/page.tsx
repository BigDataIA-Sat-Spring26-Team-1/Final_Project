import { 
  ArrowLeft, 
  CheckCircle2, 
  RefreshCcw, 
  XCircle,
  Eye,
  Send,
  Sparkles,
  FileText
} from 'lucide-react';
import Link from 'next/link';
import { PageWrapper } from '@/components/PageWrapper';

export default function NewsletterReviewPage() {
  return (
    <PageWrapper>
      <div className="space-y-8 pb-20">
        <header className="flex items-center justify-between">
          <div className="flex items-center gap-4">
             <Link href="/admin/newsletters" className="p-2.5 glass rounded-xl border border-white/5 hover:bg-white/5 transition-all">
                <ArrowLeft className="w-5 h-5 text-dim" />
             </Link>
             <div>
                <h1 className="text-3xl font-bold tracking-tight">Editorial Review</h1>
                <p className="text-dim text-sm italic">Draft #LOOP-04-A: "The Silicon Dawn" | Target: Tech Professionals</p>
             </div>
          </div>
          <div className="flex items-center gap-3">
             <button className="px-5 py-2.5 glass border border-red-500/20 text-red-500 rounded-xl text-sm font-bold hover:bg-red-500/5 transition-all flex items-center gap-2">
                <XCircle className="w-4 h-4" />
                Reject
             </button>
             <button className="px-5 py-2.5 glass border border-primary/20 text-primary rounded-xl text-sm font-bold hover:bg-primary/5 transition-all flex items-center gap-2">
                <RefreshCcw className="w-4 h-4" />
                Regenerate Sections
             </button>
             <button className="px-8 py-2.5 bg-primary text-primary-foreground rounded-xl text-sm font-black uppercase tracking-widest hover:bg-primary/90 transition-all flex items-center gap-2 shadow-xl shadow-primary/20">
                <Send className="w-4 h-4" />
                Approve & Dispatch
             </button>
          </div>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
           {/* Sidebar: Metadata & Suggestions */}
           <div className="lg:col-span-1 space-y-6">
              <div className="glass rounded-[2rem] p-8 border border-white/5 space-y-6">
                 <h3 className="text-xs font-black uppercase tracking-widest text-secondary flex items-center gap-2">
                    <Sparkles className="w-4 h-4" />
                    Agent Reasoning
                 </h3>
                 <p className="text-sm text-dim leading-relaxed">
                    This draft was prioritized based on a 94% match with the "Agentic Orchestration" trend. The editorial tone is calibrated for "Analytical Professional".
                 </p>
                 <div className="pt-4 space-y-4 border-t border-white/5">
                    <div className="flex justify-between items-center text-xs">
                       <span className="text-dim">Relevancy Score</span>
                       <span className="text-emerald-500 font-bold">94%</span>
                    </div>
                    <div className="flex justify-between items-center text-xs">
                       <span className="text-dim">Coherence Index</span>
                       <span className="text-emerald-500 font-bold">88%</span>
                    </div>
                 </div>
              </div>

              <div className="glass rounded-[2rem] p-8 border border-white/5 space-y-4">
                 <h3 className="text-xs font-black uppercase tracking-widest text-dim">Active Sources</h3>
                 <ul className="space-y-3">
                    {['OpenAI Blog', 'ArXiv', 'VentureBeat', 'Qdrant Docs'].map(src => (
                       <li key={src} className="flex items-center gap-2 text-xs font-bold text-white">
                          <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                          {src}
                       </li>
                    ))}
                 </ul>
              </div>
           </div>

           {/* Main Review Viewpoint */}
           <div className="lg:col-span-3">
              <div className="glass rounded-[2.5rem] p-2 border border-white/10 shadow-2xl relative overflow-hidden">
                 <div className="bg-white rounded-[2.25rem] overflow-hidden flex flex-col min-h-[800px]">
                    {/* EMAIL PROTOTYPE REPLICATED */}
                    <div className="bg-white border-b-4 border-slate-900 text-left p-12">
                       <h2 className="text-slate-900 font-black text-3xl tracking-tighter">The Intelligence <span className="text-secondary">Loop</span></h2>
                       <p className="text-slate-400 text-sm font-medium mt-1 uppercase tracking-widest">April 12, 2026 • Curated for Aakash</p>
                    </div>
                    
                    <div className="flex-1 p-12 text-slate-800 space-y-10">
                       <div className="text-lg leading-relaxed border-l-2 border-secondary pl-6 text-slate-600">
                          Good morning, Aakash. <br /><br />
                          The market is leaning heavily into <strong>Agentic Orchestration</strong> this morning, with Amazon's Bedrock update setting a new ceiling for enterprise reliability. We've pulled 10 high-signal insights specifically for your B2B strategy.
                       </div>

                       <div className="space-y-8">
                          <h3 className="text-slate-900 text-xl font-black uppercase tracking-tight">The Big Story</h3>
                          <div className="space-y-4 group cursor-pointer relative">
                             <h4 className="text-secondary text-2xl font-bold leading-tight hover:underline">OpenAI closes funding round at an $852B valuation</h4>
                             <p className="text-slate-600 text-lg leading-relaxed">
                                OpenAI on Tuesday announced that it closed a record-breaking funding round at a post-money valuation of $852 billion. The round totaled $122 billion of committed capital.
                             </p>
                             <div className="p-6 bg-slate-50 border-l-4 border-secondary rounded-r text-sm italic text-slate-600">
                                <strong className="block not-italic text-xs font-black uppercase text-secondary mb-2">Agent Analysis</strong>
                                This underscores a global imperative for content-intelligence infrastructure.
                             </div>
                             {/* Section Editor Overlay */}
                             <div className="absolute -right-4 top-0 opacity-0 group-hover:opacity-100 transition-opacity">
                                <button className="p-2 bg-slate-100 rounded-lg text-slate-400 hover:text-slate-900 shadow-sm"><RefreshCcw className="w-4 h-4" /></button>
                             </div>
                          </div>
                       </div>

                       <div className="pt-10 border-t border-slate-100">
                          <h3 className="text-slate-400 text-xs font-black uppercase tracking-widest mb-6">Today's Pulse Matrix</h3>
                          <div className="grid grid-cols-2 gap-x-12 gap-y-6">
                             {[1, 2, 3, 4, 5, 6].map(i => (
                                <div key={i} className="flex gap-4 items-start">
                                   <span className="text-secondary font-black">0{i}</span>
                                   <p className="text-sm font-medium leading-snug">New HNSW benchmarks suggest 12% memory reduction at PB-scale.</p>
                                </div>
                             ))}
                          </div>
                       </div>
                    </div>

                    <div className="bg-slate-50 p-12 text-center text-slate-400 text-[10px] font-bold">
                       STAY CURATED. STAY INFORMED. CURATEAI 2026.
                    </div>
                 </div>
              </div>
           </div>
        </div>
      </div>
    </PageWrapper>
  );
}
