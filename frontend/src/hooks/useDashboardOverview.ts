import {
  useEffect,
  useMemo,
  useState,
} from 'react'

import {
  listSystems,
  loadSystemDashboardOverview,
} from '../services/dashboardService'
import { listEsp32Telemetry } from '../services/esp32TelemetryService'
import { mergeDashboardEsp32Archive } from '../utils/esp32DashboardReadings'

import type {
  AquaponicsSystem,
  DashboardActuator,
  DashboardAlert,
  DashboardSensor,
  DashboardSensorReading,
  SystemDashboardOverview,
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
    let busy = false
    let hasLoaded = false

    // The main dashboard reads both persistent database sources:
    // registered sensor readings and the independent ESP32 packet archive.
    // Poll so new USB data reaches cards without browser refresh.
    async function loadOverview(): Promise<void> {
      if (busy) return
      busy = true
      if (!hasLoaded) setOverviewStatus('loading')

      try {
        const [registeredResult, esp32Result] = await Promise.allSettled([
          loadSystemDashboardOverview(systemId),
          listEsp32Telemetry(systemId),
        ])
        if (!active) return

        // If one backend resource fails, a valid saved packet archive may
        // still populate the dashboard. Never silently invent measurements.
        if (
          registeredResult.status === 'rejected' &&
          (esp32Result.status === 'rejected' || esp32Result.value.length === 0)
        ) throw new Error('Neither dashboard data source was available')

        const registered: SystemDashboardOverview =
          registeredResult.status === 'fulfilled'
            ? registeredResult.value
            : { sensors: [], actuators: [], alerts: [], latestReadings: [] }
        const savedPackets =
          esp32Result.status === 'fulfilled' ? esp32Result.value : []
        const result = mergeDashboardEsp32Archive(registered, savedPackets, systemId)

        setSensors(result.sensors)
        setActuators(result.actuators)
        setAlerts(result.alerts)
        setLatestReadings(result.latestReadings)
        setErrorMessage(null)
        setOverviewStatus('ready')
        hasLoaded = true
      } catch {
        if (!active) return
        if (!hasLoaded) {
          setSensors([])
          setActuators([])
          setAlerts([])
          setLatestReadings([])
          setOverviewStatus('error')
        }
        setErrorMessage('Unable to refresh dashboard readings. Previously loaded measurements may be stale.')
      } finally {
        busy = false
      }
    }

    void loadOverview()
    const timer = window.setInterval(() => { void loadOverview() }, 10000)
    return () => {
      active = false
      window.clearInterval(timer)
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