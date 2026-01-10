"use client";

import { useState, useMemo, useEffect } from "react";
import { Settings, ArrowUp, X } from "lucide-react";
import Image from "next/image";
import {
  useGeneratorSelection,
} from "@weirdfingers/boards";
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
  const {
    selectedGenerator,
    setSelectedGenerator,
    parsedSchema,
    selectedArtifacts,
    setSelectedArtifacts
  } = useGeneratorSelection();

  const [prompt, setPrompt] = useState("");
  const [attachedImage, setAttachedImage] = useState<Generation | null>(null);
  const [showSettings, setShowSettings] = useState(false);
  const [settings, setSettings] = useState<Record<string, unknown>>({});

  // Initialize selected generator if not set
  useEffect(() => {
    if (!selectedGenerator && generators.length > 0) {
      setSelectedGenerator(generators[0]);
    }
  }, [generators, selectedGenerator, setSelectedGenerator]);

  const artifactSlots = useMemo(() => {
    if (!parsedSchema) return [];
    return parsedSchema.artifactSlots.map((slot) => ({
      name: slot.fieldName,
      type: slot.artifactType,
      required: slot.required,
    }));
  }, [parsedSchema]);

  const needsArtifactInputs = artifactSlots.length > 0;

  // Initialize settings with defaults when generator changes
  const defaultSettings = useMemo(() => {
    const defaults: Record<string, unknown> = {};
    if (parsedSchema) {
      parsedSchema.settingsFields.forEach((field) => {
        if (field.default !== undefined) {
          defaults[field.fieldName] = field.default;
        }
      });
    }
    return defaults;
  }, [parsedSchema]);

  // Reset settings when generator changes or defaultSettings change
  useEffect(() => {
    setSettings(defaultSettings);
  }, [selectedGenerator, defaultSettings]);

  const handleSubmit = () => {
    if (!selectedGenerator || !prompt.trim()) return;

    onSubmit({
      generatorName: selectedGenerator.name,
      prompt: prompt.trim(),
      artifacts: selectedArtifacts,
      settings,
    });

    // Reset form (but keep selected artifacts and generator)
    setPrompt("");
    setAttachedImage(null);
    setSettings(defaultSettings);
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
    <div className="border border-border rounded-lg bg-background shadow-sm">
      {/* Generator selector header */}
      <div className="px-4 py-3 border-b border-border flex items-center justify-center">
        <GeneratorSelector
          generators={generators}
          selectedGenerator={selectedGenerator}
          onSelect={setSelectedGenerator}
        />
      </div>

      {/* Artifact input slots (for generators like lipsync) */}
      {needsArtifactInputs && (
        <div className="px-4 py-4 border-b border-border">
          <ArtifactInputSlots
            slots={artifactSlots}
            selectedArtifacts={selectedArtifacts}
            availableArtifacts={availableArtifacts}
            onSelectArtifact={handleSelectArtifact}
          />
          {artifactSlots.every((s) => selectedArtifacts.has(s.name)) && (
            <div className="mt-3 flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
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
        <div className="px-4 py-3 border-b border-border">
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
              <p className="text-xs text-muted-foreground">
                ID: {attachedImage.id.substring(0, 8)}
              </p>
            </div>
            <button
              onClick={() => setAttachedImage(null)}
              className="p-1 hover:bg-muted rounded"
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
            className="p-2 hover:bg-muted rounded-lg transition-colors"
            title="Settings"
          >
            <Settings className="w-5 h-5 text-muted-foreground" />
          </button>
          <button
            onClick={handleSubmit}
            disabled={!canSubmit}
            className={`p-3 rounded-full transition-all ${
              canSubmit
                ? "bg-primary hover:bg-primary/90 text-primary-foreground shadow-lg"
                : "bg-muted text-muted-foreground cursor-not-allowed"
            }`}
            title="Generate (⌘+Enter)"
          >
            <ArrowUp className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Settings panel (collapsed by default) */}
      {showSettings && (
        <div className="px-4 py-4 border-t border-border bg-muted/50">
          {!parsedSchema || parsedSchema.settingsFields.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No additional settings available for this generator
            </p>
          ) : (
            <div>
              <h3 className="text-sm font-medium text-foreground mb-4">
                Generator Settings
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {parsedSchema.settingsFields.map((field) => (
                <div key={field.fieldName} className="space-y-1.5">
                  <label
                    htmlFor={field.fieldName}
                    className="block text-sm font-medium text-foreground"
                  >
                    {field.title}
                  </label>
                  {field.description && (
                    <p className="text-xs text-muted-foreground">{field.description}</p>
                  )}

                  {/* Slider control */}
                  {field.type === "slider" && (
                    <div className="space-y-1">
                      <input
                        id={field.fieldName}
                        type="range"
                        min={field.min}
                        max={field.max}
                        step={field.step || (field.isInteger ? 1 : 0.01)}
                        value={
                          (settings[field.fieldName] as number) ?? field.default
                        }
                        onChange={(e) =>
                          setSettings({
                            ...settings,
                            [field.fieldName]: field.isInteger
                              ? parseInt(e.target.value)
                              : parseFloat(e.target.value),
                          })
                        }
                        className="w-full h-2 bg-muted rounded-lg appearance-none cursor-pointer accent-primary"
                      />
                      <div className="flex justify-between text-xs text-muted-foreground">
                        <span>{field.min}</span>
                        <span className="font-medium">
                          {String(settings[field.fieldName] ?? field.default ?? field.min)}
                        </span>
                        <span>{field.max}</span>
                      </div>
                    </div>
                  )}

                  {/* Dropdown control */}
                  {field.type === "dropdown" && (
                    <select
                      id={field.fieldName}
                      value={(settings[field.fieldName] as string) ?? field.default}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          [field.fieldName]: e.target.value,
                        })
                      }
                      className="block w-full px-3 py-2 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary"
                    >
                      {field.options.map((option) => (
                        <option key={option} value={option}>
                          {option}
                        </option>
                      ))}
                    </select>
                  )}

                  {/* Number input control */}
                  {field.type === "number" && (
                    <input
                      id={field.fieldName}
                      type="number"
                      min={field.min}
                      max={field.max}
                      step={field.isInteger ? 1 : "any"}
                      value={(settings[field.fieldName] as number) ?? field.default}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          [field.fieldName]: field.isInteger
                            ? parseInt(e.target.value)
                            : parseFloat(e.target.value),
                        })
                      }
                      className="block w-full px-3 py-2 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary"
                    />
                  )}

                  {/* Text input control */}
                  {field.type === "text" && (
                    <input
                      id={field.fieldName}
                      type="text"
                      value={(settings[field.fieldName] as string) ?? field.default ?? ""}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          [field.fieldName]: e.target.value,
                        })
                      }
                      pattern={field.pattern}
                      className="block w-full px-3 py-2 text-sm border border-border rounded-md bg-background focus:outline-none focus:ring-2 focus:ring-primary focus:border-primary"
                    />
                  )}
                </div>
              ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
