import {
  FiX,
  FiArrowRight,
  FiUser,
  FiCpu,
  FiLoader,
  FiPlus,
  FiTrash2,
  FiMessageSquare,
} from "react-icons/fi";
import { useState, useEffect, useRef, useCallback } from "react";
import { queryRagChatbot } from "../services/graphService";
import {
  fetchThreads,
  createThread,
  fetchMessages,
  deleteThread,
} from "../services/chatService";

const SUGGESTIONS = [
  "Who is the most qualified candidate?",
  "Which candidates have React experience?",
  "Compare the top 3 candidates",
];

const TABLE_SEPARATOR_RE = /^\s*\|?[\s:-]+\|[\s|:-]*\|?\s*$/;

const isTableRow = (line) => line.includes("|");

const isTableSeparator = (line) => TABLE_SEPARATOR_RE.test(line);

const parseTableBlock = (lines) => {
  if (lines.length < 2) return null;

  const headerLine = lines[0];
  const headers = headerLine
    .split("|")
    .map((h) => h.trim())
    .filter((h) => h && h !== "");

  let dataStartIndex = 1;
  if (lines[1] && isTableSeparator(lines[1])) dataStartIndex = 2;

  const rows = lines.slice(dataStartIndex).map((line) =>
    line
      .split("|")
      .map((cell) => cell.trim())
      .filter((_, i) => i > 0 && i <= headers.length)
  );

  return { headers, rows };
};

function MarkdownTable({ headers, rows }) {
  return (
    <div className="max-w-full my-2">
      <div className="max-h-64 overflow-y-auto rounded-lg border border-border">
        <table className="w-full border-collapse text-xs">
          <thead className="sticky top-0 z-10">
            <tr className="bg-brand-600/5 border-b border-border">
              {headers.map((header, idx) => (
                <th
                  key={idx}
                  className="px-2 py-2 text-left font-semibold text-gray-800 border-r border-border last:border-r-0 whitespace-nowrap"
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rowIdx) => (
              <tr
                key={rowIdx}
                className={`border-b border-border hover:bg-brand-600/5 transition ${
                  rowIdx % 2 === 0 ? "bg-surface" : "bg-muted/30"
                }`}
              >
                {row.map((cell, cellIdx) => (
                  <td
                    key={cellIdx}
                    className="px-2 py-2 text-gray-700 border-r border-border last:border-r-0 break-words"
                  >
                    <InlineMarkdown text={cell} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function InlineMarkdown({ text }) {
  if (!text) return null;

  const parts = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*)/g;
  let lastIndex = 0;
  let match;

  while ((match = re.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    const token = match[0];
    if (token.startsWith("**")) {
      parts.push(
        <strong key={`${match.index}-b`} className="font-semibold text-gray-900">
          {token.slice(2, -2)}
        </strong>
      );
    } else {
      parts.push(
        <em key={`${match.index}-i`} className="italic">
          {token.slice(1, -1)}
        </em>
      );
    }
    lastIndex = match.index + token.length;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length ? <>{parts}</> : text;
}

function parseMarkdownBlocks(text) {
  const lines = text.split("\n");
  const blocks = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    if (!line.trim()) {
      i += 1;
      continue;
    }

    // Markdown table
    if (
      isTableRow(line) &&
      i + 1 < lines.length &&
      (isTableSeparator(lines[i + 1]) || isTableRow(lines[i + 1]))
    ) {
      const tableLines = [line];
      i += 1;
      while (i < lines.length && isTableRow(lines[i])) {
        tableLines.push(lines[i]);
        i += 1;
      }
      const table = parseTableBlock(tableLines);
      if (table) {
        blocks.push({ type: "table", ...table });
        continue;
      }
      blocks.push({ type: "paragraph", text: tableLines.join("\n") });
      continue;
    }

    // Bullet list
    if (/^\s*[-*]\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*[-*]\s+/, ""));
        i += 1;
      }
      blocks.push({ type: "ul", items });
      continue;
    }

    // Numbered list
    if (/^\s*\d+\.\s+/.test(line)) {
      const items = [];
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        items.push(lines[i].replace(/^\s*\d+\.\s+/, ""));
        i += 1;
      }
      blocks.push({ type: "ol", items });
      continue;
    }

    // Paragraph (collect until blank line or structural block)
    const paraLines = [line];
    i += 1;
    while (i < lines.length) {
      const next = lines[i];
      if (
        !next.trim() ||
        isTableRow(next) ||
        /^\s*[-*]\s+/.test(next) ||
        /^\s*\d+\.\s+/.test(next)
      ) {
        break;
      }
      paraLines.push(next);
      i += 1;
    }
    blocks.push({ type: "paragraph", text: paraLines.join("\n") });
  }

  return blocks;
}

function BotMessageContent({ text }) {
  const blocks = parseMarkdownBlocks(text);

  if (!blocks.length) {
    return <div className="whitespace-pre-wrap">{text}</div>;
  }

  return (
    <div className="chat-drawer__markdown space-y-2">
      {blocks.map((block, idx) => {
        if (block.type === "table") {
          return <MarkdownTable key={idx} headers={block.headers} rows={block.rows} />;
        }
        if (block.type === "ul") {
          return (
            <ul key={idx} className="chat-drawer__list list-disc pl-5 space-y-1">
              {block.items.map((item, itemIdx) => (
                <li key={itemIdx}>
                  <InlineMarkdown text={item} />
                </li>
              ))}
            </ul>
          );
        }
        if (block.type === "ol") {
          return (
            <ol key={idx} className="chat-drawer__list list-decimal pl-5 space-y-1">
              {block.items.map((item, itemIdx) => (
                <li key={itemIdx}>
                  <InlineMarkdown text={item} />
                </li>
              ))}
            </ol>
          );
        }
        return (
          <p key={idx} className="whitespace-pre-wrap">
            <InlineMarkdown text={block.text} />
          </p>
        );
      })}
    </div>
  );
}

function buildWelcomeMessage(requisitionTitle) {
  return {
    id: "welcome",
    sender: "bot",
    text: `Hello! I am your AI Recruiting Copilot.\n\nI can search candidates, evaluate skill matches, and answer questions about resumes and scores for the "${requisitionTitle || "current"}" requisition.\n\nTry one of the suggestions below, or ask your own question.`,
    timestamp: new Date(),
  };
}

function mapApiMessages(apiMessages) {
  return apiMessages.map((m) => ({
    id: String(m.id),
    sender: m.role === "user" ? "user" : "bot",
    text: m.content,
    timestamp: new Date(m.created_at),
  }));
}

function formatThreadDate(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const now = new Date();
  const sameDay =
    d.getDate() === now.getDate() &&
    d.getMonth() === now.getMonth() &&
    d.getFullYear() === now.getFullYear();
  if (sameDay) {
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  }
  return d.toLocaleDateString([], { month: "short", day: "numeric" });
}

export default function ChatDrawer({ isOpen, onClose, requisitionId, requisitionTitle }) {
  const [threads, setThreads] = useState([]);
  const [activeThreadId, setActiveThreadId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [threadsLoading, setThreadsLoading] = useState(false);
  const [messagesLoading, setMessagesLoading] = useState(false);
  const messagesEndRef = useRef(null);

  const loadThreads = useCallback(async () => {
    if (!requisitionId) return [];
    setThreadsLoading(true);
    try {
      const data = await fetchThreads(requisitionId);
      setThreads(data);
      return data;
    } catch (err) {
      console.error("Failed to load chat threads:", err);
      setThreads([]);
      return [];
    } finally {
      setThreadsLoading(false);
    }
  }, [requisitionId]);

  const loadThreadMessages = useCallback(async (threadExternalId) => {
    if (!threadExternalId) {
      setMessages([buildWelcomeMessage(requisitionTitle)]);
      return;
    }
    setMessagesLoading(true);
    try {
      const apiMessages = await fetchMessages(threadExternalId);
      if (apiMessages.length === 0) {
        setMessages([buildWelcomeMessage(requisitionTitle)]);
      } else {
        setMessages(mapApiMessages(apiMessages));
      }
    } catch (err) {
      console.error("Failed to load messages:", err);
      setMessages([buildWelcomeMessage(requisitionTitle)]);
    } finally {
      setMessagesLoading(false);
    }
  }, [requisitionTitle]);

  useEffect(() => {
    if (!isOpen || !requisitionId) return;

    let cancelled = false;
    (async () => {
      setActiveThreadId(null);
      setMessages([]);
      const data = await loadThreads();
      if (cancelled) return;

      if (data.length > 0) {
        const latest = data[0];
        setActiveThreadId(latest.external_id);
        await loadThreadMessages(latest.external_id);
      } else {
        setMessages([buildWelcomeMessage(requisitionTitle)]);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [isOpen, requisitionId, loadThreads, loadThreadMessages, requisitionTitle]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading, messagesLoading]);

  if (!isOpen) return null;

  const handleSelectThread = async (threadExternalId) => {
    if (threadExternalId === activeThreadId) return;
    setActiveThreadId(threadExternalId);
    await loadThreadMessages(threadExternalId);
  };

  const handleNewChat = async () => {
    try {
      const thread = await createThread(requisitionId);
      setThreads((prev) => [thread, ...prev]);
      setActiveThreadId(thread.external_id);
      setMessages([buildWelcomeMessage(requisitionTitle)]);
    } catch (err) {
      console.error("Failed to create thread:", err);
    }
  };

  const handleDeleteThread = async (e, threadExternalId) => {
    e.stopPropagation();
    if (!window.confirm("Delete this conversation?")) return;
    try {
      await deleteThread(threadExternalId);
      const remaining = threads.filter((t) => t.external_id !== threadExternalId);
      setThreads(remaining);

      if (activeThreadId === threadExternalId) {
        if (remaining.length > 0) {
          setActiveThreadId(remaining[0].external_id);
          await loadThreadMessages(remaining[0].external_id);
        } else {
          setActiveThreadId(null);
          setMessages([buildWelcomeMessage(requisitionTitle)]);
        }
      }
    } catch (err) {
      console.error("Failed to delete thread:", err);
    }
  };

  const handleSend = async (e, overrideText) => {
    e?.preventDefault();
    const userMessageText = (overrideText ?? input).trim();
    if (!userMessageText || loading) return;

    setInput("");

    let threadId = activeThreadId;
    if (!threadId) {
      try {
        const thread = await createThread(requisitionId);
        threadId = thread.external_id;
        setActiveThreadId(threadId);
        setThreads((prev) => [thread, ...prev]);
      } catch (err) {
        console.error("Failed to create thread:", err);
        return;
      }
    }

    const userMsgId = Date.now().toString();
    setMessages((prev) => [
      ...prev.filter((m) => m.id !== "welcome"),
      {
        id: userMsgId,
        sender: "user",
        text: userMessageText,
        timestamp: new Date(),
      },
    ]);

    setLoading(true);

    try {
      const response = await queryRagChatbot(requisitionId, userMessageText, threadId);
      const botReply = response.result?.response || "I couldn't process that query. Please try again.";
      const returnedThreadId = response.result?.chat_thread_id;
      if (returnedThreadId && returnedThreadId !== threadId) {
        setActiveThreadId(returnedThreadId);
        threadId = returnedThreadId;
      }

      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          sender: "bot",
          text: botReply,
          timestamp: new Date(),
        },
      ]);

      await loadThreads();
    } catch (error) {
      console.error("Error communicating with RAG chatbot:", error);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          sender: "bot",
          text: "Sorry, I encountered an error while searching candidate resumes. Please ensure the backend server and RAG databases are active.",
          timestamp: new Date(),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const showSuggestions =
    !messagesLoading && messages.length <= 1 && messages.every((m) => m.id === "welcome" || m.sender === "bot");

  return (
    <>
      <div className="fixed inset-0 bg-black/35 backdrop-blur-sm z-40" onClick={onClose} />

      <div className="chat-drawer fixed top-0 right-0 h-full w-full max-w-4xl shadow-[12px_0_40px_rgb(0_0_0_/_0.12)] z-50 flex flex-col overflow-hidden border-l border-border">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 bg-surface border-b border-border shrink-0">
          <div className="flex items-center gap-3 min-w-0">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-brand-600 to-brand-800 text-white shadow-sm shrink-0">
              <FiCpu size={18} />
            </span>
            <div className="min-w-0">
              <h2 className="text-base font-bold text-gray-900">AI HR Agent</h2>
              <p className="text-xs text-muted mt-0.5 font-medium truncate max-w-[240px]">
                {requisitionTitle || "Requisition context"}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-muted hover:text-gray-700 transition p-1.5 hover:bg-muted rounded-lg shrink-0"
            aria-label="Close chat"
          >
            <FiX size={20} />
          </button>
        </div>

        <div className="flex flex-1 min-h-0">
          {/* Thread sidebar */}
          <aside className="chat-drawer__sidebar w-56 shrink-0 border-r border-border flex flex-col">
            <div className="p-3 border-b border-border">
              <button
                type="button"
                onClick={handleNewChat}
                className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm font-semibold text-white bg-brand-600 hover:bg-brand-700 rounded-lg transition"
              >
                <FiPlus size={16} />
                New chat
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-2 space-y-1">
              {threadsLoading && (
                <div className="flex items-center justify-center py-6 text-muted text-xs">
                  <FiLoader className="animate-spin mr-2" size={14} />
                  Loading...
                </div>
              )}

              {!threadsLoading && threads.length === 0 && (
                <p className="text-xs text-muted text-center px-2 py-4">
                  No conversations yet. Start a new chat.
                </p>
              )}

              {threads.map((thread) => {
                const isActive = thread.external_id === activeThreadId;
                return (
                  <div
                    key={thread.external_id}
                    className={`chat-drawer__thread-item group flex items-start gap-1 ${
                      isActive ? "chat-drawer__thread-item--active" : ""
                    }`}
                  >
                    <button
                      type="button"
                      onClick={() => handleSelectThread(thread.external_id)}
                      className="flex-1 text-left flex items-start gap-2 px-3 py-2.5 min-w-0"
                    >
                      <FiMessageSquare
                        size={14}
                        className={`mt-0.5 shrink-0 ${isActive ? "text-brand-600" : "text-muted"}`}
                      />
                      <div className="flex-1 min-w-0">
                        <p
                          className={`text-xs font-semibold truncate ${
                            isActive ? "text-brand-700" : "text-gray-800"
                          }`}
                        >
                          {thread.title || "New chat"}
                        </p>
                        <p className="text-[10px] text-muted mt-0.5">
                          {formatThreadDate(thread.last_message_at || thread.updated_at)}
                          {thread.message_count > 0 && ` · ${thread.message_count} msgs`}
                        </p>
                      </div>
                    </button>
                    <button
                      type="button"
                      onClick={(e) => handleDeleteThread(e, thread.external_id)}
                      className="opacity-0 group-hover:opacity-100 p-2 mr-1 mt-1 text-muted hover:text-red-600 transition shrink-0"
                      aria-label="Delete conversation"
                    >
                      <FiTrash2 size={12} />
                    </button>
                  </div>
                );
              })}
            </div>
          </aside>

          {/* Messages panel */}
          <div className="flex-1 flex flex-col min-w-0 bg-canvas/40">
            <div className="chat-drawer__messages flex-1 overflow-y-auto px-5 py-5">
              {messagesLoading && (
                <div className="flex items-center justify-center py-12 text-muted text-sm">
                  <FiLoader className="animate-spin mr-2 text-brand-600" size={18} />
                  Loading conversation...
                </div>
              )}

              {!messagesLoading &&
                messages.map((msg) => {
                  const isBot = msg.sender === "bot";
                  return (
                    <div
                      key={msg.id}
                      className={`flex gap-3 max-w-[92%] ${isBot ? "mr-auto" : "ml-auto flex-row-reverse"}`}
                    >
                      <div
                        className={`h-8 w-8 rounded-full flex-shrink-0 flex items-center justify-center text-sm font-semibold ${
                          isBot
                            ? "bg-gradient-to-br from-brand-600 to-brand-800 text-white"
                            : "bg-[#e0e0e5] text-gray-700"
                        }`}
                      >
                        {isBot ? <FiCpu size={14} /> : <FiUser size={14} />}
                      </div>

                      <div className="flex flex-col min-w-0">
                        <div
                          className={`px-3.5 py-3 rounded-[14px] text-sm leading-relaxed ${
                            isBot
                              ? "chat-drawer__bubble--bot"
                              : "chat-drawer__bubble--user whitespace-pre-wrap"
                          }`}
                        >
                          {isBot ? (
                            <BotMessageContent text={msg.text} />
                          ) : (
                            <div className="whitespace-pre-wrap">{msg.text}</div>
                          )}
                        </div>
                        <span
                          className={`text-[10px] text-muted mt-1 font-medium ${
                            isBot ? "text-left pl-1" : "text-right pr-1"
                          }`}
                        >
                          {msg.timestamp.toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                      </div>
                    </div>
                  );
                })}

              {showSuggestions && !loading && (
                <div className="chat-drawer__chips">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => handleSend(null, s)}
                      disabled={loading}
                      className="chat-drawer__chip"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}

              {loading && (
                <div className="flex gap-3 max-w-[92%] mr-auto">
                  <div className="h-8 w-8 rounded-full bg-gradient-to-br from-brand-600 to-brand-800 text-white flex items-center justify-center">
                    <FiCpu size={14} />
                  </div>
                  <div className="chat-drawer__bubble--bot px-3.5 py-3 rounded-[14px] text-sm flex items-center gap-2 text-muted">
                    <FiLoader size={16} className="animate-spin text-brand-600" />
                    <span>Searching resumes...</span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="px-5 py-4 bg-surface border-t border-border shrink-0">
              <form
                className="chat-drawer__form"
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSend(e);
                }}
              >
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask about skills, background, or top candidates…"
                  disabled={loading || messagesLoading}
                  className="chat-drawer__input"
                />
                <button
                  type="submit"
                  disabled={loading || messagesLoading}
                  className="chat-drawer__send"
                  aria-label="Send message"
                >
                  <span className="chat-drawer__send-label">Send</span>
                  <FiArrowRight size={18} aria-hidden />
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
