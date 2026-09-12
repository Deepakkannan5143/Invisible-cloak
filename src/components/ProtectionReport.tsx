import { motion } from 'framer-motion'
import { Check } from 'lucide-react'
import type { Detection, ScanResult } from '../types/scanner'
import { TYPE_META } from '../lib/typeMeta'
import { TYPE_ICON } from '../lib/typeIcons'

interface Props {
  result: ScanResult
}

interface Grouped {
  type: Detection['detectedType']
  count: number
  confidence: number
  protectedCount: number
}

function group(detections: Detection[]): Grouped[] {
  const map = new Map<Detection['detectedType'], Grouped>()
  for (const d of detections) {
    const g = map.get(d.detectedType) ?? {
      type: d.detectedType,
      count: 0,
      confidence: 0,
      protectedCount: 0,
    }
    g.count += 1
    g.confidence = Math.max(g.confidence, d.confidence)
    if (d.protected) g.protectedCount += 1
    map.set(d.detectedType, g)
  }
  return [...map.values()]
}

/** Detailed protection report shown beside the screenshot after scanning. */
export default function ProtectionReport({ result }: Props) {
  const groups = group(result.detections)
  const total = result.detections.length
  const protectedCount = result.detections.filter((d) => d.protected).length
  const exposed = total - protectedCount
  const avgConfidence =
    total === 0
      ? 0
      : Math.round(
          result.detections.reduce((s, d) => s + d.confidence, 0) / total,
        )

  return (
    <div className="glass-panel rounded-xl2 p-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-cloak-ink">Protection Report</h3>
        <span className="inline-flex items-center gap-2 rounded-full bg-state-safe/10 px-3 py-1 font-mono text-[11px] font-medium uppercase tracking-wide text-state-safe">
          <span className="h-2 w-2 animate-pulse-soft rounded-full bg-state-safe" />
          Cloak Active
        </span>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Metric value={total} label="Sensitive Items" />
        <Metric value={protectedCount} label="Items Cloaked" tone="safe" />
        <Metric value={exposed} label="Exposed" tone={exposed > 0 ? 'crit' : 'muted'} />
        <Metric value={`${avgConfidence}%`} label="Confidence" />
      </div>

      <ul className="mt-5 space-y-2" aria-label="Detected sensitive data categories">
        {groups.map((g, i) => {
          const meta = TYPE_META[g.type]
          const Icon = TYPE_ICON[g.type]
          const allProtected = g.protectedCount === g.count
          return (
            <motion.li
              key={g.type}
              initial={{ opacity: 0, x: 8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.08 }}
              className="flex items-center gap-3 rounded-xl2 border border-cloak-softgray bg-white/70 px-3 py-2.5"
            >
              <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-cloak-lightgray text-cloak-ink">
                <Icon className="h-4 w-4" strokeWidth={1.75} aria-hidden="true" />
              </span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-2">
                  <span className="truncate text-sm font-medium text-cloak-ink">
                    {meta.label}
                  </span>
                  <span className="mono-label shrink-0 text-[10px]">
                    {g.confidence.toFixed(1)}%
                  </span>
                </div>
                <div className="mono-label mt-0.5 text-[10px] normal-case tracking-normal">
                  {g.count} occurrence{g.count > 1 ? 's' : ''} · {meta.severity}
                </div>
              </div>
              <span
                className={`inline-flex items-center gap-1 rounded-full px-2 py-1 font-mono text-[10px] font-medium ${
                  allProtected
                    ? 'bg-state-safe/10 text-state-safe'
                    : 'bg-state-warn/10 text-state-warn'
                }`}
              >
                {allProtected ? <Check className="h-3 w-3" /> : null}
                {allProtected ? 'CLOAKED' : 'PENDING'}
              </span>
            </motion.li>
          )
        })}
      </ul>

      <div className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-1 border-t border-cloak-softgray/70 pt-3">
        <span className="mono-label text-[10px]">SCAN_ID: {result.scanId}</span>
        <span className="mono-label text-[10px]">LATENCY: {result.latencyMs}ms</span>
        <span className="mono-label text-[10px]">EXPOSURE: {exposed === 0 ? '0%' : 'HIGH'}</span>
      </div>
    </div>
  )
}

function Metric({
  value,
  label,
  tone = 'ink',
}: {
  value: number | string
  label: string
  tone?: 'ink' | 'safe' | 'crit' | 'muted'
}) {
  const color =
    tone === 'safe'
      ? 'text-state-safe'
      : tone === 'crit'
        ? 'text-state-crit'
        : tone === 'muted'
          ? 'text-cloak-medgray'
          : 'text-cloak-ink'
  return (
    <div className="rounded-xl2 border border-cloak-softgray bg-white/60 p-3 text-center">
      <div className={`text-2xl font-semibold ${color}`}>{value}</div>
      <div className="mono-label mt-0.5 text-[9px]">{label}</div>
    </div>
  )
}
