import { useEffect, useState } from 'react'

// Sample captions shown on the upload stage: Arabic-first with a French/English
// code-switch, to make the product's core visible before anything is uploaded.
const CUES = [
  'هاد الفيديو مزيان',
  'code switching بالدارجة',
  'مرحبا بكم',
]

export default function CaptionDemo() {
  const [index, setIndex] = useState(0)

  useEffect(() => {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const id = window.setInterval(() => setIndex((v) => (v + 1) % CUES.length), 2600)
    return () => window.clearInterval(id)
  }, [])

  return (
    <div
      key={index}
      dir="auto"
      className="vox-cue caption-text max-w-[92%] rounded-md px-4 py-2 text-center"
      style={{
        fontFamily: 'var(--font-caption)',
        fontWeight: 700,
        fontSize: 'clamp(20px, 3.4vw, 30px)',
        lineHeight: 1.45,
        color: '#ffffff',
        background: 'rgba(10, 13, 24, 0.55)',
        textShadow: '0 1px 2px rgba(0, 0, 0, 0.9), 0 0 1px rgba(0, 0, 0, 0.9)',
      }}
    >
      {CUES[index]}
    </div>
  )
}
