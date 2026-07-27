import type { TicketCategory, TicketPriority } from "@/lib/types";

const PRIORITY_CLASSES: Record<TicketPriority, string> = {
  low: "badge-priority-low",
  medium: "badge-priority-medium",
  high: "badge-priority-high",
  urgent: "badge-priority-urgent",
};

function formatLabel(value: string): string {
  return value.replace(/_/g, " ");
}

export function CategoryBadge({ category }: { category: TicketCategory }) {
  return (
    <span className="badge badge-category">{formatLabel(category)}</span>
  );
}

export function PriorityBadge({ priority }: { priority: TicketPriority }) {
  return (
    <span className={`badge ${PRIORITY_CLASSES[priority]}`}>
      {formatLabel(priority)}
    </span>
  );
}
