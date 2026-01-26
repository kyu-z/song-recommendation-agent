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
      <div className="fade-in space-y-4">
        {/* 图片预览 */}
        <div className="relative">
          <img
            src={imagePreview}
            alt="Selected"
            className="w-full max-h-64 object-contain rounded-lg border border-cream/20"
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

        {/* 文件信息 */}
        <div className="text-cream/70 text-sm font-departure">
          <p>📁 {selectedImage.name}</p>
          <p>📊 {(selectedImage.size / 1024 / 1024).toFixed(2)} MB</p>
        </div>
      </div>
    )
  }

  return (
    <div className="fade-in">
      <div
        className={`
          image-drop-zone rounded-lg p-8 text-center cursor-pointer
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
        <div className="space-y-4">
          {/* 图标 */}
          <div className="text-4xl text-cream/60">
            📷
          </div>
          
          {/* 主要文字 */}
          <div className="text-cream text-lg font-departure">
            {isDragOver 
              ? '松开以上传图片' 
              : '点击选择图片或拖拽到此处'
            }
          </div>
          
          {/* 说明文字 */}
          <div className="text-cream/60 text-sm font-departure space-y-1">
            <p>支持 JPG、PNG 格式</p>
            <p>AI将分析图片的视觉意境，为你推荐匹配的音乐</p>
          </div>
          
          {/* 选择按钮 */}
          <button
            type="button"
            disabled={isLoading}
            className="
              inline-flex items-center gap-2
              px-6 py-3 mt-4
              bg-cream/10 hover:bg-cream/20
              border border-cream/30 hover:border-cream/50
              text-cream font-departure
              rounded-md
              transition-all duration-200
              disabled:opacity-50 disabled:cursor-not-allowed
              backdrop-blur-sm
            "
          >
            📂 浏览文件
          </button>
        </div>
      </div>
    </div>
  )
}
