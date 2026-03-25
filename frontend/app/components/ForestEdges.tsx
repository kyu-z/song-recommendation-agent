'use client'

import { useId } from 'react'

/** One tree: soft trunk wash + layered translucent canopy blobs (no hard outlines). */
function WaterTree({
  trunk,
  canopy,
  uid,
  filterBase,
}: {
  trunk: { x: number; y: number; w: number; h: number }
  canopy: { cx: number; cy: number; rx: number; ry: number }[]
  uid: string
  filterBase: string
}) {
  const tg = `t-${uid}`
  const blobs = canopy.map((_, i) => `b-${uid}-${i}`)
  return (
    <g>
      <linearGradient id={tg} x1="0%" y1="0%" x2="0%" y2="100%">
        <stop offset="0%" stopColor="#5c4030" stopOpacity={0.55} />
        <stop offset="45%" stopColor="#3d2818" stopOpacity={0.65} />
        <stop offset="100%" stopColor="#2a1810" stopOpacity={0.45} />
      </linearGradient>
      {canopy.map((c, i) => (
        <radialGradient
          key={blobs[i]}
          id={blobs[i]}
          cx="45%"
          cy="40%"
          r="65%"
        >
          <stop offset="0%" stopColor="#1f3d24" stopOpacity={0.42} />
          <stop offset="55%" stopColor="#1a3320" stopOpacity={0.22} />
          <stop offset="100%" stopColor="#152818" stopOpacity={0} />
        </radialGradient>
      ))}
      {canopy.map((c, i) => (
        <ellipse
          key={i}
          cx={c.cx}
          cy={c.cy}
          rx={c.rx}
          ry={c.ry}
          fill={`url(#${blobs[i]})`}
        />
      ))}
      <rect
        x={trunk.x}
        y={trunk.y}
        width={trunk.w}
        height={trunk.h}
        rx={Math.min(8, trunk.w * 0.35)}
        fill={`url(#${tg})`}
        opacity={0.85}
      />
      {/* Soft side bleed on trunk — watercolor paper edge */}
      <rect
        x={trunk.x - 2}
        y={trunk.y + trunk.h * 0.15}
        width={trunk.w + 4}
        height={trunk.h * 0.55}
        rx={6}
        fill="#2a1810"
        opacity={0.12}
        filter={`url(#${filterBase}-soft)`}
      />
    </g>
  )
}

function EdgeTrees({ mirror }: { mirror?: boolean }) {
  const raw = useId().replace(/:/g, '')
  const uid = `wc-${raw}`

  const trees: {
    trunk: { x: number; y: number; w: number; h: number }
    canopy: { cx: number; cy: number; rx: number; ry: number }[]
  }[] = [
    {
      trunk: { x: 8, y: 585, w: 20, h: 195 },
      canopy: [
        { cx: 18, cy: 520, rx: 38, ry: 32 },
        { cx: 8, cy: 535, rx: 28, ry: 26 },
        { cx: 28, cy: 528, rx: 32, ry: 28 },
        { cx: 18, cy: 548, rx: 36, ry: 22 },
      ],
    },
    {
      trunk: { x: 48, y: 618, w: 17, h: 162 },
      canopy: [
        { cx: 56, cy: 558, rx: 30, ry: 26 },
        { cx: 44, cy: 568, rx: 24, ry: 22 },
        { cx: 62, cy: 565, rx: 26, ry: 24 },
      ],
    },
    {
      trunk: { x: 88, y: 568, w: 22, h: 212 },
      canopy: [
        { cx: 100, cy: 495, rx: 40, ry: 34 },
        { cx: 82, cy: 512, rx: 32, ry: 30 },
        { cx: 108, cy: 505, rx: 34, ry: 28 },
        { cx: 96, cy: 525, rx: 38, ry: 26 },
      ],
    },
  ]

  return (
    <svg
      className="absolute inset-0 h-full w-full mix-blend-multiply"
      viewBox="-42 0 198 800"
      preserveAspectRatio="xMinYMax meet"
      overflow="visible"
      aria-hidden
      style={mirror ? { transform: 'scaleX(-1)' } : undefined}
    >
      <defs>
        <filter
          id={`${uid}-soft`}
          x="-20%"
          y="-20%"
          width="140%"
          height="140%"
        >
          <feGaussianBlur in="SourceGraphic" stdDeviation="4" result="b" />
        </filter>
        <filter
          id={`${uid}-paper`}
          x="-30%"
          y="-30%"
          width="160%"
          height="160%"
        >
          <feTurbulence
            type="fractalNoise"
            baseFrequency="0.045"
            numOctaves="4"
            seed="2"
            result="noise"
          />
          <feDisplacementMap
            in="SourceGraphic"
            in2="noise"
            scale="5"
            xChannelSelector="R"
            yChannelSelector="G"
          />
        </filter>
        <radialGradient id={`${uid}-ground`} cx="50%" cy="100%" r="75%">
          <stop offset="0%" stopColor="#4a3018" stopOpacity={0.35} />
          <stop offset="100%" stopColor="#3d2818" stopOpacity={0} />
        </radialGradient>
      </defs>

      {/* Ground wash — soft ellipse, not a hard bar */}
      <ellipse
        cx="78"
        cy="792"
        rx="110"
        ry="28"
        fill={`url(#${uid}-ground)`}
        opacity={0.9}
      />

      <g
        opacity={0.72}
        filter={`url(#${uid}-paper)`}
      >
        {trees.map((t, i) => (
          <WaterTree
            key={i}
            trunk={t.trunk}
            canopy={t.canopy}
            uid={`${uid}-t${i}`}
            filterBase={uid}
          />
        ))}
      </g>

      {/* Unfiltered duplicate at very low opacity for extra bleed into background */}
      <g opacity={0.18} className="mix-blend-soft-light">
        {trees.map((t, i) => (
          <g key={`ghost-${i}`}>
            {t.canopy.map((c, j) => (
              <ellipse
                key={j}
                cx={c.cx + 3}
                cy={c.cy + 2}
                rx={c.rx * 1.08}
                ry={c.ry * 1.08}
                fill="#1a3320"
              />
            ))}
          </g>
        ))}
      </g>
    </svg>
  )
}

export default function ForestEdges() {
  const layerStyle = { width: 'clamp(140px, 28vw, 200px)' } as const
  /* Softer feather — watercolor vignette, not a hard band */
  const stripMask =
    'linear-gradient(90deg, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0.35) 38%, transparent 78%)'
  const stripMaskR =
    'linear-gradient(270deg, rgba(0,0,0,0.75) 0%, rgba(0,0,0,0.35) 38%, transparent 78%)'

  return (
    <>
      <div
        className="pointer-events-none fixed inset-y-0 left-0 z-[6] hidden overflow-visible sm:block"
        style={layerStyle}
        aria-hidden
      >
        <div
          className="absolute inset-y-0 left-0 w-[min(16vw,100px)] md:w-[min(20vw,128px)] bg-gradient-to-r from-[#964B00]/22 to-transparent"
          style={{ maskImage: stripMask, WebkitMaskImage: stripMask }}
        />
        <EdgeTrees />
      </div>
      <div
        className="pointer-events-none fixed inset-y-0 right-0 z-[6] hidden overflow-visible sm:block"
        style={layerStyle}
        aria-hidden
      >
        <div
          className="absolute inset-y-0 right-0 w-[min(16vw,100px)] md:w-[min(20vw,128px)] bg-gradient-to-l from-[#964B00]/22 to-transparent"
          style={{ maskImage: stripMaskR, WebkitMaskImage: stripMaskR }}
        />
        <EdgeTrees mirror />
      </div>
    </>
  )
}
