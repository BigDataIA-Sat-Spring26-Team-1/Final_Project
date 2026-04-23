'use client';

// Thin layout switcher that chooses between the public "marketing" chrome
// (no sidebar, no padding) and the authenticated app chrome (fixed left
// nav, padded main column). Keeping this decision out of the server layout
// means the Navigation component — which reads persona state from the
// backend — never renders on the landing page and never triggers a 401
// for anonymous visitors.
//
// Role-scoped access is enforced here too: a USER visiting /admin/* or
// /company/* is bounced back to their own home, same for each role. This
// is belt-and-braces; the backend endpoints are also role-gated.

import { usePathname, useRouter } from 'next/navigation';
import { useEffect, type ReactNode } from 'react';

import { Navigation } from '@/components/Navigation';
import {
  PUBLIC_PATHS,
  homeForRole,
  useAuth,
} from '@/components/AuthProvider';
import type { AuthRole } from '@/lib/api';

// Which path prefixes each role is allowed to visit. Anything outside this
// list for the active role triggers a redirect to their home page.
const ROLE_ALLOWED_PREFIXES: Record<AuthRole, string[]> = {
  ADMIN: ['/admin', '/user', '/company', '/newsletter'],
  USER: ['/user', '/newsletter'],
  COMPANY: ['/company'],
};

function isPathAllowed(role: AuthRole, path: string): boolean {
  return ROLE_ALLOWED_PREFIXES[role].some((prefix) => path === prefix || path.startsWith(prefix + '/'));
}

export function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { status, user } = useAuth();

  // Belt-and-braces access control — if an authenticated user somehow lands
  // on a page outside their role's allow-list, bounce them back home.
  useEffect(() => {
    if (status !== 'authenticated' || !user) return;
    if (PUBLIC_PATHS.has(pathname)) return;
    if (!isPathAllowed(user.role, pathname)) {
      router.replace(homeForRole(user.role));
    }
  }, [pathname, router, status, user]);

  // Public pages render edge-to-edge with no sidebar.
  if (PUBLIC_PATHS.has(pathname)) {
    return <main className="min-h-screen">{children}</main>;
  }

  // While we're hydrating the session we intentionally show nothing to
  // avoid a 1-frame flash of the authenticated chrome before the
  // AuthProvider redirects anon visitors.
  if (status === 'loading') {
    return (
      <main className="min-h-screen flex items-center justify-center text-dim text-sm">
        Loading…
      </main>
    );
  }

  // Anonymous visitors hitting a protected route see nothing while the
  // AuthProvider effect kicks them to /login.
  if (status === 'anonymous') {
    return <main className="min-h-screen" />;
  }

  // Authenticated but currently being redirected because of a role
  // violation — render a neutral frame while the router catches up.
  if (user && !isPathAllowed(user.role, pathname)) {
    return <main className="min-h-screen" />;
  }

  return (
    <>
      <Navigation />
      <main className="pl-64 min-h-screen">
        <div className="max-w-[1600px] mx-auto p-8 lg:p-12">{children}</div>
      </main>
    </>
  );
}
