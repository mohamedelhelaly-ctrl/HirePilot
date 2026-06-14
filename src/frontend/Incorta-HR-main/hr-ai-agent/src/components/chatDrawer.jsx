import { FiX, FiSend, FiUser, FiCpu, FiLoader } from "react-icons/fi";
import { useState, useEffect, useRef } from "react";
import { queryRagChatbot } from "../services/graphService";
import { inputClasses } from "./inputField";

const SUGGESTIONS = [
  "Who is the most qualified candidate?",
  "Which candidates have React experience?",
  "Compare the top 3 candidates",
];

const containsTable = (text) => {
  return /\|.*\|/.test(text) && (/\|-+\|/.test(text) || text.split("\n").filter((line) => line.includes("|")).length >= 3);
};

const parseTable = (text) => {
  const lines = text.split("\n");
  const tableLines = lines.filter((line) => line.includes("|"));

  if (tableLines.length < 2) return null;

  const headerLine = tableLines[0];
  const headers = headerLine.split("|").map((h) => h.trim()).filter((h) => h && h !== "");

  let dataStartIndex = 1;
  if (tableLines[1].includes("-")) {
    dataStartIndex = 2;
  }

  const rows = tableLines.slice(dataStartIndex).map((line) =>
    line.split("|").map((cell) => cell.trim()).filter((_, i) => i > 0 && i <= headers.length)
  );

  return { headers, rows };
};

function TableMessage({ text }) {
  const table = parseTable(text);

  if (!table) {
    return <div className="whitespace-pre-wrap">{text}</div>;
  }

  const { headers, rows } = table;

  return (
    <div className="max-w-full">
      <div className="max-h-64 overflow-y-auto rounded-lg border border-border">
        <table className="w-full border-collapse text-xs">
          <thead className="sticky top-0 z-10">
            <tr className="bg-blue-50 border-b border-border">
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
                className={`border-b border-border hover:bg-blue-50/50 transition ${
                  rowIdx % 2 === 0 ? "bg-white" : "bg-gray-50"
                }`}
              >
                {row.map((cell, cellIdx) => (
                  <td
                    key={cellIdx}
                    className="px-2 py-2 text-gray-700 border-r border-border last:border-r-0 break-words"
                  >
                    {cell}
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

export default function ChatDrawer({ isOpen, onClose, requisitionId, requisitionTitle }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [chatThreadId, setChatThreadId] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (isOpen && !chatThreadId) {
      const storedKey = `rag-thread-${requisitionId}`;
      const existing = sessionStorage.getItem(storedKey);
      const threadId = existing || `rag-${requisitionId}-${crypto.randomUUID()}`;
      if (!existing) {
        sessionStorage.setItem(storedKey, threadId);
      }
      setChatThreadId(threadId);
    }
  }, [isOpen, requisitionId, chatThreadId]);

  useEffect(() => {
    if (isOpen && messages.length === 0) {
      setMessages([
        {
          id: "welcome",
          sender: "bot",
          text: `Hello! I am your AI Recruiting Copilot.\n\nI can search candidates, evaluate skill matches, and answer questions about resumes and scores for the "${requisitionTitle || "current"}" requisition.\n\nTry one of the suggestions below, or ask your own question.`,
          timestamp: new Date(),
        },
      ]);
    }
  }, [isOpen, requisitionTitle, messages.length]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  if (!isOpen) return null;

  const handleSend = async (e, overrideText) => {
    e?.preventDefault();
    const userMessageText = (overrideText ?? input).trim();
    if (!userMessageText || loading) return;

    setInput("");

    const userMsgId = Date.now().toString();
    setMessages((prev) => [
      ...prev,
      {
        id: userMsgId,
        sender: "user",
        text: userMessageText,
        timestamp: new Date(),
      },
    ]);

    setLoading(true);

    try {
      const response = await queryRagChatbot(requisitionId, userMessageText, chatThreadId);
      const botReply = response.result?.response || "I couldn't process that query. Please try again.";
      const returnedThreadId = response.result?.chat_thread_id;
      if (returnedThreadId && returnedThreadId !== chatThreadId) {
        setChatThreadId(returnedThreadId);
        sessionStorage.setItem(`rag-thread-${requisitionId}`, returnedThreadId);
      }

      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          sender: "bot",
          text: botReply,
          timestamp: new Date(),
        },
      ]);
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

  const showSuggestions = messages.length <= 1;

  return (
    <>
      <div className="fixed inset-0 bg-black/35 backdrop-blur-sm z-40" onClick={onClose} />

      <div className="fixed top-0 right-0 h-full w-full max-w-2xl bg-canvas shadow-[12px_0_40px_rgb(0_0_0_/_0.12)] z-50 flex flex-col overflow-hidden border-l border-border">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 bg-surface border-b border-border">
          <div className="flex items-center gap-3">
            <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-brand-600 to-brand-800 text-white shadow-sm">
              <FiCpu size={18} />
            </span>
            <div>
              <h2 className="text-base font-bold text-gray-900">AI HR Agent</h2>
              <p className="text-xs text-muted mt-0.5 font-medium truncate max-w-[280px]">
                {requisitionTitle || "Requisition context"}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition p-1.5 hover:bg-gray-100 rounded-lg"
          >
            <FiX size={20} />
          </button>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4">
          {messages.map((msg) => {
            const isBot = msg.sender === "bot";
            return (
              <div
                key={msg.id}
                className={`flex gap-3 max-w-[90%] ${isBot ? "mr-auto" : "ml-auto flex-row-reverse"}`}
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
                        ? "bg-[#f2f2f7] text-gray-900"
                        : "bg-[#e0e0e5] text-gray-900 whitespace-pre-wrap"
                    }`}
                  >
                    {isBot && containsTable(msg.text) ? (
                      <TableMessage text={msg.text} />
                    ) : (
                      <div className="whitespace-pre-wrap">{msg.text}</div>
                    )}
                  </div>
                  <span
                    className={`text-[10px] text-muted mt-1 font-medium ${
                      isBot ? "text-left pl-1" : "text-right pr-1"
                    }`}
                  >
                    {msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </span>
                </div>
              </div>
            );
          })}

          {showSuggestions && !loading && (
            <div className="flex flex-wrap gap-2 pt-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  type="button"
                  onClick={() => handleSend(null, s)}
                  className="text-xs px-3 py-2 rounded-full border border-border bg-[#f2f2f7] text-gray-700 hover:bg-white hover:border-brand-600/30 transition"
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          {loading && (
            <div className="flex gap-3 max-w-[90%] mr-auto">
              <div className="h-8 w-8 rounded-full bg-gradient-to-br from-brand-600 to-brand-800 text-white flex items-center justify-center">
                <FiCpu size={14} />
              </div>
              <div className="px-3.5 py-3 bg-[#f2f2f7] text-muted rounded-[14px] text-sm flex items-center gap-2">
                <FiLoader size={16} className="animate-spin text-brand-600" />
                <span>Searching resumes...</span>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="px-6 py-5 bg-surface border-t border-border">
          <form onSubmit={handleSend} className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about skills, background, or top candidates..."
              disabled={loading}
              className={`flex-1 ${inputClasses}`}
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="px-4 py-2.5 bg-brand-600 hover:bg-brand-700 disabled:bg-gray-100 disabled:text-gray-400 text-white font-semibold rounded-[10px] flex items-center justify-center transition shadow-sm active:scale-95"
            >
              <FiSend size={16} />
            </button>
          </form>
        </div>
      </div>
    </>
  );
}
