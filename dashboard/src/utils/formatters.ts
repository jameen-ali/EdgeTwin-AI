/**
 * Data and metric formatters for EdgeTwin technical UI.
 */

export function formatNumber(
  value: number | null | undefined,
  decimals: number = 1,
  fallback: string = "—"
): string {
  if (value === null || value === undefined || isNaN(value)) {
    return fallback;
  }
  return value.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function formatPercent(
  probability: number | null | undefined,
  fallback: string = "—"
): string {
  if (probability === null || probability === undefined || isNaN(probability)) {
    return fallback;
  }
  return `${(probability * 100).toFixed(1)}%`;
}

export function formatTimestamp(
  isoString: string | null | undefined,
  fallback: string = "—"
): string {
  if (!isoString) return fallback;
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return fallback;
    return date.toLocaleTimeString("en-US", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return fallback;
  }
}

export function formatDateTime(
  isoString: string | null | undefined,
  fallback: string = "—"
): string {
  if (!isoString) return fallback;
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return fallback;
    return `${date.toISOString().slice(0, 10)} ${date.toLocaleTimeString("en-US", {
      hour12: false,
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    })}`;
  } catch {
    return fallback;
  }
}

export function formatTimeAgo(
  isoString: string | null | undefined,
  fallback: string = "—"
): string {
  if (!isoString) return fallback;
  try {
    const date = new Date(isoString);
    if (isNaN(date.getTime())) return fallback;
    const diffSec = Math.floor((Date.now() - date.getTime()) / 1000);
    if (diffSec < 5) return "just now";
    if (diffSec < 60) return `${diffSec}s ago`;
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHours = Math.floor(diffMin / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  } catch {
    return fallback;
  }
}
