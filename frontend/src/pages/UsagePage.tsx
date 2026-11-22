import {
  BarChart3,
  DollarSign,
  Plus,
  RefreshCw,
  Trash2,
} from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import {
  deleteModelPricing,
  fetchAnalyticsOverview,
  fetchModelPricing,
  upsertModelPricing,
  type AnalyticsOverview,
  type ModelPricing,
  type PeriodUsagePoint,
} from '../services/productivityService';

function BarChart({
  points,
  metric,
}: {
  points: PeriodUsagePoint[];
  metric: 'requests' | 'total_tokens';
}) {
  if (points.length === 0) {
    return (
      <div className="flex h-44 items-center justify-center text-xs text-ink-muted">
        No usage recorded in this period yet.
      </div>
    );
  }

  const maxVal = Math.max(...points.map((p) => p[metric]), 1);

  return (
    <div className="flex h-48 items-end gap-2 overflow-x-auto pt-6 pb-2">
      {points.map((p) => {
        const val = p[metric];
        const heightPct = Math.max((val / maxVal) * 100, val > 0 ? 6 : 2);
        return (
          <div
            key={p.period}
            className="group flex min-w-[36px] flex-1 flex-col items-center gap-1.5"
            title={`${p.period}: ${p.requests} requests, ${p.total_tokens.toLocaleString()} tokens`}
          >
            <div className="text-[10px] font-medium text-ink-muted opacity-0 transition-opacity group-hover:opacity-100">
              {val.toLocaleString()}
            </div>
            <div className="flex h-32 w-full items-end justify-center">
              <div
                style={{ height: `${heightPct}%` }}
                className="w-full max-w-[32px] rounded-t-lg bg-accent/80 transition-all group-hover:bg-accent"
              />
            </div>
            <div className="truncate text-[10px] text-ink-muted">
              {p.period.slice(-5)}
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function UsagePage() {
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [pricing, setPricing] = useState<ModelPricing[]>([]);
  const [loading, setLoading] = useState(true);
  const [chartMode, setChartMode] = useState<'daily' | 'monthly'>('daily');
  const [metric, setMetric] = useState<'requests' | 'total_tokens'>('total_tokens');

  const [provName, setProvName] = useState('');
  const [modelName, setModelName] = useState('');
  const [inCost, setInCost] = useState('0');
  const [outCost, setOutCost] = useState('0');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [ov, pr] = await Promise.all([
        fetchAnalyticsOverview(30),
        fetchModelPricing(),
      ]);
      setOverview(ov);
      setPricing(pr);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const handleAddPricing = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!provName.trim() || !modelName.trim()) return;
    await upsertModelPricing({
      provider_name: provName.trim(),
      model_name: modelName.trim(),
      input_cost_per_1m: Number(inCost) || 0,
      output_cost_per_1m: Number(outCost) || 0,
    });
    setProvName('');
    setModelName('');
    setInCost('0');
    setOutCost('0');
    await load();
  };

  const handleDeletePricing = async (id: string) => {
    await deleteModelPricing(id);
    await load();
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6 px-4 py-8 sm:px-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-ink-primary">
            Usage Analytics
          </h2>
          <p className="mt-1 text-sm text-ink-secondary">
            Real local statistics from your SQLite conversations and provider
            usage logs—zero external telemetry.
          </p>
        </div>

        <button
          type="button"
          onClick={() => void load()}
          disabled={loading}
          className="inline-flex items-center gap-1.5 rounded-xl border border-border bg-surface-elevated px-3.5 py-2 text-xs font-medium text-ink-primary hover:bg-surface-hover"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
        {[
          {
            label: 'Conversations',
            value: overview ? overview.total_conversations.toLocaleString() : '—',
          },
          {
            label: 'Messages',
            value: overview ? overview.total_messages.toLocaleString() : '—',
          },
          {
            label: 'API Requests',
            value: overview ? overview.total_requests.toLocaleString() : '—',
          },
          {
            label: 'Total Tokens',
            value: overview ? overview.total_tokens.toLocaleString() : '—',
          },
          {
            label: 'Estimated Cost',
            value:
              overview?.estimated_total_cost != null
                ? `$${overview.estimated_total_cost.toFixed(4)}`
                : 'Not configured',
          },
        ].map((card) => (
          <div
            key={card.label}
            className="rounded-2xl border border-border bg-surface-elevated p-4"
          >
            <div className="text-xs font-medium text-ink-muted">
              {card.label}
            </div>
            <div className="mt-2 text-xl font-semibold text-ink-primary">
              {card.value}
            </div>
          </div>
        ))}
      </div>

      {/* Interactive Chart */}
      <section className="rounded-2xl border border-border bg-surface-elevated p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-sm font-semibold text-ink-primary">
            <BarChart3 className="h-4 w-4 text-accent" />
            <span>
              {chartMode === 'daily' ? 'Daily Usage (Last 30 Days)' : 'Monthly Usage'}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <div className="inline-flex rounded-xl border border-border bg-surface p-0.5 text-xs">
              <button
                type="button"
                onClick={() => setChartMode('daily')}
                className={`rounded-lg px-2.5 py-1 font-medium ${
                  chartMode === 'daily'
                    ? 'bg-surface-elevated text-ink-primary shadow-sm'
                    : 'text-ink-secondary'
                }`}
              >
                Daily
              </button>
              <button
                type="button"
                onClick={() => setChartMode('monthly')}
                className={`rounded-lg px-2.5 py-1 font-medium ${
                  chartMode === 'monthly'
                    ? 'bg-surface-elevated text-ink-primary shadow-sm'
                    : 'text-ink-secondary'
                }`}
              >
                Monthly
              </button>
            </div>

            <div className="inline-flex rounded-xl border border-border bg-surface p-0.5 text-xs">
              <button
                type="button"
                onClick={() => setMetric('total_tokens')}
                className={`rounded-lg px-2.5 py-1 font-medium ${
                  metric === 'total_tokens'
                    ? 'bg-surface-elevated text-ink-primary shadow-sm'
                    : 'text-ink-secondary'
                }`}
              >
                Tokens
              </button>
              <button
                type="button"
                onClick={() => setMetric('requests')}
                className={`rounded-lg px-2.5 py-1 font-medium ${
                  metric === 'requests'
                    ? 'bg-surface-elevated text-ink-primary shadow-sm'
                    : 'text-ink-secondary'
                }`}
              >
                Requests
              </button>
            </div>
          </div>
        </div>

        <BarChart
          points={
            chartMode === 'daily'
              ? overview?.daily_usage ?? []
              : overview?.monthly_usage ?? []
          }
          metric={metric}
        />
      </section>

      {/* Most Used Models Table */}
      <section className="rounded-2xl border border-border bg-surface-elevated p-5">
        <h3 className="mb-3 text-sm font-semibold text-ink-primary">
          Most Frequently Used Models
        </h3>
        {!overview || overview.top_models.length === 0 ? (
          <p className="py-4 text-xs text-ink-muted">
            Model usage breakdown will populate automatically as you chat or run
            AI tools.
          </p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-border">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-border bg-surface text-ink-secondary">
                <tr>
                  <th className="px-3.5 py-2.5">Provider</th>
                  <th className="px-3.5 py-2.5">Model</th>
                  <th className="px-3.5 py-2.5 text-right">Requests</th>
                  <th className="px-3.5 py-2.5 text-right">Input</th>
                  <th className="px-3.5 py-2.5 text-right">Output</th>
                  <th className="px-3.5 py-2.5 text-right">Est. Cost</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {overview.top_models.map((row) => (
                  <tr key={`${row.provider_name}-${row.model_name}`}>
                    <td className="px-3.5 py-2.5 font-medium text-ink-primary">
                      {row.provider_name}
                    </td>
                    <td className="px-3.5 py-2.5 font-mono text-[11px] text-ink-secondary">
                      {row.model_name}
                    </td>
                    <td className="px-3.5 py-2.5 text-right">
                      {row.requests.toLocaleString()}
                    </td>
                    <td className="px-3.5 py-2.5 text-right text-ink-secondary">
                      {row.input_tokens.toLocaleString()}
                    </td>
                    <td className="px-3.5 py-2.5 text-right text-ink-secondary">
                      {row.output_tokens.toLocaleString()}
                    </td>
                    <td className="px-3.5 py-2.5 text-right font-medium">
                      {row.estimated_cost != null
                        ? `$${row.estimated_cost.toFixed(4)}`
                        : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Configurable Local Pricing */}
      <section className="rounded-2xl border border-border bg-surface-elevated p-5 space-y-4">
        <div>
          <h3 className="flex items-center gap-2 text-sm font-semibold text-ink-primary">
            <DollarSign className="h-4 w-4 text-accent" />
            <span>Optional Model Pricing (USD per 1M Tokens)</span>
          </h3>
          <p className="mt-0.5 text-xs text-ink-secondary">
            Configure your provider&apos;s published pricing locally to calculate
            estimated API spend. No prices are hardcoded or guessed.
          </p>
        </div>

        <form
          onSubmit={handleAddPricing}
          className="grid grid-cols-1 gap-2 sm:grid-cols-5"
        >
          <input
            type="text"
            value={provName}
            onChange={(e) => setProvName(e.target.value)}
            placeholder="Provider Display Name"
            className="rounded-xl border border-border bg-canvas px-3 py-2 text-xs text-ink-primary focus:outline-none"
          />
          <input
            type="text"
            value={modelName}
            onChange={(e) => setModelName(e.target.value)}
            placeholder="Model ID"
            className="rounded-xl border border-border bg-canvas px-3 py-2 font-mono text-xs text-ink-primary focus:outline-none"
          />
          <input
            type="number"
            step="0.01"
            min="0"
            value={inCost}
            onChange={(e) => setInCost(e.target.value)}
            placeholder="Input $/1M"
            className="rounded-xl border border-border bg-canvas px-3 py-2 text-xs text-ink-primary focus:outline-none"
          />
          <input
            type="number"
            step="0.01"
            min="0"
            value={outCost}
            onChange={(e) => setOutCost(e.target.value)}
            placeholder="Output $/1M"
            className="rounded-xl border border-border bg-canvas px-3 py-2 text-xs text-ink-primary focus:outline-none"
          />
          <button
            type="submit"
            className="inline-flex items-center justify-center gap-1 rounded-xl bg-accent px-3 py-2 text-xs font-medium text-white hover:bg-accent-hover"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Save Rate</span>
          </button>
        </form>

        {pricing.length > 0 && (
          <div className="space-y-1.5">
            {pricing.map((p) => (
              <div
                key={p.id}
                className="flex items-center justify-between rounded-xl border border-border bg-canvas/50 px-3.5 py-2 text-xs"
              >
                <div>
                  <span className="font-semibold text-ink-primary">
                    {p.provider_name}
                  </span>{' '}
                  · <code className="font-mono text-[11px]">{p.model_name}</code>
                  <span className="ml-3 text-ink-muted">
                    In: ${p.input_cost_per_1m}/1M · Out: ${p.output_cost_per_1m}/1M
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => void handleDeletePricing(p.id)}
                  className="rounded-lg p-1 text-rose-600 hover:bg-rose-500/10"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
