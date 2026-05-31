'use client'

import MixedLanguageText from './MixedLanguageText'

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

interface ResponseAreaProps {
  isLoading: boolean
  response: ResponseData | null
  error: string | null
}

const shellClass =
  'border border-cream/20 rounded-lg p-3 sm:p-4 glass-effect bg-black/20'

export default function ResponseArea({ isLoading, response, error }: ResponseAreaProps) {
  if (isLoading) {
    return (
      <div className="w-full">
        <div className={shellClass}>
          <div className="font-eb-garamond text-cream text-center">
            <div className="shoegaze-loading text-base">
              {'> '}Penetrating the wall of sound...
            </div>
            <div className="mt-2 text-xs opacity-70">
              Searching for music…
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="w-full">
        <div className="border border-red-500/30 rounded-lg p-3 sm:p-4 glass-effect bg-black/20">
          <div className="font-eb-garamond text-red-400 text-center">
            <div className="text-base mb-1">
              Connection error
            </div>
            <div className="text-xs opacity-70">
              {error}
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (!response) {
    return (
      <div className="w-full">
        <div className="border border-cream/10 rounded-lg p-3 sm:p-4 glass-effect bg-black/15">
          <div className="font-eb-garamond text-cream/45 text-center text-xs">
            Your recommendations will show up here.
          </div>
        </div>
      </div>
    )
  }

  if (!response.success) {
    return (
      <div className="w-full">
        <div className={shellClass}>
          <div className="font-eb-garamond text-cream text-center">
            <div className="text-base mb-1">
              No matches found
            </div>
            <div className="text-xs opacity-70">
              {response.message || 'Try a different description.'}
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="w-full">
      <div className={`${shellClass} rounded-xl`}>
        <div className="space-y-3">
          {response.songs.map((song, index) => (
            <div 
              key={index} 
              className="rounded-lg border border-cream/10 bg-black/25 p-3 pl-3.5 shadow-sm transition-colors duration-300 hover:border-cream/20"
            >
              <div className="font-eb-garamond mb-1.5">
                <h3 className="text-lg font-semibold text-cream leading-tight">
                  {song.title}
                </h3>
                <p className="mt-0.5 text-sm text-cream/75">
                  by {song.artist}
                </p>
              </div>

              <p className="mb-2 text-sm text-white/90 leading-snug">
                <MixedLanguageText text={song.reason} />
              </p>

              {song.link && (
                <div className="flex items-center gap-3">
                  <a
                    href={song.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="
                      font-departure inline-flex items-center gap-2 
                      px-4 py-1.5 
                      bg-cream/10 hover:bg-cream/15 
                      border border-cream/30 hover:border-cream/45
                      text-cream text-xs font-medium
                      rounded-md
                      transition-all duration-200
                    "
                  >
                    Play
                  </a>
                  {song.platform && (
                    <span className="font-departure text-cream/45 text-xs">
                      {song.platform}
                    </span>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
