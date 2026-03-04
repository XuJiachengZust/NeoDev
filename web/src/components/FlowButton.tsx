import { ButtonHTMLAttributes } from "react";

interface FlowButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  loading?: boolean;
  children: React.ReactNode;
}

export function FlowButton({ loading, disabled, children, className = "", ...props }: FlowButtonProps) {
  return (
    <button
      type="button"
      className={`flow-button ${className}`.trim()}
      disabled={disabled ?? loading}
      {...props}
    >
      {loading ? "处理中…" : children}
    </button>
  );
}
