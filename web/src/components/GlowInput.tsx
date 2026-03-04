import { InputHTMLAttributes, forwardRef } from "react";

export const GlowInput = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  function GlowInput({ className = "", ...props }, ref) {
    return (
      <input
        ref={ref}
        className={`glow-input ${className}`.trim()}
        {...props}
      />
    );
  }
);
