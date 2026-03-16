export default function Loading() {
  return (
    <div className="p-8 animate-pulse">
      <div className="h-8 w-44 bg-secondary rounded mb-1" />
      <div className="h-4 w-64 bg-secondary rounded mb-8" />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="bg-card rounded-lg p-4 border border-border h-24" />
        ))}
      </div>
      <div className="bg-card rounded-lg p-6 border border-border h-32 mb-8" />
      <div className="rounded-lg border border-border overflow-hidden">
        <div className="h-12 bg-secondary" />
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="h-12 border-t border-border flex items-center px-4 gap-4">
            {Array.from({ length: 8 }).map((_, j) => (
              <div key={j} className="h-4 bg-secondary rounded flex-1" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
