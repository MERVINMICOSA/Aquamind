export interface Reservoir {
  id: string
  system_id: string

  name: string
  capacity_liters: number
  is_active: boolean

  created_at: string
  updated_at: string
}


export interface RefillEvent {
  id: string

  reservoir_id: string
  target_tank_id: string

  start_level_percent: number
  end_level_percent: number

  started_at: string
  completed_at: string | null
  duration_seconds: number | null

  trigger: string
  status: string

  timeout_reason: string | null

  created_at: string
}