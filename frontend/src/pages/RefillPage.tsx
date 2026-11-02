import {
  useRefillOverview,
} from '../hooks/useRefillOverview'


export function RefillPage() {
  const overview =
    useRefillOverview()


  const targetTankName =
    (tankId: string) =>
      overview.tanks.find(
        (tank) =>
          tank.id === tankId,
      )?.name ??
      tankId


  return (
    <section
      className="section-page refill-page"
    >
      <div
        className="page-heading-row"
      >
        <div>
          <p
            className="eyebrow"
          >
            Water management
          </p>

          <h1>
            Refill history
          </h1>

          <p
            className="page-description"
          >
            Review persisted refill runtime activity
            for each reservoir.
          </p>
        </div>


        <label
          className="select-field"
        >
          <span>
            Aquaponics system
          </span>

          <select
            value={
              overview.selectedSystemId ??
              ''
            }
            disabled={
              overview.systemsStatus !==
              'ready'
            }
            onChange={
              (event) =>
                overview.selectSystem(
                  event.target.value,
                )
            }
          >
            {
              overview.systems.map(
                (system) => (
                  <option
                    key={
                      system.id
                    }
                    value={
                      system.id
                    }
                  >
                    {system.name}
                  </option>
                ),
              )
            }
          </select>
        </label>
      </div>


      {
        overview.systemsStatus ===
          'loading' && (
          <p
            className="status-message"
          >
            Loading aquaponics systems…
          </p>
        )
      }


      {
        overview.systemsStatus ===
          'error' && (
          <p
            className="status-message status-message--error"
            role="alert"
          >
            Unable to load aquaponics systems.
          </p>
        )
      }


      {
        overview.systemsStatus ===
          'ready' &&
        overview.systems.length ===
          0 && (
          <div
            className="empty-state"
          >
            No aquaponics system configured
          </div>
        )
      }


      {
        overview.selectedSystem !==
          null && (
          <>
            <section
              className="surface-panel"
            >
              <div>
                <p
                  className="eyebrow"
                >
                  Reservoir
                </p>

                <h2>
                  Refill activity
                </h2>

                <p
                  className="page-description"
                >
                  These are persisted refill runtime
                  records. They do not establish that
                  physical hardware executed a refill.
                </p>
              </div>


              {
                overview.resourcesStatus ===
                  'loading' && (
                  <p
                    className="status-message"
                  >
                    Loading reservoirs…
                  </p>
                )
              }


              {
                overview.resourcesStatus ===
                  'error' && (
                  <p
                    className="status-message status-message--error"
                    role="alert"
                  >
                    Unable to load refill resources.
                  </p>
                )
              }


              {
                overview.resourcesStatus ===
                  'ready' &&
                overview.reservoirs.length ===
                  0 && (
                  <div
                    className="empty-state"
                  >
                    No reservoirs configured
                  </div>
                )
              }


              {
                overview.reservoirs.length >
                  0 && (
                  <label
                    className="select-field"
                  >
                    <span>
                      Reservoir
                    </span>

                    <select
                      value={
                        overview
                          .selectedReservoirId ??
                        ''
                      }
                      disabled={
                        overview.resourcesStatus !==
                        'ready'
                      }
                      onChange={
                        (event) =>
                          overview.selectReservoir(
                            event.target.value,
                          )
                      }
                    >
                      {
                        overview.reservoirs.map(
                          (reservoir) => (
                            <option
                              key={
                                reservoir.id
                              }
                              value={
                                reservoir.id
                              }
                            >
                              {
                                reservoir.name
                              }
                            </option>
                          ),
                        )
                      }
                    </select>
                  </label>
                )
              }


              {
                overview.selectedReservoir !==
                  null && (
                  <div>
                    <p>
                      Capacity:{' '}
                      {
                        overview
                          .selectedReservoir
                          .capacity_liters
                      }{' '}
                      L
                    </p>

                    <p>
                      Status:{' '}
                      {
                        overview
                          .selectedReservoir
                          .is_active
                          ? 'Active'
                          : 'Inactive'
                      }
                    </p>
                  </div>
                )
              }
            </section>


            {
              overview.selectedReservoir !==
                null && (
                <>
                  {
                    overview.historyStatus ===
                      'loading' && (
                      <p
                        className="status-message"
                      >
                        Loading refill history…
                      </p>
                    )
                  }


                  {
                    overview.historyStatus ===
                      'error' && (
                      <p
                        className="status-message status-message--error"
                        role="alert"
                      >
                        Unable to load refill history.
                      </p>
                    )
                  }


                  {
                    overview.historyStatus ===
                      'ready' &&
                    overview.refillEvents.length ===
                      0 && (
                      <div
                        className="empty-state"
                      >
                        No refill events recorded for
                        this reservoir.
                      </div>
                    )
                  }


                  {
                    overview.refillEvents.map(
                      (event) => (
                        <article
                          key={
                            event.id
                          }
                          className="surface-panel"
                        >
                          <div>
                            <p
                              className="eyebrow"
                            >
                              {
                                event.status
                              }
                            </p>

                            <h3>
                              Refill event
                            </h3>

                            <p>
                              Event ID:{' '}
                              {event.id}
                            </p>

                            <p>
                              Target tank:{' '}
                              {
                                targetTankName(
                                  event
                                    .target_tank_id,
                                )
                              }
                            </p>

                            <p>
                              Trigger:{' '}
                              {
                                event.trigger
                              }
                            </p>

                            <p>
                              Start level:{' '}
                              {
                                event
                                  .start_level_percent
                              }
                              %
                            </p>

                            <p>
                              End level:{' '}
                              {
                                event
                                  .end_level_percent
                              }
                              %
                            </p>

                            <p>
                              Started:{' '}
                              {
                                event.started_at
                              }
                            </p>

                            <p>
                              Completed:{' '}
                              {
                                event
                                  .completed_at ??
                                'Not recorded'
                              }
                            </p>

                            <p>
                              Duration:{' '}
                              {
                                event
                                  .duration_seconds ===
                                null
                                  ? 'Not recorded'
                                  : (
                                      `${event.duration_seconds} s`
                                    )
                              }
                            </p>

                            <p>
                              Timeout reason:{' '}
                              {
                                event
                                  .timeout_reason ??
                                'Not recorded'
                              }
                            </p>

                            <p>
                              Created:{' '}
                              {
                                event.created_at
                              }
                            </p>
                          </div>
                        </article>
                      ),
                    )
                  }


                  {
                    overview.historyStatus ===
                      'ready' && (
                      <div
                        className="data-pagination"
                      >
                        <span>
                          Page{' '}
                          {
                            overview.pageNumber
                          }
                        </span>

                        <div
                          className="data-pagination__actions"
                        >
                          <button
                            type="button"
                            className="secondary-button"
                            disabled={
                              !overview
                                .hasPreviousPage
                            }
                            onClick={
                              overview.previousPage
                            }
                          >
                            Previous
                          </button>

                          <button
                            type="button"
                            className="secondary-button"
                            disabled={
                              !overview
                                .hasNextPage
                            }
                            onClick={
                              overview.nextPage
                            }
                          >
                            Next
                          </button>
                        </div>
                      </div>
                    )
                  }
                </>
              )
            }
          </>
        )
      }
    </section>
  )
}