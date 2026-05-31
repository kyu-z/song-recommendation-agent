'use client'

import { useEffect, useState } from 'react'
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

const PAGE_SIZE = 2

function SongCard({ song }: { song: Song }) {
  return (
    <div className="rounded-lg border border-cream/10 bg-black/25 p-3 pl-3.5 shadow-sm transition-colors duration-300 hover:border-cream/20">
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
  )
}

function PagerArrow({
  direction,
  disabled,
  onClick,
}: {
  direction: 'prev' | 'next'
  disabled: boolean
  onClick: () => void
}) {
  const label = direction === 'prev' ? 'Previous recommendations' : 'Next recommendations'
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      aria-label={label}
      className={`
        flex h-8 w-8 items-center justify-center rounded-md border
        font-departure text-sm transition-colors duration-200
        ${disabled
          ? 'cursor-not-allowed border-cream/10 text-cream/25'
          : 'border-cream/30 text-cream/80 hover:border-cream/50 hover:bg-cream/10'}
      `}
    >
      {direction === 'prev' ? '←' : '→'}
    </button>
  )
}

function PaginatedSongList({ songs }: { songs: Song[] }) {
  const [page, setPage] = useState(0)
  const totalPages = Math.max(1, Math.ceil(songs.length / PAGE_SIZE))
  const canPaginate = songs.length > PAGE_SIZE

  useEffect(() => {
    setPage(0)
  }, [songs])

  useEffect(() => {
    if (page >= totalPages) {
      setPage(Math.max(0, totalPages - 1))
    }
  }, [page, totalPages])

  const start = page * PAGE_SIZE
  const visibleSongs = songs.slice(start, start + PAGE_SIZE)
  const canGoPrev = canPaginate && page > 0
  const canGoNext = canPaginate && page < totalPages - 1

  return (
    <>
      <div className="grid grid-cols-2 gap-3">
        {visibleSongs.map((song, index) => (
          <SongCard key={`${start + index}-${song.title}`} song={song} />
        ))}
      </div>

      <div className="mt-3 flex items-center justify-center gap-6">
        <PagerArrow
          direction="prev"
          disabled={!canGoPrev}
          onClick={() => setPage((p) => p - 1)}
        />
        <PagerArrow
          direction="next"
          disabled={!canGoNext}
          onClick={() => setPage((p) => p + 1)}
        />
      </div>
    </>
  )
}

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
        <PaginatedSongList songs={response.songs} />
      </div>
    </div>
  )
}
