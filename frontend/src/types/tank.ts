export interface Tank {
  id: string
  system_id: string

  name: string
  capacity_liters: number
  species: string | null
  is_active: boolean

  created_at: string
  updated_at: string
}