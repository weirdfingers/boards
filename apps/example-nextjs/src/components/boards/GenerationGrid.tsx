import { ArtifactPreview } from "./ArtifactPreview";

interface Generation {
  id: string;
  artifactType: string;
  storageUrl?: string | null;
  thumbnailUrl?: string | null;
  status: string;
  errorMessage?: string | null;
  createdAt: string;
}

interface GenerationGridProps {
  generations: Generation[];
  onGenerationClick?: (generation: Generation) => void;
}

export function GenerationGrid({
  generations,
  onGenerationClick,
}: GenerationGridProps) {
  // Sort generations: newest last
  const sortedGenerations = [...generations].sort(
    (a, b) =>
      new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime()
  );

  if (sortedGenerations.length === 0) {
    return (
      <div className="flex items-center justify-center py-12 text-gray-500">
        <p>No generations yet. Create your first one below!</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      {sortedGenerations.map((generation) => (
        <ArtifactPreview
          key={generation.id}
          artifactType={generation.artifactType}
          storageUrl={generation.storageUrl}
          thumbnailUrl={generation.thumbnailUrl}
          status={generation.status}
          errorMessage={generation.errorMessage}
          onClick={() => onGenerationClick?.(generation)}
        />
      ))}
    </div>
  );
}
