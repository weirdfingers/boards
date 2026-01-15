import { useState, useCallback } from "react";
import {
  useGeneratorSelection,
  useGeneration,
  useMultiUpload,
  ArtifactType,
} from "@weirdfingers/boards";
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
  boardId: string;
  onGenerationClick?: (generation: Generation) => void;
  onRemoveSuccess?: () => void;
}

export function GenerationGrid({
  generations,
  boardId,
  onGenerationClick,
  onRemoveSuccess: onRemoveSuccess,
}: GenerationGridProps) {
  const { canArtifactBeAdded, addArtifactToSlot } = useGeneratorSelection();
  const { deleteGeneration } = useGeneration();
  const { uploadMultiple } = useMultiUpload();
  const { toast } = useToast();
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [generationToDelete, setGenerationToDelete] =
    useState<Generation | null>(null);
  const [isExtractingFrame, setIsExtractingFrame] = useState(false);

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

  const handleExtractFrame = useCallback(
    async (generation: Generation, position: "first" | "last") => {
      if (!generation.storageUrl || isExtractingFrame) return;

      setIsExtractingFrame(true);

      try {
        // Create a video element to load the video
        const video = document.createElement("video");
        video.crossOrigin = "anonymous";
        video.preload = "metadata";

        // Wait for video metadata to load
        await new Promise<void>((resolve, reject) => {
          video.onloadedmetadata = () => resolve();
          video.onerror = () => reject(new Error("Failed to load video"));
          video.src = generation.storageUrl!;
        });

        // Seek to the desired position
        const targetTime = position === "first" ? 0 : video.duration - 0.1;
        video.currentTime = Math.max(0, targetTime);

        // Wait for the video to seek to the frame
        await new Promise<void>((resolve, reject) => {
          video.onseeked = () => resolve();
          video.onerror = () => reject(new Error("Failed to seek video"));
        });

        // Create a canvas and draw the video frame
        const canvas = document.createElement("canvas");
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        const ctx = canvas.getContext("2d");

        if (!ctx) {
          throw new Error("Failed to get canvas context");
        }

        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);

        // Convert canvas to blob
        const blob = await new Promise<Blob>((resolve, reject) => {
          canvas.toBlob(
            (blob) => {
              if (blob) {
                resolve(blob);
              } else {
                reject(new Error("Failed to create image blob"));
              }
            },
            "image/png",
            1.0
          );
        });

        // Create a File object from the blob
        const fileName = `${position}-frame-${generation.id}.png`;
        const file = new File([blob], fileName, { type: "image/png" });

        // Upload the extracted frame as a new image generation
        const results = await uploadMultiple([
          {
            boardId,
            artifactType: ArtifactType.IMAGE,
            source: file,
            userDescription: `${position === "first" ? "First" : "Last"} frame extracted from video`,
            parentGenerationId: generation.id,
          },
        ]);

        if (results.length > 0) {
          toast({
            title: "Frame extracted",
            description: `${position === "first" ? "First" : "Last"} frame has been saved as a new image.`,
          });
          onRemoveSuccess?.(); // Refresh the grid to show the new generation
        }
      } catch (error) {
        console.error("Failed to extract frame:", error);
        toast({
          title: "Failed to extract frame",
          description:
            error instanceof Error ? error.message : "An unknown error occurred",
          variant: "destructive",
        });
      } finally {
        setIsExtractingFrame(false);
      }
    },
    [boardId, uploadMultiple, toast, onRemoveSuccess, isExtractingFrame]
  );

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
            onExtractFrame={(position) => handleExtractFrame(generation, position)}
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
