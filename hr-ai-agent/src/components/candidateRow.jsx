import { FiThumbsDown } from "react-icons/fi";

export default function CandidateRow({ name, score, scoreColor, status, statusBg, statusText, actionButton, actionBg, onCandidateClick, candidateData }) {
  return (
    <tr className="border-b border-gray-200 hover:bg-gray-50 transition cursor-pointer" onClick={() => onCandidateClick(candidateData)}>
      <td className="px-4 py-4 w-2/5 text-sm font-medium text-gray-900">{name}</td>
      <td className="px-4 py-4 w-1/5">
        <div className="flex items-center gap-3">
          <div className="w-24 overflow-hidden rounded-full bg-gray-200">
            <div className={`h-1.5 rounded-full ${scoreColor}`} style={{ width: `${score}%` }}></div>
          </div>
          <p className="text-sm font-medium text-gray-700">{score}</p>
        </div>
      </td>
      <td className="px-4 py-4 w-1/5">
        <span className={`inline-flex items-center rounded-md ${statusBg} px-2.5 py-1 text-xs font-semibold ${statusText}`}>
          {status}
        </span>
      </td>
      <td className="px-4 py-4 w-1/5">
        <div className="flex items-center gap-2">
          <button className={`flex items-center justify-center rounded-lg h-9 flex-1 ${actionBg} text-white text-xs font-bold`}>
            {actionButton}
          </button>
          <button className="flex items-center justify-center rounded-lg h-9 w-9 shrink-0 bg-red-100 text-red-600 hover:bg-red-200">
            <FiThumbsDown size={16} />
          </button>
        </div>
      </td>
    </tr>
  );
}
