import type { ReactNode } from 'react';

type BadgeVariant = 'neutral' | 'success' | 'warning' | 'error' | 'accent';

interface StatusBadgeProps {
  variant?: BadgeVariant;
  children: ReactNode;
}

const VARIANT_CLASSES: Record<BadgeVariant, string> = {
  neutral:
    'bg-surface text-ink-secondary border-border',
  success:
    'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border-emerald-500/25',
  warning:
    'bg-amber-500/10 text-amber-700 dark:text-amber-400 border-amber-500/25',
  error:
    'bg-rose-500/10 text-rose-700 dark:text-rose-400 border-rose-500/25',
  accent:
    'bg-accent/10 text-accent border-accent/25',
};

export function StatusBadge({
  variant = 'neutral',
  children,
}: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${VARIANT_CLASSES[variant]}`}
    >
      {children}
    </span>
  );
}
