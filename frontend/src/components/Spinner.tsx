'use client';

import { Loader2 } from 'lucide-react';

import { cn } from '@/lib/utils';

type SpinnerProps = {
  className?: string;
  size?: 'sm' | 'md' | 'lg';
  label?: string;
};

const SIZE_MAP: Record<NonNullable<SpinnerProps['size']>, string> = {
  sm: 'w-4 h-4',
  md: 'w-6 h-6',
  lg: 'w-10 h-10',
};

/**
 * Inline loading indicator used in place of em-dashes or hardcoded empty
 * states. Always prefer this over a bare "—" while data is in flight.
 */
export function Spinner({ className, size = 'md', label }: SpinnerProps) {
  return (
    <span
      role="status"
      aria-label={label ?? 'Loading'}
      className={cn('inline-flex items-center gap-2 text-dim', className)}
    >
      <Loader2 className={cn(SIZE_MAP[size], 'animate-spin')} />
      {label && <span className="text-sm">{label}</span>}
    </span>
  );
}

/**
 * Block-centered spinner for empty-state regions (lists, tables, cards).
 */
export function SpinnerBlock({ className, label }: { className?: string; label?: string }) {
  return (
    <div
      role="status"
      aria-label={label ?? 'Loading'}
      className={cn('flex flex-col items-center justify-center gap-3 py-8 text-dim', className)}
    >
      <Loader2 className="w-8 h-8 animate-spin" />
      {label && <span className="text-xs uppercase tracking-widest">{label}</span>}
    </div>
  );
}
