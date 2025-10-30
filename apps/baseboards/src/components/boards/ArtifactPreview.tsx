import { FileVideo, Volume2, FileText, Image as ImageIcon } from "lucide-react";
import Image from "next/image";

interface ArtifactPreviewProps {
  artifactType: string;
  storageUrl?: string | null;
  thumbnailUrl?: string | null;
  status: string;
  errorMessage?: string | null;
  onClick?: () => void;
}

export function ArtifactPreview({
  artifactType,
  storageUrl,
  thumbnailUrl,
  status,
  errorMessage,
  onClick,
}: ArtifactPreviewProps) {
  const isLoading = status === "PENDING" || status === "PROCESSING";
  const isFailed = status === "FAILED" || status === "CANCELLED";

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
      className={`relative aspect-square rounded-lg overflow-hidden border border-gray-200 ${
        onClick ? "cursor-pointer hover:opacity-80 transition-opacity" : ""
      }`}
      onClick={onClick}
    >
      {renderContent()}
    </div>
  );
}
