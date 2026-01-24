import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Music Agent',
  description: 'AI-powered music recommendation service',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
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
      <body className="font-departure bg-pure-black text-white min-h-screen antialiased">
        {children}
      </body>
    </html>
  )
}
