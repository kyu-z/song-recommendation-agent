'use client'

import { useState } from 'react'
import Header from './components/Header'
import InputArea from './components/InputArea'
import ResponseArea from './components/ResponseArea'
import BlackOrchidOverlay from './components/BlackOrchidOverlay'
import ForestEdges from './components/ForestEdges'

interface Song {
  title: string
  artist: string
  reason: string
  link?: string
  platform?: string
  source: string
}

interface ResponseData {
  songs: Song[]
  original_input: string
  search_goal: string
  success: boolean
  message?: string
}

export default function Home() {
  const [isLoading, setIsLoading] = useState(false)
  const [response, setResponse] = useState<ResponseData | null>(null)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (input: string | File) => {
    setIsLoading(true)
    setError(null)
    
    try {
      let apiResponse: Response
      
      if (typeof input === 'string') {
        // Text input
        apiResponse = await fetch('http://localhost:8000/recommend', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ user_input: input }),
        })
      } else {
        // File input (image)
        const formData = new FormData()
        formData.append('image', input)
        
        apiResponse = await fetch('http://localhost:8000/recommend/image', {
          method: 'POST',
          body: formData,
        })
      }

      if (!apiResponse.ok) {
        throw new Error(`HTTP error! status: ${apiResponse.status}`)
      }

      const data = await apiResponse.json()
      setResponse(data)
    } catch (err) {
      console.error('API call failed:', err)
      setError(err instanceof Error ? err.message : 'Network error')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <main className="relative min-h-screen overflow-x-hidden">
      {/* Forest floor + canopy depth */}
      <div
        className="fixed inset-0 z-0 bg-gradient-to-b from-[#2a5a0c] via-[#2d6b00] to-[#4a2e0f]"
        aria-hidden
      />
      <div
        className="fixed inset-0 z-[1] bg-[radial-gradient(ellipse_120%_80%_at_50%_20%,rgba(45,107,0,0.95)_0%,rgba(74,46,15,0.55)_100%)]"
        aria-hidden
      />
      {/* Mobile: brown edge wash without full tree strip */}
      <div
        className="pointer-events-none fixed inset-0 z-[3] bg-gradient-to-r from-[#964B00]/22 via-transparent to-[#964B00]/22 sm:hidden"
        aria-hidden
      />
      <BlackOrchidOverlay />
      <ForestEdges />
      <div className="relative z-10">
        <div className="mx-auto w-full max-w-3xl px-4 sm:px-6 lg:max-w-[52rem] lg:px-10">
          <Header />
          <InputArea onSubmit={handleSubmit} isLoading={isLoading} />
          <ResponseArea isLoading={isLoading} response={response} error={error} />
        </div>
        <div className="h-10 sm:h-12" />
      </div>
    </main>
  )
}
