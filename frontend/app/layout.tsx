import type { Metadata } from 'next'
import { EB_Garamond } from 'next/font/google'
import './globals.css'

const ebGaramond = EB_Garamond({
  subsets: ['latin'],
  weight: ['400', '500', '600'],
  display: 'swap',
  variable: '--font-eb-garamond',
})

export const metadata: Metadata = {
  title: 'Timbre',
  description:
    'Text or image in. Music that fits your vibe, out. AI music recommendations from words or pictures.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html
      lang="en"
      className={`${ebGaramond.variable} h-full bg-[#2d6b00]`}
    >
      <head>
        {/* Preload JetBrains Mono font */}
        <link
          rel="preload"
          href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,100..800;1,100..800&display=swap"
          as="style"
        />
        <link
          rel="stylesheet"
          href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,100..800;1,100..800&display=swap"
        />
      </head>
      <body className="font-departure min-h-full min-h-screen bg-[#2d6b00] text-white antialiased">
        {children}
      </body>
    </html>
  )
}
