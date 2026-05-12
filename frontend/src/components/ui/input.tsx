import * as React from "react";
import { cn } from "@/lib/utils";

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input
      ref={ref}
      className={cn(
        "h-10 w-full rounded-md border border-white/10 bg-black/30 px-3 py-2 text-sm text-parchment placeholder:text-stone-500 outline-none transition focus:border-gold-300/50 focus:ring-1 focus:ring-gold-300/30",
        className,
      )}
      {...props}
    />
  ),
);
Input.displayName = "Input";
