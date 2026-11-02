import {
  Link,
  useParams,
} from 'react-router-dom'

import {
  useCurrentTime,
} from '../hooks/useCurrentTime'

import {
  useSensorDetail,
} from '../hooks/useSensorDetail'

import {
  getTelemetryTimeliness,
} from '../utils/telemetryTimeliness'

import type {
  TelemetryTimeliness,
} from '../utils/telemetryTimeliness'

import {
  SensorTrendChart,
} from '../components/sensors/SensorTrendChart'


function formatValue(
  value: string,
): string {
  return value.replaceAll(
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


export function SensorDetailPage() {
  const {
    sensorId,
  } = useParams<{
    sensorId: string
  }>()


  const detail =
    useSensorDetail(
      sensorId,
    )


  const nowMs =
    useCurrentTime()


  const timing =
    detail.sensor !== null &&
    detail.latestReading !== null
      ? getTelemetryTimeliness(
          detail.latestReading.recorded_at,
          detail.sensor.sampling_interval_seconds,
          nowMs,
        )
      : null


  if (
    sensorId === undefined
  ) {
    return (
      <section className="section-page">
        <div
          role="alert"
          className="status-message status-message--error"
        >
          Sensor identifier is missing.
        </div>
      </section>
    )
  }


  return (
    <section className="section-page">
      <header className="sensor-detail-heading">
        <div>
          <Link
            to="/sensors"
            className="sensor-detail-back-link"
          >
            ← Sensors
          </Link>

          <p className="eyebrow">
            Sensor Detail
          </p>

          <h1>
            {detail.sensor?.name ??
              'Sensor'}
          </h1>

          <p className="page-description">
            Inspect sensor configuration
            and bounded persisted telemetry
            history.
          </p>
        </div>


        {detail.sensor !==
          null && (
          <span
            className={
              detail.sensor.is_enabled
                ? 'sensor-state sensor-state--enabled'
                : 'sensor-state sensor-state--disabled'
            }
          >
            {detail.sensor.is_enabled
              ? 'Enabled'
              : 'Disabled'}
          </span>
        )}
      </header>


      {detail.sensorStatus ===
        'loading' && (
        <div
          role="status"
          className="status-message"
        >
          Loading sensor...
        </div>
      )}


      {detail.sensorStatus ===
        'error' && (
        <div
          role="alert"
          className="status-message status-message--error"
        >
          {
            detail
              .sensorErrorMessage
          }
        </div>
      )}


      {detail.sensorStatus ===
        'ready' &&
        detail.sensor !==
          null && (
        <>
          <section className="sensor-detail-summary">
            <div>
              <span>
                Sensor type
              </span>

              <strong>
                {formatSensorType(
                  detail.sensor
                    .sensor_type,
                )}
              </strong>
            </div>


            <div>
              <span>
                Measurement
              </span>

              <strong>
                {formatValue(
                  detail.sensor
                    .measurement_type,
                )}
              </strong>
            </div>


            <div>
              <span>
                Sampling interval
              </span>

              <strong>
                {
                  detail.sensor
                    .sampling_interval_seconds
                }
                s
              </strong>
            </div>


            <div>
              <span>
                Simulation
              </span>

              <strong>
                {detail.sensor
                  .is_simulated
                  ? 'Yes'
                  : 'No'}
              </strong>
            </div>
          </section>


          <section className="sensor-detail-panel">
            <div className="sensor-detail-panel__heading">
              <div>
                <p className="eyebrow">
                  Latest Telemetry
                </p>

                <h2>
                  Latest persisted reading
                </h2>
              </div>
            </div>


            {detail.historyStatus ===
              'loading' &&
              detail.latestReading ===
                null && (
              <div
                role="status"
                className="status-message"
              >
                Loading telemetry...
              </div>
            )}


            {detail.historyStatus ===
              'error' &&
              detail.latestReading ===
                null && (
              <div
                role="alert"
                className="status-message status-message--error"
              >
                {
                  detail
                    .historyErrorMessage
                }
              </div>
            )}


            {detail.historyStatus ===
              'ready' &&
              detail.latestReading ===
                null && (
              <div className="sensor-detail-no-reading">
                <strong>
                  No reading yet
                </strong>

                <span>
                  This sensor has no persisted
                  telemetry records.
                </span>
              </div>
            )}


            {detail.latestReading !==
              null && (
              <div className="sensor-detail-latest">
                <div className="sensor-detail-latest__value">
                  <strong>
                    {
                      detail
                        .latestReading
                        .value_numeric
                    }
                  </strong>

                  <span>
                    {
                      detail
                        .latestReading
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


                <dl className="sensor-detail-latest__meta">
                  <div>
                    <dt>
                      Quality
                    </dt>

                    <dd>
                      {
                        detail
                          .latestReading
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
                        detail
                          .latestReading
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
                        detail
                          .latestReading
                          .recorded_at,
                      )}
                    </dd>
                  </div>
                </dl>
              </div>
            )}
          </section>


          <section className="sensor-detail-panel">
            <div className="sensor-detail-panel__heading">
              <div>
                <p className="eyebrow">
                  Configuration
                </p>

                <h2>
                  Sensor configuration
                </h2>
              </div>
            </div>


            <dl className="sensor-detail-configuration">
              <div>
                <dt>
                  Name
                </dt>

                <dd>
                  {detail.sensor.name}
                </dd>
              </div>


              <div>
                <dt>
                  Sensor type
                </dt>

                <dd>
                  {formatSensorType(
                    detail.sensor
                      .sensor_type,
                  )}
                </dd>
              </div>


              <div>
                <dt>
                  Measurement
                </dt>

                <dd>
                  {formatValue(
                    detail.sensor
                      .measurement_type,
                  )}
                </dd>
              </div>


              <div>
                <dt>
                  Unit
                </dt>

                <dd>
                  {detail.sensor.unit}
                </dd>
              </div>


              <div>
                <dt>
                  Location type
                </dt>

                <dd>
                  {formatValue(
                    detail.sensor
                      .location_type,
                  )}
                </dd>
              </div>


              <div>
                <dt>
                  Location ID
                </dt>

                <dd>
                  {
                    detail.sensor
                      .location_id ??
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
                    detail.sensor
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
                    detail.sensor
                      .calibration_status,
                  )}
                </dd>
              </div>


              <div>
                <dt>
                  Simulation
                </dt>

                <dd>
                  {detail.sensor
                    .is_simulated
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
                    detail.sensor
                      .hardware_identifier ??
                    'Not assigned'
                  }
                </dd>
              </div>
            </dl>
          </section>

          <section className="sensor-detail-panel">
            <div className="sensor-detail-panel__heading">
                <div>
                <p className="eyebrow">
                    Recent Trend
                </p>

                <h2>
                    Reading trend
                </h2>
                </div>
            </div>


            <p className="sensor-trend-description">
                Visualizes only the persisted
                readings currently loaded on this
                bounded history page. No warning or
                critical thresholds are inferred.
            </p>


            <SensorTrendChart
                readings={
                detail.readings
                }
                unit={
                detail.sensor.unit
                }
            />
          </section>
        

          <section className="sensor-detail-panel">
            <div className="sensor-detail-history-heading">
              <div>
                <p className="eyebrow">
                  History
                </p>

                <h2>
                  Persisted readings
                </h2>
              </div>


              <span className="sensor-detail-history-page">
                Page {
                  detail.pageNumber
                }
              </span>
            </div>


            {detail.historyStatus ===
              'loading' && (
              <div
                role="status"
                className="sensor-history-status"
              >
                Loading reading history...
              </div>
            )}


            {detail.historyStatus ===
              'error' && (
              <div
                role="alert"
                className="status-message status-message--error"
              >
                {
                  detail
                    .historyErrorMessage
                }
              </div>
            )}


            {detail.historyStatus ===
              'ready' &&
              detail.readings.length ===
                0 && (
              <div className="sensor-detail-no-reading">
                <strong>
                  No readings on this page
                </strong>

                <span>
                  No persisted telemetry was
                  returned for this history
                  page.
                </span>
              </div>
            )}


            {detail.readings.length >
              0 && (
              <div className="sensor-history-table-wrap">
                <table className="sensor-history-table">
                  <thead>
                    <tr>
                      <th>
                        Recorded
                      </th>

                      <th>
                        Value
                      </th>

                      <th>
                        Quality
                      </th>

                      <th>
                        Source
                      </th>

                      <th>
                        Sequence
                      </th>
                    </tr>
                  </thead>


                  <tbody>
                    {detail.readings.map(
                      (reading) => (
                        <tr
                          key={
                            reading.id
                          }
                        >
                          <td>
                            {formatTimestamp(
                              reading.recorded_at,
                            )}
                          </td>

                          <td>
                            {
                              reading
                                .value_numeric
                            }{' '}
                            {
                              reading
                                .unit
                            }
                          </td>

                          <td>
                            {
                              reading
                                .quality_status
                            }
                          </td>

                          <td>
                            {
                              reading
                                .source
                            }
                          </td>

                          <td>
                            {
                              reading
                                .sequence_number ??
                              '—'
                            }
                          </td>
                        </tr>
                      ),
                    )}
                  </tbody>
                </table>
              </div>
            )}


            <footer className="sensor-history-pagination">
              <span>
                Up to 50 readings per page
              </span>


              <div>
                <button
                  type="button"
                  className="sensor-history-button"
                  disabled={
                    !detail.hasPrevious ||
                    detail.historyStatus ===
                      'loading'
                  }
                  onClick={
                    detail.previousPage
                  }
                >
                  Previous
                </button>


                <button
                  type="button"
                  className="sensor-history-button"
                  disabled={
                    !detail.hasNext ||
                    detail.historyStatus ===
                      'loading'
                  }
                  onClick={
                    detail.nextPage
                  }
                >
                  Next
                </button>
              </div>
            </footer>
          </section>
        </>
      )}
    </section>
  )
}