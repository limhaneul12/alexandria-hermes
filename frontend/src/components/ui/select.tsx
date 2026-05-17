"use client";

import { useEffect, useId, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";

export type SelectOption = {
  value: string;
  label: string;
  description?: string;
};

type SelectProps = {
  label: string;
  value: string;
  options: SelectOption[];
  onChange: (value: string) => void;
  placeholder?: string;
  name?: string;
  className?: string;
};

export function Select({
  label,
  value,
  options,
  onChange,
  placeholder = "Select…",
  name,
  className = "",
}: SelectProps) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const selected = options.find((option) => option.value === value);

  useEffect(() => {
    function handlePointerDown(event: PointerEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  function choose(nextValue: string) {
    onChange(nextValue);
    setOpen(false);
  }

  return (
    <div ref={rootRef} className={`relative ${className}`} data-ui-select={name ?? label}>
      <span className="mb-2 block text-xs font-semibold uppercase tracking-[0.16em] text-[#6f6a60]">
        {label}
      </span>
      <button
        type="button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={`${id}-listbox`}
        className="flex min-h-11 w-full items-center justify-between gap-3 rounded-lg border border-[#d8d3c7] bg-white/80 px-3 py-2 text-left text-sm font-semibold text-[#111111] outline-none transition hover:bg-white focus-visible:ring-2 focus-visible:ring-black/15"
        onClick={() => setOpen((current) => !current)}
      >
        <span className={selected ? "truncate" : "truncate text-[#6f6a60]"}>
          {selected?.label ?? placeholder}
        </span>
        <ChevronDown className={`h-4 w-4 shrink-0 text-[#6f6a60] transition ${open ? "rotate-180" : ""}`} aria-hidden="true" />
      </button>
      {open ? (
        <div
          id={`${id}-listbox`}
          role="listbox"
          aria-label={label}
          className="absolute z-50 mt-2 max-h-72 w-full overflow-auto rounded-xl border border-[#cfc8b8] bg-[#fbfaf6] p-1 shadow-xl shadow-black/15"
        >
          {options.map((option) => {
            const active = option.value === value;
            return (
              <button
                key={option.value}
                type="button"
                role="option"
                aria-selected={active}
                className={`w-full rounded-lg px-3 py-2 text-left text-sm transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-black/15 ${
                  active ? "bg-[#111111] text-white" : "text-[#28241f] hover:bg-[#eee9df]"
                }`}
                onClick={() => choose(option.value)}
              >
                <span className="block font-semibold">{option.label}</span>
                {option.description ? (
                  <span className={`mt-0.5 block text-xs ${active ? "text-white/72" : "text-[#6f6a60]"}`}>
                    {option.description}
                  </span>
                ) : null}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
