export type AutomationTriggerType =
  | 'sensor_threshold'
  | 'schedule'
  | 'system_event'
  | 'manual'


export type SensorThresholdOperator =
  | 'less_than'
  | 'greater_than'


export interface SensorThresholdConditionDefinition {
  sensor_type: string
  measurement_type: string
  operator: SensorThresholdOperator
  value: number
}


export interface ActivateActuatorActionDefinition {
  action: 'activate_actuator'
  actuator_type: string
  value: number
}


/*
 * Responses remain broad enough to represent every trigger
 * type already allowed by the backend enum.
 *
 * 10H.2's editor intentionally creates/edits only the
 * currently executable sensor-threshold rule shape.
 */
export interface AutomationRule {
  id: string
  system_id: string
  name: string
  description: string | null

  trigger_type: AutomationTriggerType

  condition_definition:
    Record<string, unknown>

  action_definition:
    Record<string, unknown>

  enabled: boolean
  priority: number
  cooldown_seconds: number

  created_at: string
  updated_at: string
}


export interface SensorThresholdAutomationRuleInput {
  name: string
  description: string | null

  trigger_type: 'sensor_threshold'

  condition_definition:
    SensorThresholdConditionDefinition

  action_definition:
    ActivateActuatorActionDefinition

  enabled: boolean
  priority: number
  cooldown_seconds: number
}


export type AutomationRuleUpdateInput =
  Partial<SensorThresholdAutomationRuleInput>


/*
 * Canonical persisted automation-run response.
 *
 * Status remains a string here because the frontend should
 * render the backend value without inventing a narrower
 * runtime status vocabulary.
 */
export interface AutomationRun {
  id: string
  rule_id: string

  started_at: string
  completed_at: string | null

  trigger_value: number | null

  status: string

  result_summary: string | null
  error_message: string | null
}