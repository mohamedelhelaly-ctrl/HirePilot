import { MdCode, MdCampaign, MdDesignServices } from "react-icons/md";

export default function JobCard({ job, isSelected, onSelect }) {
  const getIcon = (jobTitle) => {
    if (jobTitle.includes("Software")) return <MdCode className="text-3xl" />;
    if (jobTitle.includes("Marketing")) return <MdCampaign className="text-3xl" />;
    if (jobTitle.includes("Designer")) return <MdDesignServices className="text-3xl" />;
    return <MdCode className="text-3xl" />;
  };

  return (
    <div
      onClick={onSelect}
      className={`flex cursor-pointer gap-4 px-4 py-3 justify-between transition ${
        isSelected
          ? "bg-blue-50 border-l-4 border-blue-600 dark:bg-blue-900/20"
          : "bg-white hover:bg-gray-50 border-l-4 border-transparent"
      }`}
    >
      <div className="flex items-start gap-4">
        <div className={`flex items-center justify-center rounded-lg shrink-0 size-12 ${
          isSelected
            ? "bg-blue-100 text-blue-600"
            : "bg-gray-100 text-gray-700"
        }`}>
          {getIcon(job.title)}
        </div>
        <div className="flex flex-1 flex-col justify-center">
          <p className="font-medium leading-normal text-gray-900">{job.title}</p>
          <p className="text-sm font-normal leading-normal text-gray-500">
            Total Candidates: {job.candidates}
          </p>
          <p className="text-sm font-normal leading-normal text-gray-500">
            JOB-ID: {job.jobId}
          </p>
        </div>
      </div>
      <div className="shrink-0 flex items-center">
        <div className="size-3 rounded-full bg-green-600"></div>
      </div>
    </div>
  );
}
