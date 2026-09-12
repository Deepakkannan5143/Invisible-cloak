import { AnimatePresence, motion } from 'framer-motion'
import { AlertTriangle, CheckCircle2, Info, X, XCircle } from 'lucide-react'
import { useToast, type ToastKind } from '../hooks/useToast'

const ICONS = {
  success: CheckCircle2,
  info: Info,
  warn: AlertTriangle,
  error: XCircle,
}

const COLORS: Record<ToastKind, string> = {
  success: 'text-state-safe',
  info: 'text-state-scan',
  warn: 'text-state-warn',
  error: 'text-state-crit',
}

/** Fixed-position toast stack. */
export default function ToastViewport() {
  const { toasts, dismiss } = useToast()

  return (
    <div
      className="pointer-events-none fixed bottom-4 right-4 z-[60] flex w-full max-w-sm flex-col gap-2"
      role="region"
      aria-label="Notifications"
      aria-live="polite"
    >
      <AnimatePresence>
        {toasts.map((t) => {
          const Icon = ICONS[t.kind]
          return (
            <motion.div
              key={t.id}
              layout
              initial={{ opacity: 0, x: 40, scale: 0.95 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 40, scale: 0.95 }}
              transition={{ type: 'spring', stiffness: 400, damping: 30 }}
              className="glass-panel pointer-events-auto flex items-start gap-3 rounded-xl2 p-3.5"
            >
              <Icon className={`mt-0.5 h-5 w-5 shrink-0 ${COLORS[t.kind]}`} />
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-cloak-ink">{t.title}</p>
                {t.description && (
                  <p className="mt-0.5 text-xs text-cloak-muted">{t.description}</p>
                )}
              </div>
              <button
                onClick={() => dismiss(t.id)}
                className="rounded-md p-1 text-cloak-medgray transition-colors hover:text-cloak-ink"
                aria-label="Dismiss notification"
              >
                <X className="h-4 w-4" />
              </button>
            </motion.div>
          )
        })}
      </AnimatePresence>
    </div>
  )
}
