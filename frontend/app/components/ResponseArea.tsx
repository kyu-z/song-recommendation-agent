'use client'

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
      <div className="w-full max-w-4xl mx-auto px-6 py-8">
        <div className="border border-cream/20 rounded-lg p-8 glass-effect">
          <div className="text-cream text-center">
            <div className="shoegaze-loading text-lg font-departure">
              > Penetrating the wall of sound...
            </div>
            <div className="mt-4 text-sm opacity-70">
              搜索音乐中，请稍候
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="w-full max-w-4xl mx-auto px-6 py-8">
        <div className="border border-red-500/30 rounded-lg p-8 glass-effect">
          <div className="text-red-400 text-center">
            <div className="text-lg font-departure mb-2">
              连接错误
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
      <div className="w-full max-w-4xl mx-auto px-6 py-8">
        <div className="border border-cream/10 rounded-lg p-8 glass-effect">
          <div className="text-cream/50 text-center text-lg font-departure">
            在这里等待AI的音乐推荐...
          </div>
        </div>
      </div>
    )
  }

  if (!response.success) {
    return (
      <div className="w-full max-w-4xl mx-auto px-6 py-8">
        <div className="border border-cream/20 rounded-lg p-8 glass-effect">
          <div className="text-cream text-center">
            <div className="text-lg font-departure mb-2">
              抱歉，没有找到匹配的音乐
            </div>
            <div className="text-sm opacity-70">
              {response.message || '请尝试用不同的描述方式'}
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="w-full max-w-4xl mx-auto px-6 py-8">
      <div className="border border-cream/20 rounded-lg p-8 glass-effect">
        {/* 搜索信息 */}
        <div className="mb-8 text-cream/70 text-sm font-departure">
          搜索目标: {response.search_goal} | 找到 {response.songs.length} 首歌曲
        </div>

        {/* 歌曲列表 */}
        <div className="space-y-8">
          {response.songs.map((song, index) => (
            <div 
              key={index} 
              className="border-l-2 border-cream/30 pl-6 hover:border-cream/50 transition-colors duration-300"
            >
              {/* 歌曲标题和艺术家 */}
              <div className="mb-3">
                <h3 className="text-xl text-cream font-departure font-semibold">
                  {song.title}
                </h3>
                <p className="text-cream/80 font-departure mt-1">
                  by {song.artist}
                </p>
              </div>

              {/* 推荐理由 */}
              <p className="text-white text-base leading-relaxed mb-4 font-departure">
                {song.reason}
              </p>

              {/* 播放链接 */}
              {song.link && (
                <div className="flex items-center gap-4">
                  <a
                    href={song.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="
                      inline-flex items-center gap-2 
                      px-4 py-2 
                      bg-cream/10 hover:bg-cream/20 
                      border border-cream/30 hover:border-cream/50
                      text-cream text-sm font-departure
                      rounded-md
                      transition-all duration-200
                      backdrop-blur-sm
                    "
                  >
                    🎵 播放
                  </a>
                  {song.platform && (
                    <span className="text-cream/50 text-xs font-departure">
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
