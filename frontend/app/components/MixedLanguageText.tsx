'use client'

/**
 * Splits text into CJK (+ common CJK punctuation / fullwidth) vs Latin runs.
 * EB Garamond reads smaller than mono CJK at the same px — we use text-sm vs text-xs.
 */
const SEGMENTS =
  /[\u3400-\u4dbf\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]+|[^\u3400-\u4dbf\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]+/g

export default function MixedLanguageText({
  text,
  className = '',
}: {
  text: string
  className?: string
}) {
  const segments = text.match(SEGMENTS) ?? [text]

  return (
    <span className={className}>
      {segments.map((seg, i) => {
        const isCjk = /[\u3400-\u4dbf\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]/.test(
          seg[0] ?? ''
        )
        return isCjk ? (
          <span key={i} className="font-departure text-xs leading-relaxed">
            {seg}
          </span>
        ) : (
          <span key={i} className="font-eb-garamond text-sm leading-relaxed">
            {seg}
          </span>
        )
      })}
    </span>
  )
}
