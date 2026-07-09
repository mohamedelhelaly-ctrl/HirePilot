import { MdVideocam, MdInfo, MdPersonAdd, MdSearch, MdFilterList } from "react-icons/md";

export default function CandidateTable({ candidates, selectedJob }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <h2 className="text-2xl font-bold text-gray-900">
          {selectedJob?.title || "Select a Job"} Candidates
        </h2>
        <div className="flex items-center gap-2">
          <button className="flex items-center justify-center gap-2 rounded-lg h-10 px-4 text-sm font-bold text-blue-600 hover:bg-blue-50 transition">
            <MdInfo size={18} />
            <span>View Job Details</span>
          </button>
          <button className="flex items-center justify-center gap-2 rounded-lg h-10 px-4 bg-gray-200 text-gray-800 text-sm font-bold hover:bg-gray-300 transition">
            <MdPersonAdd size={18} />
            <span>Add Candidate</span>
          </button>
        </div>
      </div>

      {/* Filters and Search */}
      <div className="flex flex-wrap items-center gap-4 mb-6">
        {/* Search */}
        <div className="relative flex-1 min-w-[200px]">
          <MdSearch className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
          <input
            type="text"
            placeholder="Search by name..."
            className="w-full rounded-lg border border-gray-300 h-10 pl-10 pr-4 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        {/* Stage Filter */}
        <select className="rounded-lg border border-gray-300 h-10 px-3 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500">
          <option>All Stages</option>
          <option>Phone Screen</option>
          <option>Technical Interview</option>
          <option>Offer</option>
        </select>

        {/* Filter Button */}
        <button className="flex items-center justify-center gap-2 rounded-lg h-10 px-4 border border-gray-300 text-sm font-medium hover:bg-gray-100 transition">
          <MdFilterList size={18} />
          <span>Filter</span>
        </button>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="text-xs text-gray-500 uppercase bg-gray-50">
            <tr>
              <th className="px-6 py-3 font-semibold">Candidate Name</th>
              <th className="px-6 py-3 font-semibold">Current Stage</th>
              <th className="px-6 py-3 font-semibold">Application Date</th>
              <th className="px-6 py-3 text-right font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody>
            {candidates.map((candidate, index) => (
              <tr key={index} className="border-b hover:bg-gray-50 transition">
                <td className="px-6 py-4 font-medium text-gray-900 whitespace-nowrap">
                  {candidate.name}
                </td>
                <td className="px-6 py-4 text-gray-700">{candidate.stage}</td>
                <td className="px-6 py-4 text-gray-700">{candidate.applicationDate}</td>
                <td className="px-6 py-4 text-right flex items-center justify-end gap-2">
                  <button className="rounded-lg h-9 px-4 text-sm font-bold text-gray-700 border border-gray-300 hover:bg-gray-100 transition">
                    View Profile
                  </button>
                  <button className="flex items-center gap-2 rounded-lg h-9 px-4 text-sm font-bold text-white bg-orange-500 hover:bg-orange-600 transition">
                    <MdVideocam size={16} />
                    Start Co-Pilot
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
