import { FiSearch, FiChevronDown, FiPlus } from "react-icons/fi";
import { MdSmartToy } from "react-icons/md";

export default function AIChatSidebar() {
  return (
    <div className="flex flex-col flex-[1] min-w-[320px] bg-white rounded-xl border border-gray-200 shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <div className="flex items-center gap-3">
          <MdSmartToy className="text-blue-500 text-xl" />
          <h3 className="font-bold text-gray-900">AI HR Agent</h3>
        </div>
        <button className="p-1 rounded-md hover:bg-gray-100 text-gray-500">
          <FiChevronDown size={20} />
        </button>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* AI Message 1 */}
        <div className="flex gap-3">
          <div className="flex-shrink-0 size-8 bg-blue-100 rounded-full flex items-center justify-center">
            <MdSmartToy className="text-blue-500 text-lg" />
          </div>
          <div className="bg-gray-100 rounded-lg rounded-tl-none p-3 max-w-[80%]">
            <p className="text-sm text-gray-800">Hello! How can I help you with your candidates today?</p>
          </div>
        </div>

        {/* User Message */}
        <div className="flex justify-end">
          <div className="bg-blue-500 text-white rounded-lg rounded-br-none p-3 max-w-[80%]">
            <p className="text-sm">Compare the top 3 candidates for this role.</p>
          </div>
        </div>

        {/* AI Message 2 */}
        <div className="flex gap-3">
          <div className="flex-shrink-0 size-8 bg-blue-100 rounded-full flex items-center justify-center">
            <MdSmartToy className="text-blue-500 text-lg" />
          </div>
          <div className="bg-gray-100 rounded-lg rounded-tl-none p-3 max-w-[80%]">
            <p className="text-sm text-gray-800">
              Based on their profiles and assessment scores, Jane Doe, John Smith, and Emily Clark are the top candidates.
              <br /><br />
              - <strong>Jane (95)</strong> excels in technical skills and leadership.
              <br />
              - <strong>John (88)</strong> has strong collaborative experience and fits the team culture.
              <br />
              - <strong>Emily (75)</strong> shows great potential and is a quick learner.
            </p>
          </div>
        </div>
      </div>

      {/* Quick Actions & Input */}
      <div className="p-4 border-t border-gray-200">
        <div className="grid grid-cols-2 gap-2 mb-4">
          <button className="text-left text-xs p-2 rounded-md bg-gray-50 hover:bg-gray-100 text-gray-600">
            Summarize Jane Doe's profile
          </button>
          <button className="text-left text-xs p-2 rounded-md bg-gray-50 hover:bg-gray-100 text-gray-600">
            Compare top candidates
          </button>
          <button className="text-left text-xs p-2 rounded-md bg-gray-50 hover:bg-gray-100 text-gray-600">
            Generate interview questions
          </button>
          <button className="text-left text-xs p-2 rounded-md bg-gray-50 hover:bg-gray-100 text-gray-600">
            What are John's key strengths?
          </button>
        </div>

        {/* Input */}
        <div className="relative">
          <input
            type="text"
            placeholder="Ask the AI agent..."
            className="w-full h-12 pl-4 pr-12 text-sm rounded-lg bg-gray-50 border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-500/50 text-gray-900 placeholder:text-gray-500"
          />
          <button className="absolute inset-y-0 right-0 flex items-center justify-center w-12 text-blue-500 hover:bg-blue-50 rounded-r-lg">
            <FiPlus size={20} />
          </button>
        </div>
      </div>
    </div>
  );
}
