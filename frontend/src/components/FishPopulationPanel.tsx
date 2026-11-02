import {
  useState,
} from 'react'

import {
  useFeedingOverview,
} from '../hooks/useFeedingOverview'

import type {
  FishPopulationInput,
  FishPopulationRecord,
  FishPopulationUpdateInput,
} from '../types/feeding'


type FeedingOverview =
  ReturnType<typeof useFeedingOverview>


interface FishPopulationPanelProps {
  overview: FeedingOverview
  canEdit: boolean
  canDelete: boolean
}


interface PopulationDraft {
  species: string
  count: string
  estimatedBiomassGrams: string
  effectiveAt: string
  notes: string
}


interface PopulationEditor {
  mode: 'create' | 'edit'
  recordId: string | null
  original: FishPopulationRecord | null
  draft: PopulationDraft
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


function nullableNumber(
  value: number | null,
): string {
  return value === null
    ? 'Not recorded'
    : String(value)
}


export function FishPopulationPanel({
  overview,
  canEdit,
  canDelete,
}: FishPopulationPanelProps) {
  const [
    editor,
    setEditor,
  ] = useState<PopulationEditor | null>(
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
        .selectedPopulationTankId ===
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

      recordId:
        null,

      original:
        null,

      draft: {
        species:
          overview
            .selectedPopulationTank
            ?.species ??
          '',

        count:
          '',

        estimatedBiomassGrams:
          '',

        effectiveAt:
          currentDateTimeLocal(),

        notes:
          '',
      },
    })
  }


  function openEditEditor(
    record: FishPopulationRecord,
  ) {
    setFormError(
      null,
    )

    setEditor({
      mode:
        'edit',

      recordId:
        record.id,

      original:
        record,

      draft: {
        species:
          record.species,

        count:
          String(
            record.count,
          ),

        estimatedBiomassGrams:
          record
            .estimated_biomass_grams ===
          null
            ? ''
            : String(
                record
                  .estimated_biomass_grams,
              ),

        effectiveAt:
          toDateTimeLocal(
            record.effective_at,
          ),

        notes:
          record.notes ??
          '',
      },
    })
  }


  function updateDraft(
    update:
      Partial<PopulationDraft>,
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

    const species =
      editor
        .draft
        .species
        .trim()

    const countText =
      editor
        .draft
        .count
        .trim()

    const count =
      Number(
        countText,
      )

    const biomassText =
      editor
        .draft
        .estimatedBiomassGrams
        .trim()

    let estimatedBiomassGrams:
      number | null =
      null

    const effectiveAt =
      toIsoTimestamp(
        editor
          .draft
          .effectiveAt,
      )

    const notes =
      editor
        .draft
        .notes
        .trim()


    if (
      species.length ===
      0
    ) {
      setFormError(
        'Species is required.',
      )

      return
    }


    if (
      species.length >
      150
    ) {
      setFormError(
        'Species must be 150 characters or fewer.',
      )

      return
    }


    if (
      countText.length ===
        0 ||
      !Number.isInteger(
        count,
      ) ||
      count < 0
    ) {
      setFormError(
        'Count must be a whole number of zero or greater.',
      )

      return
    }


    if (
      biomassText.length >
      0
    ) {
      const parsedBiomass =
        Number(
          biomassText,
        )

      if (
        !Number.isFinite(
          parsedBiomass,
        ) ||
        parsedBiomass < 0
      ) {
        setFormError(
          'Estimated biomass must be zero or greater when recorded.',
        )

        return
      }

      estimatedBiomassGrams =
        parsedBiomass
    }


    if (
      effectiveAt ===
      null
    ) {
      setFormError(
        'A valid effective date and time is required.',
      )

      return
    }


    const normalizedNotes =
      notes.length ===
      0
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
          FishPopulationInput = {
            species,

            count,

            estimated_biomass_grams:
              estimatedBiomassGrams,

            effective_at:
              effectiveAt,

            notes:
              normalizedNotes,
          }

        await overview
          .createPopulationRecord(
            input,
          )

        setEditor(
          null,
        )

        return
      }


      const original =
        editor.original

      const recordId =
        editor.recordId

      if (
        original === null ||
        recordId === null
      ) {
        return
      }


      const update:
        FishPopulationUpdateInput =
        {}


      if (
        species !==
        original.species
      ) {
        update.species =
          species
      }


      if (
        count !==
        original.count
      ) {
        update.count =
          count
      }


      if (
        estimatedBiomassGrams !==
        original
          .estimated_biomass_grams
      ) {
        update.estimated_biomass_grams =
          estimatedBiomassGrams
      }


      const originalEffectiveAt =
        new Date(
          original.effective_at,
        ).toISOString()

      if (
        effectiveAt !==
        originalEffectiveAt
      ) {
        update.effective_at =
          effectiveAt
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


      await overview
        .updatePopulationRecord(
          recordId,
          update,
        )

      setEditor(
        null,
      )
    } catch {
      /*
       * The overview hook owns the
       * authoritative API mutation error.
       */
    }
  }


  async function removePopulationRecord(
    record: FishPopulationRecord,
  ) {
    const confirmed =
      window.confirm(
        'Delete this fish population record?\n\n' +
        'This removes the persisted application record. ' +
        'It does not add or remove fish, undo a physical ' +
        'population change, or prove that a physical count ' +
        'or biomass measurement occurred.',
      )

    if (
      !confirmed
    ) {
      return
    }

    try {
      await overview
        .deletePopulationRecord(
          record.id,
        )

      if (
        editor?.recordId ===
        record.id
      ) {
        setEditor(
          null,
        )
      }
    } catch {
      /*
       * The overview hook owns the
       * authoritative API mutation error.
       */
    }
  }


  return (
    <section
      className="sensor-detail-panel"
      aria-labelledby={
        'fish-population-heading'
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
              'fish-population-heading'
            }
          >
            Fish population
          </h2>

          <p>
            Persisted population records for
            the selected tank.
          </p>
        </div>

        <span
          className={
            'sensor-detail-history-page'
          }
        >
          Page {
            overview
              .populationPageNumber
          }
        </span>
      </div>


      <p
        className={
          'actuator-hardware-note'
        }
      >
        Fish population records are persisted
        application data. They describe recorded
        counts and biomass estimates, but do not
        by themselves prove that a physical fish
        count or biomass measurement occurred.
      </p>


      {overview.tankStatus ===
        'loading' && (
        <div role="status">
          Loading tanks...
        </div>
      )}


      {overview.tankStatus ===
        'error' && (
        <div
          role="alert"
          className={
            'status-message ' +
            'status-message--error'
          }
        >
          Unable to load tanks for fish
          population management.
        </div>
      )}


      {overview.tankStatus ===
        'ready' &&
        overview.tanks.length ===
          0 && (
        <p>
          No configured tank is available
          for fish population records.
        </p>
      )}


      {overview.tanks.length >
        0 && (
        <div
          className="system-selector"
        >
          <label
            htmlFor={
              'fish-population-tank'
            }
          >
            Population tank
          </label>

          <select
            id={
              'fish-population-tank'
            }
            value={
              overview
                .selectedPopulationTankId ??
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
                  .selectPopulationTank(
                    event.target.value,
                  )
              }
            }
          >
            {overview.tanks.map(
              (tank) => (
                <option
                  key={
                    tank.id
                  }
                  value={
                    tank.id
                  }
                >
                  {tank.name}
                </option>
              ),
            )}
          </select>
        </div>
      )}


      {overview
        .selectedPopulationTank !==
        null && (
        <p>
          Selected tank:{' '}
          <strong>
            {
              overview
                .selectedPopulationTank
                .name
            }
          </strong>
        </p>
      )}


      {canEdit &&
        overview
          .selectedPopulationTankId !==
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
          Add population record
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
              ? 'Add fish population record'
              : 'Edit fish population record'}
          </h3>


          <div
            className="system-selector"
          >
            <label
              htmlFor={
                'population-species'
              }
            >
              Species
            </label>

            <input
              id={
                'population-species'
              }
              maxLength={
                150
              }
              value={
                editor
                  .draft
                  .species
              }
              disabled={
                overview.isMutating
              }
              onChange={
                (event) =>
                  updateDraft({
                    species:
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
                'population-count'
              }
            >
              Count
            </label>

            <input
              id={
                'population-count'
              }
              type="number"
              min="0"
              step="1"
              value={
                editor
                  .draft
                  .count
              }
              disabled={
                overview.isMutating
              }
              onChange={
                (event) =>
                  updateDraft({
                    count:
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
                'population-biomass'
              }
            >
              Estimated biomass (grams)
            </label>

            <input
              id={
                'population-biomass'
              }
              type="number"
              min="0"
              step="any"
              value={
                editor
                  .draft
                  .estimatedBiomassGrams
              }
              disabled={
                overview.isMutating
              }
              onChange={
                (event) =>
                  updateDraft({
                    estimatedBiomassGrams:
                      event.target.value,
                  })
              }
            />

            <small>
              Optional. Leave blank when no
              biomass estimate was recorded.
            </small>
          </div>


          <div
            className="system-selector"
          >
            <label
              htmlFor={
                'population-effective-at'
              }
            >
              Effective at
            </label>

            <input
              id={
                'population-effective-at'
              }
              type="datetime-local"
              value={
                editor
                  .draft
                  .effectiveAt
              }
              disabled={
                overview.isMutating
              }
              onChange={
                (event) =>
                  updateDraft({
                    effectiveAt:
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
                'population-notes'
              }
            >
              Notes
            </label>

            <input
              id={
                'population-notes'
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


          <small>
            Recorder provenance is attributed
            by the backend to the authenticated
            user when the record is created.
            Editing does not allow selecting or
            replacing the original recorder.
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
                : 'Save population record'}
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


      {overview.populationStatus ===
        'loading' && (
        <div role="status">
          Loading fish population
          history...
        </div>
      )}


      {overview.populationStatus ===
        'error' && (
        <div
          role="alert"
          className={
            'status-message ' +
            'status-message--error'
          }
        >
          Unable to load fish population
          history.
        </div>
      )}


      {overview.populationStatus ===
        'ready' &&
        overview
          .selectedPopulationTankId !==
          null &&
        (
          overview
            .populationRecords
            .length ===
          0
            ? (
              <p>
                No persisted fish population
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
                    'Fish population history'
                  }
                >
                  <thead>
                    <tr>
                      <th>
                        Effective
                      </th>

                      <th>
                        Species
                      </th>

                      <th>
                        Count
                      </th>

                      <th>
                        Estimated biomass
                        (grams)
                      </th>

                      <th>
                        Recorded by
                      </th>

                      <th>
                        Notes
                      </th>

                      {(canEdit ||
                        canDelete) && (
                        <th>
                          Actions
                        </th>
                      )}
                    </tr>
                  </thead>

                  <tbody>
                    {overview
                      .populationRecords
                      .map(
                        (record) => (
                          <tr
                            key={
                              record.id
                            }
                          >
                            <td>
                              {
                                formatTimestamp(
                                  record
                                    .effective_at,
                                )
                              }
                            </td>

                            <td>
                              {
                                record.species
                              }
                            </td>

                            <td>
                              {
                                record.count
                              }
                            </td>

                            <td>
                              {
                                nullableNumber(
                                  record
                                    .estimated_biomass_grams,
                                )
                              }
                            </td>

                            <td>
                              {
                                nullableText(
                                  record
                                    .recorded_by_user_id,
                                )
                              }
                            </td>

                            <td>
                              {
                                nullableText(
                                  record.notes,
                                )
                              }
                            </td>

                            {(canEdit ||
                              canDelete) && (
                              <td>
                                {canEdit && (
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
                                          record,
                                        )
                                    }
                                  >
                                    Edit population
                                    record
                                  </button>
                                )}

                                {canDelete && (
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
                                        void removePopulationRecord(
                                          record,
                                        )
                                      }
                                    }
                                  >
                                    Delete population
                                    record
                                  </button>
                                )}
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
          Up to 50 population records
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
                .populationHasPrevious ||
              overview.populationStatus ===
                'loading'
            }
            onClick={
              overview
                .previousPopulationPage
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
                .populationHasNext ||
              overview.populationStatus !==
                'ready'
            }
            onClick={
              overview
                .nextPopulationPage
            }
          >
            Next
          </button>
        </div>
      </footer>
    </section>
  )
}