import {
  useEffect,
  useMemo,
  useState,
} from 'react'

import {
  listSystems,
} from '../services/dashboardService'

import {
  loadSystemActuatorOverview,
} from '../services/actuatorService'

import type {
  AquaponicsSystem,
  DashboardActuator,
} from '../types/dashboard'


type LoadStatus =
  | 'idle'
  | 'loading'
  | 'ready'
  | 'error'


export function useActuatorsOverview() {
  const [
    systems,
    setSystems,
  ] = useState<
    AquaponicsSystem[]
  >(
    [],
  )

  const [
    selectedSystemId,
    setSelectedSystemId,
  ] = useState<
    string | null
  >(
    null,
  )

  const [
    actuators,
    setActuators,
  ] = useState<
    DashboardActuator[]
  >(
    [],
  )

  const [
    systemsStatus,
    setSystemsStatus,
  ] = useState<LoadStatus>(
    'loading',
  )

  const [
    actuatorsStatus,
    setActuatorsStatus,
  ] = useState<LoadStatus>(
    'idle',
  )

  const [
    errorMessage,
    setErrorMessage,
  ] = useState<
    string | null
  >(
    null,
  )


  // =========================================================
  // SYSTEMS
  // =========================================================

  useEffect(() => {
    let active =
      true


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
            (
              left,
              right,
            ) =>
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
          setActuators(
            [],
          )

          setActuatorsStatus(
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

        setActuators(
          [],
        )

        setActuatorsStatus(
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
  // ACTUATORS
  // =========================================================

  useEffect(() => {
    if (
      selectedSystemId === null
    ) {
      return
    }

    const systemId =
      selectedSystemId

    let active =
      true


    async function loadActuators():
      Promise<void> {
      try {
        setActuatorsStatus(
          'loading',
        )

        const result =
          await loadSystemActuatorOverview(
            systemId,
          )

        if (!active) {
          return
        }

        setActuators(
          [...result.actuators].sort(
            (
              left,
              right,
            ) =>
              left.name.localeCompare(
                right.name,
              ),
          ),
        )

        setErrorMessage(
          null,
        )

        setActuatorsStatus(
          'ready',
        )
      } catch {
        if (!active) {
          return
        }

        setActuators(
          [],
        )

        setErrorMessage(
          'Unable to load actuators for the selected system.',
        )

        setActuatorsStatus(
          'error',
        )
      }
    }


    void loadActuators()


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

    actuators,

    systemsStatus,
    actuatorsStatus,
    errorMessage,

    selectSystem:
      setSelectedSystemId,
  }
}