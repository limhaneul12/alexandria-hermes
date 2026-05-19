import { formatDate } from "@/lib/utils";

type RecentActivity = {
  id: string;
  occurredAt: string;
  actorName: string;
  method: string;
  sourceSurface?: string | null;
};

export function RecentActivityList({
  items,
  emptyLabel,
}: {
  items: RecentActivity[];
  emptyLabel: string;
}) {
  const recent = items.slice(0, 5);
  if (recent.length === 0) {
    return <p className="rounded-xl border border-[#d8d3c7] bg-white/60 p-4 text-sm text-[#514c44]">{emptyLabel}</p>;
  }

  return (
    <ul className="space-y-2">
      {recent.map((item) => (
        <li key={item.id} className="rounded-xl border border-[#d8d3c7] bg-white/60 p-3 text-sm">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span className="font-semibold text-[#111111]">{item.method.replaceAll("_", " ")}</span>
            <span className="text-xs tabular-nums text-[#6f6a60]">{formatDate(item.occurredAt)}</span>
          </div>
          <p className="mt-1 text-[#514c44]">
            {item.actorName}{item.sourceSurface ? ` · ${item.sourceSurface}` : ""}
          </p>
        </li>
      ))}
    </ul>
  );
}
