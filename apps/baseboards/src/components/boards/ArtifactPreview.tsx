import React from "react";
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
  Play,
  Pause,
  RotateCcw,
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
  prompt?: string | null;
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
  prompt,
}: ArtifactPreviewProps) {
  const [isPlaying, setIsPlaying] = React.useState(false);
  const [currentTime, setCurrentTime] = React.useState(0);
  const [duration, setDuration] = React.useState(0);
  const audioRef = React.useRef<HTMLAudioElement>(null);
  const videoRef = React.useRef<HTMLVideoElement>(null);

  const isLoading = status === "PENDING" || status === "PROCESSING";
  const isFailed = status === "FAILED" || status === "CANCELLED";
  const isComplete = status === "COMPLETED";

  // Determine which URL to use for preview
  const previewUrl = thumbnailUrl || storageUrl;

  // Media control functions
  const handlePlayPause = (e: React.MouseEvent) => {
    e.stopPropagation();
    const mediaElement = artifactType === "AUDIO" ? audioRef.current : videoRef.current;
    if (!mediaElement) return;

    if (isPlaying) {
      mediaElement.pause();
      setIsPlaying(false);
    } else {
      mediaElement.play();
      setIsPlaying(true);
    }
  };

  const handleRestart = (e: React.MouseEvent) => {
    e.stopPropagation();
    const mediaElement = artifactType === "AUDIO" ? audioRef.current : videoRef.current;
    if (!mediaElement) return;

    mediaElement.currentTime = 0;
    setCurrentTime(0);
  };

  const handleTimeUpdate = () => {
    const mediaElement = artifactType === "AUDIO" ? audioRef.current : videoRef.current;
    if (!mediaElement) return;
    setCurrentTime(mediaElement.currentTime);
  };

  const handleLoadedMetadata = () => {
    const mediaElement = artifactType === "AUDIO" ? audioRef.current : videoRef.current;
    if (!mediaElement) return;
    setDuration(mediaElement.duration);
  };

  const handleMediaEnded = () => {
    setIsPlaying(false);
    setCurrentTime(0);
  };

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
        if (storageUrl) {
          return (
            <div className="relative w-full h-full">
              <video
                ref={videoRef}
                src={storageUrl}
                onTimeUpdate={handleTimeUpdate}
                onLoadedMetadata={handleLoadedMetadata}
                onEnded={handleMediaEnded}
                preload="metadata"
                className="w-full h-full object-cover"
                loop
              />
              <div className="absolute top-2 right-2 z-10 rounded-full bg-black/50 p-1.5">
                <FileVideo className="w-4 h-4 text-white" />
              </div>
              {/* Video playback controls overlay */}
              <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 flex flex-col items-center gap-2 pointer-events-auto">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handlePlayPause}
                      className="p-3 rounded-full bg-white/20 hover:bg-white/30 text-white transition-colors"
                    >
                      {isPlaying ? (
                        <Pause className="w-6 h-6" />
                      ) : (
                        <Play className="w-6 h-6" />
                      )}
                    </button>
                    <button
                      onClick={handleRestart}
                      className="p-3 rounded-full bg-white/20 hover:bg-white/30 text-white transition-colors"
                    >
                      <RotateCcw className="w-6 h-6" />
                    </button>
                  </div>
                  {duration > 0 && (
                    <div className="text-sm text-white font-medium">
                      {Math.floor(currentTime)}s / {Math.floor(duration)}s
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        }
        return (
          <div className="flex items-center justify-center h-full bg-gray-100">
            <FileVideo className="w-12 h-12 text-gray-400" />
          </div>
        );

      case "AUDIO":
        if (storageUrl) {
          const truncatedPrompt = prompt
            ? prompt.length > 60
              ? prompt.substring(0, 60) + "..."
              : prompt
            : "Audio file";

          return (
            <div className="relative w-full h-full bg-gradient-to-br from-purple-500/10 to-blue-500/10">
              <audio
                ref={audioRef}
                src={storageUrl}
                onTimeUpdate={handleTimeUpdate}
                onLoadedMetadata={handleLoadedMetadata}
                onEnded={handleMediaEnded}
                preload="metadata"
              />

              <div className="flex flex-col items-center justify-center p-4 h-full">
                <Volume2 className="w-8 h-8 text-primary mb-2" />
                <p className="text-xs text-center text-foreground leading-relaxed">
                  {truncatedPrompt}
                </p>
              </div>

              {/* Audio playback controls overlay */}
              <div className="absolute inset-0 bg-black/50 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 flex flex-col items-center gap-2 pointer-events-auto">
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handlePlayPause}
                      className="p-3 rounded-full bg-white/20 hover:bg-white/30 text-white transition-colors"
                    >
                      {isPlaying ? (
                        <Pause className="w-6 h-6" />
                      ) : (
                        <Play className="w-6 h-6" />
                      )}
                    </button>
                    <button
                      onClick={handleRestart}
                      className="p-3 rounded-full bg-white/20 hover:bg-white/30 text-white transition-colors"
                    >
                      <RotateCcw className="w-6 h-6" />
                    </button>
                  </div>
                  {duration > 0 && (
                    <div className="text-sm text-white font-medium">
                      {Math.floor(currentTime)}s / {Math.floor(duration)}s
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        }
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
      <div
        className={onClick ? "cursor-pointer aspect-square" : "aspect-square"}
        onClick={onClick}
      >
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
