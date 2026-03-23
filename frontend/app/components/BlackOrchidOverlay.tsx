'use client'

/** Grain texture from black-orchid.png only */
export default function BlackOrchidOverlay() {
  return (
    <div
      className="fixed inset-0 z-[5] pointer-events-none"
      aria-hidden
      style={{
        backgroundImage: 'url(/black-orchid.png)',
        backgroundRepeat: 'repeat',
        backgroundPosition: '0 0',
        opacity: 0.42,
      }}
    />
  )
}
