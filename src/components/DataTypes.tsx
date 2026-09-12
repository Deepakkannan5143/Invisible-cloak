import { motion } from 'framer-motion'
import { SHOWCASE_TYPES, TYPE_META } from '../lib/typeMeta'
import { TYPE_ICON } from '../lib/typeIcons'

/** Beautiful grid of supported sensitive data types with hover reveal. */
export default function DataTypes() {
  return (
    <section className="mx-auto max-w-7xl px-4 py-20 sm:px-6">
      <div className="mx-auto max-w-2xl text-center">
        <span className="mono-label">// SUPPORTED_DATA_TYPES</span>
        <h2 className="mt-3 text-3xl font-semibold tracking-tight text-cloak-ink sm:text-4xl">
          Everything worth hiding.
        </h2>
        <p className="mt-3 text-cloak-muted">
          Cloak recognizes a broad range of sensitive patterns — and you can add your own.
        </p>
      </div>

      <div className="mt-12 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        {SHOWCASE_TYPES.map((type, i) => {
          const meta = TYPE_META[type]
          const Icon = TYPE_ICON[type]
          return (
            <motion.div
              key={type}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-60px' }}
              transition={{ delay: (i % 4) * 0.06 }}
              whileHover={{ rotateX: 4, rotateY: -4 }}
              style={{ transformStyle: 'preserve-3d' }}
              className="group relative overflow-hidden rounded-xl2 border border-cloak-softgray bg-white/70 p-5 shadow-soft transition-shadow hover:shadow-glass"
            >
              <span className="grid h-11 w-11 place-items-center rounded-xl2 bg-cloak-lightgray text-cloak-ink transition-colors group-hover:bg-state-scan/10 group-hover:text-state-scan">
                <Icon className="h-5 w-5" strokeWidth={1.6} aria-hidden="true" />
              </span>
              <h3 className="mt-3 text-sm font-semibold text-cloak-ink">{meta.label}</h3>
              <p className="mt-1 text-xs text-cloak-muted">{meta.description}</p>

              <span className="mono-label mt-3 inline-block text-[9px] text-state-safe opacity-0 transition-opacity group-hover:opacity-100">
                ● PROTECTION ACTIVE
              </span>
            </motion.div>
          )
        })}
      </div>
    </section>
  )
}
