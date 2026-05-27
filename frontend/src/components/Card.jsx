export default function Card({ children, className = "" }) {
  return <section className={`card${className ? ` ${className}` : ""}`}>{children}</section>;
}
