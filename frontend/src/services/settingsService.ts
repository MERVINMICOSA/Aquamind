import type {
  SystemSetting,
  SystemSettingInput,
  SystemSettingUpdateInput,
} from '../types/settings'

import {
  apiRequest,
} from './apiClient'


export async function listSystemSettings(
  systemId: string,
): Promise<SystemSetting[]> {
  const encodedSystemId =
    encodeURIComponent(
      systemId,
    )

  return apiRequest<SystemSetting[]>(
    `system-settings?system_id=${encodedSystemId}`,
  )
}


export async function createSystemSetting(
  systemId: string,
  input: SystemSettingInput,
): Promise<SystemSetting> {
  return apiRequest<SystemSetting>(
    'system-settings',
    {
      method:
        'POST',

      body:
        JSON.stringify({
          system_id:
            systemId,

          ...input,
        }),
    },
  )
}


export async function updateSystemSetting(
  settingId: string,
  input: SystemSettingUpdateInput,
): Promise<SystemSetting> {
  return apiRequest<SystemSetting>(
    `system-settings/${encodeURIComponent(settingId)}`,
    {
      method:
        'PATCH',

      body:
        JSON.stringify(
          input,
        ),
    },
  )
}


export async function deleteSystemSetting(
  settingId: string,
): Promise<void> {
  await apiRequest<void>(
    `system-settings/${encodeURIComponent(settingId)}`,
    {
      method:
        'DELETE',
    },
  )
}