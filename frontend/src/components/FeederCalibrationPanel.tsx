import {
  useState,
} from 'react'

import {
  useFeedingOverview,
} from '../hooks/useFeedingOverview'

import type {
  FeederCalibration,
  FeederCalibrationInput,
  FeederCalibrationUpdateInput,
} from '../types/feeding'


type FeedingOverview =
  ReturnType<typeof useFeedingOverview>


interface FeederCalibrationPanelProps {
  overview: FeedingOverview
  canManage: boolean
  currentUserId: string | null
}


interface CalibrationDraft {
  runCount: string
  measuredSeconds: string
  measuredGrams: string
  gramsPerSecond: string
  calibrationMethod: string
  performedAt: string
  verified: boolean
  notes: string
}


interface CalibrationEditor {
  mode: 'create' | 'edit'
  calibrationId: string | null
  original: FeederCalibration | null
  draft: CalibrationDraft
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


function toDateTimeLocal(
  value: string,
): string {
  const date =
    new Date(value)

  if (
    Number.isNaN(
      date.getTime(),
    )
  ) {
    return ''
  }

  const offsetMilliseconds =
    date.getTimezoneOffset() *
    60_000

  return new Date(
    date.getTime() -
    offsetMilliseconds,
  )
    .toISOString()
    .slice(
      0,
      16,
    )
}


function currentDateTimeLocal(): string {
  return toDateTimeLocal(
    new Date().toISOString(),
  )
}


function toIsoTimestamp(
  value: string,
): string | null {
  const date =
    new Date(value)

  if (
    Number.isNaN(
      date.getTime(),
    )
  ) {
    return null
  }

  return date.toISOString()
}


function nullableText(
  value: string | null,
): string {
  return value === null
    ? 'Not recorded'
    : value
}


export function FeederCalibrationPanel({
  overview,
  canManage,
  currentUserId,
}: FeederCalibrationPanelProps) {
  const [
    editor,
    setEditor,
  ] = useState<CalibrationEditor | null>(
    null,
  )

  const [
    formError,
    setFormError,
  ] = useState<string | null>(
    null,
  )


  function openCreateEditor() {
    if (
      overview
        .selectedCalibrationActuatorId ===
      null
    ) {
      return
    }

    setFormError(
      null,
    )

    setEditor({
      mode:
        'create',

      calibrationId:
        null,

      original:
        null,

      draft: {
        runCount:
          '',

        measuredSeconds:
          '',

        measuredGrams:
          '',

        gramsPerSecond:
          '',

        calibrationMethod:
          '',

        performedAt:
          currentDateTimeLocal(),

        verified:
          false,

        notes:
          '',
      },
    })
  }


  function openEditEditor(
    calibration: FeederCalibration,
  ) {
    setFormError(
      null,
    )

    setEditor({
      mode:
        'edit',

      calibrationId:
        calibration.id,

      original:
        calibration,

      draft: {
        runCount:
          String(
            calibration.run_count,
          ),

        measuredSeconds:
          String(
            calibration.measured_seconds,
          ),

        measuredGrams:
          String(
            calibration.measured_grams,
          ),

        gramsPerSecond:
          String(
            calibration.grams_per_second,
          ),

        calibrationMethod:
          calibration.calibration_method,

        performedAt:
          toDateTimeLocal(
            calibration.performed_at,
          ),

        verified:
          calibration
            .verified_by_user_id !==
          null,

        notes:
          calibration.notes ??
          '',
      },
    })
  }


  function updateDraft(
    update: Partial<CalibrationDraft>,
  ) {
    setEditor(
      (current) => {
        if (
          current === null
        ) {
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
    if (
      editor === null
    ) {
      return
    }

    const runCount =
      Number(
        editor.draft.runCount,
      )

    const measuredSeconds =
      Number(
        editor
          .draft
          .measuredSeconds,
      )

    const measuredGrams =
      Number(
        editor
          .draft
          .measuredGrams,
      )

    const gramsPerSecond =
      Number(
        editor
          .draft
          .gramsPerSecond,
      )

    const calibrationMethod =
      editor
        .draft
        .calibrationMethod
        .trim()

    const performedAt =
      toIsoTimestamp(
        editor
          .draft
          .performedAt,
      )

    const notes =
      editor
        .draft
        .notes
        .trim()


    if (
      !Number.isInteger(
        runCount,
      ) ||
      runCount <= 0
    ) {
      setFormError(
        'Run count must be a whole number greater than zero.',
      )

      return
    }


    if (
      !Number.isFinite(
        measuredSeconds,
      ) ||
      measuredSeconds <= 0
    ) {
      setFormError(
        'Measured seconds must be greater than zero.',
      )

      return
    }


    if (
      !Number.isFinite(
        measuredGrams,
      ) ||
      measuredGrams <= 0
    ) {
      setFormError(
        'Measured grams must be greater than zero.',
      )

      return
    }


    if (
      !Number.isFinite(
        gramsPerSecond,
      ) ||
      gramsPerSecond <= 0
    ) {
      setFormError(
        'Grams per second must be greater than zero.',
      )

      return
    }


    if (
      calibrationMethod.length ===
      0
    ) {
      setFormError(
        'Calibration method is required.',
      )

      return
    }


    if (
      calibrationMethod.length >
      100
    ) {
      setFormError(
        'Calibration method must be 100 characters or fewer.',
      )

      return
    }


    if (
      performedAt === null
    ) {
      setFormError(
        'A valid performed date and time is required.',
      )

      return
    }


    if (
      editor.draft.verified &&
      currentUserId === null
    ) {
      setFormError(
        'Unable to request verification because the current user ID is unavailable.',
      )

      return
    }


    const verifiedByUserId =
      editor.draft.verified
        ? currentUserId
        : null

    const normalizedNotes =
      notes.length === 0
        ? null
        : notes


    setFormError(
      null,
    )


    try {
      if (
        editor.mode ===
        'create'
      ) {
        const input:
          FeederCalibrationInput = {
            run_count:
              runCount,

            measured_seconds:
              measuredSeconds,

            measured_grams:
              measuredGrams,

            grams_per_second:
              gramsPerSecond,

            calibration_method:
              calibrationMethod,

            performed_at:
              performedAt,

            verified_by_user_id:
              verifiedByUserId,

            notes:
              normalizedNotes,
          }

        await overview.createCalibration(
          input,
        )

        setEditor(
          null,
        )

        return
      }


      const original =
        editor.original

      const calibrationId =
        editor.calibrationId

      if (
        original === null ||
        calibrationId === null
      ) {
        return
      }


      const update:
        FeederCalibrationUpdateInput =
        {}


      if (
        runCount !==
        original.run_count
      ) {
        update.run_count =
          runCount
      }


      if (
        measuredSeconds !==
        original.measured_seconds
      ) {
        update.measured_seconds =
          measuredSeconds
      }


      if (
        measuredGrams !==
        original.measured_grams
      ) {
        update.measured_grams =
          measuredGrams
      }


      if (
        gramsPerSecond !==
        original.grams_per_second
      ) {
        update.grams_per_second =
          gramsPerSecond
      }


      if (
        calibrationMethod !==
        original.calibration_method
      ) {
        update.calibration_method =
          calibrationMethod
      }


      const originalPerformedAt =
        new Date(
          original.performed_at,
        ).toISOString()

      if (
        performedAt !==
        originalPerformedAt
      ) {
        update.performed_at =
          performedAt
      }


      const originallyVerified =
        original
          .verified_by_user_id !==
        null

      if (
        editor.draft.verified !==
        originallyVerified
      ) {
        update.verified_by_user_id =
          verifiedByUserId
      }


      const originalNotes =
        original.notes ??
        null

      if (
        normalizedNotes !==
        originalNotes
      ) {
        update.notes =
          normalizedNotes
      }


      if (
        Object.keys(
          update,
        ).length ===
        0
      ) {
        setEditor(
          null,
        )

        return
      }


      await overview.updateCalibration(
        calibrationId,
        update,
      )

      setEditor(
        null,
      )
    } catch {
      /*
       * The overview hook owns the authoritative
       * API mutation error state.
       */
    }
  }


  async function removeCalibration(
    calibration: FeederCalibration,
  ) {
    const confirmed =
      window.confirm(
        'Delete this feeder calibration record?\n\n' +
        'This removes the persisted calibration record. ' +
        'It does not perform or undo any physical feeder action.',
      )

    if (
      !confirmed
    ) {
      return
    }

    try {
      await overview.deleteCalibration(
        calibration.id,
      )

      if (
        editor?.calibrationId ===
        calibration.id
      ) {
        setEditor(
          null,
        )
      }
    } catch {
      /*
       * The overview hook owns the authoritative
       * API mutation error state.
       */
    }
  }


  return (
    <section
      className="sensor-detail-panel"
      aria-labelledby={
        'feeder-calibration-heading'
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
              'feeder-calibration-heading'
            }
          >
            Feeder calibration
          </h2>

          <p>
            Persisted calibration records
            for the selected actuator.
          </p>
        </div>

        <span
          className={
            'sensor-detail-history-page'
          }
        >
          Page {
            overview.calibrationPageNumber
          }
        </span>
      </div>


      <p
        className={
          'actuator-hardware-note'
        }
      >
        Calibration records are persisted
        application data. They do not by
        themselves confirm that a physical
        feeder was run or measured.
      </p>


      {overview.actuatorStatus ===
        'loading' && (
        <div role="status">
          Loading actuators...
        </div>
      )}


      {overview.actuatorStatus ===
        'error' && (
        <div
          role="alert"
          className={
            'status-message ' +
            'status-message--error'
          }
        >
          Unable to load actuators for
          feeder calibration.
        </div>
      )}


      {overview.actuatorStatus ===
        'ready' &&
        overview.actuators.length ===
          0 && (
        <p>
          No configured actuator is
          available for calibration.
        </p>
      )}


      {overview.actuators.length >
        0 && (
        <div
          className="system-selector"
        >
          <label
            htmlFor={
              'feeder-calibration-actuator'
            }
          >
            Calibration actuator
          </label>

          <select
            id={
              'feeder-calibration-actuator'
            }
            value={
              overview
                .selectedCalibrationActuatorId ??
              ''
            }
            disabled={
              overview.isMutating
            }
            onChange={
              (event) => {
                setEditor(
                  null,
                )

                setFormError(
                  null,
                )

                overview
                  .selectCalibrationActuator(
                    event.target.value,
                  )
              }
            }
          >
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
      )}


      {overview
        .selectedCalibrationActuator !==
        null && (
        <p>
          Selected actuator:{' '}
          <strong>
            {
              overview
                .selectedCalibrationActuator
                .name
            }
          </strong>
        </p>
      )}


      {canManage &&
        overview
          .selectedCalibrationActuatorId !==
          null && (
        <button
          type="button"
          className={
            'sensor-history-button'
          }
          disabled={
            overview.isMutating
          }
          onClick={
            openCreateEditor
          }
        >
          Add calibration
        </button>
      )}


      {editor !== null && (
        <form
          onSubmit={
            (event) => {
              event.preventDefault()

              void submitEditor()
            }
          }
        >
          <h3>
            {editor.mode ===
            'create'
              ? 'Add feeder calibration'
              : 'Edit feeder calibration'}
          </h3>


          <div
            className="system-selector"
          >
            <label
              htmlFor={
                'calibration-run-count'
              }
            >
              Run count
            </label>

            <input
              id={
                'calibration-run-count'
              }
              type="number"
              min="1"
              step="1"
              value={
                editor
                  .draft
                  .runCount
              }
              disabled={
                overview.isMutating
              }
              onChange={
                (event) =>
                  updateDraft({
                    runCount:
                      event.target.value,
                  })
              }
            />
          </div>


          <div
            className="system-selector"
          >
            <label
              htmlFor={
                'calibration-measured-seconds'
              }
            >
              Measured seconds
            </label>

            <input
              id={
                'calibration-measured-seconds'
              }
              type="number"
              min="0"
              step="any"
              value={
                editor
                  .draft
                  .measuredSeconds
              }
              disabled={
                overview.isMutating
              }
              onChange={
                (event) =>
                  updateDraft({
                    measuredSeconds:
                      event.target.value,
                  })
              }
            />
          </div>


          <div
            className="system-selector"
          >
            <label
              htmlFor={
                'calibration-measured-grams'
              }
            >
              Measured grams
            </label>

            <input
              id={
                'calibration-measured-grams'
              }
              type="number"
              min="0"
              step="any"
              value={
                editor
                  .draft
                  .measuredGrams
              }
              disabled={
                overview.isMutating
              }
              onChange={
                (event) =>
                  updateDraft({
                    measuredGrams:
                      event.target.value,
                  })
              }
            />
          </div>


          <div
            className="system-selector"
          >
            <label
              htmlFor={
                'calibration-grams-per-second'
              }
            >
              Grams per second
            </label>

            <input
              id={
                'calibration-grams-per-second'
              }
              type="number"
              min="0"
              step="any"
              value={
                editor
                  .draft
                  .gramsPerSecond
              }
              disabled={
                overview.isMutating
              }
              onChange={
                (event) =>
                  updateDraft({
                    gramsPerSecond:
                      event.target.value,
                  })
              }
            />

            <small>
              Stored explicitly by the
              calibration API. This
              interface does not silently
              replace it with a calculated
              value.
            </small>
          </div>


          <div
            className="system-selector"
          >
            <label
              htmlFor={
                'calibration-method'
              }
            >
              Calibration method
            </label>

            <input
              id={
                'calibration-method'
              }
              maxLength={
                100
              }
              value={
                editor
                  .draft
                  .calibrationMethod
              }
              disabled={
                overview.isMutating
              }
              onChange={
                (event) =>
                  updateDraft({
                    calibrationMethod:
                      event.target.value,
                  })
              }
            />
          </div>


          <div
            className="system-selector"
          >
            <label
              htmlFor={
                'calibration-performed-at'
              }
            >
              Performed at
            </label>

            <input
              id={
                'calibration-performed-at'
              }
              type="datetime-local"
              value={
                editor
                  .draft
                  .performedAt
              }
              disabled={
                overview.isMutating
              }
              onChange={
                (event) =>
                  updateDraft({
                    performedAt:
                      event.target.value,
                  })
              }
            />
          </div>


          <div
            className="system-selector"
          >
            <label
              htmlFor={
                'calibration-notes'
              }
            >
              Notes
            </label>

            <input
              id={
                'calibration-notes'
              }
              value={
                editor
                  .draft
                  .notes
              }
              disabled={
                overview.isMutating
              }
              onChange={
                (event) =>
                  updateDraft({
                    notes:
                      event.target.value,
                  })
              }
            />
          </div>


          <label>
            <input
              type="checkbox"
              checked={
                editor
                  .draft
                  .verified
              }
              disabled={
                overview.isMutating
              }
              onChange={
                (event) =>
                  updateDraft({
                    verified:
                      event.target.checked,
                  })
              }
            />

            {' '}Verified by me
          </label>

          <small>
            Verification is attributed by
            the backend to the authenticated
            administrator. This interface
            does not allow selecting another
            user as verifier.
          </small>


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
                : 'Save calibration'}
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


      {overview.calibrationStatus ===
        'loading' && (
        <div role="status">
          Loading feeder calibration
          history...
        </div>
      )}


      {overview.calibrationStatus ===
        'error' && (
        <div
          role="alert"
          className={
            'status-message ' +
            'status-message--error'
          }
        >
          Unable to load feeder
          calibration history.
        </div>
      )}


      {overview.calibrationStatus ===
        'ready' &&
        overview
          .selectedCalibrationActuatorId !==
          null &&
        (
          overview.calibrations.length ===
          0
            ? (
              <p>
                No persisted calibration
                records on this page.
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
                    'Feeder calibration history'
                  }
                >
                  <thead>
                    <tr>
                      <th>Performed</th>
                      <th>Run count</th>
                      <th>
                        Measured seconds
                      </th>
                      <th>
                        Measured grams
                      </th>
                      <th>
                        Grams / second
                      </th>
                      <th>Method</th>
                      <th>Verification</th>
                      <th>Notes</th>

                      {canManage && (
                        <th>Actions</th>
                      )}
                    </tr>
                  </thead>

                  <tbody>
                    {overview
                      .calibrations
                      .map(
                        (
                          calibration,
                        ) => (
                          <tr
                            key={
                              calibration.id
                            }
                          >
                            <td>
                              {
                                formatTimestamp(
                                  calibration
                                    .performed_at,
                                )
                              }
                            </td>

                            <td>
                              {
                                calibration
                                  .run_count
                              }
                            </td>

                            <td>
                              {
                                calibration
                                  .measured_seconds
                              }
                            </td>

                            <td>
                              {
                                calibration
                                  .measured_grams
                              }
                            </td>

                            <td>
                              {
                                calibration
                                  .grams_per_second
                              }
                            </td>

                            <td>
                              {
                                calibration
                                  .calibration_method
                              }
                            </td>

                            <td>
                              {
                                calibration
                                  .verified_by_user_id ===
                                null
                                  ? 'Unverified'
                                  : 'Verified'
                              }
                            </td>

                            <td>
                              {
                                nullableText(
                                  calibration
                                    .notes,
                                )
                              }
                            </td>

                            {canManage && (
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
                                        calibration,
                                      )
                                  }
                                >
                                  Edit calibration
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
                                      void removeCalibration(
                                        calibration,
                                      )
                                    }
                                  }
                                >
                                  Delete calibration
                                </button>
                              </td>
                            )}
                          </tr>
                        ),
                      )}
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
          Up to 50 calibration records
          per page
        </span>

        <div>
          <button
            type="button"
            className={
              'sensor-history-button'
            }
            disabled={
              !overview
                .calibrationHasPrevious ||
              overview.calibrationStatus ===
                'loading'
            }
            onClick={
              overview
                .previousCalibrationPage
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
              !overview
                .calibrationHasNext ||
              overview.calibrationStatus !==
                'ready'
            }
            onClick={
              overview
                .nextCalibrationPage
            }
          >
            Next
          </button>
        </div>
      </footer>
    </section>
  )
}