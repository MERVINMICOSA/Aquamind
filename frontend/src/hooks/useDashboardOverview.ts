import {
  useEffect,
  useMemo,
  useState,
} from 'react'

import {
  listSystems,
  loadSystemDashboardOverview,
} from '../services/dashboardService'

import type {
  AquaponicsSystem,
  DashboardActuator,
  DashboardAlert,
  DashboardSensor,
  DashboardSensorReading,
} from '../types/dashboard'


type LoadStatus =
  | 'idle'
  | 'loading'
  | 'ready'
  | 'error'


export function useDashboardOverview() {
  const [
    systems,
    setSystems,
  ] = useState<AquaponicsSystem[]>(
    [],
  )

  const [
    selectedSystemId,
    setSelectedSystemId,
  ] = useState<string | null>(
    null,
  )

  const [
    sensors,
    setSensors,
  ] = useState<DashboardSensor[]>(
    [],
  )

  const [
    actuators,
    setActuators,
  ] = useState<DashboardActuator[]>(
    [],
  )

  const [
    alerts,
    setAlerts,
  ] = useState<DashboardAlert[]>(
    [],
  )

  const [
    latestReadings,
    setLatestReadings,
  ] = useState<DashboardSensorReading[]>(
    [],
  )

  const [
    systemsStatus,
    setSystemsStatus,
  ] = useState<LoadStatus>(
    'loading',
  )

  const [
    overviewStatus,
    setOverviewStatus,
  ] = useState<LoadStatus>(
    'idle',
  )

  const [
    errorMessage,
    setErrorMessage,
  ] = useState<string | null>(
    null,
  )


  // =========================================================
  // SYSTEMS
  // =========================================================

  useEffect(() => {
    let active = true


    async function loadSystems():
      Promise<void> {
      try {
        setSystemsStatus(
          'loading',
        )

        const result =
          await listSystems()

        if (!active) {
          return
        }

        const orderedSystems =
          [...result].sort(
            (left, right) =>
              left.name.localeCompare(
                right.name,
              ),
          )

        setSystems(
          orderedSystems,
        )

        setSelectedSystemId(
          (current) => {
            if (
              current !== null &&
              orderedSystems.some(
                (system) =>
                  system.id ===
                  current,
              )
            ) {
              return current
            }

            return (
              orderedSystems[0]?.id ??
              null
            )
          },
        )

        if (
          orderedSystems.length === 0
        ) {
          setSensors(
            [],
          )

          setActuators(
            [],
          )

          setAlerts(
            [],
          )

          setLatestReadings(
            [],
          )

          setOverviewStatus(
            'idle',
          )
        }

        setErrorMessage(
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

        setSensors(
          [],
        )

        setActuators(
          [],
        )

        setAlerts(
          [],
        )

        setLatestReadings(
          [],
        )

        setOverviewStatus(
          'idle',
        )

        setErrorMessage(
          'Unable to load AquaMind systems.',
        )

        setSystemsStatus(
          'error',
        )
      }
    }


    void loadSystems()


    return () => {
      active = false
    }
  }, [])


  // =========================================================
  // SELECTED SYSTEM OVERVIEW
  // =========================================================

  useEffect(() => {
    if (selectedSystemId === null) {
      return
    }

    /*
     * Capture the already-narrowed value before entering
     * the asynchronous function.
     */
    const systemId =
      selectedSystemId

    let active = true


    async function loadOverview():
      Promise<void> {
      try {
        setOverviewStatus(
          'loading',
        )

        const result =
          await loadSystemDashboardOverview(
            systemId,
          )

        if (!active) {
          return
        }

        setSensors(
          result.sensors,
        )

        setActuators(
          result.actuators,
        )

        setAlerts(
          result.alerts,
        )

        setLatestReadings(
          result.latestReadings,
        )

        setErrorMessage(
          null,
        )

        setOverviewStatus(
          'ready',
        )
      } catch {
        if (!active) {
          return
        }

        setSensors(
          [],
        )

        setActuators(
          [],
        )

        setAlerts(
          [],
        )

        setLatestReadings(
          [],
        )

        setErrorMessage(
          'Unable to load the selected system overview.',
        )

        setOverviewStatus(
          'error',
        )
      }
    }


    void loadOverview()


    return () => {
      active = false
    }
  }, [
    selectedSystemId,
  ])


  // =========================================================
  // SELECTED SYSTEM
  // =========================================================

  const selectedSystem =
    useMemo(
      () =>
        systems.find(
          (system) =>
            system.id ===
            selectedSystemId,
        ) ?? null,
      [
        systems,
        selectedSystemId,
      ],
    )


  // =========================================================
  // PUBLIC HOOK API
  // =========================================================

  return {
    systems,
    selectedSystem,
    selectedSystemId,

    sensors,
    actuators,
    alerts,
    latestReadings,

    systemsStatus,
    overviewStatus,
    errorMessage,

    selectSystem:
      setSelectedSystemId,
  }
}