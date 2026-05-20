export type DateBoundary = "start" | "end";

export type CountedFilterChoice = {
  value: string;
  label: string;
  count: number;
};

export function toUtcDateBoundaryIso(
  value: string,
  boundary: DateBoundary,
): string | null {
  if (!value) return null;
  const date = new Date(`${value}T00:00:00.000Z`);
  if (boundary === "end") date.setUTCHours(23, 59, 59, 999);
  return date.toISOString();
}

export function dateInputValue(value: string | null): string {
  if (!value) return "";
  const match = value.match(/^\d{4}-\d{2}-\d{2}/);
  return match?.[0] ?? "";
}

export function countFilterChoices(values: string[]): CountedFilterChoice[] {
  const counts = new Map<string, number>();
  for (const value of values) {
    const trimmed = value.trim();
    if (!trimmed) continue;
    counts.set(trimmed, (counts.get(trimmed) ?? 0) + 1);
  }
  return [...counts.entries()]
    .sort(([leftLabel, leftCount], [rightLabel, rightCount]) => {
      if (rightCount !== leftCount) return rightCount - leftCount;
      return leftLabel.localeCompare(rightLabel);
    })
    .map(([value, count]) => ({ value, label: value, count }));
}

export function humanizeFilterLabel(value: string): string {
  return value
    .toLowerCase()
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}
