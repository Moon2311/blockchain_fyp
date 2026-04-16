import type { ReactNode } from "react";

export function Card({
  title,
  children,
  className = "",
}: {
  title?: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`card-surface ${className}`}
      style={{
        background: "var(--color-bg-elevated)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius-lg)",
        boxShadow: "var(--shadow-sm)",
        padding: "1.25rem 1.35rem",
      }}
    >
      {title ? (
        <h2 style={{ marginTop: 0, marginBottom: "0.75rem" }}>{title}</h2>
      ) : null}
      {children}
    </section>
  );
}
