'use client';

// AuthProvider — owns the authenticated-user state for the whole app.
//
// On mount we try to fetch the current user from the backend via the stored
// JWT. If the token is missing or the backend responds 401, the context
// resolves to `user = null`, which downstream route guards use to redirect
// unauthenticated visitors to /login. Login / signup / logout helpers all
// flow through here so every page stays in sync without prop drilling.

import { usePathname, useRouter } from 'next/navigation';
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';

import {
  ApiError,
  clearAuthToken,
  getAuthToken,
  getCompanyProfile,
  getCurrentUser,
  getPersona,
  loginAccount,
  setAuthToken,
  signupAccount,
  type AuthEnvelope,
  type AuthUser,
  type SignupPayload,
} from '@/lib/api';

// Fields a COMPANY tenant must fill in before the app lets them past the
// profile page. Aligned with the backend's 10-field profile schema; any
// NULL / empty value here forces the COMPANY user back to /company/profile.
const REQUIRED_COMPANY_FIELDS = [
  'name',
  'domain',
  'industry',
  'description',
  'company_size',
  'target_audience',
  'key_products',
  'content_pillars',
  'competitors',
  'tone_of_voice',
] as const;

function isCompanyProfileComplete(profile: Record<string, unknown> | null): boolean {
  if (!profile) return false;
  return REQUIRED_COMPANY_FIELDS.every((key) => {
    const v = profile[key];
    if (v === null || v === undefined) return false;
    if (typeof v === 'string') return v.trim().length > 0;
    if (Array.isArray(v)) return v.length > 0;
    return true;
  });
}

export const PUBLIC_PATHS = new Set<string>(['/', '/login', '/signup']);

type AuthStatus = 'loading' | 'authenticated' | 'anonymous';

interface AuthContextValue {
  status: AuthStatus;
  user: AuthUser | null;
  /**
   * True once `/personas/{user_id}` has resolved for a USER role.
   * `null` while the probe is in flight or role isn't USER. Used by the
   * onboarding-flow route guard below: USER with `hasPersona === false`
   * is forced through `/user/onboarding` on every navigation.
   */
  hasPersona: boolean | null;
  /** Mirror of `hasPersona` for COMPANY tenants: are all profile fields filled? */
  hasCompanyProfile: boolean | null;
  login: (email: string, password: string) => Promise<AuthUser>;
  signup: (payload: SignupPayload) => Promise<AuthUser>;
  logout: () => void;
  refresh: () => Promise<void>;
  /** Called by the onboarding page after persona is successfully persisted. */
  markPersonaPresent: () => void;
  /** Called by the profile page after the required fields are filled in. */
  markCompanyProfileComplete: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [status, setStatus] = useState<AuthStatus>('loading');
  const [hasPersona, setHasPersona] = useState<boolean | null>(null);
  const [hasCompanyProfile, setHasCompanyProfile] = useState<boolean | null>(null);
  const router = useRouter();
  const pathname = usePathname();

  // Initial hydration: if there's a token, ask the backend who owns it.
  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      const token = getAuthToken();
      if (!token) {
        setStatus('anonymous');
        return;
      }
      try {
        const me = await getCurrentUser(controller.signal);
        setUser(me);
        setStatus('authenticated');
      } catch (err) {
        if ((err as Error).name === 'AbortError') return;
        // 401 → api.ts already cleared the token.
        clearAuthToken();
        setUser(null);
        setStatus('anonymous');
      }
    })();
    return () => controller.abort();
  }, []);

  const persistEnvelope = useCallback((env: AuthEnvelope) => {
    setAuthToken(env.access_token);
    setUser(env.user);
    setStatus('authenticated');
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      const env = await loginAccount(email.trim(), password);
      persistEnvelope(env);
      return env.user;
    },
    [persistEnvelope],
  );

  const signup = useCallback(
    async (payload: SignupPayload) => {
      const env = await signupAccount(payload);
      persistEnvelope(env);
      return env.user;
    },
    [persistEnvelope],
  );

  const logout = useCallback(() => {
    clearAuthToken();
    setUser(null);
    setStatus('anonymous');
    router.push('/login');
  }, [router]);

  const refresh = useCallback(async () => {
    try {
      const me = await getCurrentUser();
      setUser(me);
      setStatus('authenticated');
    } catch {
      clearAuthToken();
      setUser(null);
      setStatus('anonymous');
    }
  }, []);

  // Probe /personas/{id} when a USER authenticates so we know whether
  // to force them through onboarding. Non-USER roles don't have a
  // persona concept. State mutations live inside the async callback
  // (not the effect body) so the react-hooks/set-state-in-effect rule
  // stays happy.
  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      if (status !== 'authenticated' || !user || user.role !== 'USER') {
        setHasPersona(null);
        return;
      }
      try {
        await getPersona(user.id, controller.signal);
        if (!controller.signal.aborted) setHasPersona(true);
      } catch (err) {
        if ((err as Error).name === 'AbortError') return;
        // Fail closed: any non-200 response — 404, 500, network blip —
        // treats the user as not-yet-onboarded. We'd rather over-prompt
        // onboarding than silently let a persona-less USER into the app.
        setHasPersona(false);
      }
    })();
    return () => controller.abort();
  }, [status, user]);

  // Same probe for COMPANY tenants — do they have a fully filled profile?
  // Incomplete profiles get pinned to /company/profile. Fail-closed on
  // errors so a transient outage can't let a half-onboarded tenant drift
  // into the briefs/drafts surfaces.
  useEffect(() => {
    const controller = new AbortController();
    (async () => {
      if (status !== 'authenticated' || !user || user.role !== 'COMPANY') {
        setHasCompanyProfile(null);
        return;
      }
      try {
        const profile = await getCompanyProfile(user.id, controller.signal);
        if (controller.signal.aborted) return;
        setHasCompanyProfile(
          isCompanyProfileComplete(profile as unknown as Record<string, unknown>),
        );
      } catch (err) {
        if ((err as Error).name === 'AbortError') return;
        setHasCompanyProfile(false);
      }
    })();
    return () => controller.abort();
  }, [status, user]);

  const markPersonaPresent = useCallback(() => {
    setHasPersona(true);
  }, []);
  const markCompanyProfileComplete = useCallback(() => {
    setHasCompanyProfile(true);
  }, []);

  // Route guard:
  //   - anonymous → /login
  //   - authenticated USER without persona → /user/onboarding (forced)
  //   - authenticated COMPANY without full profile → /company/profile (forced)
  //   - authenticated on /login or /signup → role home
  useEffect(() => {
    if (status === 'loading') return;
    const isPublic = PUBLIC_PATHS.has(pathname);
    if (status === 'anonymous' && !isPublic) {
      router.replace('/login');
      return;
    }
    if (status === 'authenticated' && (pathname === '/login' || pathname === '/signup')) {
      router.replace(homeForRole(user?.role));
      return;
    }
    if (
      status === 'authenticated'
      && user?.role === 'USER'
      && hasPersona === false
      && pathname !== '/user/onboarding'
    ) {
      router.replace('/user/onboarding');
      return;
    }
    if (
      status === 'authenticated'
      && user?.role === 'COMPANY'
      && hasCompanyProfile === false
      && pathname !== '/company/profile'
    ) {
      router.replace('/company/profile');
    }
  }, [pathname, router, status, user?.role, hasPersona, hasCompanyProfile]);

  // Block-rendering gate — while the persona / profile probe is in flight,
  // render a holding screen instead of the destination page. Without this
  // the destination flashes for a frame before the redirect effect above
  // fires, which is enough to leak the feed or drafts UI to a not-yet-
  // onboarded tenant.
  const isPublic = PUBLIC_PATHS.has(pathname);
  const onOnboardingPath =
    (user?.role === 'USER' && pathname === '/user/onboarding')
    || (user?.role === 'COMPANY' && pathname === '/company/profile');
  const waitingForUserGate =
    status === 'authenticated' && user?.role === 'USER' && hasPersona === null;
  const waitingForCompanyGate =
    status === 'authenticated' && user?.role === 'COMPANY' && hasCompanyProfile === null;
  const shouldBlock =
    !isPublic && !onOnboardingPath && (status === 'loading' || waitingForUserGate || waitingForCompanyGate);

  const value = useMemo<AuthContextValue>(
    () => ({
      status,
      user,
      hasPersona,
      hasCompanyProfile,
      login,
      signup,
      logout,
      refresh,
      markPersonaPresent,
      markCompanyProfileComplete,
    }),
    [
      status,
      user,
      hasPersona,
      hasCompanyProfile,
      login,
      signup,
      logout,
      refresh,
      markPersonaPresent,
      markCompanyProfileComplete,
    ],
  );

  return (
    <AuthContext.Provider value={value}>
      {shouldBlock ? <AuthGateFallback /> : children}
    </AuthContext.Provider>
  );
}

function AuthGateFallback() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 text-slate-400 text-sm">
      Loading your workspace…
    </div>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used inside <AuthProvider>.');
  }
  return ctx;
}

/** The default landing page for each role right after login/signup. */
export function homeForRole(role: AuthUser['role'] | undefined): string {
  switch (role) {
    case 'ADMIN':
      return '/admin';
    case 'COMPANY':
      return '/company/drafts';
    case 'USER':
      return '/user';
    default:
      return '/login';
  }
}

/** Maps an ApiError to a UI-friendly error string. */
export function formatAuthError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 404) return err.detail ?? 'No account with this email.';
    if (err.status === 401) return err.detail ?? 'Incorrect password.';
    if (err.status === 409) return err.detail ?? 'An account with that email already exists.';
    if (err.status === 422) return err.detail ?? 'Double-check your inputs.';
    return err.detail ?? err.message;
  }
  return err instanceof Error ? err.message : 'Something went wrong.';
}
