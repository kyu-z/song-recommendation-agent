'use client'

import { useState } from 'react'
import Header from './components/Header'
import InputArea from './components/InputArea'
import ResponseArea from './components/ResponseArea'
import BlackOrchidOverlay from './components/BlackOrchidOverlay'

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
    <main className="relative min-h-screen bg-[#2d6b00]">
      <BlackOrchidOverlay />
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
