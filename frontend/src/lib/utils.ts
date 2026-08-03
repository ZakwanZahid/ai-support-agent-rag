import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(value?: string | Date | null) {
  if (!value) return "Not available";

  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "Not available";

  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
  }).format(date);
}

const RELATIVE_UNITS: Array<[Intl.RelativeTimeFormatUnit, number]> = [
  ["year", 365 * 24 * 60 * 60 * 1000],
  ["month", 30 * 24 * 60 * 60 * 1000],
  ["day", 24 * 60 * 60 * 1000],
  ["hour", 60 * 60 * 1000],
  ["minute", 60 * 1000],
];

/** "3 days ago" style timestamps for list rows, where exact times add noise. */
export function formatRelativeDate(value?: string | Date | null) {
  if (!value) return "Not available";

  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "Not available";

  const elapsed = date.getTime() - Date.now();
  const magnitude = Math.abs(elapsed);

  if (magnitude < 60 * 1000) {
    return "Just now";
  }

  const formatter = new Intl.RelativeTimeFormat("en", { numeric: "auto" });
  for (const [unit, milliseconds] of RELATIVE_UNITS) {
    if (magnitude >= milliseconds) {
      return formatter.format(Math.round(elapsed / milliseconds), unit);
    }
  }

  return formatDate(date);
}

export function formatScore(score?: number | null) {
  if (score === null || score === undefined || Number.isNaN(score)) {
    return null;
  }

  const normalized = score <= 1 ? score * 100 : score;
  return `${Math.max(0, Math.min(100, normalized)).toFixed(0)}%`;
}
