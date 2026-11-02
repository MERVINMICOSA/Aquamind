export type TelemetryTimeliness =
  | 'on_time'
  | 'late'
  | 'unknown'


export interface TelemetryTimingResult {
  status: TelemetryTimeliness
  ageSeconds: number | null
}


export function getTelemetryTimeliness(
  recordedAt: string,
  samplingIntervalSeconds: number,
  nowMs: number = Date.now(),
): TelemetryTimingResult {
  const recordedAtMs =
    Date.parse(
      recordedAt,
    )

  if (
    Number.isNaN(
      recordedAtMs,
    )
  ) {
    return {
      status: 'unknown',
      ageSeconds: null,
    }
  }

  if (
    !Number.isFinite(
      samplingIntervalSeconds,
    ) ||
    samplingIntervalSeconds <= 0
  ) {
    return {
      status: 'unknown',
      ageSeconds: null,
    }
  }

  const ageMs =
    nowMs -
    recordedAtMs

  /*
   * A future timestamp indicates a clock or timestamp
   * inconsistency. It must never be reported as on time.
   */
  if (
    ageMs < 0
  ) {
    return {
      status: 'unknown',
      ageSeconds: null,
    }
  }

  const ageSeconds =
    Math.floor(
      ageMs / 1000,
    )

  if (
    ageSeconds <=
    samplingIntervalSeconds
  ) {
    return {
      status: 'on_time',
      ageSeconds,
    }
  }

  return {
    status: 'late',
    ageSeconds,
  }
}