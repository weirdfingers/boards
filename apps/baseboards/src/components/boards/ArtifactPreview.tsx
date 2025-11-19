import {
  FileVideo,
  Volume2,
  FileText,
  Image as ImageIcon,
  Plus,
  MoreVertical,
  GripVertical,
  Download,
  Eye,
} from "lucide-react";
import Image from "next/image";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface ArtifactPreviewProps {
  artifactType: string;
  storageUrl?: string | null;
  thumbnailUrl?: string | null;
  status: string;
  errorMessage?: string | null;
  onClick?: () => void;
  onAddToSlot?: () => void;
  canAddToSlot?: boolean;
  onDownload?: () => void;
  onPreview?: () => void;
  artifactId?: string;
}

export function ArtifactPreview({
  artifactType,
  storageUrl,
  thumbnailUrl,
  status,
  errorMessage,
  onClick,
  onAddToSlot,
  canAddToSlot = false,
  onDownload,
  onPreview,
  artifactId,
}: ArtifactPreviewProps) {
  const isLoading = status === "PENDING" || status === "PROCESSING";
  const isFailed = status === "FAILED" || status === "CANCELLED";
  const isComplete = status === "COMPLETED";

  // Determine which URL to use for preview
  const previewUrl = thumbnailUrl || storageUrl;

  const renderContent = () => {
    if (isFailed) {
      return (
        <div className="flex flex-col items-center justify-center h-full p-4 text-center">
          <div className="text-red-500 mb-2">
            {status === "CANCELLED" ? "Cancelled" : "Failed"}
          </div>
          {errorMessage && (
            <p className="text-sm text-gray-500">{errorMessage}</p>
          )}
        </div>
      );
    }

    if (isLoading) {
      return (
        <div className="flex items-center justify-center h-full">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
        </div>
      );
    }

    switch (artifactType) {
      case "IMAGE":
        if (previewUrl) {
          return (
            <Image
              src={previewUrl}
              alt="Generated image"
              className="w-full h-full object-cover"
              width={512}
              height={512}
            />
          );
        }
        return (
          <div className="flex items-center justify-center h-full bg-gray-100">
            <ImageIcon className="w-12 h-12 text-gray-400" />
          </div>
        );

      case "VIDEO":
        return (
          <div className="relative w-full h-full">
            {previewUrl ? (
              <Image
                src={previewUrl}
                alt="Video thumbnail"
                className="w-full h-full object-cover"
                width={512}
                height={512}
              />
            ) : (
              <div className="flex items-center justify-center h-full bg-gray-100">
                <FileVideo className="w-12 h-12 text-gray-400" />
              </div>
            )}
            <div className="absolute top-2 left-2 bg-black/50 rounded p-1">
              <FileVideo className="w-5 h-5 text-white" />
            </div>
          </div>
        );

      case "AUDIO":
        return (
          <div className="flex flex-col items-center justify-center h-full bg-gradient-to-br from-blue-900 to-blue-700">
            <Volume2 className="w-12 h-12 text-white mb-2" />
            <span className="text-white text-sm">Audio file</span>
          </div>
        );

      case "TEXT":
        return (
          <div className="flex flex-col items-center justify-center h-full bg-gradient-to-br from-gray-700 to-gray-900">
            <FileText className="w-12 h-12 text-white mb-2" />
            <span className="text-white text-sm">Text</span>
          </div>
        );

      default:
        return (
          <div className="flex items-center justify-center h-full bg-gray-100">
            <span className="text-gray-400">Unknown type</span>
          </div>
        );
    }
  };

  return (
    <div
      className="relative aspect-square rounded-lg overflow-hidden border border-gray-200 group"
      draggable={isComplete && !!artifactId && canAddToSlot}
      onDragStart={(e) => {
        if (isComplete && artifactId) {
          e.dataTransfer.setData(
            "application/json",
            JSON.stringify({
              id: artifactId,
              artifactType,
              storageUrl,
              thumbnailUrl,
            })
          );
          e.dataTransfer.effectAllowed = "copy";
        }
      }}
    >
      <div className={onClick ? "cursor-pointer" : ""} onClick={onClick}>
        {renderContent()}
      </div>

      {/* Bottom overlay with controls - show for all artifacts when not loading/failed */}
      {!isLoading && !isFailed && (
        <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/70 to-transparent p-3 opacity-0 group-hover:opacity-100 transition-opacity">
          <div className="flex items-center justify-between gap-2">
            {/* Drag handle - only for completed artifacts */}
            {isComplete && (
              <div
                className="flex items-center gap-2 cursor-move text-white/80 hover:text-white"
                title="Drag to input slot"
              >
                <GripVertical className="w-4 h-4" />
              </div>
            )}

            <div
              className={`flex items-center gap-2 ${
                !isComplete ? "ml-auto" : ""
              }`}
            >
              {/* Add button - only for completed artifacts */}
              {isComplete && onAddToSlot && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onAddToSlot();
                  }}
                  disabled={!canAddToSlot}
                  className={`p-1.5 rounded transition-colors ${
                    canAddToSlot
                      ? "bg-white/20 hover:bg-white/30 text-white cursor-pointer"
                      : "bg-white/10 text-white/40 cursor-not-allowed"
                  }`}
                  title={
                    canAddToSlot
                      ? "Add to input slot"
                      : "No compatible input slots"
                  }
                >
                  <Plus className="w-4 h-4" />
                </button>
              )}

              {/* More options menu - show for all artifacts */}
              {(onPreview || onDownload) && (
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <button
                      onClick={(e) => e.stopPropagation()}
                      className="p-1.5 rounded bg-white/20 hover:bg-white/30 text-white transition-colors"
                      title="More options"
                    >
                      <MoreVertical className="w-4 h-4" />
                    </button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="end" className="w-40">
                    {onPreview && (
                      <DropdownMenuItem
                        onClick={(e) => {
                          e.stopPropagation();
                          onPreview();
                        }}
                        className="cursor-pointer"
                      >
                        <Eye className="w-4 h-4 mr-2" />
                        Preview
                      </DropdownMenuItem>
                    )}
                    {onDownload && (
                      <DropdownMenuItem
                        onClick={(e) => {
                          e.stopPropagation();
                          onDownload();
                        }}
                        className="cursor-pointer"
                      >
                        <Download className="w-4 h-4 mr-2" />
                        Download
                      </DropdownMenuItem>
                    )}
                  </DropdownMenuContent>
                </DropdownMenu>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
