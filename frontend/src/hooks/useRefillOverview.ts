import {
  useEffect,
  useMemo,
  useState,
} from 'react'

import {
  listSystems,
} from '../services/dashboardService'

import {
  loadRefillHistoryPage,
  listSystemReservoirs,
  REFILL_HISTORY_PAGE_SIZE,
} from '../services/refillService'

import {
  listSystemTanks,
} from '../services/tankService'

import type {
  AquaponicsSystem,
} from '../types/dashboard'

import type {
  RefillEvent,
  Reservoir,
} from '../types/refill'

import type {
  Tank,
} from '../types/tank'


type LoadStatus =
  | 'loading'
  | 'ready'
  | 'error'


interface SystemResourcesState {
  systemId: string

  status: LoadStatus

  reservoirs: Reservoir[]
  tanks: Tank[]
}


interface HistoryState {
  reservoirId: string
  offset: number

  status: LoadStatus

  events: RefillEvent[]

  hasNext: boolean
}


export function useRefillOverview() {
  const [
    systems,
    setSystems,
  ] = useState<AquaponicsSystem[]>(
    [],
  )

  const [
    systemsStatus,
    setSystemsStatus,
  ] = useState<LoadStatus>(
    'loading',
  )

  const [
    selectedSystemId,
    setSelectedSystemId,
  ] = useState<string | null>(
    null,
  )

  const [
    selectedReservoirId,
    setSelectedReservoirId,
  ] = useState<string | null>(
    null,
  )

  const [
    systemResourcesState,
    setSystemResourcesState,
  ] = useState<SystemResourcesState | null>(
    null,
  )

  const [
    historyOffset,
    setHistoryOffset,
  ] = useState(
    0,
  )

  const [
    historyState,
    setHistoryState,
  ] = useState<HistoryState | null>(
    null,
  )


  // ==========================================================
  // SYSTEMS
  // ==========================================================

  useEffect(
    () => {
      let active =
        true

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

          setSelectedSystemId(
            ordered[0]?.id ??
            null,
          )

          setSystemsStatus(
            'ready',
          )
        } catch {
          if (!active) {
            return
          }

          setSystems(
            [],
          )

          setSelectedSystemId(
            null,
          )

          setSystemsStatus(
            'error',
          )
        }
      }

      void load()

      return () => {
        active =
          false
      }
    },
    [],
  )


  // ==========================================================
  // SYSTEM-SCOPED RESERVOIRS + TANKS
  // ==========================================================

  useEffect(
    () => {
      if (
        selectedSystemId ===
        null
      ) {
        return
      }

      const systemId =
        selectedSystemId

      let active =
        true

      async function load() {
        try {
          const [
            reservoirResult,
            tankResult,
          ] =
            await Promise.all([
              listSystemReservoirs(
                systemId,
              ),

              listSystemTanks(
                systemId,
              ),
            ])

          if (!active) {
            return
          }

          const reservoirs =
            [...reservoirResult].sort(
              (left, right) =>
                left.name.localeCompare(
                  right.name,
                ),
            )

          const tanks =
            [...tankResult].sort(
              (left, right) =>
                left.name.localeCompare(
                  right.name,
                ),
            )

          setSystemResourcesState({
            systemId,
            status:
              'ready',
            reservoirs,
            tanks,
          })

          setSelectedReservoirId(
            reservoirs[0]?.id ??
            null,
          )

          setHistoryOffset(
            0,
          )
        } catch {
          if (!active) {
            return
          }

          setSystemResourcesState({
            systemId,
            status:
              'error',
            reservoirs:
              [],
            tanks:
              [],
          })

          setSelectedReservoirId(
            null,
          )

          setHistoryOffset(
            0,
          )
        }
      }

      void load()

      return () => {
        active =
          false
      }
    },
    [
      selectedSystemId,
    ],
  )


  // ==========================================================
  // BOUNDED REFILL HISTORY
  // ==========================================================

  useEffect(
    () => {
      if (
        selectedReservoirId ===
        null
      ) {
        return
      }

      const reservoirId =
        selectedReservoirId

      const offset =
        historyOffset

      let active =
        true

      async function load() {
        try {
          const page =
            await loadRefillHistoryPage(
              reservoirId,
              offset,
            )

          if (!active) {
            return
          }

          setHistoryState({
            reservoirId,
            offset,

            status:
              'ready',

            events:
              page.events,

            hasNext:
              page.hasNext,
          })
        } catch {
          if (!active) {
            return
          }

          setHistoryState({
            reservoirId,
            offset,

            status:
              'error',

            events:
              [],

            hasNext:
              false,
          })
        }
      }

      void load()

      return () => {
        active =
          false
      }
    },
    [
      selectedReservoirId,
      historyOffset,
    ],
  )


  // ==========================================================
  // CURRENT SYSTEM-SCOPED DATA
  // ==========================================================

  const selectedSystem =
    systems.find(
      (system) =>
        system.id ===
        selectedSystemId,
    ) ?? null


  const resourcesAreCurrent =
    systemResourcesState?.systemId ===
    selectedSystemId


  const resourcesStatus:
    LoadStatus =
    selectedSystemId ===
      null
      ? 'ready'
      : resourcesAreCurrent
        ? systemResourcesState?.status ??
          'loading'
        : 'loading'


  const reservoirs =
    useMemo(
      () =>
        resourcesAreCurrent
          ? systemResourcesState
              ?.reservoirs ??
            []
          : [],
      [
        resourcesAreCurrent,
        systemResourcesState,
      ],
    )


  const tanks =
    useMemo(
      () =>
        resourcesAreCurrent
          ? systemResourcesState
              ?.tanks ??
            []
          : [],
      [
        resourcesAreCurrent,
        systemResourcesState,
      ],
    )


  const selectedReservoir =
    reservoirs.find(
      (reservoir) =>
        reservoir.id ===
        selectedReservoirId,
    ) ?? null


  // ==========================================================
  // CURRENT HISTORY PAGE
  // ==========================================================

  const historyIsCurrent =
    historyState?.reservoirId ===
      selectedReservoirId &&
    historyState.offset ===
      historyOffset


  const historyStatus:
    LoadStatus =
    selectedReservoirId ===
      null
      ? 'ready'
      : historyIsCurrent
        ? historyState?.status ??
          'loading'
        : 'loading'


  const refillEvents =
    historyIsCurrent
      ? historyState?.events ??
        []
      : []


  const hasNextPage =
    historyStatus ===
      'ready' &&
    historyIsCurrent &&
    (
      historyState?.hasNext ??
      false
    )


  const hasPreviousPage =
    historyStatus !==
      'loading' &&
    historyOffset >
      0


  const pageNumber =
    Math.floor(
      historyOffset /
        REFILL_HISTORY_PAGE_SIZE,
    ) + 1


  // ==========================================================
  // PUBLIC API
  // ==========================================================

  return {
    systems,
    systemsStatus,

    selectedSystemId,
    selectedSystem,

    reservoirs,
    tanks,
    resourcesStatus,

    selectedReservoirId,
    selectedReservoir,

    refillEvents,
    historyStatus,

    historyOffset,
    pageNumber,

    hasNextPage,
    hasPreviousPage,

    selectSystem(
      systemId: string,
    ) {
      if (
        systemId ===
        selectedSystemId
      ) {
        return
      }

      setSelectedSystemId(
        systemId,
      )

      setSelectedReservoirId(
        null,
      )

      setHistoryOffset(
        0,
      )
    },

    selectReservoir(
      reservoirId: string,
    ) {
      if (
        reservoirId ===
        selectedReservoirId
      ) {
        return
      }

      setSelectedReservoirId(
        reservoirId,
      )

      setHistoryOffset(
        0,
      )
    },

    nextPage() {
      if (
        historyStatus !==
          'ready' ||
        !hasNextPage
      ) {
        return
      }

      setHistoryOffset(
        (current) =>
          current +
          REFILL_HISTORY_PAGE_SIZE,
      )
    },

    previousPage() {
      if (
        historyStatus ===
          'loading' ||
        historyOffset <=
          0
      ) {
        return
      }

      setHistoryOffset(
        (current) =>
          Math.max(
            0,
            current -
              REFILL_HISTORY_PAGE_SIZE,
          ),
      )
    },
  }
}