'use client'

import { useState } from 'react'
import { useInputMode, InputMode } from '../hooks/useInputMode'
import ImageUploadArea from './ImageUploadArea'

interface InputAreaProps {
  onSubmit: (input: string | File) => void
  isLoading: boolean
}

export default function InputArea({ onSubmit, isLoading }: InputAreaProps) {
  const [textInput, setTextInput] = useState('')
  const {
    mode,
    selectedImage,
    imagePreview,
    fileInputRef,
    switchToText,
    switchToImage,
    selectImage,
    clearImage,
    triggerFileSelect
  } = useInputMode()

  const handleTextSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (textInput.trim() && !isLoading) {
      onSubmit(textInput.trim())
      setTextInput('')
    }
  }

  const handleImageSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (selectedImage && !isLoading) {
      onSubmit(selectedImage)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey && mode === 'text') {
      e.preventDefault()
      handleTextSubmit(e)
    }
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file && ['image/jpeg', 'image/jpg', 'image/png'].includes(file.type)) {
      selectImage(file)
    }
  }

  return (
    <div className="w-full">
      {/* Mode toggle */}
      <div className="mb-2 flex justify-center">
        <button
          type="button"
          onClick={mode === 'text' ? switchToImage : switchToText}
          disabled={isLoading}
          className="
            px-5 py-1.5 rounded-lg font-departure text-sm
            bg-cream/10 hover:bg-cream/20
            border border-cream/30 hover:border-cream/50
            text-cream
            transition-all duration-300
            disabled:opacity-50 disabled:cursor-not-allowed
          "
        >
          {mode === 'text' ? 'Image' : 'Text'}
        </button>
      </div>

      {/* Input */}
      <div className="input-mode-transition">
        {mode === 'text' ? (
          <form onSubmit={handleTextSubmit} className="relative fade-in">
            <div className="relative">
              <textarea
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                onKeyDown={handleKeyPress}
                disabled={isLoading}
                placeholder="What do you want to listen to?"
                className={`
                  w-full min-h-[92px] sm:min-h-[96px] p-3 sm:p-4
                  bg-cream-transparent glass-effect
                  text-black placeholder-gray-600
                  border border-cream/20 rounded-xl
                  resize-none
                  focus:border-cream/40 focus:bg-cream/90
                  transition-all duration-300 ease-in-out
                  disabled:opacity-50 disabled:cursor-not-allowed
                  font-departure text-base leading-snug sm:text-lg
                `}
                rows={3}
              />
              
              {/* Send */}
              <button
                type="submit"
                disabled={!textInput.trim() || isLoading}
                className={`
                  absolute bottom-3 right-3
                  px-5 py-1.5
                  bg-cream/20 hover:bg-cream/5
                  border border-cream/30 hover:border-cream/80
                  text-pure-black text-sm font-departure
                  rounded-md
                  transition-all duration-200
                  disabled:opacity-30 disabled:cursor-not-allowed
                `}
              >
                {isLoading ? '...' : 'Send'}
              </button>
            </div>
          </form>
        ) : (
          <form onSubmit={handleImageSubmit} className="relative fade-in">
            {/* Hidden file input */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept="image/jpeg,image/jpg,image/png"
              className="hidden"
            />

            {/* Image drop zone */}
            <ImageUploadArea
              selectedImage={selectedImage}
              imagePreview={imagePreview}
              onImageSelect={selectImage}
              onClearImage={clearImage}
              onTriggerFileSelect={triggerFileSelect}
              isLoading={isLoading}
            />

            {selectedImage && (
              <div className="mt-2 flex justify-end">
                <button
                  type="submit"
                  disabled={isLoading}
                  className={`
                    px-4 py-1.5
                    bg-cream/10 hover:bg-cream/20
                    border border-cream/30 hover:border-cream/50
                    text-cream font-departure text-sm
                    rounded-md
                    transition-all duration-200
                    disabled:opacity-30 disabled:cursor-not-allowed
                  `}
                >
                  {isLoading ? 'Analyzing...' : 'Get recommendations'}
                </button>
              </div>
            )}
          </form>
        )}
      </div>
    </div>
  )
}
