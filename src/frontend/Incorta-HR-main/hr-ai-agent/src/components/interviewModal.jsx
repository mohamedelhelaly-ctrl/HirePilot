import { FiX, FiMic, FiMicOff, FiSquare } from "react-icons/fi";
import { useState, useEffect, useRef } from "react";

/**
 * InterviewModal — Popup with audio wave animation for live interviews
 * Shows candidate info, animated audio wave, and interview controls
 */
export default function InterviewModal({
  isOpen,
  onClose,
  candidateName,
  applicationId,
  requisitionId,
  sessionId,
}) {
  const [isRecording, setIsRecording] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef(null);
  const barsRef = useRef(null);

  // Timer for elapsed recording time
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

  // Animate audio bars
  useEffect(() => {
    if (!isRecording || !barsRef.current) return;

    const bars = barsRef.current.querySelectorAll(".audio-bar");
    const intervals = [];

    bars.forEach((bar, i) => {
      const animate = () => {
        const height = isRecording
          ? Math.random() * 70 + 10
          : 8;
        bar.style.height = `${height}%`;
      };

      // Stagger the animation slightly for each bar
      const interval = setInterval(animate, 80 + i * 15);
      intervals.push(interval);
      animate(); // initial
    });

    return () => intervals.forEach(clearInterval);
  }, [isRecording]);

  // Reset state on close
  useEffect(() => {
    if (!isOpen) {
      setIsRecording(false);
      setElapsed(0);
    }
  }, [isOpen]);

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, "0");
    const s = (seconds % 60).toString().padStart(2, "0");
    return `${m}:${s}`;
  };

  const handleStartRecording = () => {
    setIsRecording(true);
  };

  const handleStopRecording = () => {
    setIsRecording(false);
  };

  if (!isOpen) return null;

  const NUM_BARS = 48;

  return (
    <>
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        onClick={onClose}
      >
        {/* Modal */}
        <div
          className="bg-white rounded-2xl shadow-2xl w-full max-w-xl overflow-hidden"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-5 border-b border-gray-100">
            <div>
              <h2 className="text-xl font-bold text-gray-900">Live Interview</h2>
              <p className="text-sm text-gray-500 mt-0.5">{candidateName}</p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition p-1.5 hover:bg-gray-100 rounded-lg"
            >
              <FiX size={22} />
            </button>
          </div>

          {/* Audio Wave Section */}
          <div className="px-6 py-10 flex flex-col items-center">
            {/* Recording indicator */}
            {isRecording && (
              <div className="flex items-center gap-2 mb-6">
                <div className="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse" />
                <span className="text-sm font-semibold text-red-500 uppercase tracking-wider">
                  Recording
                </span>
              </div>
            )}

            {/* Audio Visualizer */}
            <div
              ref={barsRef}
              className="flex items-center justify-center gap-[3px] h-32 w-full max-w-md mb-8"
            >
              {Array.from({ length: NUM_BARS }).map((_, i) => (
                <div
                  key={i}
                  className="audio-bar rounded-full transition-all"
                  style={{
                    width: "4px",
                    height: isRecording ? "20%" : "8%",
                    backgroundColor: isRecording
                      ? `hsl(${220 + (i * 3)}, 70%, ${45 + Math.sin(i * 0.3) * 15}%)`
                      : "#D1D5DB",
                    transition: "height 0.08s ease-out, background-color 0.3s ease",
                  }}
                />
              ))}
            </div>

            {/* Timer */}
            <div className="text-3xl font-mono font-bold text-gray-800 mb-8 tabular-nums">
              {formatTime(elapsed)}
            </div>

            {/* Controls */}
            <div className="flex items-center gap-4">
              {!isRecording ? (
                <button
                  onClick={handleStartRecording}
                  className="flex items-center gap-3 px-8 py-3.5 bg-blue-600 text-white rounded-xl font-semibold text-base hover:bg-blue-700 transition-all shadow-lg shadow-blue-600/25 hover:shadow-xl hover:shadow-blue-600/30 active:scale-95"
                >
                  <FiMic size={20} />
                  Start Interview
                </button>
              ) : (
                <div className="flex items-center gap-3">
                  <button
                    onClick={handleStopRecording}
                    className="flex items-center gap-3 px-8 py-3.5 bg-red-500 text-white rounded-xl font-semibold text-base hover:bg-red-600 transition-all shadow-lg shadow-red-500/25 active:scale-95"
                  >
                    <FiSquare size={18} />
                    End Interview
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Footer Info */}
          <div className="px-6 py-4 bg-gray-50 border-t border-gray-100">
            <div className="flex items-center justify-between text-xs text-gray-500">
              <span>Session ID: {sessionId || "—"}</span>
              <span>Application #{applicationId}</span>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
