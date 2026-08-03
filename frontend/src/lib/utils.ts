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

export function formatScore(score?: number | null) {
  if (score === null || score === undefined || Number.isNaN(score)) {
    return null;
  }

  const normalized = score <= 1 ? score * 100 : score;
  return `${Math.max(0, Math.min(100, normalized)).toFixed(0)}%`;
}
