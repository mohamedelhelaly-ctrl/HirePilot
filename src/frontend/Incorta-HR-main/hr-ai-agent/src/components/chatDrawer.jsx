import { FiX, FiSend, FiUser, FiCpu, FiLoader } from "react-icons/fi";
import { useState, useEffect, useRef } from "react";
import { queryRagChatbot } from "../services/graphService";

/**
 * Detect if text contains a table (ASCII/markdown format)
 */
const containsTable = (text) => {
  return /\|.*\|/.test(text) && (/\|-+\|/.test(text) || text.split('\n').filter(line => line.includes('|')).length >= 3);
};

/**
 * Parse ASCII/markdown table from text
 */
const parseTable = (text) => {
  const lines = text.split('\n');
  const tableLines = lines.filter(line => line.includes('|'));
  
  if (tableLines.length < 2) return null;

  // Extract headers (first line with |)
  const headerLine = tableLines[0];
  const headers = headerLine.split('|').map(h => h.trim()).filter(h => h && h !== '');

  // Skip separator line if it exists (line with dashes)
  let dataStartIndex = 1;
  if (tableLines[1].includes('-')) {
    dataStartIndex = 2;
  }

  // Extract rows
  const rows = tableLines.slice(dataStartIndex).map(line =>
    line.split('|').map(cell => cell.trim()).filter((_, i) => i > 0 && i <= headers.length)
  );

  return { headers, rows };
};

/**
 * Table Component
 */
function TableMessage({ text }) {
  const table = parseTable(text);

  if (!table) {
    return <div className="whitespace-pre-wrap">{text}</div>;
  }

  const { headers, rows } = table;

  return (
    <div className="max-w-full">
      <div className="max-h-64 overflow-y-auto rounded-lg border border-gray-300">
        <table className="w-full border-collapse text-xs">
          <thead className="sticky top-0 z-10">
            <tr className="bg-blue-100 border-b border-gray-300">
              {headers.map((header, idx) => (
                <th
                  key={idx}
                  className="px-2 py-2 text-left font-semibold text-gray-800 border-r border-gray-300 last:border-r-0 whitespace-nowrap"
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
                className={`border-b border-gray-200 hover:bg-blue-50 transition ${
                  rowIdx % 2 === 0 ? "bg-white" : "bg-gray-50"
                }`}
              >
                {row.map((cell, cellIdx) => (
                  <td
                    key={cellIdx}
                    className="px-2 py-2 text-gray-700 border-r border-gray-200 last:border-r-0 break-words"
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

/**
 * ChatDrawer — A premium, modern slide-over chatbot assistant panel
 */
export default function ChatDrawer({ isOpen, onClose, requisitionId, requisitionTitle }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [chatThreadId, setChatThreadId] = useState(null);
  const messagesEndRef = useRef(null);

  // Stable thread id for backend in-memory LangChain history (per drawer session)
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

  // Initialize with a welcoming bot message when drawer opens
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      setMessages([
        {
          id: "welcome",
          sender: "bot",
          text: `Hello! I am your AI Recruiting Copilot. 🤖\n\nI can search candidates, evaluate skill matches, and answer questions about resumes and scores for the **${
            requisitionTitle || "current"
          }** requisition.\n\nHere are some questions you can ask me:\n• *"Who is the most qualified candidate for this role?"*\n• *"Which candidates have experience with React or Node?"*\n• *"Compare the qualifications of the top 3 candidates."*\n• *"Does anyone have a background in financial systems?"*`,
          timestamp: new Date(),
        },
      ]);
    }
  }, [isOpen, requisitionTitle, messages.length]);

  // Scroll to bottom whenever messages change or loading state changes
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  if (!isOpen) return null;

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userMessageText = input.trim();
    setInput("");

    // Add user message
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
      // Call RAG orchestrator graph API
      const response = await queryRagChatbot(requisitionId, userMessageText, chatThreadId);
      const botReply = response.result?.response || "I couldn't process that query. Please try again.";
      const returnedThreadId = response.result?.chat_thread_id;
      if (returnedThreadId && returnedThreadId !== chatThreadId) {
        setChatThreadId(returnedThreadId);
        sessionStorage.setItem(`rag-thread-${requisitionId}`, returnedThreadId);
      }

      // Add bot message
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

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black/30 backdrop-blur-sm z-40" onClick={onClose}></div>

      {/* Slide-Over Panel */}
      <div className="fixed top-0 right-0 h-full w-full max-w-2xl bg-gray-50 shadow-2xl z-50 flex flex-col overflow-hidden border-l border-gray-100">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 bg-white border-b border-gray-150 shadow-sm">
          <div>
            <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
              <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-blue-600 text-white">
                <FiCpu size={16} />
              </span>
              Recruiting Copilot
            </h2>
            <p className="text-xs text-gray-400 mt-0.5 font-medium truncate max-w-[280px]">
              Active context: {requisitionTitle || "Requisition"}
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition p-1.5 hover:bg-gray-100 rounded-lg"
          >
            <FiX size={20} />
          </button>
        </div>

        {/* Messages Body */}
        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-4">
          {messages.map((msg) => {
            const isBot = msg.sender === "bot";
            return (
              <div
                key={msg.id}
                className={`flex gap-3 max-w-[85%] ${isBot ? "mr-auto" : "ml-auto flex-row-reverse"}`}
              >
                {/* Avatar */}
                <div
                  className={`h-8 w-8 rounded-full flex-shrink-0 flex items-center justify-center text-sm font-semibold shadow-sm ${
                    isBot ? "bg-blue-600 text-white" : "bg-gray-200 text-gray-600"
                  }`}
                >
                  {isBot ? <FiCpu size={14} /> : <FiUser size={14} />}
                </div>

                {/* Bubble */}
                <div className="flex flex-col">
                  <div
                    className={`px-4 py-3 rounded-2xl shadow-sm text-sm leading-relaxed ${
                      isBot
                        ? "bg-white text-gray-800 border border-gray-200/80 rounded-tl-none"
                        : "bg-blue-600 text-white rounded-tr-none whitespace-pre-wrap"
                    }`}
                  >
                    {isBot && containsTable(msg.text) ? (
                      <TableMessage text={msg.text} />
                    ) : (
                      <div className="whitespace-pre-wrap">{msg.text}</div>
                    )}
                  </div>
                  <span
                    className={`text-[10px] text-gray-400 mt-1 font-medium ${
                      isBot ? "text-left pl-1" : "text-right pr-1"
                    }`}
                  >
                    {msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                  </span>
                </div>
              </div>
            );
          })}

          {/* Loader */}
          {loading && (
            <div className="flex gap-3 max-w-[85%] mr-auto">
              <div className="h-8 w-8 rounded-full bg-blue-600 text-white flex items-center justify-center text-sm font-semibold shadow-sm">
                <FiCpu size={14} />
              </div>
              <div className="flex flex-col">
                <div className="px-4 py-3 bg-white text-gray-500 border border-gray-200/80 rounded-2xl rounded-tl-none shadow-sm text-sm flex items-center gap-2">
                  <FiLoader size={16} className="animate-spin text-blue-600" />
                  <span>Searching resumes and matching scores...</span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Footer */}
        <div className="px-6 py-5 bg-white border-t border-gray-150 shadow-[0_-2px_10px_rgba(0,0,0,0.02)]">
          <form onSubmit={handleSend} className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask me about skills, background, or top candidates..."
              disabled={loading}
              className="flex-1 px-4 py-3 bg-gray-50 border border-gray-200 focus:border-blue-500 focus:bg-white focus:outline-none rounded-xl text-sm transition placeholder-gray-400 disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="px-4 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-100 disabled:text-gray-400 text-white font-semibold rounded-xl flex items-center justify-center transition shadow-md shadow-blue-500/10 hover:shadow-lg hover:shadow-blue-500/20 active:scale-95 disabled:shadow-none"
            >
              <FiSend size={16} />
            </button>
          </form>
        </div>
      </div>
    </>
  );
}
