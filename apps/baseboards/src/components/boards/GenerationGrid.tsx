import { useGeneratorSelection } from "@weirdfingers/boards";
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
  const { canArtifactBeAdded, addArtifactToSlot } = useGeneratorSelection();

  if (generations.length === 0) {
    return (
      <div className="flex items-center justify-center py-12 text-muted-foreground">
        <p>No generations yet. Create your first one below!</p>
      </div>
    );
  }

  const handleDownload = async (generation: Generation) => {
    if (!generation.storageUrl) return;

    try {
      // Add download query parameter to force download instead of inline preview
      // Also add custom filename based on generation ID
      const url = new URL(generation.storageUrl);
      url.searchParams.set('download', 'true');
      url.searchParams.set('filename', `gen-${generation.id}`);

      // Create temporary anchor and trigger download
      const link = document.createElement('a');
      link.href = url.toString();
      link.target = '_blank';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      console.error('Failed to download file:', error);
      // Fallback to opening in new tab if download fails
      window.open(generation.storageUrl, '_blank');
    }
  };

  const handlePreview = (generation: Generation) => {
    // For now, use the same handler as onClick
    onGenerationClick?.(generation);
  };

  const handleAddToSlot = (generation: Generation) => {
    const success = addArtifactToSlot({
      id: generation.id,
      artifactType: generation.artifactType,
      storageUrl: generation.storageUrl,
      thumbnailUrl: generation.thumbnailUrl,
    });

    if (success) {
      // Scroll to the generation input to show the user where the artifact was added
      const generationInput = document.getElementById('generation-input');
      if (generationInput) {
        generationInput.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }
  };

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      {generations.map((generation) => {
        const canAdd = generation.status === "COMPLETED" && canArtifactBeAdded(generation.artifactType);

        return (
          <ArtifactPreview
            key={generation.id}
            artifactId={generation.id}
            artifactType={generation.artifactType}
            storageUrl={generation.storageUrl}
            thumbnailUrl={generation.thumbnailUrl}
            status={generation.status}
            errorMessage={generation.errorMessage}
            onClick={() => onGenerationClick?.(generation)}
            onAddToSlot={() => handleAddToSlot(generation)}
            canAddToSlot={canAdd}
            onDownload={() => handleDownload(generation)}
            onPreview={() => handlePreview(generation)}
          />
        );
      })}
    </div>
  );
}
