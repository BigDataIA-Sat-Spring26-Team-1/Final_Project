'use client';

// /signup — collects either a USER or a COMPANY account in one form.
// The backend's /auth/signup endpoint enforces the same validation shape
// (email regex, password min length + character classes, company name
// required when role=COMPANY), but we still duplicate the checks client-
// side so the form never round-trips for obvious problems.

import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense, useEffect, useState, type FormEvent } from 'react';

import { formatAuthError, homeForRole, useAuth } from '@/components/AuthProvider';
import { Loader2, UserPlus } from 'lucide-react';

const EMAIL_RE = /^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$/;

function SignupBody() {
  const { signup } = useAuth();
  const router = useRouter();
  const params = useSearchParams();

  const [role, setRole] = useState<'USER' | 'COMPANY'>('USER');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [companyName, setCompanyName] = useState('');
  const [companyDomain, setCompanyDomain] = useState('');
  const [companyIndustry, setCompanyIndustry] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // The landing page's two pillars deep-link with ?role=USER / COMPANY.
  useEffect(() => {
    const requested = params.get('role');
    if (requested === 'COMPANY' || requested === 'USER') setRole(requested);
  }, [params]);

  const validate = (): string | null => {
    if (fullName.trim().length < 1) return 'Full name is required.';
    if (!EMAIL_RE.test(email)) return 'Enter a valid email address.';
    if (password.length < 8) return 'Password must be at least 8 characters.';
    if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) {
      return 'Password must include at least one letter and one digit.';
    }
    if (password !== confirmPassword) return "Passwords don't match.";
    if (role === 'COMPANY' && companyName.trim().length < 1) {
      return 'Company name is required for a company account.';
    }
    return null;
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const problem = validate();
    if (problem) {
      setError(problem);
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const user = await signup({
        email: email.trim(),
        password,
        full_name: fullName.trim(),
        role,
        ...(role === 'COMPANY'
          ? {
              company_name: companyName.trim(),
              company_domain: companyDomain.trim() || undefined,
              company_industry: companyIndustry.trim() || undefined,
            }
          : {}),
      });
      // New USER → bounce to onboarding; new COMPANY → the company profile
      // page where they can fill in description / authority details.
      if (user.role === 'USER') {
        router.replace('/user/onboarding');
      } else if (user.role === 'COMPANY') {
        router.replace('/company/profile');
      } else {
        router.replace(homeForRole(user.role));
      }
    } catch (err) {
      setError(formatAuthError(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-6 py-12 bg-background">
      <div className="w-full max-w-xl space-y-8">
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
            <h1 className="text-2xl font-extrabold tracking-tight">Create your account.</h1>
            <p className="text-sm text-dim">
              Pick the account that fits — you can&apos;t switch later.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <RoleToggle
              label="Reader"
              detail="Personalized newsletters"
              active={role === 'USER'}
              onClick={() => setRole('USER')}
            />
            <RoleToggle
              label="Company"
              detail="SEO briefs + trends"
              active={role === 'COMPANY'}
              onClick={() => setRole('COMPANY')}
            />
          </div>

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <Field label="Full name">
              <input
                type="text"
                autoComplete="name"
                required
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                placeholder="Ada Lovelace"
                className="input"
              />
            </Field>
            <Field label="Email">
              <input
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@company.com"
                className="input"
              />
            </Field>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Field label="Password">
                <input
                  type="password"
                  autoComplete="new-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="8+ chars · 1 letter · 1 digit"
                  className="input"
                />
              </Field>
              <Field label="Confirm password">
                <input
                  type="password"
                  autoComplete="new-password"
                  required
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  placeholder="retype password"
                  className="input"
                />
              </Field>
            </div>

            {role === 'COMPANY' && (
              <div className="space-y-4 pt-2 border-t border-white/5">
                <Field label="Company name">
                  <input
                    type="text"
                    required
                    value={companyName}
                    onChange={(e) => setCompanyName(e.target.value)}
                    placeholder="Acme Corp"
                    className="input"
                  />
                </Field>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <Field label="Domain (optional)">
                    <input
                      type="text"
                      value={companyDomain}
                      onChange={(e) => setCompanyDomain(e.target.value)}
                      placeholder="acme.com"
                      className="input"
                    />
                  </Field>
                  <Field label="Industry (optional)">
                    <input
                      type="text"
                      value={companyIndustry}
                      onChange={(e) => setCompanyIndustry(e.target.value)}
                      placeholder="SaaS, Fintech, etc."
                      className="input"
                    />
                  </Field>
                </div>
              </div>
            )}

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
              {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <UserPlus className="w-4 h-4" />}
              {submitting ? 'Creating account…' : 'Create account'}
            </button>
          </form>

          <p className="text-xs text-dim text-center">
            Already have an account?{' '}
            <Link href="/login" className="text-primary font-bold hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>

      <style jsx>{`
        .input {
          width: 100%;
          border-radius: 0.75rem;
          border: 1px solid rgba(255, 255, 255, 0.1);
          background: rgba(255, 255, 255, 0.03);
          padding: 0.75rem 1rem;
          font-size: 0.875rem;
          outline: none;
          color: inherit;
        }
        .input:focus {
          border-color: rgba(99, 102, 241, 0.4);
        }
      `}</style>
    </div>
  );
}

function RoleToggle({
  label,
  detail,
  active,
  onClick,
}: {
  label: string;
  detail: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`rounded-xl border p-3 text-left transition-all ${
        active
          ? 'border-primary/40 bg-primary/5 text-white'
          : 'border-white/10 bg-white/[0.02] text-dim hover:border-white/20 hover:text-white'
      }`}
    >
      <p className="text-sm font-bold">{label}</p>
      <p className="text-[10px] text-muted-foreground">{detail}</p>
    </button>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block space-y-1.5">
      <span className="text-[10px] font-black uppercase tracking-widest text-dim">{label}</span>
      {children}
    </label>
  );
}

export default function SignupPage() {
  return (
    <Suspense fallback={<div className="min-h-screen" />}>
      <SignupBody />
    </Suspense>
  );
}
