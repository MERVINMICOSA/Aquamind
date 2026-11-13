import {
  Link,
} from 'react-router-dom'

import {
  useMemo,
} from 'react'

import {
  useCurrentTime,
} from '../hooks/useCurrentTime'

import {
  useSensorsOverview,
} from '../hooks/useSensorsOverview'

import {
  Esp32TelemetryPanel,
} from '../components/dashboard/Esp32TelemetryPanel'

import {
  getTelemetryTimeliness,
} from '../utils/telemetryTimeliness'

import type {
  TelemetryTimeliness,
} from '../utils/telemetryTimeliness'


function formatValue(
  value: string,
): string {
  return value
    .replaceAll(
      '_',
      ' ',
    )
}


function formatSensorType(
  value: string,
): string {
  switch (value) {
    case 'ph':
      return 'pH'

    case 'tds':
      return 'TDS'

    case 'water_temperature':
      return 'Water temperature'

    case 'water_level':
      return 'Water level'

    case 'air_temperature':
      return 'Air temperature'

    case 'humidity':
      return 'Humidity'

    default:
      return formatValue(
        value,
      )
  }
}


function formatTimeliness(
  status:
    TelemetryTimeliness,
): string {
  switch (status) {
    case 'on_time':
      return 'On time'

    case 'late':
      return 'Late'

    case 'unknown':
      return 'Unknown'
  }
}


function formatTimestamp(
  value: string,
): string {
  const date =
    new Date(
      value,
    )

  if (
    Number.isNaN(
      date.getTime(),
    )
  ) {
    return value
  }

  return date.toLocaleString()
}


export function SensorsPage() {
  const sensorsOverview =
    useSensorsOverview()

  const nowMs =
    useCurrentTime()


  const latestReadingBySensorId =
    useMemo(
      () =>
        new Map(
          sensorsOverview.latestReadings.map(
            (reading) => [
              reading.sensor_id,
              reading,
            ],
          ),
        ),
      [
        sensorsOverview.latestReadings,
      ],
    )


  const enabledSensorCount =
    sensorsOverview.sensors.filter(
      (sensor) =>
        sensor.is_enabled,
    ).length


  // A historical reading is not evidence of a currently reporting device.
  // Only enabled sensors with a recent persisted reading count as on time.
  const onTimeSensorCount =
    sensorsOverview.sensors.filter(
      (sensor) => {
        if (!sensor.is_enabled) {
          return false
        }

        const reading =
          latestReadingBySensorId.get(
            sensor.id,
          )

        return reading !== undefined &&
          getTelemetryTimeliness(
            reading.recorded_at,
            sensor.sampling_interval_seconds,
            nowMs,
          ).status === 'on_time'
      },
    ).length

  const needsReviewSensorCount =
    enabledSensorCount -
    onTimeSensorCount


  return (
    <section className="section-page">
      <header className="sensors-page-heading">
        <div>
          <p className="eyebrow">
            Monitoring
          </p>

          <h1>
            Sensors
          </h1>

          <p className="page-description">
            Monitor configured AquaMind
            sensors, their latest persisted
            readings, and operational timing.
          </p>
        </div>


        {sensorsOverview.systems.length >
          0 && (
          <div className="system-selector">
            <label
              htmlFor="sensors-system"
            >
              Aquaponics system
            </label>

            <select
              id="sensors-system"
              value={
                sensorsOverview
                  .selectedSystemId ??
                ''
              }
              onChange={(event) => {
                sensorsOverview.selectSystem(
                  event.target.value,
                )
              }}
            >
              {sensorsOverview.systems.map(
                (system) => (
                  <option
                    key={system.id}
                    value={system.id}
                  >
                    {system.name}
                  </option>
                ),
              )}
            </select>
          </div>
        )}
      </header>

      <section
        className="surface-panel"
        aria-labelledby="sensors-purpose-heading"
      >
        <div>
          <p className="eyebrow">
            Page guide
          </p>

          <h2 id="sensors-purpose-heading">
            What is Sensors for?
          </h2>

          <p>
            Check each registered sensor, its last saved
            measurement, calibration state, data source,
            and reading freshness. Open a sensor to
            inspect its stored history.
          </p>
        </div>

        <div>
          <h3>
            What does it need?
          </h3>

          <ul>
            <li>
              An aquaponics system and sensor records
              registered in the AquaMind backend.
            </li>
            <li>
              Working sensor wiring, an ESP32 connected
              to the Raspberry Pi, and incoming USB
              telemetry for physical measurements.
            </li>
            <li>
              Verified pH and TDS calibration before
              treating those measurements as validated
              water-quality data.
            </li>
          </ul>

          <p>
            ESP32 USB packets are saved separately from
            registered sensor readings. Receiving a
            packet does not automatically populate this
            sensor list or authorize automatic control.
          </p>
        </div>
      </section>


      {sensorsOverview.systemsStatus ===
        'loading' && (
        <div
          role="status"
          className="status-message"
        >
          Loading AquaMind systems...
        </div>
      )}


      {sensorsOverview.systemsStatus ===
        'error' && (
        <div
          role="alert"
          className="status-message status-message--error"
        >
          {
            sensorsOverview
              .errorMessage
          }
        </div>
      )}


      {sensorsOverview.systemsStatus ===
        'ready' &&
        sensorsOverview.systems.length ===
          0 && (
          <div className="empty-state">
            <p className="eyebrow">
              No System
            </p>

            <h2>
              No aquaponics system configured
            </h2>

            <p>
              Configure an AquaMind system
              before monitoring sensors.
            </p>
          </div>
        )}


      {sensorsOverview.selectedSystem !==
        null && (
        <>
          <section className="sensor-overview-summary">
            <div>
              <span>
                Selected system
              </span>

              <strong>
                {
                  sensorsOverview
                    .selectedSystem
                    .name
                }
              </strong>
            </div>


            <div>
              <span>
                Configured
              </span>

              <strong>
                {
                  sensorsOverview
                    .sensors
                    .length
                }
              </strong>
            </div>


            <div>
              <span>
                On time
              </span>

              <strong>
                {onTimeSensorCount}
              </strong>
            </div>


            <div>
              <span>
                Needs review
              </span>

              <strong>
                {needsReviewSensorCount}
              </strong>
            </div>
          </section>

          <p className="page-description">
            On time and needs review count enabled sensors
            using their last saved timestamp and expected
            sampling interval. They do not prove a physical
            device is connected; disabled sensors are excluded.
          </p>


          {sensorsOverview.sensorsStatus ===
            'loading' && (
            <div
              role="status"
              className="status-message"
            >
              Loading sensors...
            </div>
          )}


          {sensorsOverview.sensorsStatus ===
            'error' && (
            <div
              role="alert"
              className="status-message status-message--error"
            >
              {
                sensorsOverview
                  .errorMessage
              }
            </div>
          )}


          {sensorsOverview.sensorsStatus ===
            'ready' &&
            sensorsOverview.sensors.length ===
              0 && (
            <div className="empty-state">
              <p className="eyebrow">
                Sensors
              </p>

              <h2>
                No sensors configured
              </h2>

              <p>
                This system currently has no
                configured sensor records.
              </p>
            </div>
          )}


          {sensorsOverview.sensorsStatus ===
            'ready' &&
            sensorsOverview.sensors.length >
              0 && (
            <div className="sensors-overview-grid">
              {sensorsOverview.sensors.map(
                (sensor) => {
                  const reading =
                    latestReadingBySensorId.get(
                      sensor.id,
                    )

                  const timing =
                    reading === undefined
                      ? null
                      : getTelemetryTimeliness(
                          reading.recorded_at,
                          sensor.sampling_interval_seconds,
                          nowMs,
                        )


                  return (
                    <article
                      key={sensor.id}
                      className="sensor-overview-card"
                    >
                      <header className="sensor-overview-card__header">
                        <div>
                          <span className="sensor-overview-card__type">
                            {formatSensorType(
                              sensor.sensor_type,
                            )}
                          </span>

                          <h2>
                            {sensor.name}
                          </h2>
                        </div>


                        <span
                          className={
                            sensor.is_enabled
                              ? 'sensor-state sensor-state--enabled'
                              : 'sensor-state sensor-state--disabled'
                          }
                        >
                          {sensor.is_enabled
                            ? 'Enabled'
                            : 'Disabled'}
                        </span>
                      </header>


                      {reading ===
                        undefined ? (
                        <div className="sensor-overview-reading sensor-overview-reading--empty">
                          <strong>
                            No reading yet
                          </strong>

                          <span>
                            Waiting for the first
                            persisted reading.
                          </span>
                        </div>
                      ) : (
                        <div className="sensor-overview-reading">
                          <div className="sensor-overview-reading__top">
                            <div className="sensor-overview-reading__value">
                              <strong>
                                {
                                  reading
                                    .value_numeric
                                }
                              </strong>

                              <span>
                                {
                                  reading
                                    .unit
                                }
                              </span>
                            </div>


                            <span
                              className={
                                timing?.status ===
                                'on_time'
                                  ? 'telemetry-timing telemetry-timing--on-time'
                                  : timing?.status ===
                                      'late'
                                    ? 'telemetry-timing telemetry-timing--late'
                                    : 'telemetry-timing telemetry-timing--unknown'
                              }
                            >
                              {formatTimeliness(
                                timing?.status ??
                                  'unknown',
                              )}
                            </span>
                          </div>


                          <dl className="sensor-overview-reading__meta">
                            <div>
                              <dt>
                                Quality
                              </dt>

                              <dd>
                                {
                                  reading
                                    .quality_status
                                }
                              </dd>
                            </div>

                            <div>
                              <dt>
                                Source
                              </dt>

                              <dd>
                                {
                                  reading
                                    .source
                                }
                              </dd>
                            </div>

                            <div>
                              <dt>
                                Recorded
                              </dt>

                              <dd>
                                {formatTimestamp(
                                  reading.recorded_at,
                                )}
                              </dd>
                            </div>
                          </dl>
                        </div>
                      )}


                      <dl className="sensor-configuration">
                        <div>
                          <dt>
                            Measurement
                          </dt>

                          <dd>
                            {formatValue(
                              sensor.measurement_type,
                            )}
                          </dd>
                        </div>


                        <div>
                          <dt>
                            Unit
                          </dt>

                          <dd>
                            {sensor.unit}
                          </dd>
                        </div>


                        <div>
                          <dt>
                            Location type
                          </dt>

                          <dd>
                            {formatValue(
                              sensor.location_type,
                            )}
                          </dd>
                        </div>


                        <div>
                          <dt>
                            Location ID
                          </dt>

                          <dd>
                            {
                              sensor.location_id ??
                              'Not assigned'
                            }
                          </dd>
                        </div>


                        <div>
                          <dt>
                            Sampling interval
                          </dt>

                          <dd>
                            {
                              sensor
                                .sampling_interval_seconds
                            }
                            s
                          </dd>
                        </div>


                        <div>
                          <dt>
                            Calibration
                          </dt>

                          <dd>
                            {formatValue(
                              sensor.calibration_status,
                            )}
                          </dd>
                        </div>


                        <div>
                          <dt>
                            Simulation
                          </dt>

                          <dd>
                            {sensor.is_simulated
                              ? 'Yes'
                              : 'No'}
                          </dd>
                        </div>


                        <div>
                          <dt>
                            Hardware identifier
                          </dt>

                          <dd>
                            {
                              sensor
                                .hardware_identifier ??
                              'Not assigned'
                            }
                          </dd>
                        </div>
                      </dl>
                      <Link
                        to={`/sensors/${sensor.id}`}
                        className="sensor-detail-link"
                      >
                        View sensor details
                      </Link>
                    </article>
                  )
                },
              )}
            </div>
          )}

          <Esp32TelemetryPanel
            systemId={sensorsOverview.selectedSystem.id}
          />
        </>
      )}
    </section>
  )
}