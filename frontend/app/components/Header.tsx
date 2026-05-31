'use client'

export default function Header() {
  return (
    <header className="font-eb-garamond flex w-full flex-col items-center justify-center pt-4 pb-1 text-center sm:pt-5 sm:pb-2 md:pt-6">
      <h1 className="inline-block text-4xl font-medium tracking-wide text-cream md:text-6xl lg:text-7xl [text-shadow:0_2px_6px_rgba(248,244,236,0.15),0_4px_16px_rgba(0,0,0,0.6)]">
        Timbre
      </h1>
      <p className="mt-2 max-w-md text-sm font-normal leading-snug text-cream/75 md:text-base">
        Text or image in. Music that fits your vibe, out.
      </p>
    </header>
  )
}
