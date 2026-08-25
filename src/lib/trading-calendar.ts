const DAY_MS = 86_400_000;

const utcDate = (year: number, month: number, day: number) => new Date(Date.UTC(year, month, day));
const toIsoDate = (date: Date) => date.toISOString().slice(0, 10);

function observedFixedHoliday(year: number, month: number, day: number): string {
  const holiday = utcDate(year, month, day);
  if (holiday.getUTCDay() === 6) holiday.setUTCDate(holiday.getUTCDate() - 1);
  if (holiday.getUTCDay() === 0) holiday.setUTCDate(holiday.getUTCDate() + 1);
  return toIsoDate(holiday);
}

function nthWeekday(year: number, month: number, weekday: number, occurrence: number): string {
  const first = utcDate(year, month, 1);
  const day = 1 + (weekday - first.getUTCDay() + 7) % 7 + (occurrence - 1) * 7;
  return toIsoDate(utcDate(year, month, day));
}

function lastWeekday(year: number, month: number, weekday: number): string {
  const last = utcDate(year, month + 1, 0);
  const day = last.getUTCDate() - (last.getUTCDay() - weekday + 7) % 7;
  return toIsoDate(utcDate(year, month, day));
}

function easterSunday(year: number): Date {
  const a = year % 19;
  const b = Math.floor(year / 100);
  const c = year % 100;
  const d = Math.floor(b / 4);
  const e = b % 4;
  const f = Math.floor((b + 8) / 25);
  const g = Math.floor((b - f + 1) / 3);
  const h = (19 * a + b - d - g + 15) % 30;
  const i = Math.floor(c / 4);
  const k = c % 4;
  const l = (32 + 2 * e + 2 * i - h - k) % 7;
  const m = Math.floor((a + 11 * h + 22 * l) / 451);
  const month = Math.floor((h + l - 7 * m + 114) / 31) - 1;
  const day = (h + l - 7 * m + 114) % 31 + 1;
  return utcDate(year, month, day);
}

function usMarketHolidays(year: number): Set<string> {
  const goodFriday = toIsoDate(new Date(easterSunday(year).getTime() - 2 * DAY_MS));
  return new Set([
    observedFixedHoliday(year, 0, 1),
    observedFixedHoliday(year + 1, 0, 1),
    nthWeekday(year, 0, 1, 3),
    nthWeekday(year, 1, 1, 3),
    goodFriday,
    lastWeekday(year, 4, 1),
    ...(year >= 2022 ? [observedFixedHoliday(year, 5, 19)] : []),
    observedFixedHoliday(year, 6, 4),
    nthWeekday(year, 8, 1, 1),
    nthWeekday(year, 10, 4, 4),
    observedFixedHoliday(year, 11, 25),
  ]);
}

export function isUsTradingSession(date: string): boolean {
  const parsed = new Date(`${date}T00:00:00Z`);
  const weekday = parsed.getUTCDay();
  return weekday !== 0 && weekday !== 6 && !usMarketHolidays(parsed.getUTCFullYear()).has(date);
}

export function nextUsTradingSession(date: string): string {
  const parsed = new Date(`${date}T00:00:00Z`);
  for (let offset = 1; offset <= 14; offset++) {
    const candidate = toIsoDate(new Date(parsed.getTime() + offset * DAY_MS));
    if (isUsTradingSession(candidate)) return candidate;
  }
  throw new Error(`Unable to resolve the next US trading session after ${date}`);
}
