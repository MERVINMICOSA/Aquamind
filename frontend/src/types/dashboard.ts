export interface AquaponicsSystem {
  id: string
  name: string
  description: string | null
  timezone: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface DashboardSensor {
  id: string
  system_id: string
  name: string

  sensor_type: string
  measurement_type: string

  location_type: string
  location_id: string | null

  unit: string
  hardware_identifier: string | null

  is_simulated: boolean
  is_enabled: boolean

  sampling_interval_seconds: number
  calibration_status: string

  created_at: string
  updated_at: string
}

export interface DashboardSensorReading {
  id: string
  sensor_id: string

  recorded_at: string
  value_numeric: number
  unit: string

  quality_status: string
  source: string

  sequence_number: number | null
  created_at: string
}

export interface DashboardActuator {
  id: string
  system_id: string
  name: string

  actuator_type: string
  control_mode: string

  hardware_identifier: string | null

  location_type: string | null
  location_id: string | null

  is_enabled: boolean

  safety_config:
    Record<string, unknown> | null

  current_state: string
  current_value: number | null
  last_state_at: string | null

  created_at: string
  updated_at: string
  deleted_at: string | null
}

export interface DashboardAlert {
  id: string
  system_id: string

  sensor_id: string | null
  actuator_id: string | null

  alert_type: string
  severity: string
  message: string

  trigger_value: number | null
  threshold_id: string | null

  status: string

  created_at: string

  acknowledged_at: string | null
  acknowledged_by_user_id:
    string | null

  resolved_at: string | null
  resolution_reason: string | null
}

export interface SystemDashboardOverview {
  sensors: DashboardSensor[]
  actuators: DashboardActuator[]
  alerts: DashboardAlert[]
  latestReadings: DashboardSensorReading[]
}