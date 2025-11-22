"use client";

import { Zap, Check } from "lucide-react";
import type { JSONSchema7 } from "@weirdfingers/boards";
import { useGeneratorSelection } from "@weirdfingers/boards";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

export interface GeneratorInfo {
  name: string;
  description: string;
  artifactType: string;
  inputSchema: JSONSchema7;
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
  const { setSelectedGenerator } = useGeneratorSelection();

  const getGeneratorIcon = (name: string) => {
    // You can customize icons per generator here
    return <Zap className="w-4 h-4" />;
  };

  const handleSelect = (generator: GeneratorInfo) => {
    // Update both local state and context
    setSelectedGenerator(generator);
    onSelect(generator);
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button className="px-4 py-2 bg-white border border-gray-300 rounded-lg shadow-sm hover:bg-gray-50 flex items-center gap-2">
          {selectedGenerator ? (
            <>
              {getGeneratorIcon(selectedGenerator.name)}
              <span className="font-medium">{selectedGenerator.name}</span>
            </>
          ) : (
            <span className="text-gray-500">Select Generator</span>
          )}
        </button>
      </DropdownMenuTrigger>

      <DropdownMenuContent
        className="min-w-[250px] max-w-[400px] max-h-[400px] overflow-y-auto"
        align="start"
        side="bottom"
        sideOffset={8}
        collisionPadding={8}
      >
        {generators.map((generator) => (
          <DropdownMenuItem
            key={generator.name}
            onClick={() => handleSelect(generator)}
            className="px-4 py-3 flex items-start gap-3 cursor-pointer"
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
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
