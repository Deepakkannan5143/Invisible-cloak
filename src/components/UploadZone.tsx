import { useCallback, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { ShieldCheck, UploadCloud } from 'lucide-react'
import LiquidFlow from './LiquidFlow'
import { readFileAsDataURL } from '../lib/imageProcessor'

const MAX_BYTES = 10 * 1024 * 1024
const ACCEPTED = ['image/png', 'image/jpeg', 'image/webp']

interface Props {
  onImage: (src: string) => void
  onError: (message: string) => void
  onDemo: () => void
}

export default function UploadZone({ onImage, onError, onDemo }: Props) {
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFile = useCallback(
    async (file: File | undefined) => {
      if (!file) return
      if (!ACCEPTED.includes(file.type)) {
        onError('Unsupported format. Use PNG, JPG or WEBP.')
        return
      }
      if (file.size > MAX_BYTES) {
        onError('Image too large. Maximum size is 10 MB.')
        return
      }
      try {
        const src = await readFileAsDataURL(file)
        onImage(src)
      } catch {
        onError('Could not read that file. Please try another.')
      }
    },
    [onImage, onError],
  )

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragging(false)
      void handleFile(e.dataTransfer.files?.[0])
    },
    [handleFile],
  )

  return (
    <div className="relative">
      <motion.div
        onDragOver={(e) => {
          e.preventDefault()
          setDragging(true)
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            inputRef.current?.click()
          }
        }}
        role="button"
        tabIndex={0}
        aria-label="Upload a screenshot to protect. Drop an image or press Enter to browse."
        animate={dragging ? { scale: 1.01 } : { scale: 1 }}
        className={`relative flex min-h-[320px] cursor-pointer flex-col items-center justify-center overflow-hidden rounded-xl3 border-2 border-dashed p-8 text-center transition-colors duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-state-scan focus-visible:ring-offset-2 ${
          dragging
            ? 'border-state-scan bg-state-scan/5 shadow-glow'
            : 'border-cloak-softgray bg-white/60 hover:border-state-scan/50'
        }`}
      >
        {/* flowing liquid lines */}
        <LiquidFlow className="opacity-70" speed={dragging ? 6 : 14} />

        {/* ripple + particles toward center on drag */}
        {dragging && (
          <>
            <span className="absolute inset-0 animate-ping rounded-xl3 border border-state-scan/30" />
            {[...Array(6)].map((_, i) => (
              <motion.span
                key={i}
                className="absolute h-1.5 w-1.5 rounded-full bg-state-scan/70"
                initial={{
                  x: (i % 2 === 0 ? -1 : 1) * (120 + i * 20),
                  y: (i < 3 ? -1 : 1) * (60 + i * 14),
                  opacity: 0,
                }}
                animate={{ x: 0, y: 0, opacity: [0, 1, 0] }}
                transition={{ duration: 1.1, repeat: Infinity, delay: i * 0.1 }}
              />
            ))}
          </>
        )}

        <motion.div
          animate={dragging ? { scale: 1.15 } : { scale: 1 }}
          transition={{ type: 'spring', stiffness: 300, damping: 20 }}
          className="relative z-10 grid h-20 w-20 place-items-center rounded-full border border-cloak-softgray bg-white shadow-glass"
        >
          {dragging ? (
            <ShieldCheck className="h-9 w-9 text-state-scan" strokeWidth={1.5} />
          ) : (
            <UploadCloud className="h-9 w-9 text-cloak-muted" strokeWidth={1.5} />
          )}
        </motion.div>

        <p className="relative z-10 mt-5 text-lg font-semibold text-cloak-ink">
          {dragging ? 'Release to cloak' : 'Drop your screenshot here'}
        </p>
        <p className="relative z-10 mt-1 text-sm text-cloak-muted">or click to browse</p>

        <div className="relative z-10 mt-5 flex flex-wrap items-center justify-center gap-2">
          <span className="pill">PNG • JPG • WEBP</span>
          <span className="pill">MAX 10 MB</span>
        </div>

        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED.join(',')}
          className="sr-only"
          onChange={(e) => {
            void handleFile(e.target.files?.[0])
            e.target.value = ''
          }}
        />
      </motion.div>

      <div className="mt-4 flex items-center justify-center">
        <button
          className="btn-ghost"
          onClick={(e) => {
            e.stopPropagation()
            onDemo()
          }}
        >
          No screenshot? Try the live demo
        </button>
      </div>
    </div>
  )
}
