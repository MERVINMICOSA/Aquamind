import {
  useMemo,
} from 'react'

import type {
  DashboardSensorReading,
} from '../../types/dashboard'


interface SensorTrendChartProps {
  readings:
    DashboardSensorReading[]

  unit:
    string
}


interface ChartPoint {
  id: string

  timestamp:
    number

  recordedAt:
    string

  value:
    number
}


const VIEWBOX_WIDTH =
  720

const VIEWBOX_HEIGHT =
  260

const PLOT_LEFT =
  62

const PLOT_RIGHT =
  22

const PLOT_TOP =
  24

const PLOT_BOTTOM =
  48

const PLOT_WIDTH =
  VIEWBOX_WIDTH -
  PLOT_LEFT -
  PLOT_RIGHT

const PLOT_HEIGHT =
  VIEWBOX_HEIGHT -
  PLOT_TOP -
  PLOT_BOTTOM


function formatNumber(
  value: number,
): string {
  return new Intl.NumberFormat(
    undefined,
    {
      maximumFractionDigits:
        2,
    },
  ).format(
    value,
  )
}


function formatChartTime(
  timestamp: number,
): string {
  return new Date(
    timestamp,
  ).toLocaleString(
    undefined,
    {
      month:
        'short',

      day:
        'numeric',

      hour:
        'numeric',

      minute:
        '2-digit',
    },
  )
}


export function SensorTrendChart({
  readings,
  unit,
}: SensorTrendChartProps) {
  const points =
    useMemo<ChartPoint[]>(
      () =>
        readings
          .map(
            (reading) => ({
              id:
                reading.id,

              timestamp:
                Date.parse(
                  reading.recorded_at,
                ),

              recordedAt:
                reading.recorded_at,

              value:
                reading.value_numeric,
            }),
          )
          .filter(
            (point) =>
              Number.isFinite(
                point.timestamp,
              ) &&
              Number.isFinite(
                point.value,
              ),
          )
          .sort(
            (
              left,
              right,
            ) =>
              left.timestamp -
              right.timestamp,
          ),
      [
        readings,
      ],
    )


  if (
    points.length < 2
  ) {
    return (
      <div className="sensor-trend-empty">
        <strong>
          Not enough readings for a trend
        </strong>

        <span>
          At least two valid persisted
          readings are required to draw a
          trend.
        </span>
      </div>
    )
  }


  const values =
    points.map(
      (point) =>
        point.value,
    )


  const rawMin =
    Math.min(
      ...values,
    )

  const rawMax =
    Math.max(
      ...values,
    )


  /*
   * A flat series still needs visible vertical room.
   *
   * This is display padding only. It is not an
   * operational or aquaponics threshold.
   */
  const rawRange =
    rawMax -
    rawMin

  const padding =
    rawRange === 0
      ? Math.max(
          Math.abs(
            rawMax,
          ) *
            0.05,
          0.5,
        )
      : rawRange *
        0.1


  const chartMin =
    rawMin -
    padding

  const chartMax =
    rawMax +
    padding

  const chartRange =
    chartMax -
    chartMin


  const firstTimestamp =
    points[0]!.timestamp

  const lastTimestamp =
    points[
      points.length - 1
    ]!.timestamp

  const timestampRange =
    lastTimestamp -
    firstTimestamp


  function getX(
    timestamp: number,
  ): number {
    if (
      timestampRange === 0
    ) {
      return (
        PLOT_LEFT +
        PLOT_WIDTH / 2
      )
    }

    return (
      PLOT_LEFT +
      (
        (
          timestamp -
          firstTimestamp
        ) /
        timestampRange
      ) *
        PLOT_WIDTH
    )
  }


  function getY(
    value: number,
  ): number {
    return (
      PLOT_TOP +
      (
        1 -
        (
          value -
          chartMin
        ) /
          chartRange
      ) *
        PLOT_HEIGHT
    )
  }


  const pathData =
    points
      .map(
        (
          point,
          index,
        ) => {
          const x =
            getX(
              point.timestamp,
            )

          const y =
            getY(
              point.value,
            )

          return `${
            index === 0
              ? 'M'
              : 'L'
          } ${x} ${y}`
        },
      )
      .join(
        ' ',
      )


  const midValue =
    (
      chartMax +
      chartMin
    ) /
    2


  return (
    <div className="sensor-trend-chart">
      <div className="sensor-trend-chart__summary">
        <span>
          {
            points.length
          }{' '}
          readings on this page
        </span>

        <span>
          Range:{' '}
          {formatNumber(
            rawMin,
          )}{' '}
          –{' '}
          {formatNumber(
            rawMax,
          )}{' '}
          {unit}
        </span>
      </div>


      <div className="sensor-trend-chart__canvas">
        <svg
            role="img"
            aria-labelledby="sensor-trend-title"
            aria-describedby="sensor-trend-description"
            viewBox={`0 0 ${VIEWBOX_WIDTH} ${VIEWBOX_HEIGHT}`}
            className="sensor-trend-chart__svg"
        >
          <title
            id="sensor-trend-title"
          >
            Sensor reading trend
          </title>

          <desc
            id="sensor-trend-description"
          >
            Chronological trend of the
            persisted sensor readings
            currently loaded on this
            history page.
          </desc>


          {/* Horizontal reference lines */}

          <line
            x1={PLOT_LEFT}
            y1={PLOT_TOP}
            x2={
              PLOT_LEFT +
              PLOT_WIDTH
            }
            y2={PLOT_TOP}
            className="sensor-trend-grid-line"
          />

          <line
            x1={PLOT_LEFT}
            y1={
              PLOT_TOP +
              PLOT_HEIGHT /
                2
            }
            x2={
              PLOT_LEFT +
              PLOT_WIDTH
            }
            y2={
              PLOT_TOP +
              PLOT_HEIGHT /
                2
            }
            className="sensor-trend-grid-line"
          />

          <line
            x1={PLOT_LEFT}
            y1={
              PLOT_TOP +
              PLOT_HEIGHT
            }
            x2={
              PLOT_LEFT +
              PLOT_WIDTH
            }
            y2={
              PLOT_TOP +
              PLOT_HEIGHT
            }
            className="sensor-trend-grid-line"
          />


          {/* Y-axis labels */}

          <text
            x={
              PLOT_LEFT -
              10
            }
            y={
              PLOT_TOP +
              4
            }
            textAnchor="end"
            className="sensor-trend-axis-label"
          >
            {formatNumber(
              chartMax,
            )}
          </text>

          <text
            x={
              PLOT_LEFT -
              10
            }
            y={
              PLOT_TOP +
              PLOT_HEIGHT /
                2 +
              4
            }
            textAnchor="end"
            className="sensor-trend-axis-label"
          >
            {formatNumber(
              midValue,
            )}
          </text>

          <text
            x={
              PLOT_LEFT -
              10
            }
            y={
              PLOT_TOP +
              PLOT_HEIGHT +
              4
            }
            textAnchor="end"
            className="sensor-trend-axis-label"
          >
            {formatNumber(
              chartMin,
            )}
          </text>


          {/* Data line */}

          <path
            d={pathData}
            fill="none"
            className="sensor-trend-line"
          />


          {/* Persisted points */}

          {points.map(
            (point) => (
              <circle
                key={
                  point.id
                }
                cx={
                  getX(
                    point.timestamp,
                  )
                }
                cy={
                  getY(
                    point.value,
                  )
                }
                r="4"
                className="sensor-trend-point"
              >
                <title>
                  {formatNumber(
                    point.value,
                  )}{' '}
                  {unit}
                  {' — '}
                  {new Date(
                    point.recordedAt,
                  ).toLocaleString()}
                </title>
              </circle>
            ),
          )}


          {/* X-axis labels */}

          <text
            x={PLOT_LEFT}
            y={
              VIEWBOX_HEIGHT -
              12
            }
            textAnchor="start"
            className="sensor-trend-axis-label"
          >
            {formatChartTime(
              firstTimestamp,
            )}
          </text>

          <text
            x={
              PLOT_LEFT +
              PLOT_WIDTH
            }
            y={
              VIEWBOX_HEIGHT -
              12
            }
            textAnchor="end"
            className="sensor-trend-axis-label"
          >
            {formatChartTime(
              lastTimestamp,
            )}
          </text>
        </svg>
      </div>
    </div>
  )
}