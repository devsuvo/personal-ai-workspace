interface BrandMarkProps {
  className?: string;
}

export function BrandMark({ className = 'w-7 h-7' }: BrandMarkProps) {
  return (
    <svg
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      className={className}
      aria-hidden="true"
    >
      <rect
        x="2"
        y="2"
        width="28"
        height="28"
        rx="8"
        className="fill-accent/15 stroke-accent"
        strokeWidth="1.5"
      />
      <path
        d="M16 8.5L22.5 16L16 23.5L9.5 16L16 8.5Z"
        className="stroke-accent"
        strokeWidth="1.75"
        strokeLinejoin="round"
      />
      <circle cx="16" cy="16" r="2.25" className="fill-accent" />
    </svg>
  );
}
