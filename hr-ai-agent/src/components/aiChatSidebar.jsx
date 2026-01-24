import { useState, useEffect, useRef } from "react";
import { FiSearch, FiChevronDown, FiSend } from "react-icons/fi";
import { MdSmartToy } from "react-icons/md";
import { sendChatMessage, fetchConversationHistory } from "../services/api";

export default function AIChatSidebar({ threadId, onMessageSent }) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [loadingHistory, setLoadingHistory] = useState(true);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    loadConversationHistory();
  }, [threadId]);

  const loadConversationHistory = async () => {
    try {
      setLoadingHistory(true);
      const history = await fetchConversationHistory(threadId);
      
      // Convert backend format to our messages format
      const loadedMessages = history.messages.map(msg => ({
        role: msg.role,
        content: msg.content
      }));
      
      // If there's no history, show welcome message
      if (loadedMessages.length === 0) {
        setMessages([{
          role: "assistant",
          content: "Hello! How can I help you with your candidates today? You can ask me to screen CVs, compare candidates, or answer questions about specific applicants."
        }]);
      } else {
        setMessages(loadedMessages);
      }
    } catch (error) {
      console.error('Error loading conversation history:', error);
      // Show welcome message on error
      setMessages([{
        role: "assistant",
        content: "Hello! How can I help you with your candidates today? You can ask me to screen CVs, compare candidates, or answer questions about specific applicants."
      }]);
    } finally {
      setLoadingHistory(false);
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput("");
    
    console.log("=== CHAT DEBUG START ===");
    console.log("1. Sending message:", userMessage);
    console.log("2. Thread ID:", threadId);
    
    // Add user message
    setMessages(prev => [...prev, { role: "user", content: userMessage }]);
    setLoading(true);

    try {
      console.log("3. Calling API...");
      const response = await sendChatMessage(userMessage, threadId);
      
      console.log("4. API Response received");
      console.log("5. Full response object:", response);
      console.log("6. Response type:", typeof response);
      console.log("7. Response keys:", response ? Object.keys(response) : "null");
      
      // Extract the response from the state - backend returns state with response_message field
      let assistantMessage = "";
      
      if (response && response.response_message) {
        assistantMessage = response.response_message;
        console.log("8a. Using response_message:", assistantMessage);
      } else if (response && response.error_message) {
        assistantMessage = `Error: ${response.error_message}`;
        console.log("8b. Using error_message:", assistantMessage);
      } else if (response && response.final_response) {
        assistantMessage = response.final_response;
        console.log("8c. Using final_response:", assistantMessage);
      } else if (response && response.messages && response.messages.length > 0) {
        const lastMessage = response.messages[response.messages.length - 1];
        assistantMessage = lastMessage.content || "I processed your request.";
        console.log("8d. Using messages array:", assistantMessage);
      } else {
        assistantMessage = "I processed your request successfully.";
        console.log("8e. No known response field, using default");
        console.log("Available fields:", response ? JSON.stringify(response, null, 2) : "none");
      }
      
      console.log("9. Final message to display:", assistantMessage);
      
      // Add assistant message
      setMessages(prev => [...prev, { role: "assistant", content: assistantMessage }]);
      console.log("10. Message added to state");
      
      // Trigger callback to refresh candidates table if provided
      if (onMessageSent) {
        console.log("11. Calling onMessageSent callback to refresh candidates");
        onMessageSent();
      }
    } catch (error) {
      console.error("ERROR in handleSend:", error);
      console.error("Error details:", error.message);
      console.error("Error stack:", error.stack);
      setMessages(prev => [...prev, { 
        role: "assistant", 
        content: "Sorry, I encountered an error processing your request. Please try again." 
      }]);
    } finally {
      setLoading(false);
      console.log("=== CHAT DEBUG END ===");
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const quickActions = [
    "Show me the top 3 candidates",
    "Compare candidates with Python skills",
    "Who has the most experience?",
    "Screen the uploaded CVs"
  ];

  return (
    <div className="flex flex-col flex-[1] min-w-[320px] bg-white rounded-xl border border-gray-200 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <MdSmartToy className="text-blue-500 text-xl" />
          <h3 className="font-bold text-gray-900">AI HR Agent</h3>
        </div>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {messages.map((message, index) => (
          message.role === "assistant" ? (
            <div key={index} className="flex gap-3">
              <div className="flex-shrink-0 size-8 bg-blue-100 rounded-full flex items-center justify-center">
                <MdSmartToy className="text-blue-500 text-lg" />
              </div>
              <div className="bg-gray-100 rounded-lg rounded-tl-none p-3 max-w-[80%]">
                <p className="text-sm text-gray-800 whitespace-pre-wrap">{message.content}</p>
              </div>
            </div>
          ) : (
            <div key={index} className="flex justify-end">
              <div className="bg-blue-500 text-white rounded-lg rounded-br-none p-3 max-w-[80%]">
                <p className="text-sm whitespace-pre-wrap">{message.content}</p>
              </div>
            </div>
          )
        ))}
        
        {loading && (
          <div className="flex gap-3">
            <div className="flex-shrink-0 size-8 bg-blue-100 rounded-full flex items-center justify-center">
              <MdSmartToy className="text-blue-500 text-lg" />
            </div>
            <div className="bg-gray-100 rounded-lg rounded-tl-none p-3">
              <div className="flex gap-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.4s' }}></div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Actions & Input */}
      <div className="p-4 border-t border-gray-200">
        <div className="grid grid-cols-2 gap-2 mb-4">
          {quickActions.map((action, index) => (
            <button 
              key={index}
              onClick={() => setInput(action)}
              className="text-left text-xs p-2 rounded-md bg-gray-50 hover:bg-gray-100 text-gray-600"
            >
              {action}
            </button>
          ))}
        </div>

        {/* Input */}
        <div className="relative">
          <input
            type="text"
            placeholder="Ask the AI agent..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            disabled={loading}
            className="w-full h-12 pl-4 pr-12 text-sm rounded-lg bg-gray-50 border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50 text-gray-900 placeholder:text-gray-500 disabled:opacity-50"
          />
          <button 
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="absolute inset-y-0 right-0 flex items-center justify-center w-12 text-blue-500 hover:bg-blue-50 rounded-r-lg disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <FiSend size={18} />
          </button>
        </div>
      </div>
    </div>
  );
}
