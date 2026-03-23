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
    <div className="w-full py-3 sm:py-4">
      {/* Mode toggle */}
      <div className="flex justify-center mb-3 sm:mb-4">
        <button
          type="button"
          onClick={mode === 'text' ? switchToImage : switchToText}
          disabled={isLoading}
          className="
            px-6 py-2 rounded-lg font-departure text-sm
            bg-cream/10 hover:bg-cream/20
            border border-cream/30 hover:border-cream/50
            text-cream
            transition-all duration-300
            disabled:opacity-50 disabled:cursor-not-allowed
            backdrop-blur-sm
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
                  w-full min-h-[108px] sm:min-h-[120px] p-4 sm:p-5
                  bg-cream-transparent glass-effect
                  text-black placeholder-gray-600
                  border border-cream/20 rounded-xl
                  resize-none
                  focus:border-cream/40 focus:bg-cream/90
                  transition-all duration-300 ease-in-out
                  disabled:opacity-50 disabled:cursor-not-allowed
                  font-departure text-base leading-relaxed sm:text-lg
                `}
                rows={4}
              />
              
              {/* Send */}
              <button
                type="submit"
                disabled={!textInput.trim() || isLoading}
                className={`
                  absolute bottom-4 right-4
                  px-6 py-2
                  bg-cream/20 hover:bg-cream/5
                  border border-cream/30 hover:border-cream/80
                  text-pure-black text-sm font-departure
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
              <div className="flex justify-end mt-3">
                <button
                  type="submit"
                  disabled={isLoading}
                  className={`
                    px-5 py-2
                    bg-cream/10 hover:bg-cream/20
                    border border-cream/30 hover:border-cream/50
                    text-cream font-departure
                    rounded-md
                    transition-all duration-200
                    disabled:opacity-30 disabled:cursor-not-allowed
                    backdrop-blur-sm
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
