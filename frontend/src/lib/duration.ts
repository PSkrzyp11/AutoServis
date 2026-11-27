const MINUTES_PER_HOUR = 60;

export type DurationParts = {
  hours: number;
  minutes: number;
};

export function splitDuration(totalMinutes: number): DurationParts {
  return {
    hours: Math.floor(totalMinutes / MINUTES_PER_HOUR),
    minutes: totalMinutes % MINUTES_PER_HOUR,
  };
}
