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
  getCurrentUser,
  loginAccount,
  setAuthToken,
  signupAccount,
  type AuthEnvelope,
  type AuthUser,
  type SignupPayload,
} from '@/lib/api';

export const PUBLIC_PATHS = new Set<string>(['/', '/login', '/signup']);

type AuthStatus = 'loading' | 'authenticated' | 'anonymous';

interface AuthContextValue {
  status: AuthStatus;
  user: AuthUser | null;
  login: (email: string, password: string) => Promise<AuthUser>;
  signup: (payload: SignupPayload) => Promise<AuthUser>;
  logout: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [status, setStatus] = useState<AuthStatus>('loading');
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

  // Route guard: anonymous visitors to protected pages bounce to /login.
  // Authenticated visitors to /login or /signup bounce back to their home.
  useEffect(() => {
    if (status === 'loading') return;
    const isPublic = PUBLIC_PATHS.has(pathname);
    if (status === 'anonymous' && !isPublic) {
      router.replace('/login');
      return;
    }
    if (status === 'authenticated' && (pathname === '/login' || pathname === '/signup')) {
      router.replace(homeForRole(user?.role));
    }
  }, [pathname, router, status, user?.role]);

  const value = useMemo<AuthContextValue>(
    () => ({ status, user, login, signup, logout, refresh }),
    [status, user, login, signup, logout, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
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
