import {
  useEffect,
  useState,
} from 'react'

import {
  loadSystemActuatorOverview,
} from '../services/actuatorService'

import {
  listSystems,
} from '../services/dashboardService'

import {
  CALIBRATION_HISTORY_PAGE_SIZE,
  createFeederCalibration,
  createFeedingSchedule,
  createFishPopulationRecord,
  deleteFeederCalibration,
  deleteFeedingSchedule,
  deleteFishPopulationRecord,
  FEEDING_HISTORY_PAGE_SIZE,
  listFeedingSchedules,
  loadFeederCalibrationHistoryPage,
  loadFeedingEventHistoryPage,
  loadFishPopulationHistoryPage,
  POPULATION_HISTORY_PAGE_SIZE,
  updateFeederCalibration,
  updateFeedingSchedule,
  updateFishPopulationRecord,
} from '../services/feedingService'

import type {
  FeederCalibrationHistoryPage,
  FeedingEventHistoryPage,
  FishPopulationHistoryPage,
} from '../services/feedingService'

import {
  listSystemTanks,
} from '../services/tankService'

import type {
  AquaponicsSystem,
  DashboardActuator,
} from '../types/dashboard'

import type {
  FeederCalibration,
  FeederCalibrationInput,
  FeederCalibrationUpdateInput,
  FeedingSchedule,
  FeedingScheduleInput,
  FeedingScheduleUpdateInput,
  FishPopulationInput,
  FishPopulationRecord,
  FishPopulationUpdateInput,
} from '../types/feeding'

import type {
  Tank,
} from '../types/tank'


type LoadStatus =
  'loading' |
  'ready' |
  'error'


type MutationStatus =
  'idle' |
  'saving' |
  'deleting' |
  'error'


interface ActuatorState {
  systemId: string
  status: LoadStatus
  actuators: DashboardActuator[]
}


interface ScheduleState {
  systemId: string
  revision: number
  status: LoadStatus
  schedules: FeedingSchedule[]
}


interface HistoryState {
  systemId: string
  offset: number
  revision: number
  status: LoadStatus
  data: FeedingEventHistoryPage | null
}


interface CalibrationState {
  actuatorId: string
  offset: number
  revision: number
  status: LoadStatus
  data: FeederCalibrationHistoryPage | null
}


interface TankState {
  systemId: string
  status: LoadStatus
  tanks: Tank[]
}


interface PopulationState {
  tankId: string
  offset: number
  revision: number
  status: LoadStatus
  data: FishPopulationHistoryPage | null
}


interface MutationState {
  systemId: string
  status: MutationStatus
  errorMessage: string | null
}


export function useFeedingOverview() {
  const [
    systems,
    setSystems,
  ] = useState<AquaponicsSystem[]>([])

  const [
    systemsStatus,
    setSystemsStatus,
  ] = useState<LoadStatus>(
    'loading',
  )

  const [
    selection,
    setSelection,
  ] = useState({
    systemId:
      null as string | null,

    offset: 0,
    revision: 0,
  })

  const [
    actuatorState,
    setActuatorState,
  ] = useState<ActuatorState | null>(
    null,
  )

  const [
    scheduleState,
    setScheduleState,
  ] = useState<ScheduleState | null>(
    null,
  )

  const [
    scheduleRevision,
    setScheduleRevision,
  ] = useState(
    0,
  )

  const [
    calibrationSelection,
    setCalibrationSelection,
  ] = useState({
    actuatorId:
      null as string | null,

    offset: 0,
  })

  const [
    calibrationRevision,
    setCalibrationRevision,
  ] = useState(
    0,
  )

  const [
    calibrationState,
    setCalibrationState,
  ] = useState<CalibrationState | null>(
    null,
  )

  const [
    tankState,
    setTankState,
  ] = useState<TankState | null>(
    null,
  )

  const [
    populationSelection,
    setPopulationSelection,
  ] = useState({
    tankId:
      null as string | null,

    offset: 0,
  })

  const [
    populationRevision,
    setPopulationRevision,
  ] = useState(
    0,
  )

  const [
    populationState,
    setPopulationState,
  ] = useState<PopulationState | null>(
    null,
  )

  const [
    historyState,
    setHistoryState,
  ] = useState<HistoryState | null>(
    null,
  )

  const [
    mutationState,
    setMutationState,
  ] = useState<MutationState | null>(
    null,
  )


  /*
   * Load systems once.
   */
  useEffect(() => {
    let active = true

    async function load() {
      try {
        const result =
          await listSystems()

        if (!active) {
          return
        }

        const ordered =
          [...result].sort(
            (left, right) =>
              left.name.localeCompare(
                right.name,
              ),
          )

        setSystems(
          ordered,
        )

        setSelection({
          systemId:
            ordered[0]?.id ?? null,

          offset: 0,
          revision: 0,
        })

        setSystemsStatus(
          'ready',
        )
      } catch {
        if (active) {
          setSystemsStatus(
            'error',
          )
        }
      }
    }

    void load()

    return () => {
      active = false
    }
  }, [])


  /*
   * Feeding only uses fish_feeder actuator records.
   * Keep the underlying actuator model for feeder calibration and
   * scheduling, but never offer circulation pumps or relays as
   * targets for feeding schedules.
   */
  useEffect(() => {
    const systemId =
      selection.systemId

    if (systemId === null) {
      return
    }

    const selectedSystemId =
      systemId

    let active = true

    async function load() {
      try {
        const result =
          await loadSystemActuatorOverview(
            selectedSystemId,
          )

        if (!active) {
          return
        }

        const orderedActuators =
          result.actuators
            .filter(
              (actuator) =>
                actuator.actuator_type ===
                'fish_feeder',
            )
            .sort(
              (left, right) =>
                left.name.localeCompare(
                  right.name,
                ),
            )

        setActuatorState({
          systemId:
            selectedSystemId,

          status:
            'ready',

          actuators:
            orderedActuators,
        })

        setCalibrationSelection({
          actuatorId:
            null,

          offset:
            0,
        })

        setCalibrationSelection(
          (current) => {
            const actuatorStillAvailable =
              orderedActuators.some(
                (actuator) =>
                  actuator.id ===
                  current.actuatorId,
              )

            if (actuatorStillAvailable) {
              return current
            }

            return {
              actuatorId:
                orderedActuators[0]?.id ??
                null,

              offset:
                0,
            }
          },
        )
      } catch {
        if (!active) {
          return
        }

        setActuatorState({
          systemId:
            selectedSystemId,

          status:
            'error',

          actuators:
            [],
        })
      }
    }

    void load()

    return () => {
      active = false
    }
  }, [
    selection.systemId,
  ])


  /*
   * Load configured, non-deleted tanks belonging
   * to the selected system.
   */
  useEffect(() => {
    const systemId =
      selection.systemId

    if (systemId === null) {
      return
    }

    const selectedSystemId =
      systemId

    let active = true

    async function load() {
      try {
        const tanks =
          await listSystemTanks(
            selectedSystemId,
          )

        if (!active) {
          return
        }

        setTankState({
          systemId:
            selectedSystemId,

          status:
            'ready',

          tanks,
        })

        setPopulationSelection(
          (current) => {
            const tankStillAvailable =
              tanks.some(
                (tank) =>
                  tank.id ===
                  current.tankId,
              )

            if (tankStillAvailable) {
              return current
            }

            return {
              tankId:
                tanks[0]?.id ??
                null,

              offset:
                0,
            }
          },
        )
      } catch {
        if (!active) {
          return
        }

        setTankState({
          systemId:
            selectedSystemId,

          status:
            'error',

          tanks:
            [],
        })

        setPopulationSelection({
          tankId:
            null,

          offset:
            0,
        })
      }
    }

    void load()

    return () => {
      active = false
    }
  }, [
    selection.systemId,
  ])


  /*
   * Schedule configuration reloads after a
   * successful create/update/delete.
   */
  useEffect(() => {
    const systemId =
      selection.systemId

    if (systemId === null) {
      return
    }

    const selectedSystemId =
      systemId

    const revision =
      scheduleRevision

    let active = true

    async function load() {
      try {
        const schedules =
          await listFeedingSchedules(
            selectedSystemId,
          )

        if (!active) {
          return
        }

        setScheduleState({
          systemId:
            selectedSystemId,

          revision,
          status:
            'ready',

          schedules,
        })
      } catch {
        if (!active) {
          return
        }

        setScheduleState({
          systemId:
            selectedSystemId,

          revision,
          status:
            'error',

          schedules:
            [],
        })
      }
    }

    void load()

    return () => {
      active = false
    }
  }, [
    selection.systemId,
    scheduleRevision,
  ])


  /*
   * Bounded persisted feeding-event history.
   */
  useEffect(() => {
    const {
      systemId,
      offset,
      revision,
    } = selection

    if (systemId === null) {
      return
    }

    const selectedSystemId =
      systemId

    let active = true

    async function load() {
      try {
        const data =
          await loadFeedingEventHistoryPage(
            selectedSystemId,
            offset,
          )

        if (!active) {
          return
        }

        setHistoryState({
          systemId:
            selectedSystemId,

          offset,
          revision,
          status:
            'ready',

          data,
        })
      } catch {
        if (!active) {
          return
        }

        setHistoryState({
          systemId:
            selectedSystemId,

          offset,
          revision,
          status:
            'error',

          data:
            null,
        })
      }
    }

    void load()

    return () => {
      active = false
    }
  }, [
    selection,
  ])


  /*
   * Bounded feeder-calibration history for the
   * selected actuator.
   */
  useEffect(() => {
    const {
      actuatorId,
      offset,
    } = calibrationSelection

    if (actuatorId === null) {
      return
    }

    const selectedActuatorId =
      actuatorId

    const revision =
      calibrationRevision

    let active = true

    async function load() {
      try {
        const data =
          await loadFeederCalibrationHistoryPage(
            selectedActuatorId,
            offset,
          )

        if (!active) {
          return
        }

        setCalibrationState({
          actuatorId:
            selectedActuatorId,

          offset,
          revision,
          status:
            'ready',

          data,
        })
      } catch {
        if (!active) {
          return
        }

        setCalibrationState({
          actuatorId:
            selectedActuatorId,

          offset,
          revision,
          status:
            'error',

          data:
            null,
        })
      }
    }

    void load()

    return () => {
      active = false
    }
  }, [
    calibrationSelection,
    calibrationRevision,
  ])


  /*
   * Bounded fish-population history for the
   * selected tank.
   */
  useEffect(() => {
    const {
      tankId,
      offset,
    } = populationSelection

    if (tankId === null) {
      return
    }

    const selectedTankId =
      tankId

    const revision =
      populationRevision

    let active = true

    async function load() {
      try {
        const data =
          await loadFishPopulationHistoryPage(
            selectedTankId,
            offset,
          )

        if (!active) {
          return
        }

        setPopulationState({
          tankId:
            selectedTankId,

          offset,
          revision,
          status:
            'ready',

          data,
        })
      } catch {
        if (!active) {
          return
        }

        setPopulationState({
          tankId:
            selectedTankId,

          offset,
          revision,
          status:
            'error',

          data:
            null,
        })
      }
    }

    void load()

    return () => {
      active = false
    }
  }, [
    populationSelection,
    populationRevision,
  ])


  const selectedSystem =
    systems.find(
      (system) =>
        system.id ===
        selection.systemId,
    ) ?? null


  const currentActuatorState =
    actuatorState?.systemId ===
    selection.systemId
      ? actuatorState
      : null


  const currentScheduleState =
    scheduleState?.systemId ===
      selection.systemId &&
    scheduleState?.revision ===
      scheduleRevision
      ? scheduleState
      : null


  const currentHistoryState =
    historyState?.systemId ===
      selection.systemId &&
    historyState?.offset ===
      selection.offset &&
    historyState?.revision ===
      selection.revision
      ? historyState
      : null


  const currentCalibrationState =
    calibrationState?.actuatorId ===
      calibrationSelection.actuatorId &&
    calibrationState?.offset ===
      calibrationSelection.offset &&
    calibrationState?.revision ===
      calibrationRevision
      ? calibrationState
      : null


  const currentTankState =
    tankState?.systemId ===
    selection.systemId
      ? tankState
      : null


  const currentPopulationState =
    populationState?.tankId ===
      populationSelection.tankId &&
    populationState?.offset ===
      populationSelection.offset &&
    populationState?.revision ===
      populationRevision
      ? populationState
      : null


  const currentMutationState =
    mutationState?.systemId ===
    selection.systemId
      ? mutationState
      : null


  const actuatorStatus =
    currentActuatorState?.status ??
    'loading'


  const calibrationStatus =
    calibrationSelection.actuatorId ===
      null &&
    actuatorStatus ===
      'ready'
      ? 'ready'
      : (
          currentCalibrationState
            ?.status ??
          'loading'
        )


  const calibrationHasNext =
    currentCalibrationState
      ?.data
      ?.hasNext ?? false


  const selectedCalibrationActuator =
    currentActuatorState
      ?.actuators
      .find(
        (actuator) =>
          actuator.id ===
          calibrationSelection.actuatorId,
      ) ?? null


  const tankStatus =
    currentTankState?.status ??
    'loading'


  const populationStatus =
    populationSelection.tankId ===
      null &&
    tankStatus ===
      'ready'
      ? 'ready'
      : (
          currentPopulationState
            ?.status ??
          'loading'
        )


  const populationHasNext =
    currentPopulationState
      ?.data
      ?.hasNext ?? false


  const selectedPopulationTank =
    currentTankState
      ?.tanks
      .find(
        (tank) =>
          tank.id ===
          populationSelection.tankId,
      ) ?? null


  const scheduleStatus =
    currentScheduleState?.status ??
    'loading'


  const historyStatus =
    currentHistoryState?.status ??
    'loading'


  const mutationStatus =
    currentMutationState?.status ??
    'idle'


  const hasNext =
    currentHistoryState
      ?.data
      ?.hasNext ?? false


  async function createSchedule(
    input: FeedingScheduleInput,
  ): Promise<FeedingSchedule> {
    const systemId =
      selection.systemId

    if (systemId === null) {
      throw new Error(
        'No aquaponics system selected.',
      )
    }

    setMutationState({
      systemId,
      status:
        'saving',

      errorMessage:
        null,
    })

    try {
      const schedule =
        await createFeedingSchedule(
          systemId,
          input,
        )

      setScheduleRevision(
        (current) =>
          current + 1,
      )

      setMutationState(
        null,
      )

      return schedule
    } catch (error) {
      setMutationState({
        systemId,
        status:
          'error',

        errorMessage:
          'Unable to create feeding schedule.',
      })

      throw error
    }
  }


  async function updateSchedule(
    scheduleId: string,
    input: FeedingScheduleUpdateInput,
  ): Promise<FeedingSchedule> {
    const systemId =
      selection.systemId

    if (systemId === null) {
      throw new Error(
        'No aquaponics system selected.',
      )
    }

    setMutationState({
      systemId,
      status:
        'saving',

      errorMessage:
        null,
    })

    try {
      const schedule =
        await updateFeedingSchedule(
          scheduleId,
          input,
        )

      setScheduleRevision(
        (current) =>
          current + 1,
      )

      setMutationState(
        null,
      )

      return schedule
    } catch (error) {
      setMutationState({
        systemId,
        status:
          'error',

        errorMessage:
          'Unable to update feeding schedule.',
      })

      throw error
    }
  }


  async function deleteSchedule(
    scheduleId: string,
  ): Promise<void> {
    const systemId =
      selection.systemId

    if (systemId === null) {
      throw new Error(
        'No aquaponics system selected.',
      )
    }

    setMutationState({
      systemId,
      status:
        'deleting',

      errorMessage:
        null,
    })

    try {
      await deleteFeedingSchedule(
        scheduleId,
      )

      setScheduleRevision(
        (current) =>
          current + 1,
      )

      setMutationState(
        null,
      )
    } catch (error) {
      setMutationState({
        systemId,
        status:
          'error',

        errorMessage:
          'Unable to delete feeding schedule.',
      })

      throw error
    }
  }


  async function createCalibration(
    input: FeederCalibrationInput,
  ): Promise<FeederCalibration> {
    const systemId =
      selection.systemId

    const actuatorId =
      calibrationSelection.actuatorId

    if (
      systemId === null ||
      actuatorId === null
    ) {
      throw new Error(
        'No actuator selected for calibration.',
      )
    }

    setMutationState({
      systemId,
      status:
        'saving',

      errorMessage:
        null,
    })

    try {
      const calibration =
        await createFeederCalibration(
          actuatorId,
          input,
        )

      setCalibrationRevision(
        (current) =>
          current + 1,
      )

      setMutationState(
        null,
      )

      return calibration
    } catch (error) {
      setMutationState({
        systemId,
        status:
          'error',

        errorMessage:
          'Unable to create feeder calibration.',
      })

      throw error
    }
  }


  async function updateCalibration(
    calibrationId: string,
    input: FeederCalibrationUpdateInput,
  ): Promise<FeederCalibration> {
    const systemId =
      selection.systemId

    if (systemId === null) {
      throw new Error(
        'No aquaponics system selected.',
      )
    }

    setMutationState({
      systemId,
      status:
        'saving',

      errorMessage:
        null,
    })

    try {
      const calibration =
        await updateFeederCalibration(
          calibrationId,
          input,
        )

      setCalibrationRevision(
        (current) =>
          current + 1,
      )

      setMutationState(
        null,
      )

      return calibration
    } catch (error) {
      setMutationState({
        systemId,
        status:
          'error',

        errorMessage:
          'Unable to update feeder calibration.',
      })

      throw error
    }
  }


  async function deleteCalibration(
    calibrationId: string,
  ): Promise<void> {
    const systemId =
      selection.systemId

    if (systemId === null) {
      throw new Error(
        'No aquaponics system selected.',
      )
    }

    setMutationState({
      systemId,
      status:
        'deleting',

      errorMessage:
        null,
    })

    try {
      await deleteFeederCalibration(
        calibrationId,
      )

      setCalibrationRevision(
        (current) =>
          current + 1,
      )

      setMutationState(
        null,
      )
    } catch (error) {
      setMutationState({
        systemId,
        status:
          'error',

        errorMessage:
          'Unable to delete feeder calibration.',
      })

      throw error
    }
  }


  async function createPopulationRecord(
    input: FishPopulationInput,
  ): Promise<FishPopulationRecord> {
    const systemId =
      selection.systemId

    const tankId =
      populationSelection.tankId

    if (
      systemId === null ||
      tankId === null
    ) {
      throw new Error(
        'No tank selected for fish population.',
      )
    }

    setMutationState({
      systemId,
      status:
        'saving',

      errorMessage:
        null,
    })

    try {
      const record =
        await createFishPopulationRecord(
          tankId,
          input,
        )

      setPopulationRevision(
        (current) =>
          current + 1,
      )

      setMutationState(
        null,
      )

      return record
    } catch (error) {
      setMutationState({
        systemId,
        status:
          'error',

        errorMessage:
          'Unable to create fish population record.',
      })

      throw error
    }
  }


  async function updatePopulationRecord(
    recordId: string,
    input: FishPopulationUpdateInput,
  ): Promise<FishPopulationRecord> {
    const systemId =
      selection.systemId

    if (systemId === null) {
      throw new Error(
        'No aquaponics system selected.',
      )
    }

    setMutationState({
      systemId,
      status:
        'saving',

      errorMessage:
        null,
    })

    try {
      const record =
        await updateFishPopulationRecord(
          recordId,
          input,
        )

      setPopulationRevision(
        (current) =>
          current + 1,
      )

      setMutationState(
        null,
      )

      return record
    } catch (error) {
      setMutationState({
        systemId,
        status:
          'error',

        errorMessage:
          'Unable to update fish population record.',
      })

      throw error
    }
  }


  async function deletePopulationRecord(
    recordId: string,
  ): Promise<void> {
    const systemId =
      selection.systemId

    if (systemId === null) {
      throw new Error(
        'No aquaponics system selected.',
      )
    }

    setMutationState({
      systemId,
      status:
        'deleting',

      errorMessage:
        null,
    })

    try {
      await deleteFishPopulationRecord(
        recordId,
      )

      setPopulationRevision(
        (current) =>
          current + 1,
      )

      setMutationState(
        null,
      )
    } catch (error) {
      setMutationState({
        systemId,
        status:
          'error',

        errorMessage:
          'Unable to delete fish population record.',
      })

      throw error
    }
  }


  return {
    systems,
    systemsStatus,

    selectedSystemId:
      selection.systemId,

    selectedSystem,

    actuators:
      currentActuatorState
        ?.actuators ?? [],

    actuatorStatus,

    selectedCalibrationActuatorId:
      calibrationSelection.actuatorId,

    selectedCalibrationActuator,

    calibrations:
      currentCalibrationState
        ?.data
        ?.calibrations ?? [],

    calibrationStatus,

    calibrationHasNext,

    calibrationHasPrevious:
      calibrationSelection.offset > 0,

    calibrationPageNumber:
      Math.floor(
        calibrationSelection.offset /
          CALIBRATION_HISTORY_PAGE_SIZE,
      ) + 1,

    tanks:
      currentTankState
        ?.tanks ?? [],

    tankStatus,

    selectedPopulationTankId:
      populationSelection.tankId,

    selectedPopulationTank,

    populationRecords:
      currentPopulationState
        ?.data
        ?.records ?? [],

    populationStatus,

    populationHasNext,

    populationHasPrevious:
      populationSelection.offset > 0,

    populationPageNumber:
      Math.floor(
        populationSelection.offset /
          POPULATION_HISTORY_PAGE_SIZE,
      ) + 1,

    schedules:
      currentScheduleState
        ?.schedules ?? [],

    scheduleStatus,

    events:
      currentHistoryState
        ?.data
        ?.events ?? [],

    historyStatus,

    mutationStatus,

    mutationError:
      currentMutationState
        ?.errorMessage ?? null,

    isMutating:
      mutationStatus ===
        'saving' ||
      mutationStatus ===
        'deleting',

    hasNext,

    hasPrevious:
      selection.offset > 0,

    pageNumber:
      Math.floor(
        selection.offset /
          FEEDING_HISTORY_PAGE_SIZE,
      ) + 1,

    createSchedule,
    updateSchedule,
    deleteSchedule,

    createCalibration,
    updateCalibration,
    deleteCalibration,

    createPopulationRecord,
    updatePopulationRecord,
    deletePopulationRecord,


    selectSystem(
      systemId: string,
    ) {
      if (
        !systems.some(
          (system) =>
            system.id ===
            systemId,
        )
      ) {
        return
      }

      setMutationState(
        null,
      )

      setCalibrationSelection({
        actuatorId:
          null,

        offset:
          0,
      })

      setPopulationSelection({
        tankId:
          null,

        offset:
          0,
      })

      setSelection(
        (current) => {
          if (
            current.systemId ===
            systemId
          ) {
            return current
          }

          return {
            systemId,
            offset:
              0,

            revision:
              current.revision + 1,
          }
        },
      )
    },


    selectCalibrationActuator(
      actuatorId: string,
    ) {
      if (
        !currentActuatorState
          ?.actuators
          .some(
            (actuator) =>
              actuator.id ===
              actuatorId,
          )
      ) {
        return
      }

      setMutationState(
        null,
      )

      setCalibrationSelection(
        (current) => {
          if (
            current.actuatorId ===
            actuatorId
          ) {
            return current
          }

          return {
            actuatorId,
            offset:
              0,
          }
        },
      )
    },


    nextCalibrationPage() {
      if (
        calibrationStatus !==
          'ready' ||
        !calibrationHasNext
      ) {
        return
      }

      setCalibrationSelection(
        (current) => ({
          ...current,

          offset:
            current.offset +
            CALIBRATION_HISTORY_PAGE_SIZE,
        }),
      )
    },


    previousCalibrationPage() {
      if (
        calibrationStatus ===
          'loading' ||
        calibrationSelection.offset ===
          0
      ) {
        return
      }

      setCalibrationSelection(
        (current) => ({
          ...current,

          offset:
            Math.max(
              0,
              current.offset -
                CALIBRATION_HISTORY_PAGE_SIZE,
            ),
        }),
      )
    },


    selectPopulationTank(
      tankId: string,
    ) {
      if (
        !currentTankState
          ?.tanks
          .some(
            (tank) =>
              tank.id ===
              tankId,
          )
      ) {
        return
      }

      setMutationState(
        null,
      )

      setPopulationSelection(
        (current) => {
          if (
            current.tankId ===
            tankId
          ) {
            return current
          }

          return {
            tankId,
            offset:
              0,
          }
        },
      )
    },


    nextPopulationPage() {
      if (
        populationStatus !==
          'ready' ||
        !populationHasNext
      ) {
        return
      }

      setPopulationSelection(
        (current) => ({
          ...current,

          offset:
            current.offset +
            POPULATION_HISTORY_PAGE_SIZE,
        }),
      )
    },


    previousPopulationPage() {
      if (
        populationStatus ===
          'loading' ||
        populationSelection.offset ===
          0
      ) {
        return
      }

      setPopulationSelection(
        (current) => ({
          ...current,

          offset:
            Math.max(
              0,
              current.offset -
                POPULATION_HISTORY_PAGE_SIZE,
            ),
        }),
      )
    },


    nextPage() {
      if (
        historyStatus !==
          'ready' ||
        !hasNext
      ) {
        return
      }

      setSelection(
        (current) => ({
          ...current,

          offset:
            current.offset +
            FEEDING_HISTORY_PAGE_SIZE,

          revision:
            current.revision + 1,
        }),
      )
    },


    previousPage() {
      if (
        historyStatus ===
          'loading' ||
        selection.offset ===
          0
      ) {
        return
      }

      setSelection(
        (current) => ({
          ...current,

          offset:
            Math.max(
              0,
              current.offset -
                FEEDING_HISTORY_PAGE_SIZE,
            ),

          revision:
            current.revision + 1,
        }),
      )
    },
  }
}