"use client";

import { useState, useMemo } from "react";
import { Settings, ArrowUp, X } from "lucide-react";
import Image from "next/image";
import { parseGeneratorSchema } from "@weirdfingers/boards";
import { GeneratorSelector, GeneratorInfo } from "./GeneratorSelector";
import { ArtifactInputSlots } from "./ArtifactInputSlots";

interface Generation {
  id: string;
  artifactType: string;
  storageUrl?: string | null;
  thumbnailUrl?: string | null;
}

interface GenerationInputProps {
  generators: GeneratorInfo[];
  availableArtifacts: Generation[];
  onSubmit: (params: {
    generatorName: string;
    prompt: string;
    artifacts: Map<string, Generation>;
    settings: Record<string, unknown>;
  }) => void;
  isGenerating?: boolean;
}

export function GenerationInput({
  generators,
  availableArtifacts,
  onSubmit,
  isGenerating = false,
}: GenerationInputProps) {
  const [selectedGenerator, setSelectedGenerator] =
    useState<GeneratorInfo | null>(generators[0] || null);
  const [prompt, setPrompt] = useState("");
  const [selectedArtifacts, setSelectedArtifacts] = useState<
    Map<string, Generation>
  >(new Map());
  const [attachedImage, setAttachedImage] = useState<Generation | null>(null);
  const [showSettings, setShowSettings] = useState(false);

  // Parse input schema using the toolkit's schema parser
  const parsedSchema = useMemo(() => {
    if (!selectedGenerator) {
      return { artifactSlots: [], promptField: null, settingsFields: [] };
    }
    return parseGeneratorSchema(selectedGenerator.inputSchema);
  }, [selectedGenerator]);

  const artifactSlots = useMemo(() => {
    return parsedSchema.artifactSlots.map((slot) => ({
      name: slot.fieldName,
      type: slot.artifactType,
      required: slot.required,
    }));
  }, [parsedSchema.artifactSlots]);

  const needsArtifactInputs = artifactSlots.length > 0;

  const handleSubmit = () => {
    if (!selectedGenerator || !prompt.trim()) return;

    onSubmit({
      generatorName: selectedGenerator.name,
      prompt: prompt.trim(),
      artifacts: selectedArtifacts,
      settings: {},
    });

    // Reset form
    setPrompt("");
    setSelectedArtifacts(new Map());
    setAttachedImage(null);
  };

  const handleSelectArtifact = (
    slotName: string,
    artifact: Generation | null
  ) => {
    const newSelected = new Map(selectedArtifacts);
    if (artifact) {
      newSelected.set(slotName, artifact);
    } else {
      newSelected.delete(slotName);
    }
    setSelectedArtifacts(newSelected);
  };

  const canSubmit =
    selectedGenerator &&
    prompt.trim() &&
    !isGenerating &&
    (!needsArtifactInputs ||
      artifactSlots
        .filter((s) => s.required)
        .every((s) => selectedArtifacts.has(s.name)));

  return (
    <div className="border border-gray-300 rounded-lg bg-white shadow-sm">
      {/* Generator selector header */}
      <div className="px-4 py-3 border-b border-gray-200 flex items-center justify-center">
        <GeneratorSelector
          generators={generators}
          selectedGenerator={selectedGenerator}
          onSelect={setSelectedGenerator}
        />
      </div>

      {/* Artifact input slots (for generators like lipsync) */}
      {needsArtifactInputs && (
        <div className="px-4 py-4 border-b border-gray-200">
          <ArtifactInputSlots
            slots={artifactSlots}
            selectedArtifacts={selectedArtifacts}
            availableArtifacts={availableArtifacts}
            onSelectArtifact={handleSelectArtifact}
          />
          {artifactSlots.every((s) => selectedArtifacts.has(s.name)) && (
            <div className="mt-3 flex items-center gap-2 text-sm text-green-600">
              <svg
                className="w-4 h-4"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path d="M5 13l4 4L19 7"></path>
              </svg>
              <span>
                Both files ready for {selectedGenerator?.name} generation
              </span>
            </div>
          )}
        </div>
      )}

      {/* Attached image preview (if any) */}
      {attachedImage && (
        <div className="px-4 py-3 border-b border-gray-200">
          <div className="flex items-center gap-3">
            <Image
              src={attachedImage.thumbnailUrl || attachedImage.storageUrl || ""}
              alt="Attached"
              className="w-16 h-16 object-cover rounded"
              width={64}
              height={64}
            />
            <div className="flex-1">
              <p className="text-sm font-medium">Image attached</p>
              <p className="text-xs text-gray-500">
                ID: {attachedImage.id.substring(0, 8)}
              </p>
            </div>
            <button
              onClick={() => setAttachedImage(null)}
              className="p-1 hover:bg-gray-100 rounded"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Prompt input area */}
      <div className="px-4 py-4 flex items-end gap-3">
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder={
            needsArtifactInputs
              ? "Add optional prompt or instructions..."
              : "Describe what you want to generate..."
          }
          className="flex-1 resize-none border-none outline-none text-base min-h-[60px] max-h-[200px]"
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && canSubmit) {
              handleSubmit();
            }
          }}
        />
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowSettings(!showSettings)}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
            title="Settings"
          >
            <Settings className="w-5 h-5 text-gray-600" />
          </button>
          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            className={`p-3 rounded-full transition-all ${
              canSubmit
                ? "bg-orange-500 hover:bg-orange-600 text-white shadow-lg"
                : "bg-gray-200 text-gray-400 cursor-not-allowed"
            }`}
            title="Generate (⌘+Enter)"
          >
            <ArrowUp className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Settings panel (collapsed by default) */}
      {showSettings && (
        <div className="px-4 py-4 border-t border-gray-200 bg-gray-50">
          <p className="text-sm text-gray-600">
            Generator-specific settings will appear here
          </p>
        </div>
      )}
    </div>
  );
}
