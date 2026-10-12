export default function Wordmark() {
  return (
    <div className="flex min-w-0 items-center gap-2.5">
      {/* The app icon: brand colours, deliberately not theme tokens, because a
          logo does not change with the theme. */}
      <svg
        width="26"
        height="26"
        viewBox="0 0 256 256"
        aria-hidden
        className="shrink-0"
      >
        <rect width="256" height="256" rx="56" fill="#FF5C38" />
        <g fill="#F3F5F7" transform="translate(44.51 207.5) scale(0.23)">
          <path d="M40 -150H556Q616 -150 616 -210V-741H736V-210Q736 -102 692.5 -51.0Q649 0 556 0H40ZM254 -311 411 -385 409 -392H329Q254 -392 254 -462Q254 -497 277.0 -519.0Q300 -541 343 -566L409 -604L445 -544L322 -475L324 -467H402Q479 -467 479 -405Q479 -369 458.5 -346.0Q438 -323 396 -302L287 -247Z" />
        </g>
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
