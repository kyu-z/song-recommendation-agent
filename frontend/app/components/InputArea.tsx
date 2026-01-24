'use client'

import { useState } from 'react'

interface InputAreaProps {
  onSubmit: (input: string) => void
  isLoading: boolean
}

export default function InputArea({ onSubmit, isLoading }: InputAreaProps) {
  const [input, setInput] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input.trim() && !isLoading) {
      onSubmit(input.trim())
      setInput('')
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  return (
    <div className="w-full max-w-4xl mx-auto px-6 py-8">
      <form onSubmit={handleSubmit} className="relative">
        <div className="relative">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyPress}
            disabled={isLoading}
            placeholder="告诉我你想听什么音乐..."
            className={`
              w-full min-h-[120px] p-6 
              bg-cream-transparent glass-effect
              text-black placeholder-gray-600
              border border-cream/20 rounded-lg
              resize-none
              focus:border-cream/40 focus:bg-cream/90
              transition-all duration-300 ease-in-out
              disabled:opacity-50 disabled:cursor-not-allowed
              font-departure text-lg leading-relaxed
            `}
            rows={4}
          />
          
          {/* 发送按钮 */}
          <button
            type="submit"
            disabled={!input.trim() || isLoading}
            className={`
              absolute bottom-4 right-4
              px-6 py-2
              bg-black/40 hover:bg-black/60
              border border-cream/30 hover:border-cream/50
              text-cream text-sm font-departure
              rounded-md
              transition-all duration-200
              disabled:opacity-30 disabled:cursor-not-allowed
              backdrop-blur-sm
            `}
          >
            {isLoading ? '...' : 'Send'}
          </button>
        </div>
      </form>
    </div>
  )
}
