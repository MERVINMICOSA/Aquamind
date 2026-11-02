export interface FeedingSchedule {
  id: string
  system_id: string
  actuator_id: string

  name: string
  schedule_expression: string
  enabled: boolean
  max_per_feed_grams: number

  created_at: string
  updated_at: string
}


export interface FeedingScheduleInput {
  actuator_id: string
  name: string
  schedule_expression: string
  enabled: boolean
  max_per_feed_grams: number
}


export type FeedingScheduleUpdateInput =
  Partial<FeedingScheduleInput>


export interface FeederCalibration {
  id: string
  actuator_id: string

  run_count: number
  measured_seconds: number
  measured_grams: number
  grams_per_second: number

  calibration_method: string
  performed_at: string

  verified_by_user_id: string | null
  notes: string | null
}


export interface FeederCalibrationInput {
  run_count: number
  measured_seconds: number
  measured_grams: number
  grams_per_second: number

  calibration_method: string
  performed_at: string

  verified_by_user_id: string | null
  notes: string | null
}


export type FeederCalibrationUpdateInput =
  Partial<FeederCalibrationInput>


export interface FeedingEvent {
  id: string

  schedule_id: string | null
  actuator_event_id: string
  tank_id: string

  amount_grams: number
  duration_seconds: number
  calculated_from_biomass: number | null

  calibration_id: string | null

  executed_at: string
  status: string

  notes: string | null
}

export interface FishPopulationRecord {
  id: string
  tank_id: string

  species: string
  count: number
  estimated_biomass_grams: number | null

  effective_at: string

  recorded_by_user_id: string | null
  notes: string | null
}


export interface FishPopulationInput {
  species: string
  count: number
  estimated_biomass_grams: number | null
  effective_at: string
  notes: string | null
}


export type FishPopulationUpdateInput =
  Partial<FishPopulationInput>