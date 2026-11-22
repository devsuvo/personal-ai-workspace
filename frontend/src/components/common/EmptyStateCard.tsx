import type { LucideIcon } from 'lucide-react';
import type { ReactNode } from 'react';
import { StatusBadge } from './StatusBadge';

interface EmptyStateCardProps {
  icon: LucideIcon;
  title: string;
  description: string;
  phaseLabel?: string;
  action?: ReactNode;
}

export function EmptyStateCard({
  icon: Icon,
  title,
  description,
  phaseLabel,
  action,
}: EmptyStateCardProps) {
  return (
    <div className="rounded-2xl border border-border bg-surface-elevated p-8 text-center">
      <div className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-xl border border-border bg-surface text-ink-secondary">
        <Icon className="h-5 w-5" />
      </div>
      {phaseLabel && (
        <div className="mb-3 flex justify-center">
          <StatusBadge variant="neutral">{phaseLabel}</StatusBadge>
        </div>
      )}
      <h2 className="text-lg font-semibold text-ink-primary">{title}</h2>
      <p className="mx-auto mt-2 max-w-md text-sm leading-relaxed text-ink-secondary">
        {description}
      </p>
      {action && <div className="mt-6 flex justify-center">{action}</div>}
    </div>
  );
}
