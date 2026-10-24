import * as SunCalc from 'suncalc';

export const LOWELL_TIME_ZONE = 'America/New_York';

export interface WallClockTime {
  date: string;
  time: string;
}

export interface SunPosition {
  instant: Date;
  altitudeDeg: number;
  azimuthDeg: number;
}

interface DateParts {
  year: number;
  month: number;
  day: number;
  hour: number;
  minute: number;
}

function parseWallClock(wallClock: WallClockTime): DateParts {
  const match =
    /^(\d{4})-(\d{2})-(\d{2})$/.exec(wallClock.date) &&
    /^(\d{2}):(\d{2})$/.exec(wallClock.time);
  const dateMatch = /^(\d{4})-(\d{2})-(\d{2})$/.exec(wallClock.date);
  const timeMatch = /^(\d{2}):(\d{2})$/.exec(wallClock.time);
  if (!match || !dateMatch || !timeMatch) {
    throw new Error('Date and time must use YYYY-MM-DD and HH:mm.');
  }

  const parts: DateParts = {
    year: Number(dateMatch[1]),
    month: Number(dateMatch[2]),
    day: Number(dateMatch[3]),
    hour: Number(timeMatch[1]),
    minute: Number(timeMatch[2]),
  };
  const check = new Date(
    Date.UTC(parts.year, parts.month - 1, parts.day, parts.hour, parts.minute),
  );
  if (
    parts.month < 1 ||
    parts.month > 12 ||
    parts.day < 1 ||
    parts.hour > 23 ||
    parts.minute > 59 ||
    check.getUTCFullYear() !== parts.year ||
    check.getUTCMonth() + 1 !== parts.month ||
    check.getUTCDate() !== parts.day
  ) {
    throw new Error('Date or time is outside the calendar.');
  }
  return parts;
}

function partsInZone(instant: Date, timeZone: string): DateParts {
  const formatter = new Intl.DateTimeFormat('en-CA', {
    timeZone,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  });
  const values = Object.fromEntries(
    formatter
      .formatToParts(instant)
      .filter((part) => part.type !== 'literal')
      .map((part) => [part.type, Number(part.value)]),
  );
  return {
    year: values['year'] ?? 0,
    month: values['month'] ?? 0,
    day: values['day'] ?? 0,
    hour: values['hour'] ?? 0,
    minute: values['minute'] ?? 0,
  };
}

function utcNumber(parts: DateParts): number {
  return Date.UTC(
    parts.year,
    parts.month - 1,
    parts.day,
    parts.hour,
    parts.minute,
  );
}

function sameParts(first: DateParts, second: DateParts): boolean {
  return (
    first.year === second.year &&
    first.month === second.month &&
    first.day === second.day &&
    first.hour === second.hour &&
    first.minute === second.minute
  );
}

export function wallClockToInstant(
  wallClock: WallClockTime,
  timeZone = LOWELL_TIME_ZONE,
): Date {
  const wanted = parseWallClock(wallClock);
  const wantedAsUtc = utcNumber(wanted);
  let candidate = wantedAsUtc;

  for (let attempt = 0; attempt < 4; attempt += 1) {
    const observed = partsInZone(new Date(candidate), timeZone);
    const difference = wantedAsUtc - utcNumber(observed);
    if (difference === 0) break;
    candidate += difference;
  }

  const instant = new Date(candidate);
  if (!sameParts(partsInZone(instant, timeZone), wanted)) {
    throw new Error('This wall-clock time does not exist in America/New_York.');
  }
  return instant;
}

export function sunPositionForWallClock(
  wallClock: WallClockTime,
  latitude: number,
  longitude: number,
): SunPosition {
  const instant = wallClockToInstant(wallClock);
  const position = SunCalc.getPosition(instant, latitude, longitude);
  return {
    instant,
    altitudeDeg: position.altitude,
    azimuthDeg: position.azimuth,
  };
}
