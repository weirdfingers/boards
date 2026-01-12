"use client";

import { Zap, Check, Search } from "lucide-react";
import type { JSONSchema7 } from "@weirdfingers/boards";
import { useGeneratorSelection } from "@weirdfingers/boards";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useState, useMemo, useEffect, useDeferredValue, useRef } from "react";

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

const MRU_STORAGE_KEY = "boards-generator-mru";
const MRU_MAX_SIZE = 3;

export function GeneratorSelector({
  generators,
  selectedGenerator,
  onSelect,
}: GeneratorSelectorProps) {
  const { setSelectedGenerator } = useGeneratorSelection();
  const [searchInput, setSearchInput] = useState("");
  const deferredSearch = useDeferredValue(searchInput);
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(new Set());
  const [mruGenerators, setMruGenerators] = useState<string[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Load MRU from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(MRU_STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          setMruGenerators(parsed);
        }
      }
    } catch (error) {
      console.error("Failed to load MRU generators:", error);
    }
  }, []);

  // Focus search input when dropdown opens
  useEffect(() => {
    if (isOpen) {
      // Use requestAnimationFrame to wait for the DOM to update
      requestAnimationFrame(() => {
        searchInputRef.current?.focus();
      });
    }
  }, [isOpen]);

  // Get unique artifact types from generators
  const artifactTypes = useMemo(() => {
    const types = new Set<string>();
    generators.forEach((gen) => types.add(gen.artifactType));
    return Array.from(types).sort();
  }, [generators]);

  // Filter generators based on search and type
  const filteredGenerators = useMemo(() => {
    let filtered = generators;

    // Filter by type if any selected
    if (selectedTypes.size > 0) {
      filtered = filtered.filter((gen) => selectedTypes.has(gen.artifactType));
    }

    // Filter by search text - split by spaces and require all terms to match
    if (deferredSearch.trim()) {
      const searchTerms = deferredSearch
        .toLowerCase()
        .split(/\s+/)
        .filter((term) => term.length > 0);

      filtered = filtered.filter((gen) => {
        const searchableText = `${gen.name} ${gen.description}`.toLowerCase();
        // All search terms must be present in the combined name + description
        return searchTerms.every((term) => searchableText.includes(term));
      });
    }

    return filtered;
  }, [generators, selectedTypes, deferredSearch]);

  // Get MRU generators (only when no search input)
  const mruList = useMemo(() => {
    if (searchInput.trim()) {
      return [];
    }

    return mruGenerators
      .map((name) => generators.find((gen) => gen.name === name))
      .filter((gen): gen is GeneratorInfo => gen !== undefined)
      .filter((gen) =>
        selectedTypes.size > 0 ? selectedTypes.has(gen.artifactType) : true
      );
  }, [mruGenerators, generators, searchInput, selectedTypes]);

  // Get remaining generators (excluding MRU)
  const remainingGenerators = useMemo(() => {
    if (!searchInput.trim() && mruList.length > 0) {
      const mruNames = new Set(mruList.map((gen) => gen.name));
      return filteredGenerators.filter((gen) => !mruNames.has(gen.name));
    }
    return filteredGenerators;
  }, [filteredGenerators, mruList, searchInput]);

  const getGeneratorIcon = (name: string) => {
    // You can customize icons per generator here
    return <Zap className="w-4 h-4" />;
  };

  const handleSelect = (generator: GeneratorInfo) => {
    // Update both local state and context
    setSelectedGenerator(generator);
    onSelect(generator);

    // Update MRU
    const newMru = [
      generator.name,
      ...mruGenerators.filter((name) => name !== generator.name),
    ].slice(0, MRU_MAX_SIZE);

    setMruGenerators(newMru);
    try {
      localStorage.setItem(MRU_STORAGE_KEY, JSON.stringify(newMru));
    } catch (error) {
      console.error("Failed to save MRU generators:", error);
    }
  };

  const toggleType = (type: string) => {
    setSelectedTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) {
        next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  };

  return (
    <DropdownMenu onOpenChange={setIsOpen}>
      <DropdownMenuTrigger asChild>
        <button className="px-4 py-2 bg-background border border-border rounded-lg shadow-sm hover:bg-muted/50 flex items-center gap-2">
          {selectedGenerator ? (
            <>
              {getGeneratorIcon(selectedGenerator.name)}
              <span className="font-medium">{selectedGenerator.name}</span>
            </>
          ) : (
            <span className="text-muted-foreground">Select Generator</span>
          )}
        </button>
      </DropdownMenuTrigger>

      <DropdownMenuContent
        className="min-w-[250px] max-w-[400px] max-h-[500px] overflow-y-auto"
        align="start"
        side="bottom"
        sideOffset={8}
        collisionPadding={8}
      >
        {/* Search Input */}
        <div className="px-3 py-2 sticky top-0 bg-background border-b border-border z-10">
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
            <input
              ref={searchInputRef}
              type="text"
              placeholder="Search generators..."
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="w-full pl-8 pr-3 py-2 text-sm bg-background border border-border rounded-md focus:outline-none focus:ring-2 focus:ring-ring"
              onClick={(e) => e.stopPropagation()}
              onKeyDown={(e) => e.stopPropagation()}
            />
          </div>

          {/* Type Filter Pills */}
          {artifactTypes.length > 1 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {artifactTypes.map((type) => (
                <button
                  key={type}
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleType(type);
                  }}
                  className={`px-2 py-1 text-xs rounded-full border transition-colors ${
                    selectedTypes.has(type)
                      ? "bg-primary text-primary-foreground border-primary"
                      : "bg-background border-border text-muted-foreground hover:bg-muted"
                  }`}
                >
                  {type}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* MRU Section */}
        {mruList.length > 0 && (
          <>
            <div className="px-3 py-2 text-xs font-semibold text-muted-foreground">
              Recently Used
            </div>
            {mruList.map((generator) => (
              <DropdownMenuItem
                key={`mru-${generator.name}`}
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
                    <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
                      {generator.artifactType}
                    </span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {generator.description}
                  </p>
                </div>
                {selectedGenerator?.name === generator.name && (
                  <Check className="w-4 h-4 text-success flex-shrink-0" />
                )}
              </DropdownMenuItem>
            ))}
            <div className="border-t border-border my-1" />
          </>
        )}

        {/* All Generators Section */}
        {mruList.length > 0 && remainingGenerators.length > 0 && (
          <div className="px-3 py-2 text-xs font-semibold text-muted-foreground">
            All Generators
          </div>
        )}
        {remainingGenerators.length > 0 ? (
          remainingGenerators.map((generator) => (
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
                  <span className="font-medium text-sm">{generator.name}</span>
                  <span className="text-xs text-muted-foreground bg-muted px-2 py-0.5 rounded">
                    {generator.artifactType}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground mt-1">
                  {generator.description}
                </p>
              </div>
              {selectedGenerator?.name === generator.name && (
                <Check className="w-4 h-4 text-success flex-shrink-0" />
              )}
            </DropdownMenuItem>
          ))
        ) : (
          <div className="px-4 py-3 text-sm text-muted-foreground text-center">
            No generators found
          </div>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
