import {
  useState,
} from 'react'

import type {
  FormEvent,
} from 'react'

import {
  useAuth,
} from '../hooks/useAuth'

import {
  useAutomationOverview,
} from '../hooks/useAutomationOverview'

import type {
  ActivateActuatorActionDefinition,
  AutomationRule,
  AutomationRuleUpdateInput,
  SensorThresholdAutomationRuleInput,
  SensorThresholdConditionDefinition,
  SensorThresholdOperator,
} from '../types/automation'

import {
  AutomationRunHistoryPanel,
} from '../components/automation/AutomationRunHistoryPanel'


interface RuleDraft {
  name: string
  description: string
  sensorType: string
  measurementType: string
  operator: SensorThresholdOperator
  thresholdValue: string
  actuatorType: string
  actionValue: string
  enabled: boolean
  priority: string
  cooldownSeconds: string
}


interface RuleEditor {
  systemId: string
  mode: 'create' | 'edit'
  ruleId: string | null
  original: AutomationRule | null
  draft: RuleDraft
}


interface SupportedRuleDefinition {
  condition: SensorThresholdConditionDefinition
  action: ActivateActuatorActionDefinition
}


function parseFiniteNumber(
  value: string,
): number | null {
  if (
    value.trim() ===
    ''
  ) {
    return null
  }

  const parsed =
    Number(
      value,
    )

  return Number.isFinite(
    parsed,
  )
    ? parsed
    : null
}


function parseInteger(
  value: string,
): number | null {
  const parsed =
    parseFiniteNumber(
      value,
    )

  if (
    parsed === null ||
    !Number.isInteger(
      parsed,
    )
  ) {
    return null
  }

  return parsed
}


function conditionOptionValue(
  sensorType: string,
  measurementType: string,
): string {
  return JSON.stringify([
    sensorType,
    measurementType,
  ])
}


function readSupportedRuleDefinition(
  rule: AutomationRule,
): SupportedRuleDefinition | null {
  if (
    rule.trigger_type !==
    'sensor_threshold'
  ) {
    return null
  }

  const condition =
    rule.condition_definition

  const action =
    rule.action_definition

  const sensorType =
    condition.sensor_type

  const measurementType =
    condition.measurement_type

  const operator =
    condition.operator

  const thresholdValue =
    condition.value

  const actionName =
    action.action

  const actuatorType =
    action.actuator_type

  const actionValue =
    action.value

  if (
    typeof sensorType !==
      'string' ||
    sensorType.trim() ===
      '' ||
    typeof measurementType !==
      'string' ||
    measurementType.trim() ===
      '' ||
    (
      operator !==
        'less_than' &&
      operator !==
        'greater_than'
    ) ||
    typeof thresholdValue !==
      'number' ||
    !Number.isFinite(
      thresholdValue,
    ) ||
    actionName !==
      'activate_actuator' ||
    typeof actuatorType !==
      'string' ||
    actuatorType.trim() ===
      '' ||
    typeof actionValue !==
      'number' ||
    !Number.isFinite(
      actionValue,
    )
  ) {
    return null
  }

  return {
    condition: {
      sensor_type:
        sensorType,

      measurement_type:
        measurementType,

      operator,

      value:
        thresholdValue,
    },

    action: {
      action:
        'activate_actuator',

      actuator_type:
        actuatorType,

      value:
        actionValue,
    },
  }
}


function formatTriggerType(
  value: string,
): string {
  return value
    .split(
      '_',
    )
    .map(
      (part) =>
        part.length === 0
          ? part
          : (
              part[0]
                ?.toUpperCase() ??
              ''
            ) +
            part.slice(
              1,
            ),
    )
    .join(
      ' ',
    )
}


function formatOperator(
  operator:
    SensorThresholdOperator,
): string {
  return operator ===
    'less_than'
    ? 'Less than'
    : 'Greater than'
}


export function AutomationPage() {
  const overview =
    useAutomationOverview()

  const auth =
    useAuth()

  const [
    editor,
    setEditor,
  ] = useState<RuleEditor | null>(
    null,
  )

  const [
    formError,
    setFormError,
  ] = useState<string | null>(
    null,
  )


  const canManageRules =
    auth.user?.role ===
    'admin'


  const currentEditor =
    editor?.systemId ===
      overview.selectedSystemId
      ? editor
      : null


  const mutationBusy =
    overview.mutationStatus ===
      'saving' ||
    overview.mutationStatus ===
      'deleting'


  function ruleIsEditable(
    rule: AutomationRule,
  ): boolean {
    const definition =
      readSupportedRuleDefinition(
        rule,
      )

    if (
      definition === null
    ) {
      return false
    }

    const conditionAvailable =
      overview
        .sensorConditionOptions
        .some(
          (option) =>
            option.sensorType ===
              definition
                .condition
                .sensor_type &&
            option.measurementType ===
              definition
                .condition
                .measurement_type,
        )

    const actuatorAvailable =
      overview
        .automationActuatorOptions
        .some(
          (option) =>
            option.actuatorType ===
            definition
              .action
              .actuator_type,
        )

    return (
      conditionAvailable &&
      actuatorAvailable
    )
  }


  function openCreateEditor() {
    const condition =
      overview
        .sensorConditionOptions[0]

    const actuator =
      overview
        .automationActuatorOptions[0]

    if (
      overview.selectedSystemId ===
        null ||
      condition ===
        undefined ||
      actuator ===
        undefined
    ) {
      return
    }

    setFormError(
      null,
    )

    setEditor({
      systemId:
        overview.selectedSystemId,

      mode:
        'create',

      ruleId:
        null,

      original:
        null,

      draft: {
        name:
          '',

        description:
          '',

        sensorType:
          condition.sensorType,

        measurementType:
          condition.measurementType,

        operator:
          'greater_than',

        thresholdValue:
          '',

        actuatorType:
          actuator.actuatorType,

        actionValue:
          '',

        enabled:
          true,

        priority:
          '0',

        cooldownSeconds:
          '0',
      },
    })
  }


  function openEditEditor(
    rule: AutomationRule,
  ) {
    if (
      overview.selectedSystemId ===
        null
    ) {
      return
    }

    const definition =
      readSupportedRuleDefinition(
        rule,
      )

    if (
      definition === null ||
      !ruleIsEditable(
        rule,
      )
    ) {
      return
    }

    setFormError(
      null,
    )

    setEditor({
      systemId:
        overview.selectedSystemId,

      mode:
        'edit',

      ruleId:
        rule.id,

      original:
        rule,

      draft: {
        name:
          rule.name,

        description:
          rule.description ??
          '',

        sensorType:
          definition
            .condition
            .sensor_type,

        measurementType:
          definition
            .condition
            .measurement_type,

        operator:
          definition
            .condition
            .operator,

        thresholdValue:
          String(
            definition
              .condition
              .value,
          ),

        actuatorType:
          definition
            .action
            .actuator_type,

        actionValue:
          String(
            definition
              .action
              .value,
          ),

        enabled:
          rule.enabled,

        priority:
          String(
            rule.priority,
          ),

        cooldownSeconds:
          String(
            rule.cooldown_seconds,
          ),
      },
    })
  }


  function updateDraft(
    update:
      Partial<RuleDraft>,
  ) {
    setEditor(
      (current) => {
        if (
          current ===
          null
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


  function buildInput(
    draft: RuleDraft,
  ):
    SensorThresholdAutomationRuleInput |
    null {
    const name =
      draft.name.trim()

    const thresholdValue =
      parseFiniteNumber(
        draft.thresholdValue,
      )

    const actionValue =
      parseFiniteNumber(
        draft.actionValue,
      )

    const priority =
      parseInteger(
        draft.priority,
      )

    const cooldownSeconds =
      parseInteger(
        draft.cooldownSeconds,
      )

    if (
      name ===
        '' ||
      draft.sensorType ===
        '' ||
      draft.measurementType ===
        '' ||
      draft.actuatorType ===
        '' ||
      thresholdValue ===
        null ||
      actionValue ===
        null ||
      priority ===
        null ||
      cooldownSeconds ===
        null ||
      cooldownSeconds <
        0
    ) {
      return null
    }

    const description =
      draft.description.trim()

    return {
      name,

      description:
        description ===
        ''
          ? null
          : description,

      trigger_type:
        'sensor_threshold',

      condition_definition: {
        sensor_type:
          draft.sensorType,

        measurement_type:
          draft.measurementType,

        operator:
          draft.operator,

        value:
          thresholdValue,
      },

      action_definition: {
        action:
          'activate_actuator',

        actuator_type:
          draft.actuatorType,

        value:
          actionValue,
      },

      enabled:
        draft.enabled,

      priority,

      cooldown_seconds:
        cooldownSeconds,
    }
  }


  function buildUpdate(
    original: AutomationRule,
    input:
      SensorThresholdAutomationRuleInput,
  ): AutomationRuleUpdateInput {
    const update:
      AutomationRuleUpdateInput =
      {}

    const originalDefinition =
      readSupportedRuleDefinition(
        original,
      )

    if (
      original.name !==
      input.name
    ) {
      update.name =
        input.name
    }

    if (
      original.description !==
      input.description
    ) {
      update.description =
        input.description
    }

    if (
      original.enabled !==
      input.enabled
    ) {
      update.enabled =
        input.enabled
    }

    if (
      original.priority !==
      input.priority
    ) {
      update.priority =
        input.priority
    }

    if (
      original.cooldown_seconds !==
      input.cooldown_seconds
    ) {
      update.cooldown_seconds =
        input.cooldown_seconds
    }

    if (
      originalDefinition ===
        null ||
      originalDefinition
          .condition
          .sensor_type !==
        input
          .condition_definition
          .sensor_type ||
      originalDefinition
          .condition
          .measurement_type !==
        input
          .condition_definition
          .measurement_type ||
      originalDefinition
          .condition
          .operator !==
        input
          .condition_definition
          .operator ||
      originalDefinition
          .condition
          .value !==
        input
          .condition_definition
          .value
    ) {
      update.condition_definition =
        input.condition_definition
    }

    if (
      originalDefinition ===
        null ||
      originalDefinition
          .action
          .actuator_type !==
        input
          .action_definition
          .actuator_type ||
      originalDefinition
          .action
          .value !==
        input
          .action_definition
          .value
    ) {
      update.action_definition =
        input.action_definition
    }

    return update
  }


  async function saveRule(
    event:
      FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    if (
      currentEditor ===
      null
    ) {
      return
    }

    const input =
      buildInput(
        currentEditor.draft,
      )

    if (
      input ===
      null
    ) {
      setFormError(
        'Complete all required fields with valid numeric values. Cooldown cannot be negative.',
      )

      return
    }

    setFormError(
      null,
    )

    if (
      currentEditor.mode ===
      'create'
    ) {
      const saved =
        await overview.createRule(
          input,
        )

      if (
        saved
      ) {
        setEditor(
          null,
        )
      }

      return
    }

    if (
      currentEditor.ruleId ===
        null ||
      currentEditor.original ===
        null
    ) {
      return
    }

    const update =
      buildUpdate(
        currentEditor.original,
        input,
      )

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

    const saved =
      await overview.updateRule(
        currentEditor.ruleId,
        update,
      )

    if (
      saved
    ) {
      setEditor(
        null,
      )
    }
  }


  async function removeRule(
    rule: AutomationRule,
  ) {
    const confirmed =
      window.confirm(
        `Delete automation rule "${rule.name}"?`,
      )

    if (
      !confirmed
    ) {
      return
    }

    const deleted =
      await overview.deleteRule(
        rule.id,
      )

    if (
      deleted &&
      currentEditor?.ruleId ===
        rule.id
    ) {
      setEditor(
        null,
      )
    }
  }


  return (
    <section
      className="section-page automation-page"
    >
      <div
        className="sensor-detail-heading"
      >
        <div>
          <p
            className="eyebrow"
          >
            Automation
          </p>

          <h1>
            Automation
          </h1>

          <p
            className="page-description"
          >
            Configure persisted sensor-threshold automation
            rules using the sensors and eligible automatic
            actuators already registered for each AquaMind
            system.
          </p>
        </div>

        <label
          className="system-selector"
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
              (event) => {
                setEditor(
                  null,
                )

                setFormError(
                  null,
                )

                overview.selectSystem(
                  event.target.value,
                )
              }
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
            className="status-message"
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
            {
              overview.mutationError !==
                null && (
                <p
                  className="status-message"
                  role="alert"
                >
                  {
                    overview
                      .mutationError
                  }
                </p>
              )
            }


            <div
              className="sensor-detail-panel"
            >
              <div>
                <p
                  className="eyebrow"
                >
                  Rule management
                </p>

                <h2>
                  Automation rules
                </h2>

                <p
                  className="page-description"
                >
                  Sensor-threshold rules can be created or
                  edited here. Other stored trigger types
                  remain visible but read-only in this
                  editor.
                </p>
              </div>


              {
                canManageRules && (
                  <button
                    type="button"
                    disabled={
                      mutationBusy ||
                      overview
                        .sensorConditionOptions
                        .length ===
                        0 ||
                      overview
                        .automationActuatorOptions
                        .length ===
                        0
                    }
                    onClick={
                      openCreateEditor
                    }
                  >
                    Add automation rule
                  </button>
                )
              }


              {
                canManageRules &&
                overview
                  .sensorConditionOptions
                  .length ===
                  0 && (
                  <p
                    className="status-message"
                  >
                    No enabled sensor condition is available
                    for rule creation.
                  </p>
                )
              }


              {
                canManageRules &&
                overview
                  .automationActuatorOptions
                  .length ===
                  0 && (
                  <p
                    className="status-message"
                  >
                    No unambiguous eligible automatic
                    actuator target is available for rule
                    creation.
                  </p>
                )
              }


              {
                currentEditor !==
                  null && (
                  <form
                    onSubmit={
                      saveRule
                    }
                  >
                    <h3>
                      {
                        currentEditor.mode ===
                          'create'
                          ? 'Add automation rule'
                          : 'Edit automation rule'
                      }
                    </h3>


                    <label
                      className="system-selector"
                    >
                      <span>
                        Name
                      </span>

                      <input
                        value={
                          currentEditor
                            .draft
                            .name
                        }
                        maxLength={
                          150
                        }
                        onChange={
                          (event) =>
                            updateDraft({
                              name:
                                event
                                  .target
                                  .value,
                            })
                        }
                      />
                    </label>


                    <label
                      className="system-selector"
                    >
                      <span>
                        Description
                      </span>

                      <textarea
                        value={
                          currentEditor
                            .draft
                            .description
                        }
                        onChange={
                          (event) =>
                            updateDraft({
                              description:
                                event
                                  .target
                                  .value,
                            })
                        }
                      />
                    </label>


                    <label
                      className="system-selector"
                    >
                      <span>
                        Sensor condition
                      </span>

                      <select
                        value={
                          conditionOptionValue(
                            currentEditor
                              .draft
                              .sensorType,
                            currentEditor
                              .draft
                              .measurementType,
                          )
                        }
                        onChange={
                          (event) => {
                            const selected =
                              overview
                                .sensorConditionOptions
                                .find(
                                  (option) =>
                                    conditionOptionValue(
                                      option.sensorType,
                                      option.measurementType,
                                    ) ===
                                    event
                                      .target
                                      .value,
                                )

                            if (
                              selected !==
                              undefined
                            ) {
                              updateDraft({
                                sensorType:
                                  selected
                                    .sensorType,

                                measurementType:
                                  selected
                                    .measurementType,
                              })
                            }
                          }
                        }
                      >
                        {
                          overview
                            .sensorConditionOptions
                            .map(
                              (option) => (
                                <option
                                  key={
                                    conditionOptionValue(
                                      option.sensorType,
                                      option.measurementType,
                                    )
                                  }
                                  value={
                                    conditionOptionValue(
                                      option.sensorType,
                                      option.measurementType,
                                    )
                                  }
                                >
                                  {
                                    option.sensorType
                                  }
                                  {' · '}
                                  {
                                    option.measurementType
                                  }
                                </option>
                              ),
                            )
                        }
                      </select>
                    </label>


                    <label
                      className="system-selector"
                    >
                      <span>
                        Comparison
                      </span>

                      <select
                        value={
                          currentEditor
                            .draft
                            .operator
                        }
                        onChange={
                          (event) =>
                            updateDraft({
                              operator:
                                event
                                  .target
                                  .value as
                                  SensorThresholdOperator,
                            })
                        }
                      >
                        <option
                          value="greater_than"
                        >
                          Greater than
                        </option>

                        <option
                          value="less_than"
                        >
                          Less than
                        </option>
                      </select>
                    </label>


                    <label
                      className="system-selector"
                    >
                      <span>
                        Threshold value
                      </span>

                      <input
                        type="number"
                        step="any"
                        value={
                          currentEditor
                            .draft
                            .thresholdValue
                        }
                        onChange={
                          (event) =>
                            updateDraft({
                              thresholdValue:
                                event
                                  .target
                                  .value,
                            })
                        }
                      />
                    </label>


                    <label
                      className="system-selector"
                    >
                      <span>
                        Automation actuator
                      </span>

                      <select
                        value={
                          currentEditor
                            .draft
                            .actuatorType
                        }
                        onChange={
                          (event) =>
                            updateDraft({
                              actuatorType:
                                event
                                  .target
                                  .value,
                            })
                        }
                      >
                        {
                          overview
                            .automationActuatorOptions
                            .map(
                              (option) => (
                                <option
                                  key={
                                    option
                                      .actuatorType
                                  }
                                  value={
                                    option
                                      .actuatorType
                                  }
                                >
                                  {
                                    option
                                      .actuator
                                      .name
                                  }
                                  {' · '}
                                  {
                                    option
                                      .actuatorType
                                  }
                                </option>
                              ),
                            )
                        }
                      </select>
                    </label>


                    <p>
                      Action: Activate actuator
                    </p>


                    <label
                      className="system-selector"
                    >
                      <span>
                        Requested actuator value
                      </span>

                      <input
                        type="number"
                        step="any"
                        value={
                          currentEditor
                            .draft
                            .actionValue
                        }
                        onChange={
                          (event) =>
                            updateDraft({
                              actionValue:
                                event
                                  .target
                                  .value,
                            })
                        }
                      />
                    </label>


                    <label
                      className="system-selector"
                    >
                      <span>
                        Priority
                      </span>

                      <input
                        type="number"
                        step="1"
                        value={
                          currentEditor
                            .draft
                            .priority
                        }
                        onChange={
                          (event) =>
                            updateDraft({
                              priority:
                                event
                                  .target
                                  .value,
                            })
                        }
                      />
                    </label>


                    <label
                      className="system-selector"
                    >
                      <span>
                        Cooldown (seconds)
                      </span>

                      <input
                        type="number"
                        min="0"
                        step="1"
                        value={
                          currentEditor
                            .draft
                            .cooldownSeconds
                        }
                        onChange={
                          (event) =>
                            updateDraft({
                              cooldownSeconds:
                                event
                                  .target
                                  .value,
                            })
                        }
                      />
                    </label>


                    <label>
                      <input
                        type="checkbox"
                        checked={
                          currentEditor
                            .draft
                            .enabled
                        }
                        onChange={
                          (event) =>
                            updateDraft({
                              enabled:
                                event
                                  .target
                                  .checked,
                            })
                        }
                      />

                      Enabled
                    </label>


                    {
                      formError !==
                        null && (
                        <p
                          role="alert"
                          className="status-message"
                        >
                          {formError}
                        </p>
                      )
                    }


                    <div>
                      <button
                        type="submit"
                        disabled={
                          mutationBusy
                        }
                      >
                        Save automation rule
                      </button>

                      <button
                        type="button"
                        disabled={
                          mutationBusy
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
                )
              }
            </div>


            {
              (
                overview.rulesStatus ===
                  'loading' ||
                overview.sensorStatus ===
                  'loading' ||
                overview.actuatorStatus ===
                  'loading'
              ) && (
                <p
                  className="status-message"
                >
                  Loading automation configuration…
                </p>
              )
            }


            {
              (
                overview.rulesStatus ===
                  'error' ||
                overview.sensorStatus ===
                  'error' ||
                overview.actuatorStatus ===
                  'error'
              ) && (
                <p
                  className="status-message"
                  role="alert"
                >
                  Unable to load automation configuration.
                </p>
              )
            }


            {
              overview.rulesStatus ===
                'ready' &&
              overview.rules.length ===
                0 && (
                <div
                  className="empty-state"
                >
                  No automation rules configured
                </div>
              )
            }


            {
              overview.rules.map(
                (rule) => {
                  const definition =
                    readSupportedRuleDefinition(
                      rule,
                    )

                  const editable =
                    ruleIsEditable(
                      rule,
                    )

                  return (
                    <article
                      key={
                        rule.id
                      }
                      className="sensor-detail-panel"
                    >
                      <div>
                        <p
                          className="eyebrow"
                        >
                          {
                            formatTriggerType(
                              rule
                                .trigger_type,
                            )
                          }
                        </p>

                        <h3>
                          {
                            rule.name
                          }
                        </h3>

                        <p>
                          {
                            rule.description ??
                            'No description'
                          }
                        </p>

                        <p>
                          Status:{' '}
                          {
                            rule.enabled
                              ? 'Enabled'
                              : 'Disabled'
                          }
                        </p>

                        <p>
                          Priority:{' '}
                          {
                            rule.priority
                          }
                        </p>

                        <p>
                          Cooldown:{' '}
                          {
                            rule
                              .cooldown_seconds
                          }
                          {' seconds'}
                        </p>


                        {
                          definition !==
                            null ? (
                            <>
                              <p>
                                Condition:{' '}
                                {
                                  definition
                                    .condition
                                    .sensor_type
                                }
                                {' / '}
                                {
                                  definition
                                    .condition
                                    .measurement_type
                                }
                                {' · '}
                                {
                                  formatOperator(
                                    definition
                                      .condition
                                      .operator,
                                  )
                                }
                                {' '}
                                {
                                  definition
                                    .condition
                                    .value
                                }
                              </p>

                              <p>
                                Action: Activate{' '}
                                {
                                  definition
                                    .action
                                    .actuator_type
                                }
                                {' with requested value '}
                                {
                                  definition
                                    .action
                                    .value
                                }
                              </p>

                              {
                                !editable && (
                                  <p>
                                    This rule is read-only until
                                    its referenced sensor condition
                                    and a single eligible automatic
                                    actuator target are available.
                                  </p>
                                )
                              }
                            </>
                          ) : (
                            <p>
                              This stored trigger type is
                              preserved read-only in the current
                              automation editor.
                            </p>
                          )
                        }
                      </div>


                      {
                        canManageRules && (
                          <div>
                            {
                              editable && (
                                <button
                                  type="button"
                                  aria-label={
                                    `Edit ${rule.name}`
                                  }
                                  disabled={
                                    mutationBusy
                                  }
                                  onClick={
                                    () =>
                                      openEditEditor(
                                        rule,
                                      )
                                  }
                                >
                                  Edit
                                </button>
                              )
                            }

                            <button
                              type="button"
                              aria-label={
                                `Delete ${rule.name}`
                              }
                              disabled={
                                mutationBusy
                              }
                              onClick={
                                () => {
                                  void removeRule(
                                    rule,
                                  )
                                }
                              }
                            >
                              Delete
                            </button>
                          </div>
                        )
                      }
                    </article>
                  )
                },
              )
            }
            <AutomationRunHistoryPanel
              rules={
                overview.rules
              }
            />
          </>
        )
      }
    </section>
  )
}