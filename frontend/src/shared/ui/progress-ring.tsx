const TONE_STROKE: Record<"success" | "accent" | "info" | "recommendation" | "primary", string> = {
  success: "stroke-success",
  accent: "stroke-accent",
  info: "stroke-info",
  recommendation: "stroke-recommendation",
  primary: "stroke-primary"
};

const TONE_TEXT: Record<"success" | "accent" | "info" | "recommendation" | "primary", string> = {
  success: "text-success",
  accent: "text-accent",
  info: "text-info",
  recommendation: "text-recommendation",
  primary: "text-primary"
};

/**
 * Compact circular progress indicator. `percentage: null` renders an empty
 * track with a "—" center (matches the loading-state convention used
 * elsewhere on the dashboard) instead of a misleading 0%.
 */
export function ProgressRing({
  percentage,
  tone = "accent",
  size = 56,
  strokeWidth = 5,
  label
}: {
  percentage: number | null;
  tone?: "success" | "accent" | "info" | "recommendation" | "primary";
  size?: number;
  strokeWidth?: number;
  label: string;
}) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = percentage === null ? 0 : Math.max(0, Math.min(100, percentage));
  const offset = circumference * (1 - clamped / 100);

  return (
    <div
      aria-label={label}
      aria-valuemax={100}
      aria-valuemin={0}
      aria-valuenow={percentage ?? undefined}
      className="relative inline-grid shrink-0 place-items-center"
      role="progressbar"
      style={{ width: size, height: size }}
    >
      <svg className="-rotate-90" height={size} width={size}>
        <circle
          className="stroke-elevated"
          cx={size / 2}
          cy={size / 2}
          fill="none"
          r={radius}
          strokeWidth={strokeWidth}
        />
        {percentage !== null ? (
          <circle
            className={`${TONE_STROKE[tone]} transition-[stroke-dashoffset] duration-slow ease-academic`}
            cx={size / 2}
            cy={size / 2}
            fill="none"
            r={radius}
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            strokeWidth={strokeWidth}
          />
        ) : null}
      </svg>
      <span className={`absolute text-sm font-semibold ${percentage === null ? "text-muted-foreground" : TONE_TEXT[tone]}`}>
        {percentage === null ? "—" : `${Math.round(percentage)}%`}
      </span>
    </div>
  );
}
