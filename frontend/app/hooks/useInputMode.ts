'use client'

import { useState, useRef } from 'react'

export type InputMode = 'text' | 'image'

export const useInputMode = () => {
  const [mode, setMode] = useState<InputMode>('image')
  const [selectedImage, setSelectedImage] = useState<File | null>(null)
  const [imagePreview, setImagePreview] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const switchToText = () => {
    setMode('text')
    clearImage()
  }

  const switchToImage = () => {
    setMode('image')
  }

  const selectImage = (file: File) => {
    setSelectedImage(file)
    
    // Preview URL for selected image
    const reader = new FileReader()
    reader.onload = (e) => {
      setImagePreview(e.target?.result as string)
    }
    reader.readAsDataURL(file)
  }

  const clearImage = () => {
    setSelectedImage(null)
    setImagePreview(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const triggerFileSelect = () => {
    fileInputRef.current?.click()
  }

  return {
    mode,
    selectedImage,
    imagePreview,
    fileInputRef,
    switchToText,
    switchToImage,
    selectImage,
    clearImage,
    triggerFileSelect
  }
}
