// Tiny sessionStorage-backed cache for B2B reports.
//
// The B2B agent is slow (LangGraph → LLM → Markdown) and returns one blob of
// Markdown per corporate client. We generate once on /company/drafts or /seo
// and let every other B2B page read the same cached payload, so users don't
// pay the latency twice when navigating between tabs.

import type { B2BReportResponse } from '@/lib/api';

const VERSION = 'v1';
const PREFIX = `curateai:b2b:${VERSION}:`;
const COMPANY_ID_KEY = 'curateai:b2b:company_id';

type Entry = {
  generated_at: number;
  payload: B2BReportResponse;
};

function storage(): Storage | null {
  if (typeof window === 'undefined') return null;
  try {
    return window.sessionStorage;
  } catch {
    // Safari private mode can throw when accessing storage.
    return null;
  }
}

export function saveReport(companyId: string, payload: B2BReportResponse): void {
  const s = storage();
  if (!s) return;
  const entry: Entry = { generated_at: Date.now(), payload };
  try {
    s.setItem(`${PREFIX}${companyId}`, JSON.stringify(entry));
    s.setItem(COMPANY_ID_KEY, companyId);
  } catch {
    // QuotaExceededError → cache miss on next read; that's acceptable.
  }
}

export function loadReport(companyId: string): { generated_at: number; payload: B2BReportResponse } | null {
  const s = storage();
  if (!s) return null;
  const raw = s.getItem(`${PREFIX}${companyId}`);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Entry;
  } catch {
    return null;
  }
}

export function getLastCompanyId(): string {
  return storage()?.getItem(COMPANY_ID_KEY) ?? '';
}

export function setLastCompanyId(companyId: string): void {
  if (!companyId) return;
  storage()?.setItem(COMPANY_ID_KEY, companyId);
}
