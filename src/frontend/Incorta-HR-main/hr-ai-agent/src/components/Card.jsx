const shadowCard = "shadow-[0_4px_24px_rgb(0_0_0_/_0.06)]";
const shadowCardHover = "hover:shadow-[0_8px_32px_rgb(0_0_0_/_0.1)]";

export default function Card({
  children,
  className = "",
  accentColor,
  interactive = false,
  onClick,
  as: Component = "div",
  ...props
}) {
  const base = [
    "bg-surface rounded-xl border border-border overflow-hidden",
    shadowCard,
    accentColor ? "border-l-4" : "",
    interactive
      ? `transition-all duration-150 hover:-translate-y-0.5 cursor-pointer ${shadowCardHover}`
      : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  const style = accentColor ? { borderLeftColor: accentColor } : undefined;

  return (
    <Component className={base} style={style} onClick={onClick} {...props}>
      {children}
    </Component>
  );
}
