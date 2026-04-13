import { 
  FileUp, 
  Link, 
  FileText, 
  Sparkles,
  ArrowRight,
  ShieldCheck
} from 'lucide-react';
import { PageWrapper } from '@/components/PageWrapper';
import { cn } from '@/lib/utils';

export default function UserOnboarding() {
  return (
    <PageWrapper>
      <div className="max-w-4xl mx-auto space-y-12 py-10">
        <header className="text-center space-y-4">
          <div className="w-16 h-16 bg-primary/10 rounded-2xl flex items-center justify-center mx-auto mb-6 border border-primary/20">
            <Sparkles className="text-primary w-8 h-8" />
          </div>
          <h1 className="text-5xl font-extrabold tracking-tight">Define Your Intelligence Persona</h1>
          <p className="text-dim text-xl max-w-2xl mx-auto">
            Choose how you'd like CurateAI to personalize your content loops and agentic research.
          </p>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          <OnboardingOption 
            title="LinkedIn PDF"
            description="Upload your exported LinkedIn profile to automatically extract entities and skills."
            icon={Link}
            primary
          />
          <OnboardingOption 
            title="Resume / CV"
            description="Upload a standard PDF resume for deep scanning of your professional background."
            icon={FileText}
          />
          <OnboardingOption 
            title="Manual Setup"
            description="Hand-pick your interest clusters, technical focus areas, and industry sectors."
            icon={ArrowRight}
          />
          <div className="glass rounded-3xl p-8 border border-white/5 flex flex-col items-center justify-center space-y-4 text-center">
            <div className="p-3 bg-white/5 rounded-full">
              <ShieldCheck className="w-6 h-6 text-emerald-400" />
            </div>
            <p className="text-xs text-dim lowercase font-mono">End-to-end encrypted storage of profile data.</p>
          </div>
        </div>

        <div className="glass rounded-[2.5rem] p-12 border border-white/5 flex flex-col items-center text-center space-y-8 bg-gradient-to-b from-white/[0.02] to-transparent">
           <div className="space-y-2">
              <h3 className="text-2xl font-bold">Quick Upload</h3>
              <p className="text-dim">Drag and drop your LinkedIn PDF or Resume here to start the extraction agent.</p>
           </div>
           
           <div className="w-full max-w-md aspect-video border-2 border-dashed border-white/10 rounded-3xl flex flex-col items-center justify-center gap-4 hover:border-primary/40 hover:bg-primary/5 transition-all cursor-pointer group">
              <div className="p-4 bg-white/5 rounded-2xl group-hover:scale-110 transition-transform">
                <FileUp className="w-8 h-8 text-dim group-hover:text-primary" />
              </div>
              <p className="text-sm font-bold text-dim">Click to browse or drag file</p>
           </div>

           <p className="text-[10px] text-zinc-600 uppercase tracking-widest font-black">Supported formats: PDF, DOCX (Max 10MB)</p>
        </div>
      </div>
    </PageWrapper>
  );
}

function OnboardingOption({ title, description, icon: Icon, primary }: any) {
  return (
    <div className={cn(
      "glass rounded-3xl p-8 border border-white/5 hover:border-white/10 transition-all cursor-pointer group relative overflow-hidden",
      primary && "bg-gradient-to-br from-primary/5 to-transparent border-primary/20"
    )}>
      {primary && (
        <div className="absolute top-4 right-4 px-2 py-0.5 rounded-md bg-primary text-primary-foreground text-[10px] font-black uppercase">
          Recommended
        </div>
      )}
      <div className={cn(
        "w-12 h-12 rounded-xl flex items-center justify-center mb-6 transition-transform group-hover:scale-110",
        primary ? "bg-primary text-primary-foreground shadow-lg shadow-primary/20" : "bg-white/5 text-dim border border-white/10"
      )}>
        <Icon className="w-6 h-6" />
      </div>
      <h3 className="text-xl font-bold mb-2 group-hover:text-primary transition-colors">{title}</h3>
      <p className="text-sm text-dim leading-relaxed">{description}</p>
    </div>
  );
}
