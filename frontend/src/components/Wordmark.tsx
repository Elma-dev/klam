export default function Wordmark() {
  return (
    <div className="flex min-w-0 items-center gap-2.5">
      <svg
        width="26"
        height="26"
        viewBox="0 0 26 26"
        aria-hidden
        className="shrink-0 text-accent"
      >
        <rect
          x="1.25"
          y="1.25"
          width="23.5"
          height="23.5"
          rx="7"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.5"
          opacity="0.45"
        />
        <rect x="6.5" y="10" width="13" height="2.3" rx="1.15" fill="currentColor" />
        <rect x="9.5" y="14.6" width="7" height="2.3" rx="1.15" fill="currentColor" opacity="0.6" />
      </svg>
      <span className="flex min-w-0 items-baseline gap-2">
        <span className="truncate font-display text-lg leading-none text-paper">Klam</span>
        <span
          dir="rtl"
          className="hidden truncate font-display text-base leading-none text-muted sm:inline"
        >
          كلام
        </span>
      </span>
    </div>
  )
}
