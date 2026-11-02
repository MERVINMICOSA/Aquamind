import {
  useState,
} from 'react'

import {
  useAuth,
} from '../hooks/useAuth'

import {
  useFeedingOverview,
} from '../hooks/useFeedingOverview'

import type {
  FeedingSchedule,
  FeedingScheduleInput,
  FeedingScheduleUpdateInput,
} from '../types/feeding'

import {
  FeederCalibrationPanel,
} from '../components/FeederCalibrationPanel'

import {
  FishPopulationPanel,
} from '../components/FishPopulationPanel'

interface ScheduleDraft {
  actuatorId: string
  name: string
  scheduleExpression: string
  enabled: boolean
  maxPerFeedGrams: string
}


interface ScheduleEditor {
  systemId: string
  mode: 'create' | 'edit'
  scheduleId: string | null
  original: FeedingSchedule | null
  draft: ScheduleDraft
}


function formatTimestamp(
  value: string,
): string {
  const date =
    new Date(value)

  return Number.isNaN(
    date.getTime(),
  )
    ? value
    : date.toLocaleString()
}


function formatNullableValue(
  value:
    number |
    string |
    null,
): string {
  return value === null
    ? 'Not recorded'
    : String(value)
}


export function FeedingPage() {
  const overview =
    useFeedingOverview()

  const auth =
    useAuth()

  const [
    editor,
    setEditor,
  ] = useState<ScheduleEditor | null>(
    null,
  )

  const [
    formError,
    setFormError,
  ] = useState<string | null>(
    null,
  )


  const canManageSchedules =
    auth.user?.role === 'admin'

  const canEditPopulation =
    auth.isAuthenticated

  const canDeletePopulation =
    auth.user?.role === 'admin'


  const currentEditor =
    editor?.systemId ===
    overview.selectedSystemId
      ? editor
      : null


  const enabledSchedules =
    overview.schedules.filter(
      (schedule) =>
        schedule.enabled,
    ).length


  function openCreateEditor() {
    const firstActuator =
      overview.actuators[0]

    if (
      overview.selectedSystemId ===
        null ||
      firstActuator === undefined
    ) {
      return
    }

    setFormError(
      null,
    )

    setEditor({
      systemId:
        overview.selectedSystemId,

      mode: 'create',
      scheduleId: null,
      original: null,

      draft: {
        actuatorId:
          firstActuator.id,

        name: '',

        scheduleExpression:
          '',

        enabled: true,

        maxPerFeedGrams:
          '',
      },
    })
  }


  function openEditEditor(
    schedule: FeedingSchedule,
  ) {
    if (
      overview.selectedSystemId ===
      null
    ) {
      return
    }

    setFormError(
      null,
    )

    setEditor({
      systemId:
        overview.selectedSystemId,

      mode: 'edit',

      scheduleId:
        schedule.id,

      original:
        schedule,

      draft: {
        actuatorId:
          schedule.actuator_id,

        name:
          schedule.name,

        scheduleExpression:
          schedule
            .schedule_expression,

        enabled:
          schedule.enabled,

        maxPerFeedGrams:
          String(
            schedule
              .max_per_feed_grams,
          ),
      },
    })
  }


  function updateDraft(
    update:
      Partial<ScheduleDraft>,
  ) {
    setEditor(
      (current) => {
        if (current === null) {
          return current
        }

        return {
          ...current,

          draft: {
            ...current.draft,
            ...update,
          },
        }
      },
    )
  }


  async function submitEditor() {
    if (currentEditor === null) {
      return
    }

    const name =
      currentEditor
        .draft
        .name
        .trim()

    const scheduleExpression =
      currentEditor
        .draft
        .scheduleExpression
        .trim()

    const maxPerFeedGrams =
      Number(
        currentEditor
          .draft
          .maxPerFeedGrams,
      )


    if (name.length === 0) {
      setFormError(
        'Schedule name is required.',
      )

      return
    }


    if (
      scheduleExpression.length ===
      0
    ) {
      setFormError(
        'Schedule expression is required.',
      )

      return
    }


    if (
      currentEditor
        .draft
        .actuatorId
        .length === 0
    ) {
      setFormError(
        'An actuator is required.',
      )

      return
    }


    if (
      !Number.isFinite(
        maxPerFeedGrams,
      ) ||
      maxPerFeedGrams <= 0
    ) {
      setFormError(
        'Max per feed must be greater than zero.',
      )

      return
    }


    setFormError(
      null,
    )


    try {
      if (
        currentEditor.mode ===
        'create'
      ) {
        const input:
          FeedingScheduleInput = {
            actuator_id:
              currentEditor
                .draft
                .actuatorId,

            name,

            schedule_expression:
              scheduleExpression,

            enabled:
              currentEditor
                .draft
                .enabled,

            max_per_feed_grams:
              maxPerFeedGrams,
          }

        await overview.createSchedule(
          input,
        )

        setEditor(
          null,
        )

        return
      }


      const original =
        currentEditor.original

      const scheduleId =
        currentEditor.scheduleId

      if (
        original === null ||
        scheduleId === null
      ) {
        return
      }


      const update:
        FeedingScheduleUpdateInput =
        {}


      if (
        currentEditor
          .draft
          .actuatorId !==
        original.actuator_id
      ) {
        update.actuator_id =
          currentEditor
            .draft
            .actuatorId
      }


      if (
        name !==
        original.name
      ) {
        update.name =
          name
      }


      if (
        scheduleExpression !==
        original
          .schedule_expression
      ) {
        update.schedule_expression =
          scheduleExpression
      }


      if (
        currentEditor
          .draft
          .enabled !==
        original.enabled
      ) {
        update.enabled =
          currentEditor
            .draft
            .enabled
      }


      if (
        maxPerFeedGrams !==
        original
          .max_per_feed_grams
      ) {
        update.max_per_feed_grams =
          maxPerFeedGrams
      }


      if (
        Object.keys(
          update,
        ).length === 0
      ) {
        setEditor(
          null,
        )

        return
      }


      await overview.updateSchedule(
        scheduleId,
        update,
      )

      setEditor(
        null,
      )
    } catch {
      /*
       * The hook owns the authoritative
       * mutation error state.
       */
    }
  }


  async function removeSchedule(
    schedule: FeedingSchedule,
  ) {
    const confirmed =
      window.confirm(
        `Delete feeding schedule "${schedule.name}"?\n\n` +
        'This removes the schedule configuration. ' +
        'Existing persisted feeding-event history is retained.',
      )


    if (!confirmed) {
      return
    }


    try {
      await overview.deleteSchedule(
        schedule.id,
      )

      if (
        currentEditor
          ?.scheduleId ===
        schedule.id
      ) {
        setEditor(
          null,
        )
      }
    } catch {
      /*
       * The hook displays the mutation error.
       */
    }
  }


  return (
    <section
      className="section-page feeding-page"
    >
      <header
        className="sensor-detail-heading"
      >
        <div>
          <p className="eyebrow">
            Fish Management
          </p>

          <h1>
            Feeding
          </h1>

          <p className="page-description">
            Review feeding configuration and
            persisted feeding events for the
            selected system.
          </p>
        </div>


        {overview.systems.length > 0 && (
          <div
            className="system-selector"
          >
            <label
              htmlFor="feeding-system"
            >
              Aquaponics system
            </label>

            <select
              id="feeding-system"
              value={
                overview
                  .selectedSystemId ??
                ''
              }
              disabled={
                overview.isMutating
              }
              onChange={
                (event) =>
                  overview.selectSystem(
                    event.target.value,
                  )
              }
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
          className={
            'status-message ' +
            'status-message--error'
          }
        >
          Unable to load AquaMind systems.
        </div>
      )}


      {overview.systemsStatus ===
        'ready' &&
        overview.systems.length ===
          0 && (
        <div
          className="empty-state"
        >
          <h2>
            No aquaponics system configured
          </h2>

          <p>
            No system is available for
            feeding configuration.
          </p>
        </div>
      )}


      {overview.selectedSystem !==
        null && (
        <>
          <section
            className="sensor-detail-panel"
            aria-labelledby={
              'feeding-schedules-heading'
            }
          >
            <div
              className={
                'sensor-detail-history-heading'
              }
            >
              <div>
                <h2
                  id={
                    'feeding-schedules-heading'
                  }
                >
                  Configured feeding schedules
                </h2>

                <p>
                  {
                    overview
                      .selectedSystem
                      .name
                  }
                </p>
              </div>


              {overview.scheduleStatus ===
                'ready' && (
                <span
                  className={
                    'sensor-detail-history-page'
                  }
                >
                  {
                    overview
                      .schedules
                      .length
                  } configured ·{' '}
                  {
                    enabledSchedules
                  } enabled
                </span>
              )}
            </div>


            <p
              className={
                'actuator-hardware-note'
              }
            >
              Feeding schedules are persisted
              configuration. Creating or changing
              a schedule does not itself confirm
              physical feeder execution.
            </p>


            {canManageSchedules && (
              <div>
                <button
                  type="button"
                  className={
                    'sensor-history-button'
                  }
                  disabled={
                    overview.isMutating ||
                    overview.actuatorStatus !==
                      'ready' ||
                    overview.actuators.length ===
                      0
                  }
                  onClick={
                    openCreateEditor
                  }
                >
                  Add schedule
                </button>

                {overview.actuatorStatus ===
                  'ready' &&
                  overview.actuators.length ===
                    0 && (
                  <p>
                    No configured actuator is
                    available for this system.
                  </p>
                )}
              </div>
            )}


            {overview.mutationError !==
              null && (
              <div
                role="alert"
                className={
                  'status-message ' +
                  'status-message--error'
                }
              >
                {overview.mutationError}
              </div>
            )}


            {currentEditor !== null && (
              <form
                onSubmit={
                  (event) => {
                    event.preventDefault()

                    void submitEditor()
                  }
                }
              >
                <h3>
                  {currentEditor.mode ===
                  'create'
                    ? 'Add feeding schedule'
                    : 'Edit feeding schedule'}
                </h3>


                <div
                  className="system-selector"
                >
                  <label
                    htmlFor={
                      'feeding-schedule-name'
                    }
                  >
                    Name
                  </label>

                  <input
                    id={
                      'feeding-schedule-name'
                    }
                    value={
                      currentEditor
                        .draft
                        .name
                    }
                    disabled={
                      overview.isMutating
                    }
                    onChange={
                      (event) =>
                        updateDraft({
                          name:
                            event
                              .target
                              .value,
                        })
                    }
                  />
                </div>


                <div
                  className="system-selector"
                >
                  <label
                    htmlFor={
                      'feeding-schedule-actuator'
                    }
                  >
                    Actuator
                  </label>

                  <select
                    id={
                      'feeding-schedule-actuator'
                    }
                    value={
                      currentEditor
                        .draft
                        .actuatorId
                    }
                    disabled={
                      overview.isMutating
                    }
                    onChange={
                      (event) =>
                        updateDraft({
                          actuatorId:
                            event
                              .target
                              .value,
                        })
                    }
                  >
                    {!overview.actuators.some(
                      (actuator) =>
                        actuator.id ===
                        currentEditor
                          .draft
                          .actuatorId,
                    ) && (
                      <option
                        value={
                          currentEditor
                            .draft
                            .actuatorId
                        }
                      >
                        Current actuator
                        unavailable —{' '}
                        {
                          currentEditor
                            .draft
                            .actuatorId
                        }
                      </option>
                    )}

                    {overview.actuators.map(
                      (actuator) => (
                        <option
                          key={
                            actuator.id
                          }
                          value={
                            actuator.id
                          }
                        >
                          {actuator.name}
                          {' — '}
                          {
                            actuator
                              .actuator_type
                          }
                        </option>
                      ),
                    )}
                  </select>
                </div>


                <div
                  className="system-selector"
                >
                  <label
                    htmlFor={
                      'feeding-schedule-expression'
                    }
                  >
                    Schedule expression
                  </label>

                  <input
                    id={
                      'feeding-schedule-expression'
                    }
                    value={
                      currentEditor
                        .draft
                        .scheduleExpression
                    }
                    disabled={
                      overview.isMutating
                    }
                    onChange={
                      (event) =>
                        updateDraft({
                          scheduleExpression:
                            event
                              .target
                              .value,
                        })
                    }
                  />

                  <small>
                    Stored exactly as entered.
                    This interface does not
                    interpret the expression.
                  </small>
                </div>


                <div
                  className="system-selector"
                >
                  <label
                    htmlFor={
                      'feeding-max-per-feed'
                    }
                  >
                    Max per feed (grams)
                  </label>

                  <input
                    id={
                      'feeding-max-per-feed'
                    }
                    type="number"
                    min="0"
                    step="any"
                    value={
                      currentEditor
                        .draft
                        .maxPerFeedGrams
                    }
                    disabled={
                      overview.isMutating
                    }
                    onChange={
                      (event) =>
                        updateDraft({
                          maxPerFeedGrams:
                            event
                              .target
                              .value,
                        })
                    }
                  />
                </div>


                <label>
                  <input
                    type="checkbox"
                    checked={
                      currentEditor
                        .draft
                        .enabled
                    }
                    disabled={
                      overview.isMutating
                    }
                    onChange={
                      (event) =>
                        updateDraft({
                          enabled:
                            event
                              .target
                              .checked,
                        })
                    }
                  />

                  {' '}Enabled
                </label>


                {formError !== null && (
                  <div
                    role="alert"
                    className={
                      'status-message ' +
                      'status-message--error'
                    }
                  >
                    {formError}
                  </div>
                )}


                <div>
                  <button
                    type="submit"
                    className={
                      'sensor-history-button'
                    }
                    disabled={
                      overview.isMutating
                    }
                  >
                    {overview.mutationStatus ===
                    'saving'
                      ? 'Saving...'
                      : 'Save schedule'}
                  </button>

                  <button
                    type="button"
                    className={
                      'sensor-history-button'
                    }
                    disabled={
                      overview.isMutating
                    }
                    onClick={
                      () => {
                        setEditor(
                          null,
                        )

                        setFormError(
                          null,
                        )
                      }
                    }
                  >
                    Cancel
                  </button>
                </div>
              </form>
            )}


            {overview.scheduleStatus ===
              'loading' && (
              <div role="status">
                Loading feeding schedules...
              </div>
            )}


            {overview.scheduleStatus ===
              'error' && (
              <div
                role="alert"
                className={
                  'status-message ' +
                  'status-message--error'
                }
              >
                Unable to load feeding schedules
                for the selected system.
              </div>
            )}


            {overview.scheduleStatus ===
              'ready' &&
              (
                overview.schedules.length ===
                0
                  ? (
                    <p>
                      No feeding schedules
                      configured for this
                      system.
                    </p>
                  )
                  : (
                    <div
                      className={
                        'sensor-history-table-wrap'
                      }
                    >
                      <table
                        className={
                          'sensor-history-table'
                        }
                        aria-label={
                          'Configured feeding schedules'
                        }
                      >
                        <thead>
                          <tr>
                            <th>Name</th>
                            <th>Status</th>
                            <th>
                              Schedule expression
                            </th>
                            <th>
                              Max per feed
                              (grams)
                            </th>
                            <th>
                              Actuator ID
                            </th>

                            {canManageSchedules && (
                              <th>
                                Actions
                              </th>
                            )}
                          </tr>
                        </thead>

                        <tbody>
                          {
                            overview
                              .schedules
                              .map(
                                (schedule) => (
                                  <tr
                                    key={
                                      schedule.id
                                    }
                                  >
                                    <td>
                                      {
                                        schedule
                                          .name
                                      }
                                    </td>

                                    <td>
                                      {
                                        schedule
                                          .enabled
                                          ? 'Enabled'
                                          : 'Disabled'
                                      }
                                    </td>

                                    <td>
                                      {
                                        schedule
                                          .schedule_expression
                                      }
                                    </td>

                                    <td>
                                      {
                                        schedule
                                          .max_per_feed_grams
                                      }
                                    </td>

                                    <td>
                                      {
                                        schedule
                                          .actuator_id
                                      }
                                    </td>


                                    {canManageSchedules && (
                                      <td>
                                        <button
                                          type="button"
                                          className={
                                            'sensor-history-button'
                                          }
                                          disabled={
                                            overview
                                              .isMutating
                                          }
                                          onClick={
                                            () =>
                                              openEditEditor(
                                                schedule,
                                              )
                                          }
                                        >
                                          Edit
                                        </button>

                                        <button
                                          type="button"
                                          className={
                                            'sensor-history-button'
                                          }
                                          disabled={
                                            overview
                                              .isMutating
                                          }
                                          onClick={
                                            () => {
                                              void removeSchedule(
                                                schedule,
                                              )
                                            }
                                          }
                                        >
                                          Delete
                                        </button>
                                      </td>
                                    )}
                                  </tr>
                                ),
                              )
                          }
                        </tbody>
                      </table>
                    </div>
                  )
              )}
          </section>


          <FeederCalibrationPanel
            overview={
              overview
            }
            canManage={
              canManageSchedules
            }
            currentUserId={
              auth.user?.userId ??
              null
            }
          />

          <FishPopulationPanel
            overview={
              overview
            }
            canEdit={
              canEditPopulation
            }
            canDelete={
              canDeletePopulation
            }
          />

          <section
            className="sensor-detail-panel"
            aria-labelledby={
              'feeding-history-heading'
            }
          >
            <div
              className={
                'sensor-detail-history-heading'
              }
            >
              <div>
                <h2
                  id={
                    'feeding-history-heading'
                  }
                >
                  Persisted feeding event
                  history
                </h2>

                <p>
                  {
                    overview
                      .selectedSystem
                      .name
                  }
                </p>
              </div>

              <span
                className={
                  'sensor-detail-history-page'
                }
              >
                Page {
                  overview.pageNumber
                }
              </span>
            </div>


            <p
              className={
                'actuator-hardware-note'
              }
            >
              Feeding events are persisted
              application records and do not by
              themselves confirm physical feeder
              execution.
            </p>


            {overview.historyStatus ===
              'loading' && (
              <div role="status">
                Loading feeding event
                history...
              </div>
            )}


            {overview.historyStatus ===
              'error' && (
              <div
                role="alert"
                className={
                  'status-message ' +
                  'status-message--error'
                }
              >
                Unable to load feeding event
                history for the selected
                system.
              </div>
            )}


            {overview.historyStatus ===
              'ready' &&
              (
                overview.events.length ===
                0
                  ? (
                    <p>
                      No persisted feeding
                      events on this page.
                    </p>
                  )
                  : (
                    <div
                      className={
                        'sensor-history-table-wrap'
                      }
                    >
                      <table
                        className={
                          'sensor-history-table'
                        }
                        aria-label={
                          'Persisted feeding event history'
                        }
                      >
                        <thead>
                          <tr>
                            <th>Status</th>
                            <th>Executed</th>
                            <th>
                              Amount (grams)
                            </th>
                            <th>
                              Duration (seconds)
                            </th>
                            <th>Tank ID</th>
                            <th>Schedule ID</th>
                            <th>
                              Actuator event ID
                            </th>
                            <th>
                              Biomass basis
                              (grams)
                            </th>
                            <th>
                              Calibration ID
                            </th>
                            <th>Notes</th>
                          </tr>
                        </thead>

                        <tbody>
                          {
                            overview
                              .events
                              .map(
                                (event) => (
                                  <tr
                                    key={
                                      event.id
                                    }
                                  >
                                    <td>
                                      {
                                        event.status
                                      }
                                    </td>

                                    <td>
                                      {
                                        formatTimestamp(
                                          event
                                            .executed_at,
                                        )
                                      }
                                    </td>

                                    <td>
                                      {
                                        event
                                          .amount_grams
                                      }
                                    </td>

                                    <td>
                                      {
                                        event
                                          .duration_seconds
                                      }
                                    </td>

                                    <td>
                                      {
                                        event
                                          .tank_id
                                      }
                                    </td>

                                    <td>
                                      {
                                        formatNullableValue(
                                          event
                                            .schedule_id,
                                        )
                                      }
                                    </td>

                                    <td>
                                      {
                                        event
                                          .actuator_event_id
                                      }
                                    </td>

                                    <td>
                                      {
                                        formatNullableValue(
                                          event
                                            .calculated_from_biomass,
                                        )
                                      }
                                    </td>

                                    <td>
                                      {
                                        formatNullableValue(
                                          event
                                            .calibration_id,
                                        )
                                      }
                                    </td>

                                    <td>
                                      {
                                        formatNullableValue(
                                          event
                                            .notes,
                                        )
                                      }
                                    </td>
                                  </tr>
                                ),
                              )
                          }
                        </tbody>
                      </table>
                    </div>
                  )
              )}


            <footer
              className={
                'sensor-history-pagination'
              }
            >
              <span>
                Up to 50 feeding events
                per page
              </span>

              <div>
                <button
                  type="button"
                  className={
                    'sensor-history-button'
                  }
                  disabled={
                    !overview.hasPrevious ||
                    overview.historyStatus ===
                      'loading'
                  }
                  onClick={
                    overview.previousPage
                  }
                >
                  Previous
                </button>

                <button
                  type="button"
                  className={
                    'sensor-history-button'
                  }
                  disabled={
                    !overview.hasNext ||
                    overview.historyStatus !==
                      'ready'
                  }
                  onClick={
                    overview.nextPage
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