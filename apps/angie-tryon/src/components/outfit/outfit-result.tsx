"use client";

import { useCallback } from "react";
import Image from "next/image";
import { Share2, Download, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface OutfitResultProps {
  imageUrl: string;
  onRegenerate: () => void;
  onBack: () => void;
  isRegenerating?: boolean;
}

export function OutfitResult({
  imageUrl,
  onRegenerate,
  onBack,
  isRegenerating,
}: OutfitResultProps) {
  const handleShare = useCallback(async () => {
    if (!navigator.share) {
      // Fallback: copy URL to clipboard
      try {
        await navigator.clipboard.writeText(imageUrl);
      } catch {
        // Ignore clipboard errors
      }
      return;
    }

    try {
      // Try sharing with the image file
      const response = await fetch(imageUrl);
      const blob = await response.blob();
      const file = new File([blob], "outfit.png", { type: blob.type });

      await navigator.share({
        title: "My AI Outfit",
        files: [file],
      });
    } catch {
      // User cancelled or share failed — try URL-only share
      try {
        await navigator.share({
          title: "My AI Outfit",
          url: imageUrl,
        });
      } catch {
        // User cancelled
      }
    }
  }, [imageUrl]);

  const handleDownload = useCallback(async () => {
    try {
      const response = await fetch(imageUrl);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "outfit.png";
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch {
      // Fallback: open in new tab
      window.open(imageUrl, "_blank");
    }
  }, [imageUrl]);

  return (
    <div className="flex flex-col gap-4">
      {/* Generated Image */}
      <div className="relative aspect-[3/4] w-full overflow-hidden rounded-2xl bg-muted">
        <Image
          src={imageUrl}
          alt="Generated outfit"
          fill
          className="object-cover"
          sizes="(max-width: 512px) 100vw, 512px"
          priority
        />
      </div>

      {/* Action Buttons */}
      <div className="grid grid-cols-2 gap-3">
        <Button
          variant="outline"
          className="h-12 gap-2 rounded-xl"
          onClick={handleShare}
        >
          <Share2 className="size-4" />
          Share
        </Button>
        <Button
          variant="outline"
          className="h-12 gap-2 rounded-xl"
          onClick={handleDownload}
        >
          <Download className="size-4" />
          Download
        </Button>
      </div>

      {/* Regenerate */}
      <Button
        variant="secondary"
        className={cn("h-12 gap-2 rounded-xl")}
        onClick={onRegenerate}
        disabled={isRegenerating}
      >
        <RefreshCw className={cn("size-4", isRegenerating && "animate-spin")} />
        {isRegenerating ? "Regenerating..." : "Regenerate"}
      </Button>
    </div>
  );
}
