import { isUsTradingSession, previousUsTradingSession } from "./trading-calendar";

const newYorkParts = (now: Date) => Object.fromEntries(new Intl.DateTimeFormat("en-CA", {
  timeZone: "America/New_York",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
}).formatToParts(now).filter((part) => part.type !== "literal").map((part) => [part.type, part.value]));

export function latestCompletedUsTradingSession(now = new Date()): string {
  const parts = newYorkParts(now);
  const today = `${parts.year}-${parts.month}-${parts.day}`;
  const minutes = Number(parts.hour) * 60 + Number(parts.minute);
  // The backend waits for and validates the completed regular-session close.
  // Keep this display check equally conservative by allowing a 15-minute buffer.
  if (isUsTradingSession(today) && minutes >= 16 * 60 + 15) return today;
  return previousUsTradingSession(today);
}
