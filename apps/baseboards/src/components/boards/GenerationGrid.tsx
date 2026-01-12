import { useState } from "react";
import { useGeneratorSelection, useGeneration } from "@weirdfingers/boards";
import { ArtifactPreview } from "./ArtifactPreview";
import { useToast } from "@/components/ui/use-toast";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";

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
  onRemoveSuccess?: () => void;
}

export function GenerationGrid({
  generations,
  onGenerationClick,
  onRemoveSuccess: onRemoveSuccess,
}: GenerationGridProps) {
  const { canArtifactBeAdded, addArtifactToSlot } = useGeneratorSelection();
  const { deleteGeneration } = useGeneration();
  const { toast } = useToast();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [generationToDelete, setGenerationToDelete] =
    useState<Generation | null>(null);

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
      url.searchParams.set("download", "true");
      url.searchParams.set("filename", `gen-${generation.id}`);

      // Create temporary anchor and trigger download
      const link = document.createElement("a");
      link.href = url.toString();
      link.target = "_blank";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (error) {
      console.error("Failed to download file:", error);
      // Fallback to opening in new tab if download fails
      window.open(generation.storageUrl, "_blank");
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
      const generationInput = document.getElementById("generation-input");
      if (generationInput) {
        generationInput.scrollIntoView({
          behavior: "smooth",
          block: "nearest",
        });
      }
    }
  };

  const handleDeleteClick = (generation: Generation) => {
    setGenerationToDelete(generation);
    setDeleteDialogOpen(true);
  };

  const handleDeleteConfirm = async () => {
    if (!generationToDelete) return;

    try {
      await deleteGeneration(generationToDelete.id);
      toast({
        title: "Generation deleted",
        description: "The generation has been permanently removed.",
      });
      setDeleteDialogOpen(false);
      setGenerationToDelete(null);
      // Refresh the board data to update the generations list
      onRemoveSuccess?.();
    } catch (error) {
      console.error("Failed to delete generation:", error);
      toast({
        title: "Failed to delete generation",
        description:
          error instanceof Error ? error.message : "An unknown error occurred",
        variant: "destructive",
      });
      setDeleteDialogOpen(false);
    }
  };

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
      {generations.map((generation) => {
        const canAdd =
          generation.status === "COMPLETED" &&
          canArtifactBeAdded(generation.artifactType);

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
            onDelete={() => handleDeleteClick(generation)}
          />
        );
      })}

      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete generation?</AlertDialogTitle>
            <AlertDialogDescription>
              This action cannot be undone. The generation will be permanently
              deleted.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDeleteConfirm}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
