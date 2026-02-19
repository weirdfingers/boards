"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Image from "next/image";
import { Share2, Download, RefreshCw, Copy, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface OutfitResultProps {
  imageUrl: string;
  onRegenerate: () => void;
  onBack: () => void;
  isRegenerating?: boolean;
}

function useCanNativeShare() {
  const [canShare, setCanShare] = useState(false);
  useEffect(() => {
    setCanShare(typeof navigator !== "undefined" && !!navigator.share);
  }, []);
  return canShare;
}

export function OutfitResult({
  imageUrl,
  onRegenerate,
  onBack: _onBack,
  isRegenerating,
}: OutfitResultProps) {
  const canNativeShare = useCanNativeShare();
  const [copied, setCopied] = useState(false);
  const copiedTimerRef = useRef<ReturnType<typeof setTimeout>>();

  useEffect(() => {
    return () => {
      if (copiedTimerRef.current) clearTimeout(copiedTimerRef.current);
    };
  }, []);

  const showCopiedFeedback = useCallback(() => {
    setCopied(true);
    if (copiedTimerRef.current) clearTimeout(copiedTimerRef.current);
    copiedTimerRef.current = setTimeout(() => setCopied(false), 2000);
  }, []);

  const handleShare = useCallback(async () => {
    if (!navigator.share) {
      try {
        await navigator.clipboard.writeText(imageUrl);
        showCopiedFeedback();
      } catch {
        // Ignore clipboard errors
      }
      return;
    }

    try {
      const response = await fetch(imageUrl);
      const blob = await response.blob();
      const file = new File([blob], "outfit.png", { type: blob.type });

      if (navigator.canShare && navigator.canShare({ files: [file] })) {
        await navigator.share({
          title: "My AI Outfit",
          files: [file],
        });
      } else {
        await navigator.share({
          title: "My AI Outfit",
          url: imageUrl,
        });
      }
    } catch (err) {
      if (err instanceof Error && err.name === "AbortError") return;
      try {
        await navigator.share({
          title: "My AI Outfit",
          url: imageUrl,
        });
      } catch {
        // User cancelled
      }
    }
  }, [imageUrl, showCopiedFeedback]);

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
          {canNativeShare ? (
            <>
              <Share2 className="size-4" />
              Share
            </>
          ) : copied ? (
            <>
              <Check className="size-4" />
              Copied!
            </>
          ) : (
            <>
              <Copy className="size-4" />
              Copy Link
            </>
          )}
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
