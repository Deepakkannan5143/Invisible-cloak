import { useState } from 'react'
import { motion } from 'framer-motion'
import { Plus } from 'lucide-react'
import type { ProtectionMode, SensitiveType } from '../types/scanner'
import { TOGGLEABLE_TYPES, TYPE_META } from '../lib/typeMeta'
import { TYPE_ICON } from '../lib/typeIcons'

interface Props {
  enabled: Set<SensitiveType>
  onToggle: (type: SensitiveType) => void
  mode: ProtectionMode
  onModeChange: (mode: ProtectionMode) => void
  customPatterns: string[]
  onAddPattern: (pattern: string) => void
}

const MODES: { value: ProtectionMode; label: string }[] = [
  { value: 'blur', label: 'Blur' },
  { value: 'pixelate', label: 'Pixelate' },
  { value: 'redact', label: 'Redact' },
  { value: 'frosted', label: 'Frosted Cloak' },
]

export default function ProtectionSettings({
  enabled,
  onToggle,
  mode,
  onModeChange,
  customPatterns,
  onAddPattern,
}: Props) {
  const [draft, setDraft] = useState('')

  const submitPattern = () => {
    const v = draft.trim()
    if (!v) return
    onAddPattern(v)
    setDraft('')
  }

  return (
    <div className="glass-panel rounded-xl2 p-6">
      <h3 className="text-lg font-semibold text-cloak-ink">Protection Settings</h3>
      <p className="mono-label mt-1">CONFIGURE_DETECTION_LAYERS</p>

      {/* toggles */}
      <div className="mt-4 space-y-2">
        {TOGGLEABLE_TYPES.map((type) => {
          const meta = TYPE_META[type]
          const Icon = TYPE_ICON[type]
          const on = enabled.has(type)
          return (
            <div
              key={type}
              className="flex items-center gap-3 rounded-xl2 border border-cloak-softgray bg-white/60 px-3 py-2"
            >
              <span className="grid h-8 w-8 place-items-center rounded-lg bg-cloak-lightgray text-cloak-ink">
                <Icon className="h-4 w-4" strokeWidth={1.75} aria-hidden="true" />
              </span>
              <span className="flex-1 text-sm font-medium text-cloak-ink">
                {meta.label}
              </span>
              <button
                type="button"
                role="switch"
                aria-checked={on}
                aria-label={`Toggle protection for ${meta.label}`}
                onClick={() => onToggle(type)}
                className={`relative h-6 w-11 shrink-0 rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-state-scan focus-visible:ring-offset-2 ${
                  on ? 'bg-state-safe' : 'bg-cloak-softgray'
                }`}
              >
                <motion.span
                  layout
                  transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                  className="absolute top-0.5 h-5 w-5 rounded-full bg-white shadow"
                  style={{ left: on ? 22 : 2 }}
                />
              </button>
            </div>
          )
        })}
      </div>

      {/* custom pattern */}
      <div className="mt-4">
        <label htmlFor="custom-pattern" className="mono-label">
          CUSTOM_SENSITIVE_PATTERN
        </label>
        <div className="mt-2 flex gap-2">
          <input
            id="custom-pattern"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && submitPattern()}
            placeholder="e.g. Employee ID, Project Code"
            className="min-w-0 flex-1 rounded-full border border-cloak-softgray bg-white px-4 py-2 text-sm text-cloak-ink placeholder:text-cloak-medgray focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-state-scan"
          />
          <button type="button" className="btn-primary shrink-0" onClick={submitPattern}>
            <Plus className="h-4 w-4" /> Add
          </button>
        </div>
        {customPatterns.length > 0 && (
          <div className="mt-3 flex flex-wrap gap-2">
            {customPatterns.map((p) => (
              <span key={p} className="pill normal-case tracking-normal">
                {p}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* protection mode */}
      <div className="mt-5">
        <span className="mono-label">PROTECTION_MODE</span>
        <div
          className="mt-2 grid grid-cols-2 gap-2"
          role="radiogroup"
          aria-label="Protection mode"
        >
          {MODES.map((m) => {
            const selected = mode === m.value
            return (
              <button
                key={m.value}
                type="button"
                role="radio"
                aria-checked={selected}
                onClick={() => onModeChange(m.value)}
                className={`flex items-center gap-2 rounded-xl2 border px-3 py-2.5 text-sm font-medium transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-state-scan ${
                  selected
                    ? 'border-state-scan bg-state-scan/5 text-cloak-ink shadow-glow'
                    : 'border-cloak-softgray bg-white/60 text-cloak-muted hover:border-state-scan/40'
                }`}
              >
                <span
                  className={`grid h-4 w-4 place-items-center rounded-full border ${
                    selected ? 'border-state-scan' : 'border-cloak-medgray'
                  }`}
                >
                  {selected && <span className="h-2 w-2 rounded-full bg-state-scan" />}
                </span>
                {m.label}
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
