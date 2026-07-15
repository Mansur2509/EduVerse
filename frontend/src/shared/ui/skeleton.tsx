export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded-sm bg-muted-foreground/15 motion-reduce:animate-none ${className}`}
    />
  );
}

export function SkeletonCard({ className = "" }: { className?: string }) {
  return (
    <div className={`rounded-sm border bg-card p-5 ${className}`}>
      <div className="space-y-3">
        <Skeleton className="h-3 w-1/3" />
        <Skeleton className="h-4 w-2/3" />
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-5/6" />
        <div className="flex gap-2 pt-2">
          <Skeleton className="h-8 w-20" />
          <Skeleton className="h-8 w-20" />
        </div>
      </div>
    </div>
  );
}

export function SkeletonRow({ className = "" }: { className?: string }) {
  return (
    <div className={`rounded-sm border bg-card p-4 ${className}`}>
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0 flex-1 space-y-2">
          <Skeleton className="h-4 w-1/2" />
          <Skeleton className="h-3 w-1/3" />
        </div>
        <Skeleton className="h-8 w-20 shrink-0" />
      </div>
    </div>
  );
}

export function SkeletonCards({ count = 6, className = "" }: { count?: number; className?: string }) {
  return (
    <>
      {Array.from({ length: count }, (_item, index) => (
        <SkeletonCard className={className} key={index} />
      ))}
    </>
  );
}

export function SkeletonRows({ count = 6, className = "" }: { count?: number; className?: string }) {
  return (
    <>
      {Array.from({ length: count }, (_item, index) => (
        <SkeletonRow className={className} key={index} />
      ))}
    </>
  );
}

export function SkeletonText({ lines = 1, className = "" }: { lines?: number; className?: string }) {
  return (
    <div className={`space-y-2 ${className}`}>
      {Array.from({ length: lines }, (_item, index) => (
        <Skeleton className={index === lines - 1 && lines > 1 ? "h-3 w-2/3" : "h-3 w-full"} key={index} />
      ))}
    </div>
  );
}

export function SkeletonTable({
  rows = 5,
  columns = 4,
  className = ""
}: {
  rows?: number;
  columns?: number;
  className?: string;
}) {
  return (
    <div className={`overflow-hidden rounded-sm border ${className}`}>
      {Array.from({ length: rows }, (_row, rowIndex) => (
        <div
          className="flex items-center gap-4 border-b bg-card p-3 last:border-b-0"
          key={rowIndex}
        >
          {Array.from({ length: columns }, (_column, columnIndex) => (
            <Skeleton
              className={columnIndex === 0 ? "h-3 flex-[2]" : "h-3 flex-1"}
              key={columnIndex}
            />
          ))}
        </div>
      ))}
    </div>
  );
}
