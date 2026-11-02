import {
  useEffect,
  useMemo,
  useState,
} from 'react'

import {
  listSystems,
} from '../services/dashboardService'

import {
  loadSystemSensorOverview,
} from '../services/sensorService'

import type {
  AquaponicsSystem,
  DashboardSensor,
  DashboardSensorReading,
} from '../types/dashboard'


type LoadStatus =
  | 'idle'
  | 'loading'
  | 'ready'
  | 'error'


export function useSensorsOverview() {
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
    sensorsStatus,
    setSensorsStatus,
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


    async function loadAvailableSystems():
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
                  system.id === current,
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

          setLatestReadings(
            [],
          )

          setSensorsStatus(
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

        setLatestReadings(
          [],
        )

        setSensorsStatus(
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


    void loadAvailableSystems()


    return () => {
      active = false
    }
  }, [])


  // =========================================================
  // SENSOR OVERVIEW
  // =========================================================

  useEffect(() => {
    if (
      selectedSystemId === null
    ) {
      return
    }

    const systemId =
      selectedSystemId

    let active = true


    async function loadSensors():
      Promise<void> {
      try {
        setSensorsStatus(
          'loading',
        )

        const result =
          await loadSystemSensorOverview(
            systemId,
          )

        if (!active) {
          return
        }

        setSensors(
          [...result.sensors].sort(
            (left, right) =>
              left.name.localeCompare(
                right.name,
              ),
          ),
        )

        setLatestReadings(
          result.latestReadings,
        )

        setErrorMessage(
          null,
        )

        setSensorsStatus(
          'ready',
        )
      } catch {
        if (!active) {
          return
        }

        setSensors(
          [],
        )

        setLatestReadings(
          [],
        )

        setErrorMessage(
          'Unable to load sensors for the selected system.',
        )

        setSensorsStatus(
          'error',
        )
      }
    }


    void loadSensors()


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


  return {
    systems,
    selectedSystem,
    selectedSystemId,

    sensors,
    latestReadings,

    systemsStatus,
    sensorsStatus,
    errorMessage,

    selectSystem:
      setSelectedSystemId,
  }
}