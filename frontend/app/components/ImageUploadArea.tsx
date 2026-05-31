'use client'

import React, { useState, DragEvent } from 'react'

interface ImageUploadAreaProps {
  selectedImage: File | null
  imagePreview: string | null
  onImageSelect: (file: File) => void
  onClearImage: () => void
  onTriggerFileSelect: () => void
  isLoading: boolean
}

export default function ImageUploadArea({
  selectedImage,
  imagePreview,
  onImageSelect,
  onClearImage,
  onTriggerFileSelect,
  isLoading
}: ImageUploadAreaProps) {
  const [isDragOver, setIsDragOver] = useState(false)

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragOver(true)
  }

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragOver(false)
  }

  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setIsDragOver(false)
    
    const files = Array.from(e.dataTransfer.files)
    const imageFile = files.find(file => 
      file.type.startsWith('image/') && 
      ['image/jpeg', 'image/jpg', 'image/png'].includes(file.type)
    )
    
    if (imageFile) {
      onImageSelect(imageFile)
    }
  }

  if (selectedImage && imagePreview) {
    return (
      <div className="fade-in">
        <div className="relative">
          <img
            src={imagePreview}
            alt="Selected"
            className="w-full max-h-32 object-contain rounded-lg border border-cream/20"
          />
          <button
            onClick={onClearImage}
            disabled={isLoading}
            className="
              absolute top-2 right-2
              w-8 h-8 rounded-full
              bg-black/80 hover:bg-black
              border border-cream/30 hover:border-cream/50
              text-cream text-sm
              transition-all duration-200
              disabled:opacity-50 disabled:cursor-not-allowed
              backdrop-blur-sm
            "
          >
            ×
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="fade-in">
      <div
        className={`
          image-drop-zone w-full rounded-xl px-4 py-4 sm:py-5 text-center cursor-pointer
          bg-cream/5 hover:bg-cream/10
          transition-all duration-300
          ${isDragOver ? 'dragover' : ''}
          ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}
        `}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={!isLoading ? onTriggerFileSelect : undefined}
      >
        <div className="space-y-2">
          <div className="font-eb-garamond text-2xl leading-none text-cream/45">
            +
          </div>
          
          <div className="font-eb-garamond text-sm text-cream sm:text-base">
            {isDragOver 
              ? 'Drop to upload' 
              : 'Click or drag an image here'
            }
          </div>
          
          <div className="font-eb-garamond text-cream/55 space-y-0.5 text-xs leading-snug">
            <p>JPG or PNG</p>
            <p>We read the mood of your image and suggest music to match.</p>
          </div>
          
          <button
            type="button"
            disabled={isLoading}
            className="
              inline-flex items-center gap-2
              px-4 py-1.5 mt-2
              bg-cream/10 hover:bg-cream/20
              border border-cream/30 hover:border-cream/50
              text-cream text-xs font-departure
              rounded-md
              transition-all duration-200
              disabled:opacity-50 disabled:cursor-not-allowed
              backdrop-blur-sm
            "
          >
            Browse
          </button>
        </div>
      </div>
    </div>
  )
}
