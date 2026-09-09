/**
 * Formatting utilities for time, duration, and position representations.
 * Pure presentation logic — does not alter underlying analytical values.
 */

export function formatMillisToLapTime(millis: number | null | undefined): string {
  if (millis == null || isNaN(millis)) return "—";
  const totalSeconds = millis / 1000;
  const minutes = Math.floor(totalSeconds / 60);
  const remainingSeconds = (totalSeconds % 60).toFixed(3);
  const paddedSeconds = remainingSeconds.padStart(6, "0");
  if (minutes > 0) {
    return `${minutes}:${paddedSeconds}`;
  }
  return `${remainingSeconds}s`;
}

export function formatMillisToSeconds(millis: number | null | undefined): string {
  if (millis == null || isNaN(millis)) return "—";
  return `${(millis / 1000).toFixed(3)} s`;
}

export function formatDeltaMillis(millis: number | null | undefined): string {
  if (millis == null || isNaN(millis)) return "—";
  const sign = millis > 0 ? "+" : "";
  const sec = (millis / 1000).toFixed(3);
  return `${sign}${sec} s (${millis > 0 ? "+" : ""}${millis} ms)`;
}

export function formatPositionChange(change: number | null | undefined): {
  label: string;
  badgeClass: string;
  icon: string;
} {
  if (change == null) {
    return { label: "—", badgeClass: "pos-na", icon: "" };
  }
  if (change > 0) {
    return { label: `+${change}`, badgeClass: "pos-gain", icon: "▲" };
  }
  if (change < 0) {
    return { label: `${change}`, badgeClass: "pos-loss", icon: "▼" };
  }
  return { label: "0", badgeClass: "pos-equal", icon: "▬" };
}

export function formatPoints(points: number | string | null | undefined): string {
  if (points == null) return "0";
  const num = typeof points === "string" ? parseFloat(points) : points;
  return Number.isInteger(num) ? num.toString() : num.toFixed(1);
}
