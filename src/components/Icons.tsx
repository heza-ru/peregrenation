type LogoProps = {
  size?: number
  stroke?: string
  fill?: string
  className?: string
}

export function Logo({
  size = 44,
  stroke = 'currentColor',
  fill = 'currentColor',
  className,
}: LogoProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 48 48"
      fill="none"
      stroke={stroke}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      className={className}
    >
      <path d="M9 45 V21 A15 15 0 0 1 39 21 V45" strokeWidth="1.9" />
      <path d="M13.5 45 V22 A10.5 10.5 0 0 1 34.5 22 V45" strokeWidth="0.9" />
      <path d="M13.5 34 H34.5" strokeWidth="0.8" />
      <path
        d="M24 34 L13.5 45 M24 34 L19 45 M24 34 L24 45 M24 34 L29 45 M24 34 L34.5 45"
        strokeWidth="0.8"
      />
      <path d="M13.5 35.6 H34.5 M13.5 38.2 H34.5 M13.5 42.2 H34.5" strokeWidth="0.55" />
      <path d="M5 45.2 H43" strokeWidth="1.9" />
      <path
        d="M24 17.2 L25.3 22.7 L30.8 24 L25.3 25.3 L24 30.8 L22.7 25.3 L17.2 24 L22.7 22.7 Z"
        fill={fill}
        stroke="none"
      />
      <path d="M24 3.4 L26.4 6 L24 8.6 L21.6 6 Z" fill={fill} stroke="none" />
    </svg>
  )
}

export function StarIcon({ size = 12, fill = '#A8843C' }: { size?: number; fill?: string }) {
  return (
    <svg width={size} height={size} viewBox="0 0 14 14" fill={fill} aria-hidden="true">
      <path d="M7 0 L8.4 5.6 L14 7 L8.4 8.4 L7 14 L5.6 8.4 L0 7 L5.6 5.6 Z" />
    </svg>
  )
}
