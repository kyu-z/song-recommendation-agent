'use client'

export default function Header() {
  return (
    <header className="font-eb-garamond w-full pt-6 pb-4 sm:pt-8 sm:pb-5 flex flex-col items-center justify-center text-center md:pt-10 md:pb-6">
      <h1 className="inline-block text-4xl font-medium tracking-wide text-cream md:text-6xl lg:text-7xl [text-shadow:0_2px_6px_rgba(248,244,236,0.2),0_4px_20px_rgba(0,0,0,0.5)]">
        Timbre
      </h1>
      <p className="mt-4 max-w-md text-sm font-normal leading-relaxed text-cream/85 md:text-base">
        Text or image in. Music that fits your vibe, out.
      </p>
    </header>
  )
}
