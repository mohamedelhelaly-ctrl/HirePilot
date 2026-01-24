import Badge from "./badge";
import { Link } from "react-router-dom";

export default function JobRow({ title, department, location, candidates, screened, newApplicants, jobId }) {
  return (
    <tr className="border-b border-gray-200/100 hover:bg-gray-50 transition">
      <td className="py-4 px-4 font-medium">{title}</td>

      <td className="py-4 px-4">
        <Badge text={department} />
      </td>

      <td className="py-4 px-4 text-gray-600">{location}</td>

      <td className="py-4 px-4">{candidates}</td>

      <td className="py-4 px-4">
        <span className="text-green-600 font-medium">{screened}</span>
      </td>

      <td className="py-4 px-4">
        {newApplicants > 0 ? (
          <span className="bg-blue-100 text-blue-600 px-3 py-1 rounded-full text-sm">
            {newApplicants}
          </span>
        ) : (
          "0"
        )}
      </td>

      <td className="py-4 px-4">
        <Link to={`/jobs/${jobId}`}>
          <button className="bg-blue-100 text-blue-600 px-4 py-2 rounded-lg hover:bg-blue-200">
            Quick View
          </button>
        </Link>
      </td>
    </tr>
  );
}
