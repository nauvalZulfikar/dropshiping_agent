export default function Loading() {
  return (
    <div className="p-8 animate-pulse">
      <div className="h-8 w-32 bg-secondary rounded mb-1" />
      <div className="h-4 w-24 bg-secondary rounded mb-6" />
      <div className="flex gap-4 mb-6">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-10 w-32 bg-card border border-border rounded" />
        ))}
      </div>
      <div className="rounded-lg border border-border overflow-hidden">
        <div className="h-12 bg-secondary" />
        {Array.from({ length: 10 }).map((_, i) => (
          <div key={i} className="h-14 border-t border-border flex items-center px-4 gap-4">
            {Array.from({ length: 8 }).map((_, j) => (
              <div key={j} className="h-4 bg-secondary rounded flex-1" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
