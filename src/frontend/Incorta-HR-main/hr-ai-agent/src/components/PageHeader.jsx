export default function PageHeader({ title, description, actions, className = "" }) {
  return (
    <header
      className={`shrink-0 w-full flex flex-wrap items-center justify-between gap-x-5 gap-y-3 pb-3 mb-4 border-b border-border ${className}`}
    >
      <div className="flex-1 min-w-[200px]">
        <h1 className="m-0 text-[1.2rem] font-bold leading-[1.2] text-gray-900">{title}</h1>
        {description && (
          <p className="m-0 mt-1 text-[0.9rem] text-muted leading-snug">{description}</p>
        )}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2 shrink-0">{actions}</div>}
    </header>
  );
}
