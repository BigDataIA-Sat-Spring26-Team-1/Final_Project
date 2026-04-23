'use client';

// /login — minimal email + password form. Errors returned by the backend
// are surfaced inline; the 404 / 401 distinction is preserved so the user
// can tell "I typed the wrong email" from "my password is wrong".

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState, type FormEvent } from 'react';

import { formatAuthError, homeForRole, useAuth } from '@/components/AuthProvider';
import { Loader2, LogIn } from 'lucide-react';

const EMAIL_RE = /^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$/;

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!EMAIL_RE.test(email)) {
      setError('Enter a valid email address.');
      return;
    }
    if (password.length < 1) {
      setError('Password is required.');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const user = await login(email, password);
      router.replace(homeForRole(user.role));
    } catch (err) {
      setError(formatAuthError(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-6 py-12 bg-background">
      <div className="w-full max-w-md space-y-8">
        <Link href="/" className="flex items-center justify-center gap-2 group">
          <div className="w-9 h-9 rounded-xl bg-primary flex items-center justify-center font-black text-sm text-primary-foreground">
            C
          </div>
          <span className="text-2xl font-bold tracking-tight gradient-text group-hover:opacity-80 transition">
            CurateAI
          </span>
        </Link>

        <div className="glass rounded-3xl p-8 border border-white/5 space-y-6">
          <div className="space-y-2 text-center">
            <h1 className="text-2xl font-extrabold tracking-tight">Welcome back.</h1>
            <p className="text-sm text-dim">
              Sign in to your CurateAI console.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <label className="block space-y-1.5">
              <span className="text-[10px] font-black uppercase tracking-widest text-dim">Email</span>
              <input
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                className="w-full rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm outline-none focus:border-primary/40"
              />
            </label>
            <label className="block space-y-1.5">
              <span className="text-[10px] font-black uppercase tracking-widest text-dim">Password</span>
              <input
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full rounded-xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm outline-none focus:border-primary/40"
              />
            </label>

            {error && (
              <div className="rounded-xl border border-rose-500/20 bg-rose-500/5 px-4 py-3 text-sm text-rose-200">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="w-full flex items-center justify-center gap-2 bg-primary hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed text-primary-foreground px-4 py-3 rounded-xl text-sm font-bold transition"
            >
              {submitting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <LogIn className="w-4 h-4" />
              )}
              {submitting ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <p className="text-xs text-dim text-center">
            New here?{' '}
            <Link href="/signup" className="text-primary font-bold hover:underline">
              Create an account
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
