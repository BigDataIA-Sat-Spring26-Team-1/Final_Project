'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard, 
  Newspaper, 
  Search, 
  Settings, 
  User, 
  TrendingUp, 
  Briefcase
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';

const NAV_ITEMS = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Trending', href: '/trending', icon: TrendingUp },
  { name: 'Newsletter', href: '/newsletter', icon: Newspaper },
  { name: 'SEO Strategy', href: '/seo', icon: Briefcase },
  { name: 'Discovery', href: '/discovery', icon: Search },
];

export function Navigation() {
  const pathname = usePathname();

  return (
    <nav className="fixed left-0 top-0 h-full w-64 glass border-r border-white/5 p-6 space-y-8 z-50 overflow-y-auto">
      <div className="flex items-center gap-2 mb-10">
        <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
          <TrendingUp className="text-primary-foreground w-5 h-5" />
        </div>
        <span className="text-xl font-bold tracking-tight bg-gradient-to-r from-white to-white/60 bg-clip-text text-transparent">
          CurateAI
        </span>
      </div>

      <div className="space-y-1">
        <p className="px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4">
          Intelligence Console
        </p>
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;

          return (
            <Link key={item.href} href={item.href} className="block relative">
              <span className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 group",
                isActive 
                  ? "text-primary-foreground" 
                  : "text-muted-foreground hover:text-white hover:bg-white/5"
              )}>
                {isActive && (
                  <motion.div 
                    layoutId="nav-bg"
                    className="absolute inset-0 bg-primary rounded-xl z-[-1]"
                    transition={{ type: "spring", stiffness: 300, damping: 30 }}
                  />
                )}
                <Icon className={cn(
                  "w-5 h-5",
                  isActive ? "text-primary-foreground" : "text-muted-foreground group-hover:text-white"
                )} />
                {item.name}
              </span>
            </Link>
          );
        })}
      </div>

      <div className="pt-8 space-y-1 border-t border-white/5">
        <p className="px-3 text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4">
          Account
        </p>
        <Link href="/profile" className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-muted-foreground hover:text-white hover:bg-white/5 transition-all">
          <User className="w-5 h-5" />
          Profile
        </Link>
        <Link href="/settings" className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-muted-foreground hover:text-white hover:bg-white/5 transition-all">
          <Settings className="w-5 h-5" />
          Settings
        </Link>
      </div>

      <div className="absolute bottom-6 left-6 right-6">
        <div className="p-4 rounded-2xl bg-gradient-to-br from-primary/20 to-transparent border border-primary/20">
          <p className="text-xs font-medium text-primary mb-1">PRO PLAN</p>
          <p className="text-sm font-semibold text-white mb-3">Upgrade for more agents</p>
          <div className="w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
            <div className="w-3/4 h-full bg-primary" />
          </div>
          <p className="text-[10px] text-muted-foreground mt-2">75% of monthly tokens used</p>
        </div>
      </div>
    </nav>
  );
}
