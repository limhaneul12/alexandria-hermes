import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "h-10 w-full rounded-sm border border-[#cfc8b8] bg-white/70 px-3 py-2 text-sm text-[#111111] placeholder:text-[#8d8578] outline-none transition-colors hover:border-[#a39b8d] focus-visible:border-[#111111] focus-visible:ring-2 focus-visible:ring-[#111111]/10",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";
