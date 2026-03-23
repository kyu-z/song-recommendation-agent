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

export default function ResponseArea({ isLoading, response, error }: ResponseAreaProps) {
  if (isLoading) {
    return (
      <div className="w-full py-3 sm:py-4">
        <div className="border border-cream/20 rounded-lg p-5 sm:p-6 glass-effect">
          <div className="font-eb-garamond text-cream text-center">
            <div className="shoegaze-loading text-lg">
              {'> '}Penetrating the wall of sound...
            </div>
            <div className="mt-3 text-sm opacity-70">
              Searching for music…
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="w-full py-3 sm:py-4">
        <div className="border border-red-500/30 rounded-lg p-5 sm:p-6 glass-effect">
          <div className="font-eb-garamond text-red-400 text-center">
            <div className="text-lg mb-2">
              Connection error
            </div>
            <div className="text-sm opacity-70">
              {error}
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (!response) {
    return (
      <div className="w-full py-3 sm:py-4">
        <div className="border border-cream/10 rounded-lg p-5 sm:p-6 glass-effect">
          <div className="font-eb-garamond text-cream/50 text-center text-sm">
            Your recommendations will show up here.
          </div>
        </div>
      </div>
    )
  }

  if (!response.success) {
    return (
      <div className="w-full py-3 sm:py-4">
        <div className="border border-cream/20 rounded-lg p-5 sm:p-6 glass-effect">
          <div className="font-eb-garamond text-cream text-center">
            <div className="text-lg mb-2">
              No matches found
            </div>
            <div className="text-sm opacity-70">
              {response.message || 'Try a different description.'}
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="w-full py-3 sm:py-4">
      <div className="border border-cream/20 rounded-xl p-4 sm:p-6 glass-effect">
        <div className="space-y-5 sm:space-y-6">
          {response.songs.map((song, index) => (
            <div 
              key={index} 
              className="rounded-lg border border-cream/10 bg-black/15 p-4 sm:p-5 pl-5 sm:pl-6 shadow-sm transition-colors duration-300 hover:border-cream/25"
            >
              <div className="font-eb-garamond mb-2">
                <h3 className="text-xl font-semibold text-cream">
                  {song.title}
                </h3>
                <p className="mt-1 text-cream/80">
                  by {song.artist}
                </p>
              </div>

              <p className="mb-3 text-white">
                <MixedLanguageText text={song.reason} />
              </p>

              {song.link && (
                <div className="flex items-center gap-4">
                  <a
                    href={song.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="
                      font-departure inline-flex items-center gap-2 
                      px-5 py-2.5 
                      bg-[#143805] hover:bg-[#1a5208] 
                      border border-cream/35 hover:border-cream/55
                      text-cream text-sm font-medium
                      rounded-md
                      shadow-md transition-all duration-200
                    "
                  >
                    Play
                  </a>
                  {song.platform && (
                    <span className="font-departure text-cream/50 text-xs">
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
