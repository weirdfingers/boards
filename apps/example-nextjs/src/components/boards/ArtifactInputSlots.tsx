"use client";

import { FileVideo, Volume2, X } from "lucide-react";
import Image from "next/image";

interface Generation {
  id: string;
  artifactType: string;
  storageUrl?: string | null;
  thumbnailUrl?: string | null;
}

interface ArtifactSlot {
  name: string;
  type: string; // "audio", "video", "image", etc.
  required: boolean;
}

interface ArtifactInputSlotsProps {
  slots: ArtifactSlot[];
  selectedArtifacts: Map<string, Generation>;
  availableArtifacts: Generation[];
  onSelectArtifact: (slotName: string, artifact: Generation | null) => void;
}

export function ArtifactInputSlots({
  slots,
  selectedArtifacts,
  availableArtifacts,
  onSelectArtifact,
}: ArtifactInputSlotsProps) {
  const getIcon = (type: string) => {
    switch (type.toLowerCase()) {
      case "video":
        return <FileVideo className="w-5 h-5" />;
      case "audio":
        return <Volume2 className="w-5 h-5" />;
      default:
        return <FileVideo className="w-5 h-5" />;
    }
  };

  const getFilteredArtifacts = (slotType: string) => {
    return availableArtifacts.filter(
      (artifact) =>
        artifact.artifactType.toLowerCase() === slotType.toLowerCase()
    );
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {slots.map((slot) => {
        const selectedArtifact = selectedArtifacts.get(slot.name);
        const matchingArtifacts = getFilteredArtifacts(slot.type);

        return (
          <div key={slot.name} className="relative">
            {selectedArtifact ? (
              // Show selected artifact
              <div className="border-2 border-yellow-500 rounded-lg p-4 bg-yellow-50">
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0">
                    {selectedArtifact.thumbnailUrl ||
                    selectedArtifact.storageUrl ? (
                      <Image
                        src={
                          selectedArtifact.thumbnailUrl ||
                          selectedArtifact.storageUrl ||
                          ""
                        }
                        alt={`${slot.type} preview`}
                        className="w-16 h-16 object-cover rounded"
                        width={64}
                        height={64}
                      />
                    ) : (
                      <div className="w-16 h-16 bg-gray-200 rounded flex items-center justify-center">
                        {getIcon(slot.type)}
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      {getIcon(slot.type)}
                      <span className="font-medium text-sm capitalize">
                        {slot.type} {selectedArtifact.id.substring(0, 7)}
                      </span>
                    </div>
                    <p className="text-xs text-gray-600 mt-1">
                      {slot.name.replace(/_/g, " ")}
                    </p>
                  </div>
                  <button
                    onClick={() => onSelectArtifact(slot.name, null)}
                    className="flex-shrink-0 p-1 hover:bg-yellow-200 rounded"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ) : (
              // Show slot placeholder
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 hover:border-gray-400 transition-colors">
                <div className="flex flex-col items-center justify-center text-center">
                  <div className="mb-2">{getIcon(slot.type)}</div>
                  <p className="text-sm font-medium text-gray-700 mb-1">
                    Add a {slot.type}
                  </p>
                  {matchingArtifacts.length > 0 ? (
                    <select
                      onChange={(e) => {
                        const artifact = matchingArtifacts.find(
                          (a) => a.id === e.target.value
                        );
                        if (artifact) {
                          onSelectArtifact(slot.name, artifact);
                        }
                      }}
                      className="mt-2 px-3 py-1.5 text-sm border border-gray-300 rounded bg-white"
                    >
                      <option value="">Select from board...</option>
                      {matchingArtifacts.map((artifact) => (
                        <option key={artifact.id} value={artifact.id}>
                          {artifact.artifactType} -{" "}
                          {artifact.id.substring(0, 8)}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <p className="text-xs text-gray-500 mt-1">
                      No {slot.type} artifacts in this board yet
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
