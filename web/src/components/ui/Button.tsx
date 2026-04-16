import type { ButtonHTMLAttributes, CSSProperties, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";

const variants: Record<Variant, CSSProperties> = {
  primary: {
    background: "var(--color-primary)",
    color: "#fff",
    border: "1px solid var(--color-primary)",
  },
  secondary: {
    background: "var(--color-bg-elevated)",
    color: "var(--color-text)",
    border: "1px solid var(--color-border-strong)",
  },
  ghost: {
    background: "transparent",
    color: "var(--color-primary)",
    border: "1px solid transparent",
  },
  danger: {
    background: "#fff",
    color: "var(--color-danger)",
    border: "1px solid var(--color-danger)",
  },
};

export function Button({
  children,
  variant = "primary",
  ...props
}: {
  children: ReactNode;
  variant?: Variant;
} & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      type="button"
      {...props}
      style={{
        fontFamily: "inherit",
        fontWeight: 600,
        fontSize: "0.9rem",
        padding: "0.5rem 1rem",
        borderRadius: "var(--radius-md)",
        cursor: props.disabled ? "not-allowed" : "pointer",
        opacity: props.disabled ? 0.6 : 1,
        ...variants[variant],
        ...props.style,
      }}
    />
  );
}
