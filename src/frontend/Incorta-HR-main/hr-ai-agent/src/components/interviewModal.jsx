import { FiX, FiMic, FiSquare, FiMonitor, FiChevronDown, FiChevronRight } from "react-icons/fi";
import { useState, useEffect, useRef, useCallback, useMemo } from "react";
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

const PHASE = {
  SETUP: "setup",
  RECORDING: "recording",
  EVALUATING: "evaluating",
  RESULTS: "results",
};

const AUDIO_SOURCE = {
  MICROPHONE: "microphone",
  MIXED: "mixed",
};

function formatTime(seconds) {
  const m = Math.floor(seconds / 60)
    .toString()
    .padStart(2, "0");
  const s = (seconds % 60).toString().padStart(2, "0");
  return `${m}:${s}`;
}

function getScoreColor10(score) {
  if (score == null) return "#6e6e73";
  if (score >= 8) return "#22c55e";
  if (score >= 5) return "#f59e0b";
  return "#dc2626";
}

function QuestionCard({ index, label, hint, hintLabel = "Guide" }) {
  const [open, setOpen] = useState(false);

  return (
    <div className={`qmodal-q-card${open ? " qmodal-q-card--open" : ""}`}>
      {hint ? (
        <>
          <button
            type="button"
            className="qmodal-q-header"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
          >
            <span className="qmodal-q-num">{index}</span>
            <p className="qmodal-q-text">{label}</p>
            <span className="qmodal-q-chevron" aria-hidden="true">
              {open ? "▾" : "▸"}
            </span>
          </button>
          {open && (
            <div className="qmodal-q-answer">
              <span className="qmodal-q-answer-label">{hintLabel}</span>
              <p>{hint}</p>
            </div>
          )}
        </>
      ) : (
        <div className="qmodal-q-header qmodal-q-header--static">
          <span className="qmodal-q-num">{index}</span>
          <p className="qmodal-q-text">{label}</p>
        </div>
      )}
    </div>
  );
}

function CollapsibleGuideCard({ title, subtitle, count, isOpen, onToggle, variant = "prepared", children }) {
  return (
    <div className={`iv-guide-card iv-guide-card--${variant}${isOpen ? "" : " iv-guide-card--collapsed"}`}>
      <button
        type="button"
        className="iv-guide-card__header"
        onClick={onToggle}
        aria-expanded={isOpen}
      >
        <div className="iv-guide-card__header-text">
          <h3 className="iv-guide-card__title">{title}</h3>
          {subtitle && <p className="iv-guide-card__subtitle">{subtitle}</p>}
        </div>
        <div className="iv-guide-card__header-actions">
          {count != null && (
            <span className="iv-guide-card__count">{count}</span>
          )}
          {isOpen ? (
            <FiChevronDown size={18} className="iv-guide-card__chevron" aria-hidden="true" />
          ) : (
            <FiChevronRight size={18} className="iv-guide-card__chevron" aria-hidden="true" />
          )}
        </div>
      </button>
      {isOpen && <div className="iv-guide-card__body">{children}</div>}
    </div>
  );
}

function InterviewGuideColumn({ candidateName, selectedType, interviewQuestions, followups }) {
  const [preparedOpen, setPreparedOpen] = useState(true);
  const [followupsOpen, setFollowupsOpen] = useState(true);

  const sections = useMemo(() => {
    const result = [];
    const isTechnical = selectedType === INTERVIEW_TYPES.TECHNICAL;

    if (isTechnical && interviewQuestions.tech.length > 0) {
      result.push({
        title: "Technical Questions",
        items: interviewQuestions.tech.map((q) => ({
          label: q.question,
          hint: q.answer ? q.answer : null,
          hintLabel: "Model answer",
        })),
      });
    }

    if (!isTechnical && interviewQuestions.cbi.length > 0) {
      result.push({
        title: "CBI Questions (STAR)",
        items: interviewQuestions.cbi.map((q) => ({
          label: q.question,
          hint: q.star_guide || q.competency || null,
          hintLabel: q.competency ? "Competency" : "STAR guide",
        })),
      });
    }

    if (interviewQuestions.session.length > 0) {
      result.push({
        title: "Session Questions",
        items: interviewQuestions.session.map((q) => ({
          label: typeof q === "string" ? q : q.question || String(q),
          hint: null,
        })),
      });
    }

    return result;
  }, [selectedType, interviewQuestions]);

  const preparedCount = sections.reduce((sum, section) => sum + section.items.length, 0);

  useEffect(() => {
    if (followups.length > 0) {
      setFollowupsOpen(true);
    }
  }, [followups.length]);

  return (
    <div className="iv-guide-column">
      <CollapsibleGuideCard
        title="Prepared Questions"
        subtitle={`Tailored for ${candidateName}`}
        count={preparedCount > 0 ? preparedCount : null}
        isOpen={preparedOpen}
        onToggle={() => setPreparedOpen((v) => !v)}
        variant="prepared"
      >
        {sections.length > 0 ? (
          sections.map((section) => (
            <div key={section.title} className="iv-questions-panel__section">
              <p className="iv-questions-panel__section-title">{section.title}</p>
              <div className="qmodal-questions">
                {section.items.map((item, idx) => (
                  <QuestionCard
                    key={`${section.title}-${idx}`}
                    index={idx + 1}
                    label={item.label}
                    hint={item.hint}
                    hintLabel={item.hintLabel}
                  />
                ))}
              </div>
            </div>
          ))
        ) : (
          <p className="iv-followup-empty">
            No prepared questions yet. Generate Tech Q or CBI Q from the candidate row before
            starting.
          </p>
        )}
      </CollapsibleGuideCard>

      <CollapsibleGuideCard
        title="AI Follow-up Questions"
        subtitle="Suggested probes based on the live conversation"
        count={followups.length > 0 ? followups.length : null}
        isOpen={followupsOpen}
        onToggle={() => setFollowupsOpen((v) => !v)}
        variant="followup"
      >
        {followups.length === 0 ? (
          <p className="iv-followup-empty">
            Follow-ups appear here as the interview progresses and the AI detects gaps in
            responses.
          </p>
        ) : (
          <div className="iv-followup-list">
            {followups.map((item, idx) => {
              const isLatest = idx === followups.length - 1;
              return (
                <div
                  key={`${item.timestamp}-${idx}`}
                  className={`iv-followup-card${isLatest ? " iv-followup-card--latest" : ""}`}
                >
                  <span className="iv-followup-card__num">{idx + 1}</span>
                  <div className="iv-followup-card__content">
                    {isLatest && (
                      <span className="iv-followup-card__badge">Latest</span>
                    )}
                    <p className="iv-followup-card__text">{item.question}</p>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CollapsibleGuideCard>
    </div>
  );
}

function InterviewSetupPanel({
  candidateName,
  selectedType,
  setSelectedType,
  audioSource,
  setAudioSource,
  error,
  isConnecting,
  onStart,
  onClose,
}) {
  return (
    <div className="modal-panel modal-panel--interview-setup">
      <div className="modal-header">
        <div>
          <h2>Start Interview</h2>
          <p className="muted small" style={{ margin: "4px 0 0" }}>
            {candidateName}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 transition p-1.5 hover:bg-gray-100 rounded-lg"
          aria-label="Close"
        >
          <FiX size={20} />
        </button>
      </div>

      <div className="iv-setup-section">
        <p className="field-label">Interview type</p>
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

      <div className="iv-setup-section">
        <p className="field-label">Audio source</p>
        <div className="iv-radio-group">
          <label
            className={`iv-radio-card${
              audioSource === AUDIO_SOURCE.MICROPHONE ? " iv-radio-card--active" : ""
            }`}
          >
            <input
              type="radio"
              name="iv-audio-src"
              value={AUDIO_SOURCE.MICROPHONE}
              checked={audioSource === AUDIO_SOURCE.MICROPHONE}
              onChange={() => setAudioSource(AUDIO_SOURCE.MICROPHONE)}
            />
            <span className="iv-radio-card__icon">🎤</span>
            <span className="iv-radio-card__label">Mic only</span>
          </label>
          <label
            className={`iv-radio-card${
              audioSource === AUDIO_SOURCE.MIXED ? " iv-radio-card--active" : ""
            }`}
          >
            <input
              type="radio"
              name="iv-audio-src"
              value={AUDIO_SOURCE.MIXED}
              checked={audioSource === AUDIO_SOURCE.MIXED}
              onChange={() => setAudioSource(AUDIO_SOURCE.MIXED)}
            />
            <span className="iv-radio-card__icon">🖥</span>
            <span className="iv-radio-card__label">Mic + System audio</span>
          </label>
        </div>
        {audioSource === AUDIO_SOURCE.MIXED && (
          <p className="muted small" style={{ marginTop: 8, lineHeight: 1.5 }}>
            Your browser will ask you to share a screen or tab to capture system audio. Video is
            not recorded.
          </p>
        )}
      </div>

      {error && <p className="form-error">{error}</p>}

      <button
        type="button"
        onClick={onStart}
        disabled={isConnecting}
        className="w-full flex items-center justify-center gap-2 px-6 py-3.5 bg-blue-600 text-white rounded-xl font-semibold text-sm hover:bg-blue-700 transition-all shadow-lg shadow-blue-600/20 disabled:opacity-50"
      >
        <FiMic size={18} />
        {isConnecting ? "Connecting…" : `Start ${getInterviewTypeLabel(selectedType)}`}
      </button>
    </div>
  );
}

function InterviewLivePanel({
  candidateName,
  selectedType,
  audioSource,
  seconds,
  status,
  onStop,
  isEnding,
}) {
  return (
    <div className="modal-panel modal-panel--interview-setup iv-live-panel">
      <div className="iv-live-panel__controls">
        <div style={{ textAlign: "center", padding: "8px 0 12px" }}>
          <div className="iv-rec-badge">
            <span className="iv-rec-dot" aria-hidden="true" />
            REC
          </div>
          <h2 style={{ margin: "16px 0 4px", fontSize: "1.25rem" }}>{candidateName}</h2>
          <p className="muted small" style={{ margin: 0 }}>
            {getInterviewTypeLabel(selectedType)} Interview
          </p>

          <div className="iv-waveform iv-waveform--tall" aria-hidden="true">
            {Array.from({ length: 9 }).map((_, i) => (
              <div
                key={i}
                className="iv-waveform__bar"
                style={{ animationDelay: `${i * 0.09}s` }}
              />
            ))}
          </div>

          <p className="iv-timer">{formatTime(seconds)}</p>
          <p className="muted small" style={{ margin: 0 }}>
            Interview in progress — speak clearly into your microphone.
          </p>
          {status && status !== "transcribing" && (
            <p className="muted small" style={{ marginTop: 8, textTransform: "capitalize" }}>
              {status.replace(/_/g, " ")}
            </p>
          )}
          <div className="iv-audio-badge">
            {audioSource === AUDIO_SOURCE.MIXED ? (
              <>
                <FiMonitor size={14} /> Mic + System audio
              </>
            ) : (
              <>
                <FiMic size={14} /> Microphone only
              </>
            )}
          </div>
        </div>

        <button
          type="button"
          onClick={onStop}
          disabled={isEnding}
          className="w-full flex items-center justify-center gap-2 px-6 py-3 border-2 border-red-500 text-red-600 rounded-xl font-semibold text-sm hover:bg-red-50 transition-all disabled:opacity-50"
        >
          <FiSquare size={16} />
          {isEnding ? "Generating evaluation…" : "Stop & Evaluate"}
        </button>
      </div>
    </div>
  );
}

function EvaluatingPanel({ candidateName }) {
  return (
    <div className="modal-panel modal-panel--interview-setup" role="status" aria-live="polite">
      <div style={{ textAlign: "center" }}>
        <div className="iv-evaluating-spinner" aria-hidden="true" />
        <h2 style={{ margin: "20px 0 6px", fontSize: "1.15rem" }}>Evaluating interview…</h2>
        <p className="muted small">
          {candidateName} · Please wait while the AI analyses the session.
        </p>
      </div>
    </div>
  );
}

function EvaluationResultsPanel({ candidateName, selectedType, summary, onClose }) {
  const recommendation = summary?.recommendation_score ?? null;
  const technicalDepth = summary?.technical_depth_score ?? null;
  const scoreColor = getScoreColor10(recommendation);
  const pct = recommendation != null ? Math.round((recommendation / 10) * 100) : null;

  return (
    <div className="modal-panel modal-panel--wide modal-panel--eval">
      <div className="modal-header modal-header--eval">
        <div>
          <h2>Interview Evaluation</h2>
          <p className="muted small" style={{ margin: "4px 0 0" }}>
            {candidateName} · {getInterviewTypeLabel(selectedType)}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 transition p-1.5 hover:bg-gray-100 rounded-lg shrink-0"
        >
          Close
        </button>
      </div>

      <div className="eval-results-body">
      <div className="eval-score-row">
        <div className="eval-score-circle" style={{ borderColor: scoreColor, color: scoreColor }}>
          <span className="eval-score-circle__value">
            {recommendation != null ? recommendation.toFixed(1) : "—"}
          </span>
          <span className="eval-score-circle__denom">/10</span>
        </div>
        <div className="eval-score-meta">
          <p className="eval-score-meta__label">Recommendation Score</p>
          {pct != null && (
            <div className="score-bar" style={{ width: "100%", maxWidth: 220 }}>
              <div
                className="score-bar__fill"
                style={{ width: `${pct}%`, background: scoreColor }}
              />
            </div>
          )}
          {technicalDepth != null && (
            <p className="muted small" style={{ marginTop: 8 }}>
              Technical depth: {technicalDepth.toFixed(1)}/10
            </p>
          )}
        </div>
      </div>

      {summary?.summary && (
        <div className="eval-summary-block">
          <h3>Summary</h3>
          <p>{summary.summary}</p>
        </div>
      )}

      {summary?.overall_assessment && (
        <div className="eval-summary-block">
          <h3>Overall Assessment</h3>
          <p>{summary.overall_assessment}</p>
        </div>
      )}

      {(summary?.key_strengths?.length > 0 || summary?.key_concerns?.length > 0) && (
        <div className="eval-summary-block">
          {summary.key_strengths?.length > 0 && (
            <>
              <h3>Key Strengths</h3>
              <div className="eval-tags">
                {summary.key_strengths.map((s, i) => (
                  <span key={`s-${i}`} className="eval-tag eval-tag--strength">
                    {s}
                  </span>
                ))}
              </div>
            </>
          )}
          {summary.key_concerns?.length > 0 && (
            <>
              <h3 style={{ marginTop: summary.key_strengths?.length ? 14 : 0 }}>Key Concerns</h3>
              <div className="eval-tags">
                {summary.key_concerns.map((c, i) => (
                  <span key={`c-${i}`} className="eval-tag eval-tag--concern">
                    {c}
                  </span>
                ))}
              </div>
            </>
          )}
        </div>
      )}
      </div>
    </div>
  );
}

/**
 * InterviewModal — Live interview with WebSocket streaming, mic/system audio capture,
 * prepared question guide, AI follow-ups, and structured evaluation.
 */
export default function InterviewModal({
  isOpen,
  onClose,
  onInterviewComplete,
  candidateName,
  applicationId,
  requisitionId,
}) {
  const [phase, setPhase] = useState(PHASE.SETUP);
  const [selectedType, setSelectedType] = useState(INTERVIEW_TYPES.HR_SCREEN);
  const [audioSource, setAudioSource] = useState(AUDIO_SOURCE.MICROPHONE);
  const [activeAudioSource, setActiveAudioSource] = useState(AUDIO_SOURCE.MICROPHONE);
  const [sessionId, setSessionId] = useState(null);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isEnding, setIsEnding] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const [followups, setFollowups] = useState([]);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [summary, setSummary] = useState(null);
  const [interviewQuestions, setInterviewQuestions] = useState({
    session: [],
    tech: [],
    cbi: [],
  });

  const timerRef = useRef(null);
  const wsRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const mediaStreamRef = useRef(null);
  const micStreamRef = useRef(null);
  const sysStreamRef = useRef(null);
  const audioCtxRef = useRef(null);
  const segmentTimerRef = useRef(null);
  const isEndingRef = useRef(false);
  const audioSourceRef = useRef(AUDIO_SOURCE.MICROPHONE);
  const phaseRef = useRef(PHASE.SETUP);

  useEffect(() => {
    phaseRef.current = phase;
  }, [phase]);

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
    micStreamRef.current?.getTracks().forEach((t) => t.stop());
    sysStreamRef.current?.getTracks().forEach((t) => t.stop());
    void audioCtxRef.current?.close();

    mediaStreamRef.current = null;
    micStreamRef.current = null;
    sysStreamRef.current = null;
    audioCtxRef.current = null;
  }, []);

  const cleanupWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.close();
    }
    wsRef.current = null;
  }, []);

  const resetState = useCallback(() => {
    setPhase(PHASE.SETUP);
    setIsConnecting(false);
    setIsEnding(false);
    setSelectedType(INTERVIEW_TYPES.HR_SCREEN);
    setAudioSource(AUDIO_SOURCE.MICROPHONE);
    setActiveAudioSource(AUDIO_SOURCE.MICROPHONE);
    setSessionId(null);
    setElapsed(0);
    setFollowups([]);
    setStatus("");
    setError("");
    setSummary(null);
    setInterviewQuestions({ session: [], tech: [], cbi: [] });
    audioSourceRef.current = AUDIO_SOURCE.MICROPHONE;
    cleanupMedia();
    cleanupWebSocket();
  }, [cleanupMedia, cleanupWebSocket]);

  useEffect(() => {
    if (!isOpen) resetState();
  }, [isOpen, resetState]);

  useEffect(() => {
    if (phase === PHASE.RECORDING) {
      timerRef.current = setInterval(() => {
        setElapsed((prev) => prev + 1);
      }, 1000);
    } else {
      clearInterval(timerRef.current);
    }
    return () => clearInterval(timerRef.current);
  }, [phase]);

  const acquireAudioStream = useCallback(async (source) => {
    const mic = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });
    micStreamRef.current = mic;

    if (source === AUDIO_SOURCE.MIXED) {
      try {
        const sys = await navigator.mediaDevices.getDisplayMedia({
          video: true,
          audio: true,
        });
        sys.getVideoTracks().forEach((t) => t.stop());
        sysStreamRef.current = sys;

        const ctx = new AudioContext();
        audioCtxRef.current = ctx;
        const dest = ctx.createMediaStreamDestination();
        ctx.createMediaStreamSource(mic).connect(dest);
        ctx.createMediaStreamSource(sys).connect(dest);
        return { stream: dest.stream, source: AUDIO_SOURCE.MIXED };
      } catch {
        return { stream: mic, source: AUDIO_SOURCE.MICROPHONE };
      }
    }

    return { stream: mic, source: AUDIO_SOURCE.MICROPHONE };
  }, []);

  const startMediaCapture = useCallback(
    async (source) => {
      const { stream, source: resolvedSource } = await acquireAudioStream(source);
      mediaStreamRef.current = stream;
      setActiveAudioSource(resolvedSource);
      audioSourceRef.current = resolvedSource;

      const mimeType =
        [
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
              micStreamRef.current?.getTracks().forEach((t) => t.stop());
              sysStreamRef.current?.getTracks().forEach((t) => t.stop());
              void audioCtxRef.current?.close();
              setTimeout(() => {
                if (wsRef.current?.readyState === WebSocket.OPEN) {
                  sendEndInterview(wsRef.current);
                }
              }, 300);
            }
          };

          if (
            segmentChunks.length === 0 ||
            !socket ||
            socket.readyState !== WebSocket.OPEN
          ) {
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
              sendAudioChunk(socket, b64, fmt, audioSourceRef.current);
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
    },
    [acquireAudioStream]
  );

  const handleWsMessage = useCallback(
    async (msg) => {
      switch (msg.type) {
        case "init_ok":
          setStatus("Interview started");
          setIsConnecting(false);
          setInterviewQuestions({
            session: msg.questions || [],
            tech: msg.tech_questions || [],
            cbi: msg.cbi_questions || [],
          });
          setPhase(PHASE.RECORDING);
          try {
            await startMediaCapture(audioSourceRef.current);
          } catch (err) {
            setError(err.message || "Microphone access denied");
            setPhase(PHASE.SETUP);
            cleanupWebSocket();
          }
          break;
        case "followup_question":
          setFollowups((prev) => [
            ...prev,
            { question: msg.question, timestamp: msg.timestamp ?? Date.now() },
          ]);
          break;
        case "status":
          if (msg.status === "generating_summary") {
            setPhase(PHASE.EVALUATING);
          } else if (msg.status !== "transcribing") {
            setStatus(msg.status);
          }
          break;
        case "summary":
          setSummary(msg.data);
          setIsEnding(false);
          setPhase(PHASE.RESULTS);
          cleanupMedia();
          onInterviewComplete?.();
          break;
        case "error":
          setError(msg.message || "Unknown server error");
          setIsConnecting(false);
          setIsEnding(false);
          if (
            phaseRef.current === PHASE.RECORDING ||
            phaseRef.current === PHASE.EVALUATING
          ) {
            setPhase(PHASE.SETUP);
          }
          break;
        default:
          break;
      }
    },
    [cleanupMedia, cleanupWebSocket, startMediaCapture, onInterviewComplete]
  );

  const handleStartInterview = async () => {
    if (!applicationId || !requisitionId) {
      setError("Missing session details — close and try again.");
      return;
    }

    setError("");
    setIsConnecting(true);
    setStatus("Preparing session...");
    audioSourceRef.current = audioSource;

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
          if (phaseRef.current !== PHASE.RESULTS) setStatus("Disconnected");
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
    setPhase(PHASE.EVALUATING);
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
      micStreamRef.current?.getTracks().forEach((t) => t.stop());
      sysStreamRef.current?.getTracks().forEach((t) => t.stop());
      void audioCtxRef.current?.close();
      setTimeout(() => {
        if (wsRef.current?.readyState === WebSocket.OPEN) {
          sendEndInterview(wsRef.current);
        }
      }, 100);
    }
  };

  const handleClose = () => {
    if (phase === PHASE.RECORDING || phase === PHASE.EVALUATING) return;
    onClose();
  };

  if (!isOpen) return null;

  if (phase === PHASE.RESULTS && summary) {
    return (
      <div className="modal-backdrop" onClick={onClose}>
        <div onClick={(e) => e.stopPropagation()}>
          <EvaluationResultsPanel
            candidateName={candidateName}
            selectedType={selectedType}
            summary={summary}
            onClose={onClose}
          />
        </div>
      </div>
    );
  }

  if (phase === PHASE.SETUP) {
    return (
      <div className="modal-backdrop" onClick={handleClose}>
        <div onClick={(e) => e.stopPropagation()}>
          <InterviewSetupPanel
            candidateName={candidateName}
            selectedType={selectedType}
            setSelectedType={setSelectedType}
            audioSource={audioSource}
            setAudioSource={setAudioSource}
            error={error}
            isConnecting={isConnecting}
            onStart={handleStartInterview}
            onClose={handleClose}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="modal-backdrop modal-backdrop--interview-dual" onClick={handleClose}>
      <div className="iv-dual-layout" onClick={(e) => e.stopPropagation()}>
        {phase === PHASE.EVALUATING ? (
          <EvaluatingPanel candidateName={candidateName} />
        ) : (
          <InterviewLivePanel
            candidateName={candidateName}
            selectedType={selectedType}
            audioSource={activeAudioSource}
            seconds={elapsed}
            status={status}
            onStop={handleStopRecording}
            isEnding={isEnding}
          />
        )}
        <InterviewGuideColumn
          candidateName={candidateName}
          selectedType={selectedType}
          interviewQuestions={interviewQuestions}
          followups={followups}
        />
      </div>
    </div>
  );
}
