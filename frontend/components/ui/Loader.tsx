interface LoaderProps {
  size?: number
  color?: string
  fullscreen?: boolean
  label?: string
}

export default function Loader({ size = 40, color, fullscreen = false, label }: LoaderProps) {
  const el = (
    <div className="flex flex-col items-center gap-3">
      <div className="loader-jh" style={{ '--size': `${size}px`, '--color': color ?? 'var(--loader-color)' } as React.CSSProperties}>
        <span/><span/><span/><span/><span/><span/>
      </div>
      {label && <p className="animate-pulse text-xs tracking-wide text-slate-400 dark:text-slate-500">{label}</p>}
    </div>
  )

  if (fullscreen) return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-white/80 backdrop-blur-sm dark:bg-slate-950/80">
      {el}
    </div>
  )
  return el
}
