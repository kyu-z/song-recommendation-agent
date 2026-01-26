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
    <div className="w-full max-w-4xl mx-auto px-6 py-8">
      {/* 模式切换按钮 */}
      <div className="flex justify-center mb-6">
        <div className="flex bg-cream/5 rounded-lg p-1 glass-effect border border-cream/20">
          <button
            type="button"
            onClick={switchToText}
            disabled={isLoading}
            className={`
              mode-switch-button px-6 py-2 rounded-md font-departure text-sm
              transition-all duration-300
              disabled:opacity-50 disabled:cursor-not-allowed
              ${mode === 'text' 
                ? 'bg-cream/20 text-cream border border-cream/40' 
                : 'text-cream/70 hover:text-cream hover:bg-cream/10'
              }
            `}
          >
            📝 文字输入
          </button>
          <button
            type="button"
            onClick={switchToImage}
            disabled={isLoading}
            className={`
              mode-switch-button px-6 py-2 rounded-md font-departure text-sm
              transition-all duration-300
              disabled:opacity-50 disabled:cursor-not-allowed
              ${mode === 'image' 
                ? 'bg-cream/20 text-cream border border-cream/40' 
                : 'text-cream/70 hover:text-cream hover:bg-cream/10'
              }
            `}
          >
            📷 图片输入
          </button>
        </div>
      </div>

      {/* 输入区域 */}
      <div className="input-mode-transition">
        {mode === 'text' ? (
          <form onSubmit={handleTextSubmit} className="relative fade-in">
            <div className="relative">
              <textarea
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
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
                disabled={!textInput.trim() || isLoading}
                className={`
                  absolute bottom-4 right-4
                  px-6 py-2
                  bg-cream/20 hover:bg-cream/40
                  border border-cream/50 hover:border-cream/80
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
        ) : (
          <form onSubmit={handleImageSubmit} className="relative fade-in">
            {/* 隐藏的文件输入 */}
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept="image/jpeg,image/jpg,image/png"
              className="hidden"
            />

            {/* 图片上传区域 */}
            <ImageUploadArea
              selectedImage={selectedImage}
              imagePreview={imagePreview}
              onImageSelect={selectImage}
              onClearImage={clearImage}
              onTriggerFileSelect={triggerFileSelect}
              isLoading={isLoading}
            />

            {/* 发送按钮 - 仅在有图片时显示 */}
            {selectedImage && (
              <div className="flex justify-end mt-4">
                <button
                  type="submit"
                  disabled={isLoading}
                  className={`
                    px-8 py-3
                    bg-cream/10 hover:bg-cream/20
                    border border-cream/30 hover:border-cream/50
                    text-cream font-departure
                    rounded-md
                    transition-all duration-200
                    disabled:opacity-30 disabled:cursor-not-allowed
                    backdrop-blur-sm
                  `}
                >
                  {isLoading ? 'Analyzing...' : '🎵 分析图片推荐音乐'}
                </button>
              </div>
            )}
          </form>
        )}
      </div>
    </div>
  )
}
