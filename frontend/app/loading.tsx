export default function Loading() {
  return (
    <div className="p-8 animate-pulse">
      <div className="h-8 w-48 bg-secondary rounded mb-2" />
      <div className="h-4 w-64 bg-secondary rounded mb-10" />
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-10">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="bg-card rounded-lg p-5 border border-border h-20" />
        ))}
      </div>
      <div className="h-6 w-48 bg-secondary rounded mb-4" />
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="bg-card rounded-lg p-4 border border-border h-40" />
        ))}
      </div>
    </div>
  );
}
