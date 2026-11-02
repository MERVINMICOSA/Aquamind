export interface SystemSetting {
  id: string
  system_id: string

  setting_key: string
  setting_value: string
  value_type: string

  created_at: string
  updated_at: string

  updated_by_user_id: string | null
  deleted_at: string | null
}


export interface SystemSettingInput {
  setting_key: string
  setting_value: string
  value_type: string
}


export type SystemSettingUpdateInput =
  Partial<SystemSettingInput>