import { Link } from 'react-router-dom'
import {
  useActuatorsOverview,
} from '../hooks/useActuatorsOverview'


function formatValue(
  value: string,
): string {
  return value
    .replaceAll(
      '_',
      ' ',
    )
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


function hasSafetyConfiguration(
  value:
    Record<string, unknown> |
    null,
): boolean {
  return (
    value !== null &&
    Object.keys(
      value,
    ).length > 0
  )
}


export function ActuatorsPage() {
  const overview =
    useActuatorsOverview()


  const enabledCount =
    overview.actuators.filter(
      (actuator) =>
        actuator.is_enabled,
    ).length


  /*
   * current_state may have a model/database default.
   *
   * last_state_at gives us stronger evidence that an
   * actual persisted state update has occurred, so the
   * UI uses that timestamp rather than treating a
   * default value as proof of device activity.
   */
  const stateRecordedCount =
    overview.actuators.filter(
      (actuator) =>
        actuator.last_state_at !==
        null,
    ).length


  return (
    <section className="section-page">
      <header className="actuators-page-heading">
        <div>
          <p className="eyebrow">
            Control
          </p>

          <h1>
            Actuators
          </h1>

          <p className="page-description">
            Inspect configured AquaMind
            actuators and their last
            persisted control state.
          </p>
        </div>


        {overview.systems.length >
          0 && (
          <div className="system-selector">
            <label
              htmlFor="actuators-system"
            >
              Aquaponics system
            </label>

            <select
              id="actuators-system"
              value={
                overview
                  .selectedSystemId ??
                ''
              }
              onChange={(event) => {
                overview.selectSystem(
                  event.target.value,
                )
              }}
            >
              {overview.systems.map(
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


      {/* =====================================================
          SYSTEM STATUS
          ===================================================== */}


      {overview.systemsStatus ===
        'loading' && (
        <div
          role="status"
          className="status-message"
        >
          Loading AquaMind systems...
        </div>
      )}


      {overview.systemsStatus ===
        'error' && (
        <div
          role="alert"
          className="status-message status-message--error"
        >
          {overview.errorMessage}
        </div>
      )}


      {overview.systemsStatus ===
        'ready' &&
        overview.systems.length ===
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
              before monitoring actuator
              configuration.
            </p>
          </div>
        )}


      {/* =====================================================
          SELECTED SYSTEM
          ===================================================== */}


      {overview.selectedSystem !==
        null && (
        <>
          <section className="actuator-overview-summary">
            <div>
              <span>
                Selected system
              </span>

              <strong>
                {
                  overview
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
                  overview
                    .actuators
                    .length
                }
              </strong>
            </div>


            <div>
              <span>
                Enabled
              </span>

              <strong>
                {enabledCount}
              </strong>
            </div>


            <div>
              <span>
                State recorded
              </span>

              <strong>
                {stateRecordedCount}
              </strong>
            </div>
          </section>


          {/* =================================================
              ACTUATOR STATUS
              ================================================= */}


          {overview.actuatorsStatus ===
            'loading' && (
            <div
              role="status"
              className="status-message"
            >
              Loading actuators...
            </div>
          )}


          {overview.actuatorsStatus ===
            'error' && (
            <div
              role="alert"
              className="status-message status-message--error"
            >
              {overview.errorMessage}
            </div>
          )}


          {overview.actuatorsStatus ===
            'ready' &&
            overview.actuators.length ===
              0 && (
            <div className="empty-state">
              <p className="eyebrow">
                Actuators
              </p>

              <h2>
                No actuators configured
              </h2>

              <p>
                This system currently has no
                configured actuator records.
              </p>
            </div>
          )}


          {/* =================================================
              ACTUATOR CARDS
              ================================================= */}


          {overview.actuatorsStatus ===
            'ready' &&
            overview.actuators.length >
              0 && (
            <div className="actuators-overview-grid">
              {overview.actuators.map(
                (actuator) => {
                  const hasStateRecord =
                    actuator.last_state_at !==
                    null


                  return (
                    <article
                      key={actuator.id}
                      className="actuator-overview-card"
                    >
                      <header className="actuator-overview-card__header">
                        <div>
                          <span className="actuator-overview-card__type">
                            {formatValue(
                              actuator.actuator_type,
                            )}
                          </span>

                          <h2>
                            <Link to={`/actuators/${encodeURIComponent(actuator.id)}`}>
                              {actuator.name}
                            </Link>
                          </h2>
                        </div>


                        <span
                          className={
                            actuator.is_enabled
                              ? 'actuator-state actuator-state--enabled'
                              : 'actuator-state actuator-state--disabled'
                          }
                        >
                          {actuator.is_enabled
                            ? 'Enabled'
                            : 'Disabled'}
                        </span>
                      </header>


                      {/* =============================
                          PERSISTED STATE
                          ============================= */}


                      <section className="actuator-persisted-state">
                        <div className="actuator-persisted-state__heading">
                          <span>
                            Persisted state
                          </span>
                        </div>


                        {hasStateRecord ? (
                          <>
                            <strong className="actuator-persisted-state__value">
                              {formatValue(
                                actuator.current_state,
                              )}
                            </strong>


                            <dl className="actuator-persisted-state__meta">
                              <div>
                                <dt>
                                  Value
                                </dt>

                                <dd>
                                  {
                                    actuator.current_value ??
                                    'Not recorded'
                                  }
                                </dd>
                              </div>


                              <div>
                                <dt>
                                  State recorded
                                </dt>

                                <dd>
                                  {formatTimestamp(
                                    actuator.last_state_at!,
                                  )}
                                </dd>
                              </div>
                            </dl>
                          </>
                        ) : (
                          <div className="actuator-no-state">
                            <strong>
                              No state recorded
                            </strong>

                            <span>
                              AquaMind has no
                              timestamped persisted
                              actuator state yet.
                            </span>
                          </div>
                        )}
                      </section>


                      {/* =============================
                          CONFIGURATION
                          ============================= */}


                      <dl className="actuator-configuration">
                        <div>
                          <dt>
                            Actuator type
                          </dt>

                          <dd>
                            {formatValue(
                              actuator.actuator_type,
                            )}
                          </dd>
                        </div>


                        <div>
                          <dt>
                            Control mode
                          </dt>

                          <dd>
                            {formatValue(
                              actuator.control_mode,
                            )}
                          </dd>
                        </div>


                        <div>
                          <dt>
                            Location type
                          </dt>

                          <dd>
                            {actuator.location_type ===
                            null
                              ? 'Not assigned'
                              : formatValue(
                                  actuator.location_type,
                                )}
                          </dd>
                        </div>


                        <div>
                          <dt>
                            Location ID
                          </dt>

                          <dd>
                            {
                              actuator.location_id ??
                              'Not assigned'
                            }
                          </dd>
                        </div>


                        <div>
                          <dt>
                            Hardware identifier
                          </dt>

                          <dd>
                            {
                              actuator
                                .hardware_identifier ??
                              'Not assigned'
                            }
                          </dd>
                        </div>


                        <div>
                          <dt>
                            Safety configuration
                          </dt>

                          <dd>
                            {hasSafetyConfiguration(
                              actuator.safety_config,
                            )
                              ? 'Configured'
                              : 'Not configured'}
                          </dd>
                        </div>
                      </dl>


                      <p className="actuator-hardware-note">
                        Configuration and
                        persisted state do not
                        confirm that physical
                        hardware is currently
                        connected or energized.
                      </p>
                    </article>
                  )
                },
              )}
            </div>
          )}
        </>
      )}
    </section>
  )
}
