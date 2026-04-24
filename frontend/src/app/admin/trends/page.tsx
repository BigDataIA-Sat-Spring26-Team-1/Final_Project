'use client';

// Admin-facing Global Trends has been folded into the B2B keyword-velocity
// view so ops + admins see the same SpaCy NER signal the company console
// uses. Re-exports the company/trends page component directly to keep a
// single source of truth — avoids two drifting copies of the same UI.

export { default } from '@/app/company/trends/page';
