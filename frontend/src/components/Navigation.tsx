'use client';

// Sidebar navigation. The link set + header badge are fully driven by the
// authenticated user's role (ADMIN / USER / COMPANY) — no more manual view
// switcher. Onboarding is conditionally disabled for USER accounts whose
// persona already exists, and the newsletter link is only offered once a
// persona is in place.

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Building2,
  ChevronRight,
  LayoutDashboard,
  LogOut,
  Mail,
  Newspaper,
  Settings,
  ShieldCheck,
  TrendingUp,
  Users,
} from 'lucide-react';

import { useAuth } from '@/components/AuthProvider';
import { cn } from '@/lib/utils';

type NavItem = {
  name: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
  // When set, the link is disabled until `enabledWhen` returns true.
  enabledWhen?: (ctx: NavCtx) => boolean;
  hidden?: (ctx: NavCtx) => boolean;
};

type NavCtx = {
  hasPersona: boolean | null;
};

const ADMIN_ITEMS: NavItem[] = [
  { name: 'Admin Console', href: '/admin', icon: ShieldCheck },
  { name: 'Global Trends', href: '/admin/trends', icon: TrendingUp },
  { name: 'Global Archive', href: '/admin/newsletters', icon: Newspaper },
  { name: 'All Users', href: '/admin/users', icon: Users },
  { name: 'All Companies', href: '/admin/companies', icon: Building2 },
];

// Onboarding is NOT in the nav — it's the forced landing page for USERs
// without a persona (see AuthProvider's persona route guard). Once the
// persona is saved, the user is routed to /user and the nav items below
// activate.
const USER_ITEMS: NavItem[] = [
  {
    name: 'My Feed',
    href: '/user',
    icon: Newspaper,
    enabledWhen: (ctx) => ctx.hasPersona === true,
  },
  {
    name: 'Newsletter',
    href: '/newsletter',
    icon: Mail,
    enabledWhen: (ctx) => ctx.hasPersona === true,
  },
  {
    name: 'My Persona',
    href: '/user/persona',
    icon: Settings,
    enabledWhen: (ctx) => ctx.hasPersona === true,
  },
];

const COMPANY_ITEMS: NavItem[] = [
  { name: 'Strategic Drafts', href: '/company/drafts', icon: LayoutDashboard },
  { name: 'Keyword Velocity', href: '/company/trends', icon: TrendingUp },
  { name: 'Company Profile', href: '/company/profile', icon: Settings },
];

export function Navigation() {
  const { user, hasPersona, logout } = useAuth();
  const pathname = usePathname();

  if (!user) return null; // AppShell will render the loading state.

  const items =
    user.role === 'ADMIN' ? ADMIN_ITEMS : user.role === 'COMPANY' ? COMPANY_ITEMS : USER_ITEMS;

  const ctx: NavCtx = { hasPersona };

  const roleBadge =
    user.role === 'ADMIN'
      ? { color: 'bg-amber-400', label: 'ADMIN' }
      : user.role === 'COMPANY'
      ? { color: 'bg-indigo-400', label: 'COMPANY' }
      : { color: 'bg-emerald-400', label: 'USER' };

  return (
    <nav className="fixed left-0 top-0 h-full w-64 glass border-r border-white/5 p-6 space-y-8 z-50 flex flex-col">
      <div className="flex items-center gap-2 mb-2">
        <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center font-black text-xs text-primary-foreground">
          C
        </div>
        <span className="text-xl font-bold tracking-tight gradient-text">CurateAI</span>
      </div>

      {user.role === 'COMPANY' && user.company_name && (
        <div className="glass rounded-xl border border-secondary/20 bg-secondary/[0.04] px-3 py-3 space-y-0.5">
          <div className="text-[10px] font-black uppercase tracking-widest text-secondary">
            Company
          </div>
          <p className="text-sm font-bold truncate text-white">
            {user.company_name}
          </p>
        </div>
      )}

      <div className="glass rounded-xl border border-white/5 px-3 py-3 space-y-1">
        <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-widest">
          <span className={cn('w-2 h-2 rounded-full', roleBadge.color)} />
          <span className="text-muted-foreground">{roleBadge.label}</span>
        </div>
        <p className="text-sm font-bold truncate">{user.full_name || user.email}</p>
        <p className="text-[10px] text-dim truncate">{user.email}</p>
      </div>

      <div className="flex-1 space-y-1 overflow-y-auto">
        <p className="px-3 text-[10px] font-black text-muted-foreground uppercase tracking-widest mb-4">
          Navigation
        </p>
        {items.map((item) => {
          if (item.hidden?.(ctx)) return null;
          const isActive = pathname === item.href;
          const disabled = item.enabledWhen ? !item.enabledWhen(ctx) : false;
          const Icon = item.icon;

          const content = (
            <span
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 group relative',
                disabled
                  ? 'text-muted-foreground/40 cursor-not-allowed'
                  : isActive
                  ? 'text-primary-foreground bg-secondary'
                  : 'text-muted-foreground hover:text-white hover:bg-white/5',
              )}
            >
              <Icon className={cn('w-5 h-5', disabled ? 'opacity-40' : '')} />
              {item.name}
              {isActive && !disabled && <ChevronRight className="w-4 h-4 ml-auto" />}
            </span>
          );

          if (disabled) {
            const tip =
              item.href === '/user/onboarding'
                ? 'Already onboarded — update from My Persona.'
                : 'Finish onboarding to unlock this page.';
            return (
              <div
                key={item.href}
                className="block"
                aria-disabled="true"
                title={tip}
              >
                {content}
              </div>
            );
          }

          return (
            <Link key={item.href} href={item.href} className="block">
              {content}
            </Link>
          );
        })}
      </div>

      <button
        type="button"
        onClick={logout}
        className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-destructive hover:bg-destructive/10 transition-all"
      >
        <LogOut className="w-5 h-5" />
        Log out
      </button>
    </nav>
  );
}
