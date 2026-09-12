import { useState } from 'react'
import { motion } from 'framer-motion'
import { Copy, Download, RotateCcw, ShieldCheck } from 'lucide-react'

interface Props {
  protectedSrc: string
  itemsCloaked: number
  onDownload: () => void
  onCopy: () => void
  onReset: () => void
}

/** Final "safe to share" CTA with download / copy / reset actions. */
export default function ShareResult({
  protectedSrc,
  itemsCloaked,
  onDownload,
  onCopy,
  onReset,
}: Props) {
  const [cloaking, setCloaking] = useState(false)

  const handleDownload = () => {
    setCloaking(true)
    onDownload()
    setTimeout(() => setCloaking(false), 900)
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="relative overflow-hidden rounded-xl2 border border-state-safe/30 bg-gradient-to-br from-state-safe/[0.06] to-white p-6 text-center shadow-glass"
    >
      <div className="mx-auto grid h-14 w-14 place-items-center rounded-full bg-state-safe/10">
        <motion.span
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 300, damping: 18, delay: 0.1 }}
        >
          <ShieldCheck className="h-7 w-7 text-state-safe" strokeWidth={1.75} />
        </motion.span>
      </div>

      <h3 className="mt-4 text-xl font-semibold text-cloak-ink">
        Your screenshot is safe to share.
      </h3>
      <p className="led-text mt-1 text-[12px] text-state-safe">
        {itemsCloaked} SENSITIVE ITEM{itemsCloaked === 1 ? '' : 'S'} CLOAKED · SAFE TO SHARE
      </p>

      <div className="mt-5 flex flex-wrap items-center justify-center gap-3">
        <button className="btn-primary relative overflow-hidden" onClick={handleDownload}>
          {cloaking && (
            <span className="absolute inset-0 -translate-x-full animate-[grid-pan_0.9s_linear] bg-gradient-to-r from-transparent via-white/40 to-transparent" />
          )}
          <Download className="h-4 w-4" /> Download Protected Image
        </button>
        <button className="btn-ghost" onClick={onCopy}>
          <Copy className="h-4 w-4" /> Copy to Clipboard
        </button>
        <button className="btn-ghost" onClick={onReset}>
          <RotateCcw className="h-4 w-4" /> Protect Another
        </button>
      </div>

      {/* hidden preview to keep protectedSrc referenced / previewable */}
      <img src={protectedSrc} alt="" aria-hidden="true" className="sr-only" />
    </motion.div>
  )
}
