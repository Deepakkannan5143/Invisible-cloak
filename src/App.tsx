import { useCallback, useRef, useState } from 'react'
import type { ScanPhase } from './types/scanner'
import { ToastProvider } from './hooks/useToast'
import LiquidBackground from './components/LiquidBackground'
import Navbar from './components/Navbar'
import Hero from './components/Hero'
import ProtectFlow, { type ProtectFlowHandle } from './components/ProtectFlow'
import HowItWorks from './components/HowItWorks'
import DataTypes from './components/DataTypes'
import Statistics from './components/Statistics'
import SystemStatus from './components/SystemStatus'
import SecurityVisualization from './components/SecurityVisualization'
import Footer from './components/Footer'
import ToastViewport from './components/ToastViewport'

function AppShell() {
  const [heroPhase, setHeroPhase] = useState<ScanPhase>('idle')
  const [heroProgress, setHeroProgress] = useState(0)
  const flowRef = useRef<ProtectFlowHandle>(null)

  const onPhaseChange = useCallback((phase: ScanPhase, progress: number) => {
    setHeroPhase(phase)
    setHeroProgress(progress)
  }, [])

  const scrollToProtect = useCallback(() => {
    document.getElementById('protect')?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  const runDemo = useCallback(() => {
    scrollToProtect()
    // allow the smooth scroll to begin before the scan kicks off
    window.setTimeout(() => flowRef.current?.runDemo(), 350)
  }, [scrollToProtect])

  return (
    <div className="relative min-h-screen">
      <LiquidBackground />

      {/* Skip link for keyboard users */}
      <a
        href="#protect"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[80] focus:rounded-full focus:bg-cloak-ink focus:px-4 focus:py-2 focus:text-sm focus:text-white"
      >
        Skip to protection tool
      </a>

      <Navbar onLaunch={scrollToProtect} />

      <main>
        <Hero
          phase={heroPhase}
          progress={heroProgress}
          onProtect={scrollToProtect}
          onDemo={runDemo}
        />

        <ProtectFlow ref={flowRef} onPhaseChange={onPhaseChange} />

        <HowItWorks />

        <DataTypes />

        <Statistics />

        {/* Security engine section */}
        <section id="security" className="mx-auto max-w-7xl scroll-mt-24 px-4 py-20 sm:px-6">
          <div className="mx-auto max-w-2xl text-center">
            <span className="mono-label">// CLOAK_ENGINE</span>
            <h2 className="mt-3 text-3xl font-semibold tracking-tight text-cloak-ink sm:text-4xl">
              A live privacy network.
            </h2>
            <p className="mt-3 text-cloak-muted">
              Detection, classification, redaction, verification and export — orchestrated
              on-device, in real time.
            </p>
          </div>
          <div className="mt-12 grid items-start gap-6 lg:grid-cols-2">
            <SecurityVisualization />
            <SystemStatus />
          </div>
        </section>
      </main>

      <Footer />

      <ToastViewport />
    </div>
  )
}

export default function App() {
  return (
    <ToastProvider>
      <AppShell />
    </ToastProvider>
  )
}
