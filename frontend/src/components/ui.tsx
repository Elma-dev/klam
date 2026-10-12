// Shared primitives: icons, buttons, and labelled form rows. Keeping these in
// one place is what makes the panels consistent — every control gets the same
// hit area, label column, and focus treatment.

import type { ButtonHTMLAttributes, ReactNode } from 'react'

/* ------------------------------------------------------------------ icons */

type IconProps = { className?: string }

function Svg({ className = 'h-4 w-4', children }: { className?: string; children: ReactNode }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      className={className}
    >
      {children}
    </svg>
  )
}

export const IconUndo = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="M9 14 4 9l5-5" />
    <path d="M4 9h11a5 5 0 0 1 0 10h-3" />
  </Svg>
)

export const IconRedo = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="m15 14 5-5-5-5" />
    <path d="M20 9H9a5 5 0 0 0 0 10h3" />
  </Svg>
)

export const IconSun = ({ className }: IconProps) => (
  <Svg className={className}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M6.3 17.7l-1.4 1.4M19.1 4.9l-1.4 1.4" />
  </Svg>
)

export const IconMoon = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z" />
  </Svg>
)

export const IconPlus = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="M12 5v14M5 12h14" />
  </Svg>
)

export const IconClose = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="M18 6 6 18M6 6l12 12" />
  </Svg>
)

export const IconTrash = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="M3 6h18M8 6V4h8v2M19 6l-1 14H6L5 6" />
    <path d="M10 11v6M14 11v6" />
  </Svg>
)

export const IconChevron = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="m6 9 6 6 6-6" />
  </Svg>
)

export const IconUpload = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="M12 16V4m0 0L8 8m4-4 4 4" />
    <path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
  </Svg>
)

export const IconDownload = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="M12 4v12m0 0 4-4m-4 4-4-4" />
    <path d="M4 18v1a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-1" />
  </Svg>
)

export const IconCheck = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="m4 12.5 5 5L20 6.5" />
  </Svg>
)

export const IconAlert = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="M12 8v5M12 16.5v.5" />
    <circle cx="12" cy="12" r="9" />
  </Svg>
)

export const IconBookmark = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="M6 4h12v16l-6-4-6 4V4Z" />
  </Svg>
)

export const IconList = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="M4 7h16M4 12h16M4 17h10" />
  </Svg>
)

export const IconPalette = ({ className }: IconProps) => (
  <Svg className={className}>
    <path d="M12 3a9 9 0 1 0 0 18h1.5a2 2 0 0 0 1.4-3.4 2 2 0 0 1 1.4-3.4H18a3 3 0 0 0 3-3A6 6 0 0 0 12 3Z" />
    <path d="M8 9v.01M12 7v.01M16 9v.01" />
  </Svg>
)

/* ---------------------------------------------------------------- buttons */

type Variant = 'primary' | 'outline' | 'ghost' | 'danger'
type Size = 'sm' | 'md' | 'icon'

const VARIANT: Record<Variant, string> = {
  primary:
    'bg-accent text-on-accent font-semibold hover:bg-accent/90 active:bg-accent/80 disabled:bg-line disabled:text-muted',
  outline:
    'border border-line text-muted hover:border-accent hover:text-paper disabled:hover:border-line disabled:hover:text-muted',
  ghost: 'text-muted hover:bg-surface-2 hover:text-paper',
  danger: 'text-danger hover:bg-danger/10',
}

const SIZE: Record<Size, string> = {
  sm: 'h-9 gap-1.5 rounded-lg px-3 text-[13px]',
  md: 'h-11 gap-2 rounded-xl px-4 text-sm',
  // Icons are 40px on pointer devices and grow to a 44px touch target on small
  // screens, where these controls are tapped rather than clicked.
  icon: 'h-10 w-10 rounded-lg sm:w-10 max-sm:h-11 max-sm:w-11',
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant
  size?: Size
}

export function Button({
  variant = 'outline',
  size = 'sm',
  className = '',
  ...props
}: ButtonProps) {
  return (
    <button
      {...props}
      className={`inline-flex shrink-0 cursor-pointer items-center justify-center whitespace-nowrap transition-colors duration-150 disabled:cursor-not-allowed ${
        VARIANT[variant]
      } ${SIZE[size]} ${className}`}
    />
  )
}

export function IconButton({
  label,
  variant = 'ghost',
  className = '',
  ...props
}: Omit<ButtonProps, 'size'> & { label: string }) {
  return (
    <Button
      {...props}
      variant={variant}
      size="icon"
      aria-label={props['aria-label'] ?? label}
      title={props.title ?? label}
      className={className}
    />
  )
}

/* ------------------------------------------------------------ form rows */

function RowShell({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="w-24 shrink-0 truncate text-muted">{label}</span>
      {children}
    </div>
  )
}

export function SliderRow({
  label,
  value,
  min,
  max,
  step = 1,
  suffix,
  onChange,
}: {
  label: string
  value: number
  min: number
  max: number
  step?: number
  suffix?: string
  onChange: (v: number) => void
}) {
  return (
    <label className="flex items-center gap-3 text-sm">
      <span className="w-24 shrink-0 truncate text-muted">{label}</span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="range min-w-0 flex-1"
      />
      <span className="tnum w-11 shrink-0 text-end text-[11px] text-muted">
        {Number.isInteger(value) ? value : value.toFixed(2)}
        {suffix}
      </span>
    </label>
  )
}

export function ColorRow({
  label,
  value,
  onChange,
}: {
  label: string
  value: string
  onChange: (v: string) => void
}) {
  return (
    <label className="flex min-h-9 items-center gap-3 text-sm">
      <span className="w-24 shrink-0 truncate text-muted">{label}</span>
      <input
        type="color"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-8 w-10 cursor-pointer rounded-md border border-line bg-surface-2 p-0.5"
      />
      <span className="tnum text-[11px] uppercase text-muted">{value}</span>
    </label>
  )
}

export function SelectRow<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: T
  options: { value: T; label: string }[]
  onChange: (v: T) => void
}) {
  return (
    <RowShell label={label}>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as T)}
        className="h-9 min-w-0 flex-1 cursor-pointer rounded-lg border border-line bg-surface-2 px-2 text-paper"
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </RowShell>
  )
}

export function ToggleRow({
  label,
  value,
  onChange,
}: {
  label: string
  value: boolean
  onChange: (v: boolean) => void
}) {
  return (
    <label className="flex min-h-9 cursor-pointer items-center gap-3 text-sm">
      <span className="w-24 shrink-0 truncate text-muted">{label}</span>
      <button
        type="button"
        role="switch"
        aria-checked={value}
        onClick={() => onChange(!value)}
        className={`relative h-6 w-11 shrink-0 cursor-pointer rounded-full border transition-colors ${
          value ? 'border-accent bg-accent' : 'border-line bg-surface-2'
        }`}
      >
        <span
          className={`absolute top-0.5 h-4 w-4 rounded-full transition-all ${
            value ? 'start-[22px] bg-ink' : 'start-0.5 bg-muted'
          }`}
        />
      </button>
    </label>
  )
}

/* -------------------------------------------------------------- segmented */

export function Segmented<T extends string>({
  value,
  options,
  onChange,
  ariaLabel,
}: {
  value: T
  options: { value: T; label: string }[]
  onChange: (v: T) => void
  ariaLabel?: string
}) {
  return (
    <div
      role="tablist"
      aria-label={ariaLabel}
      className="flex gap-1 rounded-xl border border-line bg-surface p-1"
    >
      {options.map((o) => {
        const active = o.value === value
        return (
          <button
            key={o.value}
            role="tab"
            aria-selected={active}
            onClick={() => onChange(o.value)}
            className={`h-9 flex-1 cursor-pointer rounded-lg text-[13px] transition-colors ${
              active ? 'bg-accent font-semibold text-on-accent' : 'text-muted hover:text-paper'
            }`}
          >
            {o.label}
          </button>
        )
      })}
    </div>
  )
}

/* ----------------------------------------------------------------- misc */
