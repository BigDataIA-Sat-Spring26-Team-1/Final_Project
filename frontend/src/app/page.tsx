'use client';

// Public landing page. Renders without the authenticated sidebar so visitors
// who land here unauthenticated can read the pitch and then drive into
// /login or /signup. Copy is deliberately generic — it describes both the
// consumer (personalized newsletters) and enterprise (SEO briefs) sides.

import {
  ArrowRight,
  Brain,
  CheckCircle2,
  Gauge,
  LineChart,
  Mail,
  Rocket,
  Sparkles,
  Wand2,
} from 'lucide-react';
import Link from 'next/link';

import { useAuth, homeForRole } from '@/components/AuthProvider';

export default function LandingPage() {
  const { status, user } = useAuth();
  const primaryCta =
    status === 'authenticated' && user
      ? { href: homeForRole(user.role), label: 'Open your console' }
      : { href: '/signup', label: 'Get started free' };

  return (
    <div className="min-h-screen bg-background text-foreground">
      {/* Header */}
      <header className="relative z-10">
        <div className="max-w-6xl mx-auto px-6 lg:px-10 py-6 flex items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center font-black text-xs text-primary-foreground">
              C
            </div>
            <span className="text-xl font-bold tracking-tight gradient-text">CurateAI</span>
          </Link>
          <nav className="flex items-center gap-2">
            {status === 'authenticated' ? (
              <Link
                href={primaryCta.href}
                className="px-4 py-2 rounded-xl bg-primary text-primary-foreground text-sm font-bold hover:bg-primary/90 transition"
              >
                {primaryCta.label}
              </Link>
            ) : (
              <>
                <Link
                  href="/login"
                  className="px-4 py-2 rounded-xl text-sm font-bold text-muted-foreground hover:text-white transition"
                >
                  Log in
                </Link>
                <Link
                  href="/signup"
                  className="px-4 py-2 rounded-xl bg-primary text-primary-foreground text-sm font-bold hover:bg-primary/90 transition inline-flex items-center gap-2"
                >
                  Sign up <ArrowRight className="w-4 h-4" />
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="relative">
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-primary/10 blur-[140px] rounded-full -z-0" />
        <div className="relative max-w-5xl mx-auto px-6 lg:px-10 pt-20 pb-24 text-center space-y-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-primary/30 bg-primary/5 text-primary text-[11px] uppercase tracking-widest font-bold">
            <Sparkles className="w-3.5 h-3.5" />
            Real-time content intelligence
          </div>
          <h1 className="text-5xl lg:text-7xl font-extrabold tracking-tight leading-[1.05]">
            Your <span className="gradient-text">daily tech brief</span>,
            <br className="hidden md:block" /> personalised to the individual.
          </h1>
          <p className="text-dim text-lg lg:text-xl max-w-2xl mx-auto leading-relaxed">
            CurateAI ingests thousands of articles every day, dedupes the
            noise, and ships two products on top: a persona-aware newsletter
            for every professional, and an SEO intelligence brief for every
            enterprise — all backed by a transparent multi-agent pipeline.
          </p>
          <div className="flex items-center justify-center gap-3 flex-wrap pt-2">
            <Link
              href={primaryCta.href}
              className="px-6 py-3 rounded-2xl bg-primary text-primary-foreground text-sm font-bold hover:bg-primary/90 transition inline-flex items-center gap-2 shadow-2xl shadow-primary/20"
            >
              {primaryCta.label} <ArrowRight className="w-4 h-4" />
            </Link>
            {status !== 'authenticated' && (
              <Link
                href="/login"
                className="px-6 py-3 rounded-2xl border border-white/10 text-sm font-bold hover:border-white/20 transition"
              >
                I already have an account
              </Link>
            )}
          </div>
          <div className="flex items-center justify-center gap-6 text-xs text-dim pt-4 flex-wrap">
            <span className="inline-flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              30+ feeds ingested daily
            </span>
            <span className="inline-flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              Persona-first caching · 98% LLM savings
            </span>
            <span className="inline-flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
              MCP-ready for Claude Desktop
            </span>
          </div>
        </div>
      </section>

      {/* Two product pillars */}
      <section className="max-w-6xl mx-auto px-6 lg:px-10 py-20 grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="glass rounded-[2rem] p-10 border border-white/5 space-y-6 bg-gradient-to-br from-primary/5 to-transparent">
          <div className="flex items-center gap-2 text-primary uppercase tracking-widest text-xs font-black">
            <Mail className="w-4 h-4" /> For consumers
          </div>
          <h2 className="text-3xl font-extrabold leading-tight">
            A newsletter that <em className="not-italic gradient-text">actually</em> knows your role.
          </h2>
          <p className="text-dim leading-relaxed">
            Upload a LinkedIn PDF or hand-pick your interests. Every morning
            we deliver 10 articles chosen by your persona plus the 20
            biggest stories across 30+ feeds — all sourced, all linked,
            every one a click away from the original publisher.
          </p>
          <ul className="space-y-2 text-sm text-dim">
            <Bullet text="Persona-aware ranking — researchers get papers, investors get term sheets" />
            <Bullet text="Feedback loops adjust interest weights as you like / skip" />
            <Bullet text="Delivered to your inbox daily · preview + regenerate from the console" />
          </ul>
          <Link
            href="/signup?role=USER"
            className="inline-flex items-center gap-2 text-sm font-bold text-primary hover:underline"
          >
            Start as a reader <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        <div className="glass rounded-[2rem] p-10 border border-white/5 space-y-6 bg-gradient-to-br from-secondary/5 to-transparent">
          <div className="flex items-center gap-2 text-secondary uppercase tracking-widest text-xs font-black">
            <Rocket className="w-4 h-4" /> For enterprises
          </div>
          <h2 className="text-3xl font-extrabold leading-tight">
            SEO briefs you&apos;d actually ship.
          </h2>
          <p className="text-dim leading-relaxed">
            We score surging entities against your company&apos;s authority
            profile and emit a full content brief — angle, titles, structure,
            keyword coverage, reference sources. Built for content teams who
            want to move from &ldquo;watch trends&rdquo; to &ldquo;ship before the peak&rdquo;.
          </p>
          <ul className="space-y-2 text-sm text-dim">
            <Bullet text="SpaCy NER tracks which brands + products are accelerating today" />
            <Bullet text="4-signal opportunity scoring: Relevance · Velocity · Competition · Brand gap" />
            <Bullet text="Markdown brief with inline citations, delivered in under a minute" />
          </ul>
          <Link
            href="/signup?role=COMPANY"
            className="inline-flex items-center gap-2 text-sm font-bold text-secondary hover:underline"
          >
            Start as a company <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
      </section>

      {/* How it works */}
      <section className="max-w-6xl mx-auto px-6 lg:px-10 py-20 space-y-10">
        <div className="text-center space-y-3 max-w-2xl mx-auto">
          <div className="text-primary uppercase tracking-widest text-xs font-black">
            How it works
          </div>
          <h2 className="text-4xl font-extrabold leading-tight">
            Four layers, one pipeline, one story per click.
          </h2>
          <p className="text-dim text-lg leading-relaxed">
            Our Airflow stack ingests, dedupes, ranks and generates — LangGraph
            agents pick up from there.
          </p>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          <Step icon={Gauge} title="Ingest" copy="30+ RSS feeds, Reddit, Hacker News, ArXiv — 3,000+ articles a day." />
          <Step icon={Brain} title="Dedupe + classify" copy="Sentence-Transformer clustering, hybrid keyword + LLM topic tagging." />
          <Step icon={LineChart} title="Rank + score" copy="Trend detection, velocity, SEO opportunity — all persisted in Snowflake." />
          <Step icon={Wand2} title="Generate + deliver" copy="Multi-agent writer/editor cycle · persona-cached summaries · MailerSend delivery." />
        </div>
      </section>

      {/* CTA strip */}
      <section className="max-w-5xl mx-auto px-6 lg:px-10 py-16">
        <div className="glass rounded-[2.5rem] p-12 border border-white/10 text-center space-y-6 bg-gradient-to-br from-primary/10 via-transparent to-secondary/10">
          <h2 className="text-4xl font-extrabold">Ready to try it on your own feed?</h2>
          <p className="text-dim text-lg max-w-xl mx-auto">
            Free to sign up. One minute to set up a persona. Your first
            newsletter lands before you finish your coffee.
          </p>
          <div className="flex items-center justify-center gap-3 flex-wrap pt-2">
            <Link
              href={primaryCta.href}
              className="px-6 py-3 rounded-2xl bg-primary text-primary-foreground text-sm font-bold hover:bg-primary/90 transition inline-flex items-center gap-2 shadow-2xl shadow-primary/20"
            >
              {primaryCta.label} <ArrowRight className="w-4 h-4" />
            </Link>
            {status !== 'authenticated' && (
              <Link href="/login" className="text-sm font-bold text-dim hover:text-white transition">
                Log in instead
              </Link>
            )}
          </div>
        </div>
      </section>

      <footer className="border-t border-white/5 mt-10">
        <div className="max-w-6xl mx-auto px-6 lg:px-10 py-8 text-xs text-dim flex items-center justify-between flex-wrap gap-4">
          <span>© {new Date().getFullYear()} CurateAI · built for the Big Data & Intelligent Analytics capstone.</span>
          <div className="flex items-center gap-4">
            <Link href="/login" className="hover:text-white transition">Log in</Link>
            <Link href="/signup" className="hover:text-white transition">Sign up</Link>
          </div>
        </div>
      </footer>
    </div>
  );
}

function Bullet({ text }: { text: string }) {
  return (
    <li className="flex items-start gap-2">
      <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
      <span>{text}</span>
    </li>
  );
}

function Step({
  icon: Icon,
  title,
  copy,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  copy: string;
}) {
  return (
    <div className="glass rounded-3xl border border-white/5 p-6 space-y-3 hover:border-white/10 transition">
      <div className="w-10 h-10 rounded-xl bg-primary/10 text-primary flex items-center justify-center">
        <Icon className="w-5 h-5" />
      </div>
      <h3 className="font-bold">{title}</h3>
      <p className="text-sm text-dim leading-relaxed">{copy}</p>
    </div>
  );
}
