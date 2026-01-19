"use client";

import React from "react";
import { useParams } from "next/navigation";
import {
  useBoard,
  useGenerators,
  useGeneration,
  GeneratorSelectionProvider,
} from "@weirdfingers/boards";
import { GenerationGrid } from "@/components/boards/GenerationGrid";
import { GenerationInput } from "@/components/boards/GenerationInput";
import { UploadArtifact } from "@/components/boards/UploadArtifact";
import { Button } from "@/components/ui/button";
import { Pencil, Check, X } from "lucide-react";

export default function BoardPage() {
  const params = useParams();
  const boardId = params.boardId as string;

  const {
    board,
    error: boardError,
    refresh: refreshBoard,
    updateBoard,
  } = useBoard(boardId);

  // State for inline title editing
  const [isEditingTitle, setIsEditingTitle] = React.useState(false);
  const [editedTitle, setEditedTitle] = React.useState("");
  const [titleError, setTitleError] = React.useState<string | null>(null);
  const [isUpdatingTitle, setIsUpdatingTitle] = React.useState(false);
  const titleInputRef = React.useRef<HTMLInputElement>(null);

  // Fetch available generators
  const {
    generators,
    loading: generatorsLoading,
    error: generatorsError,
  } = useGenerators();

  // Use generation hook for submitting generations and real-time progress
  const { submit, isGenerating, progress } = useGeneration();

  // Auto-focus input when entering edit mode
  React.useEffect(() => {
    if (isEditingTitle && titleInputRef.current) {
      titleInputRef.current.focus();
      titleInputRef.current.select();
    }
  }, [isEditingTitle]);

  // Handlers for title editing
  const handleEditTitle = () => {
    if (board) {
      setEditedTitle(board.title);
      setTitleError(null);
      setIsEditingTitle(true);
    }
  };

  const handleCancelEdit = () => {
    setIsEditingTitle(false);
    setEditedTitle("");
    setTitleError(null);
  };

  const handleSaveTitle = async () => {
    const trimmedTitle = editedTitle.trim();

    // Validation
    if (!trimmedTitle) {
      setTitleError("Title cannot be empty");
      return;
    }

    if (trimmedTitle === board?.title) {
      // No changes, just exit edit mode
      handleCancelEdit();
      return;
    }

    setIsUpdatingTitle(true);
    setTitleError(null);

    try {
      await updateBoard({ title: trimmedTitle });
      setIsEditingTitle(false);
      setEditedTitle("");
    } catch (error) {
      console.error("Failed to update board title:", error);
      setTitleError(
        error instanceof Error ? error.message : "Failed to update title"
      );
    } finally {
      setIsUpdatingTitle(false);
    }
  };

  const handleTitleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleSaveTitle();
    } else if (e.key === "Escape") {
      e.preventDefault();
      handleCancelEdit();
    }
  };

  // Refresh board when a generation completes or fails
  // MUST be before conditional returns to satisfy Rules of Hooks
  React.useEffect(() => {
    if (
      progress &&
      (progress.status === "completed" || progress.status === "failed")
    ) {
      refreshBoard();
    }
  }, [progress, refreshBoard]);

  // Merge database generations with live progress for real-time updates
  // MUST be before conditional returns to satisfy Rules of Hooks
  const generations = React.useMemo(() => {
    const dbGenerations = board?.generations || [];

    // If we have live progress, update the matching generation's status
    if (progress) {
      return dbGenerations.map((gen) => {
        if (gen.id === progress.jobId) {
          // Map SSE status to GraphQL status format (lowercase to UPPERCASE)
          const statusMap: Record<string, string> = {
            queued: "PENDING",
            processing: "PROCESSING",
            completed: "COMPLETED",
            failed: "FAILED",
            cancelled: "CANCELLED",
          };

          return {
            ...gen,
            status: statusMap[progress.status] || gen.status,
            errorMessage:
              progress.status === "failed"
                ? progress.message || "Generation failed"
                : gen.errorMessage,
          };
        }
        return gen;
      });
    }

    return dbGenerations;
  }, [board?.generations, progress]);

  // Handle board error
  if (boardError) {
    console.error("[BoardPage] Board error:", boardError);
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="bg-destructive/10 border border-destructive/50 rounded-lg p-6 max-w-lg">
          <h2 className="text-destructive text-xl font-semibold mb-2">
            Error Loading Board
          </h2>
          <p className="text-destructive/90">{boardError.message}</p>
        </div>
      </div>
    );
  }
  if (generatorsError) {
    console.error("[BoardPage] Generators error:", generatorsError);
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="bg-destructive/10 border border-destructive/50 rounded-lg p-6 max-w-lg">
          <h2 className="text-destructive text-xl font-semibold mb-2">
            Error Loading Generators
          </h2>
          <p className="text-destructive/90">{generatorsError.message}</p>
        </div>
      </div>
    );
  }

  // Handle loading state
  if (!board) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
      </div>
    );
  }

  // Filter completed generations that can be used as inputs
  const availableArtifacts = generations.filter(
    (gen) => gen.status === "COMPLETED" && gen.storageUrl
  );

  const handleGenerationSubmit = async (params: {
    generatorName: string;
    prompt: string;
    artifacts: Map<string, unknown>;
    settings: Record<string, unknown>;
  }) => {
    try {
      // Find the selected generator to validate it exists
      const selectedGenerator = generators.find(
        (g) => g.name === params.generatorName
      );

      if (!selectedGenerator) {
        throw new Error(`Generator ${params.generatorName} not found`);
      }

      // Build inputs object with prompt and artifact references
      const inputs: Record<string, unknown> = {
        prompt: params.prompt,
      };

      // Add artifact inputs (convert artifact objects to their IDs)
      params.artifacts.forEach((artifact, slotName) => {
        if (artifact && typeof artifact === "object" && "id" in artifact) {
          inputs[slotName] = artifact.id;
        } else if (artifact) {
          inputs[slotName] = artifact;
        }
      });

      // Submit generation using the hook
      // Provider is typically encoded in the generator name or use "default"
      await submit({
        boardId,
        model: params.generatorName,
        artifactType: selectedGenerator.artifactType,
        inputs: inputs as { prompt: string; [key: string]: unknown },
        options: params.settings,
      });
    } catch (error) {
      console.error("Failed to create generation:", error);
    }
  };

  return (
    <GeneratorSelectionProvider>
      <main className="min-h-screen bg-muted/30">
        <div className="container mx-auto px-4 py-6 max-w-7xl">
          {/* Header */}
          <div className="mb-6 flex items-start justify-between">
            <div className="flex-1">
              {isEditingTitle ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <input
                      ref={titleInputRef}
                      type="text"
                      value={editedTitle}
                      onChange={(e) => setEditedTitle(e.target.value)}
                      onKeyDown={handleTitleKeyDown}
                      disabled={isUpdatingTitle}
                      className="text-3xl font-bold text-foreground border-2 border-border rounded px-2 py-1 focus:outline-none focus:border-primary disabled:opacity-50 disabled:cursor-not-allowed flex-1"
                      placeholder="Enter board title"
                      aria-label="Edit board title"
                      aria-invalid={!!titleError}
                    />
                    <Button
                      onClick={handleSaveTitle}
                      disabled={isUpdatingTitle}
                      size="icon"
                      variant="default"
                      aria-label="Save title"
                    >
                      <Check className="h-4 w-4" />
                    </Button>
                    <Button
                      onClick={handleCancelEdit}
                      disabled={isUpdatingTitle}
                      size="icon"
                      variant="outline"
                      aria-label="Cancel editing"
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  </div>
                  {titleError && (
                    <p className="text-sm text-destructive" role="alert">
                      {titleError}
                    </p>
                  )}
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <h1 className="text-3xl font-bold text-foreground">
                    {board.title}
                  </h1>
                  <Button
                    onClick={handleEditTitle}
                    size="icon"
                    variant="ghost"
                    className="h-8 w-8"
                    aria-label="Edit board title"
                  >
                    <Pencil className="h-4 w-4" />
                  </Button>
                </div>
              )}
              {board.description && !isEditingTitle && (
                <p className="text-muted-foreground mt-2">
                  {board.description}
                </p>
              )}
            </div>
            <UploadArtifact
              boardId={boardId}
              onUploadComplete={() => {
                refreshBoard();
              }}
            />
          </div>

          {/* Generation Grid */}
          <div className="mb-8">
            <GenerationGrid
              generations={generations}
              onGenerationClick={() => {
                // TODO: Open generation detail modal
              }}
              onRemoveSuccess={refreshBoard}
            />
          </div>

          {/* Generation Input */}
          <div id="generation-input" className="sticky bottom-6 z-10">
            {generatorsLoading ? (
              <div className="bg-background rounded-lg shadow-lg p-6 text-center">
                <p className="text-muted-foreground">Loading generators...</p>
              </div>
            ) : generators.length === 0 ? (
              <div className="bg-background rounded-lg shadow-lg p-6 text-center">
                <p className="text-muted-foreground">No generators available</p>
              </div>
            ) : (
              <GenerationInput
                generators={generators}
                availableArtifacts={availableArtifacts}
                onSubmit={handleGenerationSubmit}
                isGenerating={isGenerating}
              />
            )}
          </div>
        </div>
      </main>
    </GeneratorSelectionProvider>
  );
}
