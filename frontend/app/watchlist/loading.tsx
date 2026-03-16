export default function Loading() {
  return (
    <div className="p-8 animate-pulse">
      <div className="h-8 w-32 bg-secondary rounded mb-6" />
      <div className="rounded-lg border border-border overflow-hidden">
        <div className="h-12 bg-secondary" />
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-14 border-t border-border flex items-center px-4 gap-4">
            {Array.from({ length: 7 }).map((_, j) => (
              <div key={j} className="h-4 bg-secondary rounded flex-1" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
