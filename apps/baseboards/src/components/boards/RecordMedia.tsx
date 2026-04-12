"use client";

import React, { useCallback, useState, useRef, useEffect } from "react";
import {
  useMediaRecorder,
  useMultiUpload,
  mediaResultToFile,
  ArtifactType,
  MediaRecordingType,
} from "@weirdfingers/boards";
import { toast } from "@/components/ui/use-toast";

interface RecordMediaProps {
  boardId: string;
  onRecordingComplete?: (generationId: string) => void;
}

function formatDuration(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${minutes}:${seconds.toString().padStart(2, "0")}`;
}

export function RecordMedia({
  boardId,
  onRecordingComplete,
}: RecordMediaProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [recordingType, setRecordingType] = useState<MediaRecordingType | null>(
    null
  );
  const videoPreviewRef = useRef<HTMLVideoElement>(null);

  const {
    status,
    error,
    previewStream,
    duration,
    initialize,
    startRecording,
    pauseRecording,
    resumeRecording,
    stopRecording,
    cancelRecording,
    reset,
  } = useMediaRecorder({ maxDuration: 5 * 60 * 1000 }); // 5 minute max

  const { uploadMultiple, isUploading } = useMultiUpload();

  // Connect preview stream to video element
  useEffect(() => {
    if (videoPreviewRef.current && previewStream) {
      videoPreviewRef.current.srcObject = previewStream;
    }
  }, [previewStream]);

  const handleStartRecording = useCallback(
    async (type: MediaRecordingType) => {
      setRecordingType(type);
      setIsOpen(true);
      await initialize(type);
    },
    [initialize]
  );

  const handleRecord = useCallback(() => {
    startRecording();
  }, [startRecording]);

  const handlePause = useCallback(() => {
    pauseRecording();
  }, [pauseRecording]);

  const handleResume = useCallback(() => {
    resumeRecording();
  }, [resumeRecording]);

  const handleStop = useCallback(async () => {
    try {
      const result = await stopRecording();
      const file = mediaResultToFile(result, recordingType!);

      // Upload the recorded file
      const artifactType =
        recordingType === "audio" ? ArtifactType.AUDIO : ArtifactType.VIDEO;

      const uploadResults = await uploadMultiple([
        {
          boardId,
          artifactType,
          source: file,
        },
      ]);

      if (uploadResults.length > 0) {
        onRecordingComplete?.(uploadResults[0].id);
        toast({
          title: "Recording uploaded",
          description: `Your ${recordingType} recording has been uploaded successfully.`,
        });
      }

      handleClose();
    } catch (err) {
      toast({
        variant: "destructive",
        title: "Recording failed",
        description:
          err instanceof Error ? err.message : "An unknown error occurred",
      });
    }
  }, [
    stopRecording,
    recordingType,
    uploadMultiple,
    boardId,
    onRecordingComplete,
  ]);

  const handleCancel = useCallback(() => {
    cancelRecording();
    handleClose();
  }, [cancelRecording]);

  const handleClose = useCallback(() => {
    reset();
    setIsOpen(false);
    setRecordingType(null);
  }, [reset]);

  const handleRetry = useCallback(() => {
    if (recordingType) {
      initialize(recordingType);
    }
  }, [recordingType, initialize]);

  const isRecordingActive = status === "recording" || status === "paused";

  return (
    <div className="relative inline-flex gap-1">
      {/* Record Audio Button */}
      <button
        onClick={() => handleStartRecording("audio")}
        className="inline-flex items-center gap-2 px-3 py-2 bg-secondary text-secondary-foreground rounded-lg hover:bg-secondary/80 transition-colors"
        title="Record audio"
      >
        <svg
          className="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
          />
        </svg>
        <span className="hidden sm:inline">Audio</span>
      </button>

      {/* Record Video Button */}
      <button
        onClick={() => handleStartRecording("video")}
        className="inline-flex items-center gap-2 px-3 py-2 bg-secondary text-secondary-foreground rounded-lg hover:bg-secondary/80 transition-colors"
        title="Record video"
      >
        <svg
          className="w-5 h-5"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
          />
        </svg>
        <span className="hidden sm:inline">Video</span>
      </button>

      {/* Recording Modal */}
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="w-full max-w-md bg-background rounded-lg shadow-xl p-6 mx-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-foreground">
                Record {recordingType === "audio" ? "Audio" : "Video"}
              </h3>
              <button
                onClick={handleCancel}
                className="text-muted-foreground hover:text-foreground"
                aria-label="Close recording dialog"
                disabled={isUploading}
              >
                <svg
                  className="w-6 h-6"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M6 18L18 6M6 6l12 12"
                  />
                </svg>
              </button>
            </div>

            {/* Error State */}
            {status === "error" && error && (
              <div className="text-center py-8">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
                  <svg
                    className="w-8 h-8 text-red-600 dark:text-red-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                </div>
                <p className="text-foreground font-medium mb-2">
                  {error.type === "permission"
                    ? "Permission Required"
                    : error.type === "not-supported"
                      ? "Not Supported"
                      : "Error"}
                </p>
                <p className="text-muted-foreground text-sm mb-4">
                  {error.message}
                </p>
                {error.type === "permission" && (
                  <p className="text-muted-foreground text-xs mb-4">
                    Please allow access to your{" "}
                    {recordingType === "audio"
                      ? "microphone"
                      : "camera and microphone"}{" "}
                    in your browser settings.
                  </p>
                )}
                <button
                  onClick={handleRetry}
                  className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
                >
                  Try Again
                </button>
              </div>
            )}

            {/* Requesting Permission State */}
            {status === "requesting" && (
              <div className="text-center py-8">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-muted flex items-center justify-center animate-pulse">
                  {recordingType === "audio" ? (
                    <svg
                      className="w-8 h-8 text-muted-foreground"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
                      />
                    </svg>
                  ) : (
                    <svg
                      className="w-8 h-8 text-muted-foreground"
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
                      />
                    </svg>
                  )}
                </div>
                <p className="text-foreground font-medium">
                  Requesting Permission
                </p>
                <p className="text-muted-foreground text-sm mt-2">
                  Please allow access to your{" "}
                  {recordingType === "audio"
                    ? "microphone"
                    : "camera and microphone"}
                </p>
              </div>
            )}

            {/* Preview and Recording State */}
            {(status === "ready" || isRecordingActive || status === "stopped") && (
              <div>
                {/* Video Preview */}
                {recordingType === "video" && previewStream && (
                  <div className="relative mb-4 rounded-lg overflow-hidden bg-black aspect-video">
                    <video
                      ref={videoPreviewRef}
                      autoPlay
                      muted
                      playsInline
                      className="w-full h-full object-cover"
                    />
                    {isRecordingActive && (
                      <div className="absolute top-3 left-3 flex items-center gap-2 px-2 py-1 bg-red-600 text-white text-sm rounded">
                        <span className="w-2 h-2 bg-white rounded-full animate-pulse" />
                        REC
                      </div>
                    )}
                  </div>
                )}

                {/* Audio Waveform Placeholder */}
                {recordingType === "audio" && (
                  <div className="relative mb-4 rounded-lg bg-muted aspect-[2/1] flex items-center justify-center">
                    {isRecordingActive ? (
                      <div className="flex items-center gap-1">
                        {[...Array(5)].map((_, i) => (
                          <div
                            key={i}
                            className="w-2 bg-primary rounded-full animate-pulse"
                            style={{
                              height: `${20 + Math.random() * 40}px`,
                              animationDelay: `${i * 0.1}s`,
                            }}
                          />
                        ))}
                      </div>
                    ) : (
                      <div className="text-center">
                        <svg
                          className="w-12 h-12 mx-auto text-muted-foreground mb-2"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
                          />
                        </svg>
                        <p className="text-muted-foreground text-sm">
                          Ready to record
                        </p>
                      </div>
                    )}
                    {isRecordingActive && (
                      <div className="absolute top-3 left-3 flex items-center gap-2 px-2 py-1 bg-red-600 text-white text-sm rounded">
                        <span className="w-2 h-2 bg-white rounded-full animate-pulse" />
                        REC
                      </div>
                    )}
                  </div>
                )}

                {/* Duration Display */}
                <div className="text-center mb-4">
                  <span className="text-2xl font-mono text-foreground">
                    {formatDuration(duration)}
                  </span>
                  <p className="text-xs text-muted-foreground mt-1">
                    Max: 5:00
                  </p>
                </div>

                {/* Controls */}
                <div className="flex items-center justify-center gap-3">
                  {status === "ready" && (
                    <button
                      onClick={handleRecord}
                      className="flex items-center justify-center w-14 h-14 rounded-full bg-red-600 text-white hover:bg-red-700 transition-colors"
                      title="Start recording"
                    >
                      <span className="w-5 h-5 rounded-full bg-white" />
                    </button>
                  )}

                  {status === "recording" && (
                    <>
                      <button
                        onClick={handlePause}
                        className="flex items-center justify-center w-12 h-12 rounded-full bg-muted text-foreground hover:bg-muted/80 transition-colors"
                        title="Pause recording"
                      >
                        <svg
                          className="w-6 h-6"
                          fill="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <rect x="6" y="4" width="4" height="16" rx="1" />
                          <rect x="14" y="4" width="4" height="16" rx="1" />
                        </svg>
                      </button>
                      <button
                        onClick={handleStop}
                        disabled={isUploading}
                        className="flex items-center justify-center w-14 h-14 rounded-full bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        title="Stop and save"
                      >
                        <span className="w-5 h-5 rounded bg-white" />
                      </button>
                    </>
                  )}

                  {status === "paused" && (
                    <>
                      <button
                        onClick={handleResume}
                        className="flex items-center justify-center w-12 h-12 rounded-full bg-muted text-foreground hover:bg-muted/80 transition-colors"
                        title="Resume recording"
                      >
                        <svg
                          className="w-6 h-6"
                          fill="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path d="M8 5v14l11-7z" />
                        </svg>
                      </button>
                      <button
                        onClick={handleStop}
                        disabled={isUploading}
                        className="flex items-center justify-center w-14 h-14 rounded-full bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                        title="Stop and save"
                      >
                        <span className="w-5 h-5 rounded bg-white" />
                      </button>
                    </>
                  )}
                </div>

                {/* Uploading indicator */}
                {isUploading && (
                  <div className="mt-4 text-center">
                    <p className="text-sm text-muted-foreground">
                      Uploading recording...
                    </p>
                  </div>
                )}

                {/* Instructions */}
                {status === "ready" && (
                  <p className="text-center text-muted-foreground text-sm mt-4">
                    Click the red button to start recording
                  </p>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
