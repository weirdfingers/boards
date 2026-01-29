/**
 * Hook for recording audio and video using browser MediaRecorder API.
 */

import { useCallback, useState, useRef, useEffect } from "react";

export type MediaRecordingType = "audio" | "video";
export type MediaRecorderStatus =
  | "idle"
  | "requesting"
  | "ready"
  | "recording"
  | "paused"
  | "stopped"
  | "error";

export interface MediaRecorderError {
  type: "permission" | "not-supported" | "stream" | "recording" | "unknown";
  message: string;
}

export interface UseMediaRecorderOptions {
  /**
   * Maximum recording duration in milliseconds.
   * Default: 5 minutes (300000ms)
   */
  maxDuration?: number;
  /**
   * Preferred MIME type for the recording.
   * Will fall back to supported types if not available.
   */
  mimeType?: string;
  /**
   * Audio bitrate in bits per second.
   * Default: 128000 (128 kbps)
   */
  audioBitsPerSecond?: number;
  /**
   * Video bitrate in bits per second.
   * Default: 2500000 (2.5 Mbps)
   */
  videoBitsPerSecond?: number;
}

export interface MediaRecorderResult {
  blob: Blob;
  mimeType: string;
  duration: number;
}

export interface MediaRecorderHook {
  /** Current status of the recorder */
  status: MediaRecorderStatus;
  /** Error if status is 'error' */
  error: MediaRecorderError | null;
  /** Preview stream for displaying live video/audio feedback */
  previewStream: MediaStream | null;
  /** Recording duration in milliseconds */
  duration: number;
  /** Start requesting media permissions and initialize recorder */
  initialize: (type: MediaRecordingType) => Promise<void>;
  /** Start recording */
  startRecording: () => void;
  /** Pause recording */
  pauseRecording: () => void;
  /** Resume recording */
  resumeRecording: () => void;
  /** Stop recording and return the recorded blob */
  stopRecording: () => Promise<MediaRecorderResult>;
  /** Cancel recording and release resources */
  cancelRecording: () => void;
  /** Reset to idle state */
  reset: () => void;
}

const PREFERRED_AUDIO_MIME_TYPES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/ogg;codecs=opus",
  "audio/mp4",
];

const PREFERRED_VIDEO_MIME_TYPES = [
  "video/webm;codecs=vp9,opus",
  "video/webm;codecs=vp8,opus",
  "video/webm",
  "video/mp4",
];

function getSupportedMimeType(type: MediaRecordingType): string | undefined {
  const mimeTypes =
    type === "audio" ? PREFERRED_AUDIO_MIME_TYPES : PREFERRED_VIDEO_MIME_TYPES;

  for (const mimeType of mimeTypes) {
    if (MediaRecorder.isTypeSupported(mimeType)) {
      return mimeType;
    }
  }
  return undefined;
}

function getFileExtension(mimeType: string): string {
  if (mimeType.includes("webm")) return "webm";
  if (mimeType.includes("mp4")) return "mp4";
  if (mimeType.includes("ogg")) return "ogg";
  return "bin";
}

export function useMediaRecorder(
  options: UseMediaRecorderOptions = {}
): MediaRecorderHook {
  const {
    maxDuration = 5 * 60 * 1000, // 5 minutes default
    mimeType: preferredMimeType,
    audioBitsPerSecond = 128000,
    videoBitsPerSecond = 2500000,
  } = options;

  const [status, setStatus] = useState<MediaRecorderStatus>("idle");
  const [error, setError] = useState<MediaRecorderError | null>(null);
  const [previewStream, setPreviewStream] = useState<MediaStream | null>(null);
  const [duration, setDuration] = useState(0);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const startTimeRef = useRef<number>(0);
  const durationIntervalRef = useRef<ReturnType<typeof setInterval> | null>(
    null
  );
  const maxDurationTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(
    null
  );
  const recordingTypeRef = useRef<MediaRecordingType>("audio");
  const resolveStopRef = useRef<
    ((result: MediaRecorderResult) => void) | null
  >(null);
  const mimeTypeRef = useRef<string>("");

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (durationIntervalRef.current) {
        clearInterval(durationIntervalRef.current);
      }
      if (maxDurationTimeoutRef.current) {
        clearTimeout(maxDurationTimeoutRef.current);
      }
      if (previewStream) {
        previewStream.getTracks().forEach((track) => track.stop());
      }
    };
  }, [previewStream]);

  const cleanup = useCallback(() => {
    if (durationIntervalRef.current) {
      clearInterval(durationIntervalRef.current);
      durationIntervalRef.current = null;
    }
    if (maxDurationTimeoutRef.current) {
      clearTimeout(maxDurationTimeoutRef.current);
      maxDurationTimeoutRef.current = null;
    }
    if (previewStream) {
      previewStream.getTracks().forEach((track) => track.stop());
      setPreviewStream(null);
    }
    mediaRecorderRef.current = null;
    chunksRef.current = [];
    resolveStopRef.current = null;
  }, [previewStream]);

  const reset = useCallback(() => {
    cleanup();
    setStatus("idle");
    setError(null);
    setDuration(0);
  }, [cleanup]);

  const initialize = useCallback(
    async (type: MediaRecordingType) => {
      // Check if MediaRecorder is supported
      if (typeof MediaRecorder === "undefined") {
        setStatus("error");
        setError({
          type: "not-supported",
          message: "MediaRecorder is not supported in this browser",
        });
        return;
      }

      setStatus("requesting");
      setError(null);
      recordingTypeRef.current = type;

      try {
        const constraints: MediaStreamConstraints =
          type === "audio"
            ? { audio: true, video: false }
            : { audio: true, video: { facingMode: "user" } };

        const stream = await navigator.mediaDevices.getUserMedia(constraints);
        setPreviewStream(stream);

        // Determine MIME type
        let selectedMimeType = preferredMimeType;
        if (!selectedMimeType || !MediaRecorder.isTypeSupported(selectedMimeType)) {
          selectedMimeType = getSupportedMimeType(type);
        }

        if (!selectedMimeType) {
          stream.getTracks().forEach((track) => track.stop());
          setStatus("error");
          setError({
            type: "not-supported",
            message: `No supported MIME type found for ${type} recording`,
          });
          return;
        }

        mimeTypeRef.current = selectedMimeType;

        // Create MediaRecorder
        const recorderOptions: MediaRecorderOptions = {
          mimeType: selectedMimeType,
          audioBitsPerSecond,
        };
        if (type === "video") {
          recorderOptions.videoBitsPerSecond = videoBitsPerSecond;
        }

        const recorder = new MediaRecorder(stream, recorderOptions);

        recorder.ondataavailable = (event) => {
          if (event.data.size > 0) {
            chunksRef.current.push(event.data);
          }
        };

        recorder.onstop = () => {
          const recordedDuration = Date.now() - startTimeRef.current;
          const blob = new Blob(chunksRef.current, {
            type: mimeTypeRef.current,
          });

          if (resolveStopRef.current) {
            resolveStopRef.current({
              blob,
              mimeType: mimeTypeRef.current,
              duration: recordedDuration,
            });
            resolveStopRef.current = null;
          }
        };

        recorder.onerror = () => {
          setStatus("error");
          setError({
            type: "recording",
            message: "An error occurred during recording",
          });
        };

        mediaRecorderRef.current = recorder;
        setStatus("ready");
      } catch (err) {
        let errorType: MediaRecorderError["type"] = "unknown";
        let errorMessage = "Failed to access media devices";

        if (err instanceof Error) {
          if (
            err.name === "NotAllowedError" ||
            err.name === "PermissionDeniedError"
          ) {
            errorType = "permission";
            errorMessage = `Permission denied to access ${type === "audio" ? "microphone" : "camera and microphone"}`;
          } else if (err.name === "NotFoundError") {
            errorType = "stream";
            errorMessage = `No ${type === "audio" ? "microphone" : "camera"} found`;
          } else if (err.name === "NotReadableError") {
            errorType = "stream";
            errorMessage = `${type === "audio" ? "Microphone" : "Camera"} is already in use`;
          } else {
            errorMessage = err.message;
          }
        }

        setStatus("error");
        setError({ type: errorType, message: errorMessage });
      }
    },
    [preferredMimeType, audioBitsPerSecond, videoBitsPerSecond]
  );

  const startRecording = useCallback(() => {
    if (!mediaRecorderRef.current || status !== "ready") {
      return;
    }

    chunksRef.current = [];
    startTimeRef.current = Date.now();
    setDuration(0);

    // Start duration tracking
    durationIntervalRef.current = setInterval(() => {
      setDuration(Date.now() - startTimeRef.current);
    }, 100);

    // Set max duration timeout
    maxDurationTimeoutRef.current = setTimeout(() => {
      if (
        mediaRecorderRef.current &&
        mediaRecorderRef.current.state === "recording"
      ) {
        mediaRecorderRef.current.stop();
      }
    }, maxDuration);

    mediaRecorderRef.current.start(1000); // Collect data every second
    setStatus("recording");
  }, [status, maxDuration]);

  const pauseRecording = useCallback(() => {
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state === "recording"
    ) {
      mediaRecorderRef.current.pause();
      if (durationIntervalRef.current) {
        clearInterval(durationIntervalRef.current);
        durationIntervalRef.current = null;
      }
      setStatus("paused");
    }
  }, []);

  const resumeRecording = useCallback(() => {
    if (
      mediaRecorderRef.current &&
      mediaRecorderRef.current.state === "paused"
    ) {
      const pausedDuration = duration;
      startTimeRef.current = Date.now() - pausedDuration;

      durationIntervalRef.current = setInterval(() => {
        setDuration(Date.now() - startTimeRef.current);
      }, 100);

      mediaRecorderRef.current.resume();
      setStatus("recording");
    }
  }, [duration]);

  const stopRecording = useCallback((): Promise<MediaRecorderResult> => {
    return new Promise((resolve, reject) => {
      if (!mediaRecorderRef.current) {
        reject(new Error("No active recording"));
        return;
      }

      if (
        mediaRecorderRef.current.state !== "recording" &&
        mediaRecorderRef.current.state !== "paused"
      ) {
        reject(new Error("Recording is not active"));
        return;
      }

      resolveStopRef.current = resolve;

      if (durationIntervalRef.current) {
        clearInterval(durationIntervalRef.current);
        durationIntervalRef.current = null;
      }
      if (maxDurationTimeoutRef.current) {
        clearTimeout(maxDurationTimeoutRef.current);
        maxDurationTimeoutRef.current = null;
      }

      mediaRecorderRef.current.stop();
      setStatus("stopped");

      // Stop the stream tracks
      if (previewStream) {
        previewStream.getTracks().forEach((track) => track.stop());
        setPreviewStream(null);
      }
    });
  }, [previewStream]);

  const cancelRecording = useCallback(() => {
    if (mediaRecorderRef.current) {
      if (
        mediaRecorderRef.current.state === "recording" ||
        mediaRecorderRef.current.state === "paused"
      ) {
        mediaRecorderRef.current.stop();
      }
    }
    cleanup();
    setStatus("idle");
    setDuration(0);
  }, [cleanup]);

  return {
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
  };
}

/**
 * Helper function to convert a MediaRecorderResult to a File object
 * suitable for uploading.
 */
export function mediaResultToFile(
  result: MediaRecorderResult,
  type: MediaRecordingType
): File {
  const extension = getFileExtension(result.mimeType);
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
  const filename = `${type}-recording-${timestamp}.${extension}`;

  return new File([result.blob], filename, { type: result.mimeType });
}
