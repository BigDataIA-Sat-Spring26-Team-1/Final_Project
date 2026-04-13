'use client';

import { 
  Newspaper, 
  Search, 
  Sparkles,
  ArrowRight,
  TrendingUp,
  Mail,
  User as UserIcon
} from 'lucide-react';
import { PageWrapper } from '@/components/PageWrapper';
import { ActivityItem } from '@/components/DashboardComponents';
import { useState } from 'react';
import { cn } from '@/lib/utils';

export default function UserDashboard() {
  const [activeTab, setActiveTab] = useState<'PERSONALIZED' | 'COMMON'>('PERSONALIZED');

  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex flex-col gap-2">
          <div className="flex items-center gap-2 text-primary font-bold text-sm uppercase tracking-widest">
            <Sparkles className="w-4 h-4" />
            Welcome back, Aakash
          </div>
          <h1 className="text-4xl font-bold tracking-tight">Your Intelligence Loop</h1>
          <p className="text-dim text-lg">Daily tech updates curated for your <strong>Tech Strategist</strong> persona.</p>
        </header>

        {/* Tab Switcher */}
        <div className="flex items-center gap-1 p-1 glass rounded-2xl w-fit border border-white/5">
          <button 
            onClick={() => setActiveTab('PERSONALIZED')}
            className={cn(
              "px-6 py-2 rounded-xl text-sm font-bold transition-all",
              activeTab === 'PERSONALIZED' ? "bg-secondary text-white shadow-lg shadow-secondary/20" : "text-dim hover:text-white"
            )}
          >
            Personalized Feed
          </button>
          <button 
            onClick={() => setActiveTab('COMMON')}
            className={cn(
              "px-6 py-2 rounded-xl text-sm font-bold transition-all",
              activeTab === 'COMMON' ? "bg-secondary text-white shadow-lg shadow-secondary/20" : "text-dim hover:text-white"
            )}
          >
            Global Highlights
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-10">
          {/* Main Feed */}
          <div className="lg:col-span-2 space-y-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold flex items-center gap-2">
                <Newspaper className="w-5 h-5 text-primary" />
                {activeTab === 'PERSONALIZED' ? 'Curated Just For You' : 'Top 20 Technical Daily'}
              </h2>
            </div>
            
            <div className="space-y-4">
              <ActivityItem 
                title="The Rise of Agentic Frameworks: Why Bedrock is Winning"
                source="STRATEGY DEEP DIVE"
                time="2h ago"
                status="MATCH"
                relevancy={99}
              />
              <ActivityItem 
                title="HNSW vs Flat Indexing: PB-Scale Benchmarks"
                source="TECHNICAL DEPTH"
                time="4h ago"
                status="MATCH"
                relevancy={92}
              />
              <ActivityItem 
                title="EU AI Act Compliance Guide for Small VCs"
                source="POLITICAL SIGNAL"
                time="6h ago"
                status="MATCH"
                relevancy={88}
              />
              <button className="w-full py-4 glass rounded-2xl border-dashed border-white/10 text-sm font-bold text-dim hover:text-white hover:border-white/20 transition-all flex items-center justify-center gap-2">
                Load More Articles
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* User Sidebar */}
          <div className="space-y-8">
            <div className="glass rounded-3xl p-8 border border-white/5 space-y-6">
              <h3 className="text-lg font-bold flex items-center gap-2">
                <UserIcon className="w-5 h-5 text-secondary" />
                Your Profile
              </h3>
              <div className="space-y-4">
                 <div className="space-y-1">
                    <p className="text-[10px] font-black text-dim uppercase tracking-widest leading-none mb-2">Core Alignment</p>
                    <p className="text-sm font-bold text-white">Tech Strategist / Data Engineer</p>
                 </div>
                 <div className="space-y-1">
                    <p className="text-[10px] font-black text-dim uppercase tracking-widest leading-none mb-2">Primary Interests</p>
                    <div className="flex flex-wrap gap-2">
                       <span className="px-2 py-1 rounded-md bg-white/5 text-[10px] font-bold border border-white/10 uppercase">Vector DBs</span>
                       <span className="px-2 py-1 rounded-md bg-white/5 text-[10px] font-bold border border-white/10 uppercase">Agentic AI</span>
                       <span className="px-2 py-1 rounded-md bg-white/5 text-[10px] font-bold border border-white/10 uppercase">Cloud Ops</span>
                    </div>
                 </div>
              </div>
              <button className="w-full py-3 bg-white text-black rounded-xl text-xs font-black uppercase tracking-widest hover:bg-zinc-200 transition-colors">
                 Update Persona
              </button>
            </div>

            <div className="glass rounded-3xl p-8 border border-white/5 space-y-4 bg-gradient-to-br from-secondary/10 to-transparent">
              <Mail className="w-6 h-6 text-secondary mb-2" />
              <h3 className="text-lg font-bold">Newsletter Schedule</h3>
              <p className="text-xs text-dim leading-relaxed">Your personalized newsletter is dispatched daily at <strong>09:00 EST</strong> based on your interest velocity.</p>
              <div className="pt-2">
                 <span className="px-3 py-1 rounded-full bg-emerald-500/10 text-emerald-500 text-[10px] font-black border border-emerald-500/20 uppercase">Next Sync: 14h 22m</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </PageWrapper>
  );
}
