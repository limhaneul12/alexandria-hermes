import * as React from "react";
import { cn } from "@/lib/utils";

export function Badge({ className, ...props }: React.HTMLAttributes<HTMLSpanElement>) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-sm border border-[#cfc8b8] bg-[#eee9df] px-2.5 py-0.5 text-xs font-medium text-[#111111]",
        className,
      )}
      {...props}
    />
  );
}
