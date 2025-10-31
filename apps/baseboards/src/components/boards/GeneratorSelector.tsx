"use client";

import { useState } from "react";
import { Zap, Check } from "lucide-react";

export interface GeneratorInfo {
  name: string;
  description: string;
  artifactType: string;
  inputSchema: Record<string, unknown>;
}

interface GeneratorSelectorProps {
  generators: GeneratorInfo[];
  selectedGenerator: GeneratorInfo | null;
  onSelect: (generator: GeneratorInfo) => void;
}

export function GeneratorSelector({
  generators,
  selectedGenerator,
  onSelect,
}: GeneratorSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);

  const getGeneratorIcon = (name: string) => {
    // You can customize icons per generator here
    return <Zap className="w-4 h-4" />;
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="px-4 py-2 bg-white border border-gray-300 rounded-lg shadow-sm hover:bg-gray-50 flex items-center gap-2"
      >
        {selectedGenerator ? (
          <>
            {getGeneratorIcon(selectedGenerator.name)}
            <span className="font-medium">{selectedGenerator.name}</span>
          </>
        ) : (
          <span className="text-gray-500">Select Generator</span>
        )}
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute top-full mt-2 left-0 bg-white border border-gray-200 rounded-lg shadow-lg z-20 min-w-[250px] max-h-[400px] overflow-y-auto">
            {generators.map((generator) => (
              <button
                key={generator.name}
                onClick={() => {
                  onSelect(generator);
                  setIsOpen(false);
                }}
                className="w-full px-4 py-3 hover:bg-gray-50 flex items-start gap-3 text-left border-b border-gray-100 last:border-b-0"
              >
                <div className="flex-shrink-0 mt-0.5">
                  {getGeneratorIcon(generator.name)}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm">
                      {generator.name}
                    </span>
                    <span className="text-xs text-gray-500 bg-gray-100 px-2 py-0.5 rounded">
                      {generator.artifactType}
                    </span>
                  </div>
                  <p className="text-xs text-gray-600 mt-1">
                    {generator.description}
                  </p>
                </div>
                {selectedGenerator?.name === generator.name && (
                  <Check className="w-4 h-4 text-green-600 flex-shrink-0" />
                )}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
