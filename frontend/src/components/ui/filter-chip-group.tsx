import { cn } from "@/lib/utils";

export type FilterChipChoice = {
  value: string;
  label: string;
  count?: number;
};

export type FilterChipProps = {
  active?: boolean;
  label: string;
  count?: number;
  onClick: () => void;
  variant?: "boxed" | "toolbar";
  className?: string;
};

type FilterChipGroupProps = {
  label: string;
  value: string;
  choices: FilterChipChoice[];
  onChange: (value: string) => void;
  allLabel?: string | null;
  emptyLabel?: string;
  name?: string;
  className?: string;
  showCounts?: boolean;
  variant?: "boxed" | "toolbar";
};

export function FilterChipGroup({
  label,
  value,
  choices,
  onChange,
  allLabel = "All",
  emptyLabel,
  name,
  className,
  showCounts = true,
  variant = "boxed",
}: FilterChipGroupProps) {
  if (variant === "toolbar") {
    return (
      <fieldset className={cn("min-w-0", className)} data-filter-group={name ?? label}>
        <legend className="sr-only">{label}</legend>
        <div className="flex gap-1.5 overflow-x-auto pb-1">
          {allLabel ? (
            <FilterChip
              active={value === "ALL"}
              label={allLabel}
              onClick={() => onChange("ALL")}
              variant="toolbar"
            />
          ) : null}
          {choices.map((choice) => (
            <FilterChip
              key={choice.value}
              active={choice.value === value}
              label={choice.label}
              count={showCounts ? choice.count : undefined}
              onClick={() => onChange(choice.value)}
              variant="toolbar"
            />
          ))}
        </div>
      </fieldset>
    );
  }

  return (
    <fieldset className={cn("min-w-0 space-y-2", className)} data-filter-group={name ?? label}>
      <legend className="text-xs font-semibold uppercase tracking-[0.16em] text-[#6f6a60]">
        {label}
      </legend>
      <div className="flex max-h-32 flex-wrap gap-1.5 overflow-y-auto rounded-2xl border border-[#d8d3c7] bg-[#fbfaf6]/70 p-2">
        {allLabel ? (
          <FilterChip
            active={value === "ALL"}
            label={allLabel}
            onClick={() => onChange("ALL")}
          />
        ) : null}
        {choices.map((choice) => (
          <FilterChip
            key={choice.value}
            active={choice.value === value}
            label={choice.label}
            count={showCounts ? choice.count : undefined}
            onClick={() => onChange(choice.value)}
          />
        ))}
        {choices.length === 0 && emptyLabel ? (
          <span className="px-2 py-1 text-xs text-[#6f6a60]">{emptyLabel}</span>
        ) : null}
      </div>
    </fieldset>
  );
}

export function FilterChip({
  active,
  label,
  count,
  onClick,
  variant = "boxed",
  className,
}: FilterChipProps) {
  return (
    <button
      type="button"
      aria-pressed={Boolean(active)}
      className={cn(
        "inline-flex min-h-8 items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold leading-none transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-black/15",
        variant === "toolbar" ? "shrink-0" : null,
        active
          ? "border-[#111111] bg-[#eee9df] text-[#111111]"
          : "border-[#d8d3c7] bg-white text-[#28241f] hover:bg-[#f6f3ec]",
        className,
      )}
      onClick={onClick}
    >
      <span>{label}</span>
      {typeof count === "number" ? (
        <span
          className={cn(
            "rounded-full px-1.5 py-0.5 text-[10px]",
            active ? "bg-white/55 text-[#514c44]" : "bg-[#eee9df] text-[#6f6a60]",
          )}
        >
          {count}
        </span>
      ) : null}
    </button>
  );
}
