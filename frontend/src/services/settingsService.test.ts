import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest'

import {
  apiRequest,
} from './apiClient'

import {
  createSystemSetting,
  deleteSystemSetting,
  listSystemSettings,
  updateSystemSetting,
} from './settingsService'

import type {
  SystemSettingInput,
} from '../types/settings'


vi.mock(
  './apiClient',
  () => ({
    apiRequest:
      vi.fn(),
  }),
)


const mockedApiRequest =
  vi.mocked(
    apiRequest,
  )


const input:
  SystemSettingInput = {
    setting_key:
      'synthetic_setting',

    setting_value:
      'synthetic-value',

    value_type:
      'synthetic-type',
  }


beforeEach(
  () => {
    mockedApiRequest
      .mockReset()
  },
)


describe(
  'settingsService',
  () => {
    it(
      'lists active settings for one encoded system',
      async () => {
        mockedApiRequest
          .mockResolvedValue(
            [],
          )

        const result =
          await listSystemSettings(
            'system / one',
          )

        expect(
          result,
        ).toEqual(
          [],
        )

        expect(
          mockedApiRequest,
        ).toHaveBeenCalledWith(
          'system-settings?system_id=system%20%2F%20one',
        )
      },
    )


    it(
      'creates a system-scoped setting',
      async () => {
        mockedApiRequest
          .mockResolvedValue({
            id:
              'setting-1',
          })

        await createSystemSetting(
          'system-1',
          input,
        )

        expect(
          mockedApiRequest,
        ).toHaveBeenCalledWith(
          'system-settings',
          {
            method:
              'POST',

            body:
              JSON.stringify({
                system_id:
                  'system-1',

                ...input,
              }),
          },
        )
      },
    )


    it(
      'updates an encoded setting id',
      async () => {
        mockedApiRequest
          .mockResolvedValue({
            id:
              'setting-1',
          })

        await updateSystemSetting(
          'setting / one',
          {
            setting_value:
              'updated-value',

            value_type:
              'updated-type',
          },
        )

        expect(
          mockedApiRequest,
        ).toHaveBeenCalledWith(
          'system-settings/setting%20%2F%20one',
          {
            method:
              'PATCH',

            body:
              JSON.stringify({
                setting_value:
                  'updated-value',

                value_type:
                  'updated-type',
              }),
          },
        )
      },
    )


    it(
      'deletes an encoded setting id',
      async () => {
        mockedApiRequest
          .mockResolvedValue(
            undefined,
          )

        await deleteSystemSetting(
          'setting / one',
        )

        expect(
          mockedApiRequest,
        ).toHaveBeenCalledWith(
          'system-settings/setting%20%2F%20one',
          {
            method:
              'DELETE',
          },
        )
      },
    )
  },
)