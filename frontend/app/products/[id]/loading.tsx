export default function Loading() {
  return (
    <div className="p-8 max-w-5xl animate-pulse">
      <div className="h-4 w-40 bg-secondary rounded mb-6" />
      <div className="flex gap-6 mb-8">
        <div className="w-48 h-48 bg-card border border-border rounded-lg flex-shrink-0" />
        <div className="flex-1 space-y-3">
          <div className="h-7 bg-secondary rounded w-3/4" />
          <div className="h-4 bg-secondary rounded w-32" />
          <div className="h-9 bg-secondary rounded w-40 mt-4" />
          <div className="flex gap-4 mt-3">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="h-4 bg-secondary rounded w-24" />
            ))}
          </div>
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
        <div className="bg-card rounded-lg p-5 border border-border h-52" />
        <div className="bg-card rounded-lg p-5 border border-border h-52" />
      </div>
      <div className="bg-card rounded-lg p-4 border border-border h-64 mb-8" />
    </div>
  );
}
