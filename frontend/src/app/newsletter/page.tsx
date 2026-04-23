'use client';

// Newsletter page. Auto-renders the exact email HTML the user will receive,
// fetched on the fly from /newsletter/preview. A single "Send to my inbox"
// button dispatches via MailerSend; the backend guarantees idempotency per
// (user_id, edition_date), and the UI reflects `sent_at` so the button
// disables once today's copy has been delivered.

import { Calendar, CheckCircle2, Loader2, Mail, Send, TriangleAlert } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';

import { PageWrapper } from '@/components/PageWrapper';
import { useAuth } from '@/components/AuthProvider';
import {
  ApiError,
  previewNewsletterEmail,
  sendNewsletterEmail,
  type NewsletterPreviewResponse,
  type NewsletterSendResponse,
} from '@/lib/api';

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export default function NewsletterPage() {
  const { user } = useAuth();
  const userId = user?.id ?? '';

  const [preview, setPreview] = useState<NewsletterPreviewResponse | null>(null);
  const [editionDate, setEditionDate] = useState<string>(todayIso());
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const iframeRef = useRef<HTMLIFrameElement | null>(null);

  const loadPreview = useCallback(
    async (id: string, date: string, signal?: AbortSignal) => {
      setLoading(true);
      setError(null);
      setPreview(null);
      try {
        const res = await previewNewsletterEmail(id, date, signal);
        setPreview(res);
      } catch (err) {
        if ((err as Error).name === 'AbortError') return;
        setError(
          err instanceof ApiError
            ? err.status === 404
              ? `No newsletter available for ${date}.`
              : `${err.status}: ${err.detail ?? err.message}`
            : (err as Error).message,
        );
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    if (!userId) return;
    const controller = new AbortController();
    loadPreview(userId, editionDate, controller.signal);
    return () => controller.abort();
  }, [userId, editionDate, loadPreview]);

  // Inject the email HTML into an iframe so its inline styles don't bleed
  // into the site's dark chrome (and vice versa).
  useEffect(() => {
    if (!preview || !iframeRef.current) return;
    const doc = iframeRef.current.contentDocument;
    if (!doc) return;
    doc.open();
    doc.write(preview.html_content);
    doc.close();
  }, [preview]);

  const isToday = editionDate === todayIso();
  const alreadySent = Boolean(preview?.already_sent);
  // Only allow sending when viewing today — historical editions were already delivered on their date.
  const sendDisabled = sending || loading || !preview || alreadySent || !isToday;

  const handleSend = async () => {
    if (!userId || !preview || alreadySent) return;
    setSending(true);
    setError(null);
    setNotice(null);
    try {
      const res: NewsletterSendResponse = await sendNewsletterEmail(
        userId,
        preview.edition_date,
      );
      // Fall through to result handling below; preview is reloaded for the
      // current edition date to refresh sent_at / already_sent.
      if (res.status === 'SENT') {
        setNotice(`Newsletter sent to ${res.recipient ?? 'your inbox'}.`);
      } else if (res.status === 'ALREADY_SENT') {
        setNotice("Today's newsletter was already delivered.");
      } else if (res.status === 'MAILER_DISABLED') {
        setError('Email delivery is not configured on this environment.');
      } else if (res.status === 'NO_RECIPIENT') {
        setError('No email address is on file for your account.');
      } else if (res.status === 'FAILED') {
        setError(res.detail || 'Email delivery failed.');
      } else {
        setNotice(res.detail || `Status: ${res.status}`);
      }
      // Re-pull preview so `already_sent` and `sent_at` reflect the new row.
      await loadPreview(userId, editionDate);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? `${err.status}: ${err.detail ?? err.message}`
          : (err as Error).message,
      );
    } finally {
      setSending(false);
    }
  };

  return (
    <PageWrapper>
      <div className="space-y-10">
        <header className="flex items-end justify-between gap-6 flex-wrap">
          <div className="space-y-2">
            <h1 className="text-4xl font-bold tracking-tight">
              {isToday ? "Today's Newsletter" : 'Newsletter Archive'}
            </h1>
            <p className="text-muted-foreground text-lg">
              {isToday
                ? `This is exactly what will land in your inbox for ${editionDate}.`
                : `Newsletter delivered on ${editionDate}.`}
            </p>
            {preview?.sent_at && (
              <p className="text-xs text-emerald-400 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Sent · {new Date(preview.sent_at).toLocaleString()}
                {preview.recipient ? ` · ${preview.recipient}` : ''}
              </p>
            )}
          </div>
          <div className="flex items-end gap-3 flex-wrap">
            <label className="flex items-center glass rounded-xl px-4 py-2 border border-white/5 focus-within:border-primary/40 gap-2">
              <Calendar className="w-4 h-4 text-dim" />
              <input
                type="date"
                value={editionDate}
                max={todayIso()}
                onChange={(e) => setEditionDate(e.target.value || todayIso())}
                className="bg-transparent border-none outline-none text-sm text-white placeholder:text-dim"
              />
            </label>
            <button
              type="button"
              onClick={handleSend}
              disabled={sendDisabled}
              title={
                !isToday
                  ? 'Viewing a past edition — sending is only available for today.'
                  : alreadySent
                  ? "You've already been emailed today's newsletter."
                  : undefined
              }
              className="flex items-center gap-2 bg-primary hover:bg-primary/90 disabled:opacity-40 disabled:cursor-not-allowed text-primary-foreground px-6 py-3 rounded-2xl text-sm font-bold transition-all shadow-lg shadow-primary/20"
            >
              {sending ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" /> Sending…
                </>
              ) : !isToday ? (
                <>
                  <Mail className="w-5 h-5" /> Archive View
                </>
              ) : alreadySent ? (
                <>
                  <Mail className="w-5 h-5" /> Already Sent Today
                </>
              ) : (
                <>
                  <Send className="w-5 h-5" /> Send to My Inbox
                </>
              )}
            </button>
          </div>
        </header>

        {notice && (
          <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-4 text-sm text-emerald-200 flex items-start gap-2">
            <CheckCircle2 className="w-4 h-4 mt-0.5 shrink-0" />
            <span>{notice}</span>
          </div>
        )}

        {error && (
          <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-6 flex items-start gap-3">
            <TriangleAlert className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
            <p className="text-sm text-rose-200">{error}</p>
          </div>
        )}

        {loading ? (
          <div className="glass rounded-3xl p-10 border border-dashed border-white/20 text-center space-y-4">
            <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto" />
            <p className="text-dim">Rendering your email preview…</p>
          </div>
        ) : preview ? (
          <div className="glass rounded-3xl p-6 border border-white/5 space-y-4">
            <div className="flex items-center justify-between flex-wrap gap-3 px-2">
              <div className="flex items-center gap-2 text-sm font-bold">
                <Mail className="w-4 h-4 text-primary" />
                Email Preview
              </div>
              <div className="text-[10px] font-mono uppercase tracking-widest text-dim flex items-center gap-3">
                <span>{preview.personal_count} personal</span>
                <span>·</span>
                <span>{preview.common_count} trending</span>
                <span>·</span>
                <span>{preview.edition_date}</span>
              </div>
            </div>
            <iframe
              ref={iframeRef}
              title="Newsletter email preview"
              className="w-full rounded-2xl border border-white/10 bg-slate-900"
              style={{ height: '75vh' }}
            />
          </div>
        ) : (
          <div className="glass rounded-3xl p-10 border border-dashed border-white/20 text-center">
            <p className="text-dim">No preview available.</p>
          </div>
        )}
      </div>
    </PageWrapper>
  );
}
