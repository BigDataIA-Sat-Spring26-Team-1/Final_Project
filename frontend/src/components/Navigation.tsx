'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  Newspaper,
  Settings,
  User,
  TrendingUp,
  Users,
  Building2,
  ShieldCheck,
  LogOut,
  ChevronDown,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'framer-motion';
import { useState, useEffect } from 'react';
import { CompanySwitcher } from '@/components/CompanySwitcher';
import { UserSwitcher } from '@/components/UserSwitcher';

type Role = 'ADMIN' | 'USER' | 'COMPANY';

const NAV_CONFIG = {
  ADMIN: [
    { name: 'Admin Console', href: '/admin', icon: ShieldCheck },
    { name: 'Global Trends', href: '/admin/trends', icon: TrendingUp },
    { name: 'Global Archive', href: '/admin/newsletters', icon: Newspaper },
    { name: 'All Users', href: '/admin/users', icon: Users },
    { name: 'All Companies', href: '/admin/companies', icon: Building2 },
  ],
  USER: [
    { name: 'My Feed', href: '/user', icon: Newspaper },
    { name: 'Onboarding', href: '/user/onboarding', icon: Users },
    { name: 'My Persona', href: '/user/persona', icon: Settings },
  ],
  COMPANY: [
    { name: 'Strategic Drafts', href: '/company/drafts', icon: LayoutDashboard },
    { name: 'Keyword Velocity', href: '/company/trends', icon: TrendingUp },
  ]
};

const USER_KEY = 'curateai:user_id';
const COMPANY_KEY = 'selectedCompanyId';

export function Navigation() {
  const pathname = usePathname();
  const [role, setRole] = useState<Role>('ADMIN');
  const [isRoleMenuOpen, setIsRoleMenuOpen] = useState(false);
  const [hasMounted, setHasMounted] = useState(false);

  // Global active-tenant state. These are the same sessionStorage keys each
  // page already reads, so this sidebar picker stays in sync with the
  // existing per-page switchers without any extra plumbing.
  const [globalUserId, setGlobalUserId] = useState<string | null>(null);
  const [globalCompanyId, setGlobalCompanyId] = useState<string | null>(null);

  // Initialize role + active tenants from browser storage on mount.
  useEffect(() => {
    (async () => {
      setHasMounted(true);
      const savedRole = localStorage.getItem('curateai_role') as Role;
      if (savedRole && (['ADMIN', 'USER', 'COMPANY'] as Role[]).includes(savedRole)) {
        setRole(savedRole);
      }
      if (typeof window !== 'undefined') {
        setGlobalUserId(sessionStorage.getItem(USER_KEY));
        setGlobalCompanyId(sessionStorage.getItem(COMPANY_KEY));
      }
    })();
  }, []);

  // Persist role changes
  const handleRoleChange = (newRole: Role) => {
    setRole(newRole);
    localStorage.setItem('curateai_role', newRole);
    setIsRoleMenuOpen(false);
  };

  const activeNav = NAV_CONFIG[role];

  // Prevent hydration mismatch by not rendering role-dependent UI until mounted
  // In a real app, you might want a localized fallback or skeleton
  if (!hasMounted) {
    return (
      <nav className="fixed left-0 top-0 h-full w-64 glass border-r border-white/5 p-6 space-y-8 z-50 flex flex-col">
        <div className="flex items-center gap-2 mb-4">
          <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center font-black text-xs text-primary-foreground">C</div>
          <span className="text-xl font-bold tracking-tight gradient-text">CurateAI</span>
        </div>
        <div className="flex-1" />
      </nav>
    );
  }

  return (
    <nav className="fixed left-0 top-0 h-full w-64 glass border-r border-white/5 p-6 space-y-8 z-50 flex flex-col">
      <div className="flex items-center gap-2 mb-4">
        <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center font-black text-xs text-primary-foreground">
          C
        </div>
        <span className="text-xl font-bold tracking-tight gradient-text">
          CurateAI
        </span>
      </div>

      {/* Role Switcher (Developer Helper) */}
      <div className="relative mb-6">
        <button 
          onClick={() => setIsRoleMenuOpen(!isRoleMenuOpen)}
          className="w-full flex items-center justify-between px-3 py-2 bg-white/5 border border-white/10 rounded-xl text-xs font-bold text-muted-foreground hover:bg-white/10 transition-all"
        >
          <span className="flex items-center gap-2">
            <div className={cn(
              "w-2 h-2 rounded-full",
              role === 'ADMIN' ? "bg-amber-400" : role === 'USER' ? "bg-emerald-400" : "bg-indigo-400"
            )} />
            {role} VIEW
          </span>
          <ChevronDown className={cn("w-3 h-3 transition-transform", isRoleMenuOpen && "rotate-180")} />
        </button>
        
        <AnimatePresence>
          {isRoleMenuOpen && (
            <motion.div 
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="absolute top-full left-0 right-0 mt-2 bg-card border border-white/10 rounded-xl shadow-2xl overflow-hidden z-50"
            >
              {(['ADMIN', 'USER', 'COMPANY'] as Role[]).map((r) => (
                <button
                  key={r}
                  onClick={() => handleRoleChange(r)}
                  className="w-full text-left px-4 py-2 text-xs font-bold hover:bg-white/5 transition-colors"
                >
                  {r}
                </button>
              ))}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {role === 'USER' && (
        <div className="mb-4 space-y-2">
          <p className="px-1 text-[10px] font-black text-muted-foreground uppercase tracking-widest">
            Active User
          </p>
          <UserSwitcher
            currentUserId={globalUserId}
            onSelect={(id) => {
              setGlobalUserId(id);
              if (typeof window !== 'undefined') sessionStorage.setItem(USER_KEY, id);
            }}
          />
        </div>
      )}

      {role === 'COMPANY' && (
        <div className="mb-4 space-y-2">
          <p className="px-1 text-[10px] font-black text-muted-foreground uppercase tracking-widest">
            Active Company
          </p>
          <CompanySwitcher
            currentCompanyId={globalCompanyId}
            onSelect={(id) => {
              setGlobalCompanyId(id);
              if (typeof window !== 'undefined') sessionStorage.setItem(COMPANY_KEY, id);
            }}
          />
        </div>
      )}

      <div className="flex-1 space-y-1 overflow-y-auto">
        <p className="px-3 text-[10px] font-black text-muted-foreground uppercase tracking-widest mb-4">
          Navigation
        </p>
        {activeNav.map((item) => {
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
                    className="absolute inset-0 bg-secondary rounded-xl z-[-1]"
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
        <p className="px-3 text-[10px] font-black text-muted-foreground uppercase tracking-widest mb-4">
          Session
        </p>
        <Link href="/user/profile" className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-muted-foreground hover:text-white hover:bg-white/5 transition-all">
          <User className="w-5 h-5" />
          General Profile
        </Link>
        <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium text-destructive hover:bg-destructive/10 transition-all">
          <LogOut className="w-5 h-5" />
          Logout
        </button>
      </div>
    </nav>
  );
}
