"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { useBoard, useGenerators } from "@weirdfingers/boards";
import { GenerationGrid } from "@/components/boards/GenerationGrid";
import { GenerationInput } from "@/components/boards/GenerationInput";

export default function BoardPage() {
  const params = useParams();
  const boardId = params.boardId as string;
  const { board } = useBoard(boardId);
  const [isGenerating, setIsGenerating] = useState(false);

  // Fetch available generators
  const { generators, loading: generatorsLoading } = useGenerators();

  if (!board) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  const generations = board.generations || [];

  // Filter completed generations that can be used as inputs
  const availableArtifacts = generations.filter(
    (gen) => gen.status === "COMPLETED" && gen.storageUrl
  );

  const handleGenerationSubmit = async (params: {
    generatorName: string;
    prompt: string;
    artifacts: Map<string, any>;
    settings: Record<string, unknown>;
  }) => {
    setIsGenerating(true);
    try {
      // Build input params
      const inputParams: Record<string, unknown> = {
        prompt: params.prompt,
        ...params.settings,
      };

      // Add artifact inputs
      params.artifacts.forEach((artifact, slotName) => {
        inputParams[slotName] = artifact.id;
      });

      // TODO: Call the createGeneration mutation
      console.log("Creating generation:", {
        boardId,
        generatorName: params.generatorName,
        inputParams,
      });

      // This should be replaced with actual mutation call
      // const result = await createGenerationMutation({
      //   input: {
      //     boardId,
      //     generatorName: params.generatorName,
      //     providerName: "default", // or derive from generator
      //     artifactType: selectedGenerator.artifactType,
      //     inputParams,
      //   }
      // });
    } catch (error) {
      console.error("Failed to create generation:", error);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <main className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-6 max-w-7xl">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900">{board.title}</h1>
          {board.description && (
            <p className="text-gray-600 mt-2">{board.description}</p>
          )}
        </div>

        {/* Generation Grid */}
        <div className="mb-8">
          <GenerationGrid
            generations={generations}
            onGenerationClick={(gen) => {
              console.log("Clicked generation:", gen);
              // TODO: Open generation detail modal
            }}
          />
        </div>

        {/* Generation Input */}
        <div className="sticky bottom-6 z-10">
          {generatorsLoading ? (
            <div className="bg-white rounded-lg shadow-lg p-6 text-center">
              <p className="text-gray-500">Loading generators...</p>
            </div>
          ) : generators.length === 0 ? (
            <div className="bg-white rounded-lg shadow-lg p-6 text-center">
              <p className="text-gray-500">No generators available</p>
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
  );
}
