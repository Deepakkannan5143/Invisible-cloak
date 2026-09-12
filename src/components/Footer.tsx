import { Shield } from 'lucide-react'

const GROUPS = [
  { title: 'Product', links: ['Protect', 'How It Works', 'Data Types', 'Demo'] },
  { title: 'Security', links: ['Privacy', 'Encryption', 'Compliance', 'Documentation'] },
  { title: 'Company', links: ['About', 'GitHub', 'Contact', 'Careers'] },
]

export default function Footer() {
  return (
    <footer id="about" className="relative scroll-mt-24 border-t border-cloak-softgray bg-white/60 backdrop-blur">
      <div className="mx-auto max-w-7xl px-4 py-14 sm:px-6">
        <div className="grid gap-10 md:grid-cols-2 lg:grid-cols-4">
          <div>
            <div className="flex items-center gap-3">
              <span className="grid h-10 w-10 place-items-center rounded-xl2 border border-cloak-softgray bg-white shadow-soft">
                <Shield className="h-5 w-5 text-cloak-ink" strokeWidth={1.75} />
              </span>
              <span className="text-sm font-semibold tracking-[0.18em] text-cloak-ink">
                INVISIBLE CLOAK
              </span>
            </div>
            <p className="mt-4 max-w-xs text-sm text-cloak-muted">
              Privacy should happen before sharing.
            </p>
          </div>

          {GROUPS.map((g) => (
            <div key={g.title}>
              <h4 className="mono-label">{g.title}</h4>
              <ul className="mt-3 space-y-2">
                {g.links.map((l) => (
                  <li key={l}>
                    <a
                      href="#top"
                      className="text-sm text-cloak-muted transition-colors hover:text-cloak-ink"
                    >
                      {l}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-12 flex flex-col items-start justify-between gap-4 border-t border-cloak-softgray/70 pt-6 sm:flex-row sm:items-center">
          <span className="text-sm text-cloak-muted">© 2026 Invisible Cloak</span>
          <div className="flex flex-wrap gap-x-5 gap-y-1">
            <span className="mono-label text-[10px]">CLOAK ENGINE v1.0</span>
            <span className="mono-label text-[10px]">
              SYSTEM STATUS: <span className="text-state-safe">OPERATIONAL</span>
            </span>
          </div>
        </div>
      </div>
    </footer>
  )
}
