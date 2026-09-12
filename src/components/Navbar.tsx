import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Menu, Shield, X } from 'lucide-react'

const NAV_LINKS = [
  { label: 'Protect', href: '#protect' },
  { label: 'How It Works', href: '#how-it-works' },
  { label: 'Security', href: '#security' },
  { label: 'About', href: '#about' },
]

interface Props {
  onLaunch: () => void
}

export default function Navbar({ onLaunch }: Props) {
  const [scrolled, setScrolled] = useState(false)
  const [open, setOpen] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <header
      className={`sticky top-0 z-50 transition-all duration-300 ${
        scrolled
          ? 'border-b border-cloak-softgray/80 bg-white/80 shadow-soft backdrop-blur-2xl'
          : 'border-b border-transparent bg-white/50 backdrop-blur-lg'
      }`}
    >
      <nav
        className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3 sm:px-6"
        aria-label="Primary"
      >
        {/* Logo */}
        <a href="#top" className="group flex items-center gap-3" aria-label="Invisible Cloak home">
          <span className="relative grid h-10 w-10 place-items-center rounded-xl2 border border-cloak-softgray bg-white shadow-soft">
            <Shield className="h-5 w-5 text-cloak-ink" strokeWidth={1.75} aria-hidden="true" />
            <span className="absolute inset-0 rounded-xl2 bg-state-scan/10 opacity-0 transition-opacity group-hover:opacity-100" />
          </span>
          <span className="leading-tight">
            <span className="block text-sm font-semibold tracking-[0.18em] text-cloak-ink">
              INVISIBLE CLOAK
            </span>
            <span className="mono-label block text-[10px]">Privacy Intelligence</span>
          </span>
        </a>

        {/* Desktop links */}
        <ul className="hidden items-center gap-1 md:flex">
          {NAV_LINKS.map((l) => (
            <li key={l.href}>
              <a
                href={l.href}
                className="rounded-full px-3 py-2 text-sm text-cloak-muted transition-colors hover:bg-cloak-lightgray hover:text-cloak-ink focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-state-scan"
              >
                {l.label}
              </a>
            </li>
          ))}
        </ul>

        {/* Right side */}
        <div className="hidden items-center gap-4 md:flex">
          <span className="pill">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-state-safe opacity-60" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-state-safe" />
            </span>
            System Online
          </span>
          <button className="btn-primary" onClick={onLaunch}>
            Launch Cloak
          </button>
        </div>

        {/* Mobile toggle */}
        <button
          className="grid h-10 w-10 place-items-center rounded-xl2 border border-cloak-softgray bg-white text-cloak-ink md:hidden"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          aria-controls="mobile-menu"
          aria-label={open ? 'Close menu' : 'Open menu'}
        >
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </nav>

      {/* Mobile menu */}
      <AnimatePresence>
        {open && (
          <motion.div
            id="mobile-menu"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="overflow-hidden border-t border-cloak-softgray bg-white/90 backdrop-blur-xl md:hidden"
          >
            <ul className="flex flex-col gap-1 px-4 py-3">
              {NAV_LINKS.map((l) => (
                <li key={l.href}>
                  <a
                    href={l.href}
                    onClick={() => setOpen(false)}
                    className="block rounded-xl2 px-3 py-3 text-sm text-cloak-ink hover:bg-cloak-lightgray"
                  >
                    {l.label}
                  </a>
                </li>
              ))}
              <li className="mt-2 flex items-center justify-between px-1">
                <span className="pill">
                  <span className="h-2 w-2 rounded-full bg-state-safe" /> System Online
                </span>
                <button
                  className="btn-primary"
                  onClick={() => {
                    setOpen(false)
                    onLaunch()
                  }}
                >
                  Launch Cloak
                </button>
              </li>
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  )
}
