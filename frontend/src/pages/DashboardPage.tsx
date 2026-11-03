import {
  useMemo,
  useState,
} from 'react'

import {
  Link,
} from 'react-router-dom'

import {
  useCurrentTime,
} from '../hooks/useCurrentTime'

import {
  useDashboardOverview,
} from '../hooks/useDashboardOverview'

import {
  getTelemetryTimeliness,
} from '../utils/telemetryTimeliness'

import type {
  TelemetryTimeliness,
} from '../utils/telemetryTimeliness'

import {
  buildDashboardDemo,
  buildDemoSensorTrend,
  buildDemoActuatorEvents,
  buildDemoEsp32Packets,
} from '../data/dashboardDemo'

import './DashboardPageDemo.css'

import { Esp32TelemetryPanel } from '../components/dashboard/Esp32TelemetryPanel'

import {
  PlantHero,
} from '../components/dashboard/PlantHero'

import {
  SensorTrendChart,
} from '../components/sensors/SensorTrendChart'

import {
  useDashboardSensorTrend,
} from '../hooks/useDashboardSensorTrend'

import {
  useDashboardActuatorActivity,
} from '../hooks/useDashboardActuatorActivity'

// ============================================================
// SENSOR TYPE DISPLAY
// ============================================================


function formatSensorType(
  sensorType: string,
): string {
  switch (sensorType) {
    case 'ph':
      return 'pH'

    case 'water_temperature':
      return 'Water temperature'

    case 'tds':
      return 'TDS'

    case 'water_level':
      return 'Water level'

    case 'air_temperature':
      return 'Air temperature'

    case 'humidity':
      return 'Humidity'

    default:
      return sensorType.replaceAll(
        '_',
        ' ',
      )
  }
}


// ============================================================
// READING TIMESTAMP DISPLAY
// ============================================================


function formatReadingTime(
  recordedAt: string,
): string {
  const date =
    new Date(
      recordedAt,
    )

  if (
    Number.isNaN(
      date.getTime(),
    )
  ) {
    return recordedAt
  }

  return date.toLocaleString()
}


// ============================================================
// TELEMETRY TIMELINESS DISPLAY
// ============================================================


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


// ============================================================
// DASHBOARD
// ============================================================


export function DashboardPage() {
  const liveDashboard =
    useDashboardOverview()

  const [previewRequested, setPreviewRequested] = useState(false)

  /*
   * Local browser clock only.
   *
   * This does not poll the backend.
   * It lets telemetry timing change naturally as time passes.
   */
  const nowMs =
    useCurrentTime()

  // Only offer the browser-only preview for an empty, successfully loaded
  // installation. It never creates a database record or uses the real API.
  const demoPreview =
    previewRequested &&
    liveDashboard.systemsStatus === 'ready' &&
    liveDashboard.systems.length === 0

  const dashboard =
    demoPreview ? buildDashboardDemo(nowMs) : liveDashboard


  const [
    requestedTrendSensorId,
    setRequestedTrendSensorId,
  ] = useState<string | null>(
    null,
  )


  const trendSensor =
    dashboard.sensors.find(
      (sensor) =>
        sensor.id ===
        requestedTrendSensorId,
    ) ??
    dashboard.sensors[0] ??
    null


  const realTrend =
    useDashboardSensorTrend(
      demoPreview ? null : trendSensor?.id ?? null,
    )

  const trend = demoPreview
    ? {
        readings: buildDemoSensorTrend(trendSensor?.id ?? null, nowMs),
        status: 'ready' as const,
        errorMessage: null,
      }
    : realTrend


  const [
    requestedActivityActuatorId,
    setRequestedActivityActuatorId,
  ] = useState<string | null>(
    null,
  )


  const activityActuator =
    dashboard.actuators.find(
      (actuator) =>
        actuator.id ===
        requestedActivityActuatorId,
    ) ??
    dashboard.actuators[0] ??
    null


  const realActivity =
    useDashboardActuatorActivity(
      demoPreview ? null : activityActuator?.id ?? null,
    )

  const activity = demoPreview
    ? {
        events: buildDemoActuatorEvents(activityActuator?.id ?? null, nowMs),
        status: 'ready' as const,
        errorMessage: null,
      }
    : realActivity


  // ==========================================================
  // RESOURCE COUNTS
  // ==========================================================


  const enabledSensorCount =
    dashboard.sensors.filter(
      (sensor) =>
        sensor.is_enabled,
    ).length


  const enabledActuatorCount =
    dashboard.actuators.filter(
      (actuator) =>
        actuator.is_enabled,
    ).length


  // ==========================================================
  // LATEST READING LOOKUP
  // ==========================================================


  const latestReadingBySensorId =
    useMemo(
      () =>
        new Map(
          dashboard.latestReadings.map(
            (reading) => [
              reading.sensor_id,
              reading,
            ],
          ),
        ),
      [
        dashboard.latestReadings,
      ],
    )


  // ==========================================================
  // RENDER
  // ==========================================================


  return (
    <section className="section-page">
      <header className="dashboard-heading">
        <div>
          <p className="eyebrow">
            System Overview
          </p>

          <h1>
            Dashboard
          </h1>

          <p className="page-description">
            Monitor AquaMind water quality,
            environmental conditions,
            automation, and alerts.
          </p>
        </div>


        {!demoPreview && dashboard.systems.length >
          0 && (
          <div className="system-selector">
            <label
              htmlFor="dashboard-system"
            >
              Aquaponics system
            </label>

            <select
              id="dashboard-system"
              value={
                dashboard.selectedSystemId ??
                ''
              }
              onChange={(event) => {
                dashboard.selectSystem(
                  event.target.value,
                )
              }}
            >
              {dashboard.systems.map(
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

      {demoPreview && (
        <div className="dashboard-demo-banner" role="status">
          <div>
            <strong>DEMO PREVIEW — sample data only</strong>
            <p>
              These readings, device packets, alerts and actuator events are
              fictional layout examples. No hardware is connected, no database
              records are written and no pumps are controlled.
            </p>
          </div>
          <button
            type="button"
            className="dashboard-demo-button"
            onClick={() => setPreviewRequested(false)}
          >
            Exit demo preview
          </button>
        </div>
      )}


      {/* =====================================================
          SYSTEM LIST LOADING
          ===================================================== */}


      {dashboard.systemsStatus ===
        'loading' && (
        <div
          role="status"
          className="dashboard-message"
        >
          Loading AquaMind systems...
        </div>
      )}


      {/* =====================================================
          SYSTEM LIST ERROR
          ===================================================== */}


      {dashboard.systemsStatus ===
        'error' && (
        <div
          role="alert"
          className="dashboard-message dashboard-message--error"
        >
          {dashboard.errorMessage}
        </div>
      )}


      {/* =====================================================
          NO SYSTEMS
          ===================================================== */}


      {dashboard.systemsStatus ===
        'ready' &&
        dashboard.systems.length ===
          0 && (
          <div className="dashboard-empty">
            <p className="eyebrow">
              No System
            </p>

            <h2>
              No aquaponics system configured
            </h2>

            <p>
              AquaMind has no system records
              available yet. Sensor, actuator,
              and alert data will appear after
              a system is configured.
            </p>
            <button
              type="button"
              className="dashboard-demo-button"
              onClick={() => setPreviewRequested(true)}
            >
              Preview dashboard with sample data
            </button>
            <p>
              Demo preview is temporary and browser-only; it will not
              create systems or alter your live AquaMind data.
            </p>
          </div>
        )}


      {/* =====================================================
          SELECTED SYSTEM
          ===================================================== */}


      {dashboard.selectedSystem !==
        null && (
        <>
          <section className="system-summary">
            <div>
              <span className="system-summary__label">
                Selected system
              </span>

              <strong>
                {
                  dashboard
                    .selectedSystem
                    .name
                }
              </strong>
            </div>


            <div>
              <span className="system-summary__label">
                Timezone
              </span>

              <strong>
                {
                  dashboard
                    .selectedSystem
                    .timezone
                }
              </strong>
            </div>


            <div>
              <span className="system-summary__label">
                Status
              </span>

              <strong>
                {dashboard
                  .selectedSystem
                  .is_active
                  ? 'Active'
                  : 'Inactive'}
              </strong>
            </div>
          </section>


          <Esp32TelemetryPanel
            key={dashboard.selectedSystem.id}
            systemId={dashboard.selectedSystem.id}
            demoPackets={demoPreview ? buildDemoEsp32Packets(nowMs) : undefined}
          />

          {/* =================================================
              OVERVIEW LOADING
              ================================================= */}


          {dashboard.overviewStatus ===
            'loading' && (
            <div
              role="status"
              className="dashboard-message"
            >
              Loading system overview...
            </div>
          )}


          {/* =================================================
              OVERVIEW ERROR
              ================================================= */}


          {dashboard.overviewStatus ===
            'error' && (
            <div
              role="alert"
              className="dashboard-message dashboard-message--error"
            >
              {dashboard.errorMessage}
            </div>
          )}


          {/* =================================================
              READY OVERVIEW
              ================================================= */}


          {dashboard.overviewStatus ===
            'ready' && (
            <>
              {/* =============================================
                  RESOURCE OVERVIEW
                  ============================================= */}

              <section className="dashboard-hero-grid">
                <PlantHero />

                <article className="dashboard-system-panel">
                  <div>
                    <p className="eyebrow">
                      System Status
                    </p>

                    <h2>
                      {
                        dashboard
                          .selectedSystem
                          .name
                      }
                    </h2>

                    <span
                      className={
                        dashboard
                          .selectedSystem
                          .is_active
                          ? 'dashboard-system-state dashboard-system-state--active'
                          : 'dashboard-system-state dashboard-system-state--inactive'
                      }
                    >
                      {
                        dashboard
                          .selectedSystem
                          .is_active
                          ? 'Active'
                          : 'Inactive'
                      }
                    </span>
                  </div>

                  <dl className="dashboard-system-stats">
                    <div>
                      <dt>
                        Sensors
                      </dt>

                      <dd>
                        <strong>
                          {enabledSensorCount}
                        </strong>

                        <span>
                          of{' '}
                          {
                            dashboard
                              .sensors
                              .length
                          }{' '}
                          enabled
                        </span>
                      </dd>
                    </div>

                    <div>
                      <dt>
                        Actuators
                      </dt>

                      <dd>
                        <strong>
                          {enabledActuatorCount}
                        </strong>

                        <span>
                          of{' '}
                          {
                            dashboard
                              .actuators
                              .length
                          }{' '}
                          enabled
                        </span>
                      </dd>
                    </div>

                    <div>
                      <dt>
                        Alert records
                      </dt>

                      <dd>
                        <strong>
                          {
                            dashboard
                              .alerts
                              .length
                          }
                        </strong>

                        <span>
                          for this system
                        </span>
                      </dd>
                    </div>
                  </dl>

                  <div className="dashboard-system-panel__footer">
                    <span>
                      Timezone
                    </span>

                    <strong>
                      {
                        dashboard
                          .selectedSystem
                          .timezone
                      }
                    </strong>
                  </div>
                </article>
              </section>


              {/* =============================================
                  LATEST TELEMETRY
                  ============================================= */}


              <section className="sensor-telemetry">
                <div className="sensor-telemetry__heading">
                  <div>
                    <p className="eyebrow">
                      Latest Telemetry
                    </p>

                    <h2>
                      Latest sensor readings
                    </h2>
                  </div>


                  <span className="sensor-telemetry__count">
                    {
                      dashboard
                        .latestReadings
                        .length
                    }{' '}
                    of{' '}
                    {
                      dashboard
                        .sensors
                        .length
                    }{' '}
                    reporting
                  </span>
                </div>


                {/* ===========================================
                    NO CONFIGURED SENSORS
                    =========================================== */}


                {dashboard.sensors.length ===
                  0 ? (
                  <div className="telemetry-empty">
                    No sensors are configured
                    for this system.
                  </div>
                ) : (
                  <div className="sensor-card-grid">
                    {dashboard.sensors.map(
                      (sensor) => {
                        /*
                         * Find the newest persisted reading
                         * belonging to this configured sensor.
                         */
                        const reading =
                          latestReadingBySensorId.get(
                            sensor.id,
                          )


                        /*
                         * Timeliness is deliberately calculated
                         * from the sensor's own configured
                         * sampling interval.
                         *
                         * It does not assume anything about
                         * physical sensor hardware.
                         */
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
                            className="sensor-reading-card"
                          >
                            {/* =================================
                                SENSOR HEADER
                                ================================= */}


                            <div className="sensor-reading-card__header">
                              <div>
                                <span className="sensor-reading-card__type">
                                  {formatSensorType(
                                    sensor.sensor_type,
                                  )}
                                </span>

                                <h3>
                                  {sensor.name}
                                </h3>
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
                            </div>


                            {/* =================================
                                NO READING
                                ================================= */}


                            {reading ===
                              undefined ? (
                              <div className="sensor-reading-card__empty">
                                <strong>
                                  No reading yet
                                </strong>

                                <span>
                                  Waiting for the first
                                  persisted sensor
                                  reading.
                                </span>
                              </div>
                            ) : (
                              <>
                                {/* =============================
                                    TELEMETRY TIMELINESS
                                    ============================= */}


                                <div className="sensor-reading-timing">
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


                                  <span className="sensor-reading-timing__interval">
                                    Expected every{' '}
                                    {
                                      sensor
                                        .sampling_interval_seconds
                                    }
                                    s
                                  </span>
                                </div>


                                {/* =============================
                                    SENSOR VALUE
                                    ============================= */}


                                <div className="sensor-reading-value">
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


                                {/* =============================
                                    READING METADATA
                                    ============================= */}


                                <dl className="sensor-reading-meta">
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
                                      {formatReadingTime(
                                        reading.recorded_at,
                                      )}
                                    </dd>
                                  </div>
                                </dl>
                              </>
                            )}
                          </article>
                        )
                      },
                    )}
                  </div>
                )}
              </section>


              {/* =============================================
                  SENSOR TRENDS
                  ============================================= */}


              <section className="dashboard-trend-panel">
                <div className="dashboard-trend-panel__heading">
                  <div>
                    <p className="eyebrow">
                      Persisted History
                    </p>

                    <h2>
                      Sensor trends
                    </h2>

                    <p>
                      Bounded history from persisted
                      sensor readings.
                    </p>
                  </div>


                  {dashboard.sensors.length >
                    0 && (
                    <div className="dashboard-trend-selector">
                      <label
                        htmlFor="dashboard-trend-sensor"
                      >
                        Trend sensor
                      </label>

                      <select
                        id="dashboard-trend-sensor"
                        value={
                          trendSensor?.id ??
                          ''
                        }
                        onChange={(event) => {
                          setRequestedTrendSensorId(
                            event.target.value,
                          )
                        }}
                      >
                        {dashboard.sensors.map(
                          (sensor) => (
                            <option
                              key={sensor.id}
                              value={sensor.id}
                            >
                              {sensor.name}
                            </option>
                          ),
                        )}
                      </select>
                    </div>
                  )}
                </div>


                {trendSensor === null ? (
                  <div className="sensor-trend-empty">
                    <strong>
                      No sensor available for a trend
                    </strong>

                    <span>
                      Configure a sensor before
                      persisted history can be shown.
                    </span>
                  </div>
                ) : trend.status ===
                  'loading' ? (
                  <div
                    role="status"
                    className="dashboard-trend-message"
                  >
                    Loading persisted sensor history...
                  </div>
                ) : trend.status ===
                  'error' ? (
                  <div
                    role="alert"
                    className="dashboard-trend-message dashboard-trend-message--error"
                  >
                    {trend.errorMessage}
                  </div>
                ) : trend.status ===
                  'ready' ? (
                  <SensorTrendChart
                    readings={trend.readings}
                    unit={trendSensor.unit}
                  />
                ) : null}
              </section>

              {/* =============================================
                  ACTUATOR ACTIVITY
                  ============================================= */}


              <section className="dashboard-activity-panel">
                <div className="dashboard-activity-panel__heading">
                  <div>
                    <p className="eyebrow">
                      Persisted History
                    </p>

                    <h2>
                      Recent actuator activity
                    </h2>

                    <p>
                      Persisted software events for the
                      selected actuator. These records do
                      not confirm physical actuator execution
                      or connection.
                    </p>
                  </div>


                  {dashboard.actuators.length >
                    0 && (
                    <div className="dashboard-activity-selector">
                      <label
                        htmlFor="dashboard-activity-actuator"
                      >
                        Activity actuator
                      </label>

                      <select
                        id="dashboard-activity-actuator"
                        value={
                          activityActuator?.id ??
                          ''
                        }
                        onChange={(event) => {
                          setRequestedActivityActuatorId(
                            event.target.value,
                          )
                        }}
                      >
                        {dashboard.actuators.map(
                          (actuator) => (
                            <option
                              key={actuator.id}
                              value={actuator.id}
                            >
                              {actuator.actuator_type.replaceAll(
                                '_',
                                ' ',
                              )}
                            </option>
                          ),
                        )}
                      </select>
                    </div>
                  )}
                </div>


                {activityActuator === null ? (
                  <div className="dashboard-activity-empty">
                    <strong>
                      No actuator available for activity
                    </strong>

                    <span>
                      Configure an actuator before persisted
                      software event history can be shown.
                    </span>
                  </div>
                ) : activity.status ===
                  'loading' ? (
                  <div
                    role="status"
                    className="dashboard-activity-message"
                  >
                    Loading persisted actuator activity...
                  </div>
                ) : activity.status ===
                  'error' ? (
                  <div
                    role="alert"
                    className="dashboard-activity-message dashboard-activity-message--error"
                  >
                    {activity.errorMessage}
                  </div>
                ) : activity.status ===
                  'ready' &&
                  activity.events.length ===
                    0 ? (
                  <div className="dashboard-activity-empty">
                    <strong>
                      No persisted software events
                    </strong>

                    <span>
                      No actuator events were returned for
                      this actuator.
                    </span>
                  </div>
                ) : activity.status ===
                  'ready' ? (
                  <>
                    <div className="dashboard-activity-list">
                      {activity.events
                        .slice(0, 5)
                        .map((event) => (
                          <article
                            className="dashboard-activity-item"
                            key={event.id}
                          >
                            <div>
                              <strong>
                                {event.command_type.replaceAll(
                                  '_',
                                  ' ',
                                )}
                              </strong>

                              <span>
                                {event.trigger_source.replaceAll(
                                  '_',
                                  ' ',
                                )}
                              </span>
                            </div>

                            <div className="dashboard-activity-item__meta">
                              <span className="dashboard-activity-status">
                                {event.status.replaceAll(
                                  '_',
                                  ' ',
                                )}
                              </span>

                              <time dateTime={event.started_at}>
                                {formatReadingTime(
                                  event.started_at,
                                )}
                              </time>
                            </div>
                          </article>
                        ))}
                    </div>

                    {!demoPreview && (
                      <Link
                        className="dashboard-activity-link"
                        to={`/actuators/${encodeURIComponent(
                          activityActuator.id,
                        )}`}
                      >
                        View full actuator history
                      </Link>
                    )}
                  </>
                ) : null}
              </section>

            </>
          )}
        </>
      )}
    </section>
  )
}