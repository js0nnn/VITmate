interface LogoMarkProps {
  size?: number;
}

/** The VITmate "V" mark (original artwork, not a VIT asset). */
export function LogoMark({ size = 32 }: LogoMarkProps) {
  return (
    <svg className="logo-mark" width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
      <defs>
        <linearGradient id="vitmate-mark" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#3b82f6" />
          <stop offset="1" stopColor="#1e3a8a" />
        </linearGradient>
      </defs>
      <rect width="64" height="64" rx="16" fill="url(#vitmate-mark)" />
      <path d="M17 20l15 26 15-26" fill="none" stroke="#fff" strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
      <circle cx="47" cy="17" r="5" fill="#fbbf24" />
    </svg>
  );
}

export function Wordmark() {
  return (
    <span className="wordmark">
      VIT<span className="wordmark-accent">mate</span>
    </span>
  );
}
