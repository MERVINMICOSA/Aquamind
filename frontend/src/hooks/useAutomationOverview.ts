import {
  useEffect,
  useMemo,
  useState,
} from 'react'

import {
  loadSystemActuatorOverview,
} from '../services/actuatorService'

import {
  createAutomationRule,
  deleteAutomationRule,
  listAutomationRules,
  updateAutomationRule,
} from '../services/automationService'

import {
  listSystems,
} from '../services/dashboardService'

import {
  loadSystemSensorOverview,
} from '../services/sensorService'

import type {
  AutomationRule,
  AutomationRuleUpdateInput,
  SensorThresholdAutomationRuleInput,
} from '../types/automation'

import type {
  AquaponicsSystem,
  DashboardActuator,
  DashboardSensor,
} from '../types/dashboard'


type LoadStatus =
  | 'loading'
  | 'ready'
  | 'error'


type MutationStatus =
  | 'idle'
  | 'saving'
  | 'deleting'
  | 'error'


interface ResourceState<T> {
  systemId: string
  revision: number
  status: LoadStatus
  data: T
}


interface MutationState {
  systemId: string
  status: MutationStatus
  errorMessage: string | null
}


export interface SensorConditionOption {
  sensorType: string
  measurementType: string
}


export interface AutomationActuatorOption {
  actuatorType: string
  actuator: DashboardActuator
}


function mutationErrorMessage(
  action: 'save' | 'delete',
): string {
  return action === 'save'
    ? 'Unable to save automation rule.'
    : 'Unable to delete automation rule.'
}


export function useAutomationOverview() {
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
    revision,
    setRevision,
  ] = useState(
    0,
  )

  const [
    sensorState,
    setSensorState,
  ] = useState<
    ResourceState<DashboardSensor[]> |
    null
  >(
    null,
  )

  const [
    actuatorState,
    setActuatorState,
  ] = useState<
    ResourceState<DashboardActuator[]> |
    null
  >(
    null,
  )

  const [
    ruleState,
    setRuleState,
  ] = useState<
    ResourceState<AutomationRule[]> |
    null
  >(
    null,
  )

  const [
    mutationState,
    setMutationState,
  ] = useState<MutationState | null>(
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
            ordered[0]?.id ?? null,
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
  // SELECTED SYSTEM RESOURCES
  // ==========================================================

  useEffect(
    () => {
      if (
        selectedSystemId === null
      ) {
        return
      }

      const systemId =
        selectedSystemId

      const currentRevision =
        revision

      let active =
        true

      async function load() {
        try {
          const [
            sensorOverview,
            actuatorOverview,
            rules,
          ] =
            await Promise.all([
              loadSystemSensorOverview(
                systemId,
              ),

              loadSystemActuatorOverview(
                systemId,
              ),

              listAutomationRules(
                systemId,
              ),
            ])

          if (!active) {
            return
          }

          setSensorState({
            systemId,
            revision:
              currentRevision,
            status:
              'ready',

            data:
              [...sensorOverview.sensors]
                .sort(
                  (left, right) =>
                    left.name.localeCompare(
                      right.name,
                    ),
                ),
          })

          setActuatorState({
            systemId,
            revision:
              currentRevision,
            status:
              'ready',

            data:
              [...actuatorOverview.actuators]
                .sort(
                  (left, right) =>
                    left.name.localeCompare(
                      right.name,
                    ),
                ),
          })

          setRuleState({
            systemId,
            revision:
              currentRevision,
            status:
              'ready',
            data:
              rules,
          })
        } catch {
          if (!active) {
            return
          }

          setSensorState({
            systemId,
            revision:
              currentRevision,
            status:
              'error',
            data:
              [],
          })

          setActuatorState({
            systemId,
            revision:
              currentRevision,
            status:
              'error',
            data:
              [],
          })

          setRuleState({
            systemId,
            revision:
              currentRevision,
            status:
              'error',
            data:
              [],
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
      selectedSystemId,
      revision,
    ],
  )


  // ==========================================================
  // CURRENT SYSTEM DATA
  // ==========================================================

  const selectedSystem =
    systems.find(
      (system) =>
        system.id ===
        selectedSystemId,
    ) ?? null


  const sensorStateIsCurrent =
    sensorState?.systemId ===
      selectedSystemId &&
    sensorState.revision ===
      revision


  const actuatorStateIsCurrent =
    actuatorState?.systemId ===
      selectedSystemId &&
    actuatorState.revision ===
      revision


  const ruleStateIsCurrent =
    ruleState?.systemId ===
      selectedSystemId &&
    ruleState.revision ===
      revision


  const currentSensors =
    useMemo(
      () =>
        sensorStateIsCurrent
          ? sensorState?.data ?? []
          : [],
      [
        sensorState,
        sensorStateIsCurrent,
      ],
    )


  const currentActuators =
    useMemo(
      () =>
        actuatorStateIsCurrent
          ? actuatorState?.data ?? []
          : [],
      [
        actuatorState,
        actuatorStateIsCurrent,
      ],
    )


  const currentRules =
    ruleStateIsCurrent
      ? ruleState?.data ?? []
      : []


  const sensorStatus:
    LoadStatus =
    sensorStateIsCurrent
      ? sensorState?.status ??
        'loading'
      : 'loading'


  const actuatorStatus:
    LoadStatus =
    actuatorStateIsCurrent
      ? actuatorState?.status ??
        'loading'
      : 'loading'


  const rulesStatus:
    LoadStatus =
    ruleStateIsCurrent
      ? ruleState?.status ??
        'loading'
      : 'loading'


  // ==========================================================
  // SENSOR CONDITION OPTIONS
  // ==========================================================

  const sensorConditionOptions =
    useMemo<
      SensorConditionOption[]
    >(
      () => {
        const keys =
          new Set<string>()

        const options:
          SensorConditionOption[] =
          []

        for (
          const sensor
          of currentSensors
        ) {
          if (
            !sensor.is_enabled
          ) {
            continue
          }

          const key =
            `${sensor.sensor_type}\u0000` +
            sensor.measurement_type

          if (
            keys.has(
              key,
            )
          ) {
            continue
          }

          keys.add(
            key,
          )

          options.push({
            sensorType:
              sensor.sensor_type,

            measurementType:
              sensor.measurement_type,
          })
        }

        return options.sort(
          (left, right) => {
            const sensorTypeOrder =
              left.sensorType.localeCompare(
                right.sensorType,
              )

            if (
              sensorTypeOrder !== 0
            ) {
              return sensorTypeOrder
            }

            return left
              .measurementType
              .localeCompare(
                right.measurementType,
              )
          },
        )
      },
      [
        currentSensors,
      ],
    )


  // ==========================================================
  // AUTOMATION ACTUATOR OPTIONS
  //
  // Runtime resolves targets by actuator_type and requires
  // exactly one eligible actuator of that type.
  // ==========================================================

  const automationActuatorOptions =
    useMemo<
      AutomationActuatorOption[]
    >(
      () => {
        const eligible =
          currentActuators.filter(
            (actuator) =>
              actuator.is_enabled &&
              actuator.deleted_at ===
                null &&
              actuator.control_mode ===
                'automatic',
          )

        const groups =
          new Map<
            string,
            DashboardActuator[]
          >()

        for (
          const actuator
          of eligible
        ) {
          const existing =
            groups.get(
              actuator.actuator_type,
            )

          if (
            existing === undefined
          ) {
            groups.set(
              actuator.actuator_type,
              [
                actuator,
              ],
            )

            continue
          }

          existing.push(
            actuator,
          )
        }

        const options:
          AutomationActuatorOption[] =
          []

        for (
          const [
            actuatorType,
            actuators,
          ]
          of groups
        ) {
          if (
            actuators.length !== 1
          ) {
            continue
          }

          const actuator =
            actuators[0]

          if (
            actuator === undefined
          ) {
            continue
          }

          options.push({
            actuatorType,
            actuator,
          })
        }

        return options.sort(
          (left, right) =>
            left.actuator.name
              .localeCompare(
                right.actuator.name,
              ),
        )
      },
      [
        currentActuators,
      ],
    )


  // ==========================================================
  // MUTATION STATE
  // ==========================================================

  const mutationStatus:
    MutationStatus =
    mutationState?.systemId ===
      selectedSystemId
      ? mutationState.status
      : 'idle'


  const mutationError =
    mutationState?.systemId ===
      selectedSystemId
      ? mutationState.errorMessage
      : null


  function refresh() {
    setRevision(
      (current) =>
        current + 1,
    )
  }


  // ==========================================================
  // CREATE
  // ==========================================================

  async function createRule(
    input:
      SensorThresholdAutomationRuleInput,
  ): Promise<boolean> {
    if (
      selectedSystemId === null
    ) {
      return false
    }

    const systemId =
      selectedSystemId

    setMutationState({
      systemId,
      status:
        'saving',
      errorMessage:
        null,
    })

    try {
      await createAutomationRule(
        systemId,
        input,
      )

      setMutationState({
        systemId,
        status:
          'idle',
        errorMessage:
          null,
      })

      refresh()

      return true
    } catch {
      setMutationState({
        systemId,
        status:
          'error',

        errorMessage:
          mutationErrorMessage(
            'save',
          ),
      })

      return false
    }
  }


  // ==========================================================
  // UPDATE
  // ==========================================================

  async function updateRule(
    ruleId: string,
    input:
      AutomationRuleUpdateInput,
  ): Promise<boolean> {
    if (
      selectedSystemId === null
    ) {
      return false
    }

    const systemId =
      selectedSystemId

    setMutationState({
      systemId,
      status:
        'saving',
      errorMessage:
        null,
    })

    try {
      await updateAutomationRule(
        ruleId,
        input,
      )

      setMutationState({
        systemId,
        status:
          'idle',
        errorMessage:
          null,
      })

      refresh()

      return true
    } catch {
      setMutationState({
        systemId,
        status:
          'error',

        errorMessage:
          mutationErrorMessage(
            'save',
          ),
      })

      return false
    }
  }


  // ==========================================================
  // DELETE
  // ==========================================================

  async function deleteRule(
    ruleId: string,
  ): Promise<boolean> {
    if (
      selectedSystemId === null
    ) {
      return false
    }

    const systemId =
      selectedSystemId

    setMutationState({
      systemId,
      status:
        'deleting',
      errorMessage:
        null,
    })

    try {
      await deleteAutomationRule(
        ruleId,
      )

      setMutationState({
        systemId,
        status:
          'idle',
        errorMessage:
          null,
      })

      refresh()

      return true
    } catch {
      setMutationState({
        systemId,
        status:
          'error',

        errorMessage:
          mutationErrorMessage(
            'delete',
          ),
      })

      return false
    }
  }


  // ==========================================================
  // PUBLIC API
  // ==========================================================

  return {
    systems,
    systemsStatus,

    selectedSystemId,
    selectedSystem,

    sensors:
      currentSensors,

    sensorStatus,
    sensorConditionOptions,

    actuators:
      currentActuators,

    actuatorStatus,
    automationActuatorOptions,

    rules:
      currentRules,

    rulesStatus,

    mutationStatus,
    mutationError,

    selectSystem(
      systemId: string,
    ) {
      if (
        systemId ===
        selectedSystemId
      ) {
        return
      }

      setMutationState(
        null,
      )

      setSelectedSystemId(
        systemId,
      )
    },

    createRule,
    updateRule,
    deleteRule,

    refresh,
  }
}