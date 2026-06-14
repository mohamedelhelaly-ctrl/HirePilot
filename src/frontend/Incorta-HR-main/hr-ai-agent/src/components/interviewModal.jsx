import { FiX, FiMic, FiSquare } from "react-icons/fi";
import { useState, useEffect, useRef, useCallback } from "react";
import {
  createInterviewWebSocket,
  sendInterviewInit,
  sendAudioChunk,
  sendEndInterview,
  getOrCreateInterviewSession,
  INTERVIEW_TYPES,
  INTERVIEW_TYPE_OPTIONS,
  getInterviewTypeLabel,
} from "../services/interviewService";

const CHUNK_INTERVAL_MS = 5000;

/**
 * InterviewModal — Live interview with WebSocket streaming and mic capture.
 */
export default function InterviewModal({
  isOpen,
  onClose,
  candidateName,
  applicationId,
  requisitionId,
}) {
  const [selectedType, setSelectedType] = useState(INTERVIEW_TYPES.HR_SCREEN);
  const [sessionId, setSessionId] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isEnding, setIsEnding] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [followups, setFollowups] = useState([]);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [summary, setSummary] = useState(null);

  const timerRef = useRef(null);
  const barsRef = useRef(null);
  const wsRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const segmentTimerRef = useRef(null);
  const isEndingRef = useRef(false);

  const cleanupMedia = useCallback(() => {
    isEndingRef.current = true;

    if (segmentTimerRef.current) {
      clearInterval(segmentTimerRef.current);
      segmentTimerRef.current = null;
    }

    if (mediaRecorderRef.current?.state !== "inactive") {
      try {
        mediaRecorderRef.current?.stop();
      } catch {
        /* already stopped */
      }
    }
    mediaRecorderRef.current = null;

    mediaStreamRef.current?.getTracks().forEach((t) => t.stop());
    mediaStreamRef.current = null;
  }, []);

  const cleanupWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.close();
    }
    wsRef.current = null;
  }, []);

  const resetState = useCallback(() => {
    setIsRecording(false);
    setIsConnecting(false);
    setIsEnding(false);
    setSelectedType(INTERVIEW_TYPES.HR_SCREEN);
    setSessionId(null);
    setElapsed(0);
    setFollowups([]);
    setStatus("");
    setError("");
    setSummary(null);
    cleanupMedia();
    cleanupWebSocket();
  }, [cleanupMedia, cleanupWebSocket]);

  useEffect(() => {
    if (!isOpen) resetState();
  }, [isOpen, resetState]);

  useEffect(() => {
    if (isRecording) {
      timerRef.current = setInterval(() => {
        setElapsed((prev) => prev + 1);
      }, 1000);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [isRecording]);

  useEffect(() => {
    if (!isRecording || !barsRef.current) return;

    const bars = barsRef.current.querySelectorAll(".audio-bar");
    const intervals = [];

    bars.forEach((bar, i) => {
      const animate = () => {
        const height = isRecording ? Math.random() * 70 + 10 : 8;
        bar.style.height = `${height}%`;
      };
      const interval = setInterval(animate, 80 + i * 15);
      intervals.push(interval);
      animate();
    });

    return () => intervals.forEach(clearInterval);
  }, [isRecording]);

  const startMediaCapture = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaStreamRef.current = stream;

    const mimeType = [
      "audio/webm;codecs=opus",
      "audio/webm",
      "audio/ogg;codecs=opus",
      "audio/ogg",
      "audio/mp4",
    ].find((t) => MediaRecorder.isTypeSupported(t)) ?? "";

    const fmt = mimeType.includes("ogg")
      ? "ogg"
      : mimeType.includes("mp4")
        ? "mp4"
        : "webm";

    isEndingRef.current = false;

    const startSegment = () => {
      if (isEndingRef.current || !mediaStreamRef.current) return;

      const segmentChunks = [];
      const recorder = new MediaRecorder(
        mediaStreamRef.current,
        mimeType ? { mimeType } : undefined
      );
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) segmentChunks.push(e.data);
      };

      recorder.onstop = () => {
        const socket = wsRef.current;

        const restartOrEnd = () => {
          if (!isEndingRef.current) {
            startSegment();
          } else {
            mediaStreamRef.current?.getTracks().forEach((t) => t.stop());
            setTimeout(() => {
              if (wsRef.current?.readyState === WebSocket.OPEN) {
                sendEndInterview(wsRef.current);
              }
            }, 300);
          }
        };

        if (segmentChunks.length === 0 || !socket || socket.readyState !== WebSocket.OPEN) {
          restartOrEnd();
          return;
        }

        const blob = new Blob(segmentChunks, { type: mimeType || "audio/webm" });
        if (blob.size < 500) {
          restartOrEnd();
          return;
        }

        const reader = new FileReader();
        reader.onload = () => {
          const b64 = String(reader.result).split(",")[1];
          if (b64 && socket.readyState === WebSocket.OPEN) {
            sendAudioChunk(socket, b64, fmt, "microphone");
          }
          restartOrEnd();
        };
        reader.onerror = () => {
          console.error("Failed to read audio chunk");
          restartOrEnd();
        };
        reader.readAsDataURL(blob);
      };

      recorder.start();
    };

    startSegment();

    segmentTimerRef.current = setInterval(() => {
      if (mediaRecorderRef.current?.state === "recording") {
        mediaRecorderRef.current.stop();
      }
    }, CHUNK_INTERVAL_MS);
  }, []);

  const handleWsMessage = useCallback(async (msg) => {
    switch (msg.type) {
      case "init_ok":
        setStatus("Interview started");
        setIsConnecting(false);
        try {
          await startMediaCapture();
          setIsRecording(true);
        } catch (err) {
          setError(err.message || "Microphone access denied");
          cleanupWebSocket();
        }
        break;
      case "followup_question":
        setFollowups((prev) => [...prev, msg.question]);
        break;
      case "status":
        if (msg.status !== "transcribing") {
          setStatus(msg.status);
        }
        break;
      case "summary":
        setSummary(msg.data);
        setIsEnding(false);
        setIsRecording(false);
        cleanupMedia();
        break;
      case "error":
        setError(msg.message || "Unknown server error");
        setIsConnecting(false);
        setIsEnding(false);
        break;
      default:
        break;
    }
  }, [cleanupMedia, cleanupWebSocket, startMediaCapture]);

  const handleStartRecording = async () => {
    if (!applicationId || !requisitionId) {
      setError("Missing session details — close and try again.");
      return;
    }

    setError("");
    setIsConnecting(true);
    setStatus("Preparing session...");

    try {
      const session = await getOrCreateInterviewSession(
        applicationId,
        requisitionId,
        selectedType
      );
      setSessionId(session.id);
      setStatus("Connecting...");

      const ws = createInterviewWebSocket(
        handleWsMessage,
        () => {
          if (!summary) setStatus("Disconnected");
        },
        () => setError("WebSocket connection failed"),
        (socket) => {
          wsRef.current = socket;
          sendInterviewInit(socket, {
            sessionId: session.id,
            applicationId,
            requisitionId,
            interviewType: selectedType,
          });
        }
      );
      wsRef.current = ws;
    } catch (err) {
      setError(err.message || "Failed to start interview session");
      setIsConnecting(false);
      setStatus("");
    }
  };

  const handleStopRecording = () => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setError("Not connected to interview server");
      return;
    }

    setIsEnding(true);
    setIsRecording(false);
    setStatus("generating_summary");

    if (segmentTimerRef.current) {
      clearInterval(segmentTimerRef.current);
      segmentTimerRef.current = null;
    }

    isEndingRef.current = true;

    const rec = mediaRecorderRef.current;
    if (rec && rec.state === "recording") {
      rec.stop();
    } else {
      mediaStreamRef.current?.getTracks().forEach((t) => t.stop());
      setTimeout(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          sendEndInterview(wsRef.current);
        }
      }, 100);
    }
  };

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, "0");
    const s = (seconds % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

  if (!isOpen) return null;

  const NUM_BARS = 48;
  const showControls = !summary;

  return (
    <div
      className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-xl overflow-hidden max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-6 py-5 border-b border-gray-100">
          <div>
            <h2 className="text-xl font-bold text-gray-900">Live Interview</h2>
            <p className="text-sm text-gray-500 mt-0.5">
              {candidateName}
              {(isRecording || isConnecting || summary) && (
                <span className="text-gray-400"> · {getInterviewTypeLabel(selectedType)}</span>
              )}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition p-1.5 hover:bg-gray-100 rounded-lg"
          >
            <FiX size={22} />
          </button>
        </div>

        <div className="px-6 py-6 flex flex-col items-center overflow-y-auto flex-1">
          {isRecording && (
            <div className="flex items-center gap-2 mb-4">
              <div className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse" />
              <span className="text-sm font-semibold text-red-500 uppercase tracking-wider">
                Recording
              </span>
            </div>
          )}

          <div
            ref={barsRef}
            className="flex items-center justify-center gap-[3px] h-24 w-full max-w-md mb-6"
          >
            {Array.from({ length: NUM_BARS }).map((_, i) => (
              <div
                key={i}
                className="audio-bar rounded-full transition-all"
                style={{
                  width: "4px",
                  height: isRecording ? "20%" : "8%",
                  backgroundColor: isRecording
                    ? `hsl(${220 + i * 3}, 70%, ${45 + Math.sin(i * 0.3) * 15}%)`
                    : "#D1D5DB",
                  transition: "height 0.08s ease-out, background-color 0.3s ease",
                }}
              />
            ))}
          </div>

          <div className="text-3xl font-mono font-bold text-gray-800 mb-4 tabular-nums">
            {formatTime(elapsed)}
          </div>

          {status && (
            <p className="text-sm text-gray-500 mb-4 capitalize">
              {status.replace(/_/g, " ")}
            </p>
          )}

          {error && (
            <p className="text-sm text-red-600 mb-4 text-center">{error}</p>
          )}

          {followups.length > 0 && !summary && (
            <div className="w-full mb-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
              <p className="text-xs font-semibold text-amber-700 uppercase mb-1">
                Suggested follow-up
              </p>
              <p className="text-sm text-amber-900">
                {followups[followups.length - 1]}
              </p>
            </div>
          )}

          {summary && (
            <div className="w-full mb-4 p-4 bg-blue-50 border border-blue-200 rounded-lg text-left space-y-3">
              <p className="text-sm font-semibold text-blue-900">Interview Evaluation</p>
              {summary.summary && (
                <p className="text-sm text-gray-700">{summary.summary}</p>
              )}
              {summary.overall_assessment && (
                <p className="text-sm text-gray-600">{summary.overall_assessment}</p>
              )}
              <p className="text-sm font-medium text-gray-800">
                Recommendation: {summary.recommendation_score}/10
                {summary.technical_depth_score != null &&
                  ` · Technical depth: ${summary.technical_depth_score}/10`}
              </p>
              {summary.key_strengths?.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase mb-1">
                    Strengths
                  </p>
                  <p className="text-sm text-gray-700">
                    {summary.key_strengths.join(", ")}
                  </p>
                </div>
              )}
              {summary.key_concerns?.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-gray-500 uppercase mb-1">
                    Concerns
                  </p>
                  <p className="text-sm text-gray-700">
                    {summary.key_concerns.join(", ")}
                  </p>
                </div>
              )}
            </div>
          )}

          {showControls && !isRecording && !isConnecting && (
            <div className="w-full mb-6">
              <p className="text-sm font-semibold text-gray-700 mb-3 text-center">
                Choose interview type
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {INTERVIEW_TYPE_OPTIONS.map((option) => {
                  const selected = selectedType === option.value;
                  return (
                    <button
                      key={option.value}
                      type="button"
                      onClick={() => setSelectedType(option.value)}
                      className={`text-left p-4 rounded-xl border-2 transition-all ${
                        selected
                          ? "border-blue-600 bg-blue-50 shadow-sm"
                          : "border-gray-200 bg-white hover:border-gray-300"
                      }`}
                    >
                      <p
                        className={`text-sm font-semibold ${
                          selected ? "text-blue-700" : "text-gray-900"
                        }`}
                      >
                        {option.label}
                      </p>
                      <p className="text-xs text-gray-500 mt-1 leading-relaxed">
                        {option.description}
                      </p>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {showControls && (
            <div className="flex items-center gap-4">
              {!isRecording && !isConnecting ? (
                <button
                  onClick={handleStartRecording}
                  disabled={isEnding}
                  className="flex items-center gap-3 px-8 py-3.5 bg-blue-600 text-white rounded-xl font-semibold text-base hover:bg-blue-700 transition-all shadow-lg shadow-blue-600/25 disabled:opacity-50"
                >
                  <FiMic size={20} />
                  Start {getInterviewTypeLabel(selectedType)}
                </button>
              ) : isConnecting ? (
                <button
                  disabled
                  className="flex items-center gap-3 px-8 py-3.5 bg-gray-400 text-white rounded-xl font-semibold text-base"
                >
                  Connecting...
                </button>
              ) : (
                <button
                  onClick={handleStopRecording}
                  disabled={isEnding}
                  className="flex items-center gap-3 px-8 py-3.5 bg-red-500 text-white rounded-xl font-semibold text-base hover:bg-red-600 transition-all shadow-lg shadow-red-500/25 disabled:opacity-50"
                >
                  <FiSquare size={18} />
                  {isEnding ? "Generating summary..." : "End Interview"}
                </button>
              )}
            </div>
          )}
        </div>

        <div className="px-6 py-4 bg-gray-50 border-t border-gray-100">
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>Session ID: {sessionId || "—"}</span>
            <span>Application #{applicationId}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
