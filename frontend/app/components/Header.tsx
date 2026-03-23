'use client'

export default function Header() {
  return (
    <header className="font-eb-garamond w-full pt-6 pb-4 sm:pt-8 sm:pb-5 flex flex-col items-center justify-center text-center md:pt-10 md:pb-6">
      <h1 className="music-agent-title inline-block text-4xl font-medium tracking-wide text-cream md:text-6xl lg:text-7xl">
        Timbre
      </h1>
      <p className="mt-4 max-w-md text-sm font-normal leading-relaxed text-cream/85 md:text-base">
        Text or image in. Music that fits your vibe, out.
      </p>
    </header>
  )
}
