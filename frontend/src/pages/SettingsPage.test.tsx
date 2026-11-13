import {
  fireEvent,
  render,
  screen,
  waitFor,
} from '@testing-library/react'

import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest'

import {
  useAuth,
} from '../hooks/useAuth'

import {
  useSettingsOverview,
} from '../hooks/useSettingsOverview'

import type {
  SystemSetting,
} from '../types/settings'

import {
  SettingsPage,
} from './SettingsPage'


vi.mock(
  '../hooks/useAuth',
  () => ({
    useAuth:
      vi.fn(),
  }),
)


vi.mock(
  '../hooks/useSettingsOverview',
  () => ({
    useSettingsOverview:
      vi.fn(),
  }),
)


const mockedUseAuth =
  vi.mocked(
    useAuth,
  )


const mockedUseSettingsOverview =
  vi.mocked(
    useSettingsOverview,
  )


const selectSystem =
  vi.fn()

const refresh =
  vi.fn()

const createSetting =
  vi.fn(
    async () =>
      true,
  )

const updateSetting =
  vi.fn(
    async () =>
      true,
  )

const deleteSetting =
  vi.fn(
    async () =>
      true,
  )


const system = {
  id:
    'system-1',

  name:
    'Main System',

  description:
    null,

  timezone:
    'UTC',

  is_active:
    true,

  created_at:
    '2026-09-20T00:00:00Z',

  updated_at:
    '2026-09-20T00:00:00Z',
}


const setting:
  SystemSetting = {
    id:
      'setting-1',

    system_id:
      system.id,

    setting_key:
      'synthetic_setting',

    setting_value:
      'synthetic-value',

    value_type:
      'synthetic-type',

    created_at:
      '2026-09-20T00:00:00Z',

    updated_at:
      '2026-09-20T01:00:00Z',

    updated_by_user_id:
      'user-1',

    deleted_at:
      null,
  }


function readyOverview():
  ReturnType<
    typeof useSettingsOverview
  > {
  return {
    systems: [
      system,
    ],

    systemsStatus:
      'ready',

    selectedSystemId:
      system.id,

    selectedSystem:
      system,

    settings: [
      setting,
    ],

    settingsStatus:
      'ready',

    mutationStatus:
      'idle',

    mutationError:
      null,

    selectSystem,

    createSetting,

    updateSetting,

    deleteSetting,

    refresh,
  }
}


beforeEach(
  () => {
    selectSystem.mockReset()
    refresh.mockReset()

    createSetting.mockReset()
    createSetting.mockResolvedValue(
      true,
    )

    updateSetting.mockReset()
    updateSetting.mockResolvedValue(
      true,
    )

    deleteSetting.mockReset()
    deleteSetting.mockResolvedValue(
      true,
    )

    mockedUseSettingsOverview
      .mockReset()

    mockedUseSettingsOverview
      .mockReturnValue(
        readyOverview(),
      )

    mockedUseAuth
      .mockReset()

    mockedUseAuth
      .mockReturnValue({
        user: {
          role:
            'admin',
        },
      } as ReturnType<typeof useAuth>)
  },
)


describe(
  'SettingsPage',
  () => {
    it(
      'explains that saved keys do not control hardware or contain secrets',
      () => {
        render(<SettingsPage />)

        expect(screen.getByRole('heading', {
          name: 'What Settings is for',
        })).toBeInTheDocument()
        expect(screen.getByText(/These stored values are not/))
          .toBeInTheDocument()
        expect(screen.getByText(/Do not store/))
          .toHaveTextContent('API secrets')
        expect(screen.getByText(/external water-circulation pump operates independently/))
          .toBeInTheDocument()
      },
    )


    it(
      'renders persisted settings and changes systems through the overview hook',
      () => {
        mockedUseSettingsOverview
          .mockReturnValue({
            ...readyOverview(),

            systems: [
              system,

              {
                ...system,

                id:
                  'system-2',

                name:
                  'Second System',
              },
            ],
          })

        render(
          <SettingsPage />,
        )

        expect(
          screen.getByText(
            'synthetic_setting',
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByText(
            /synthetic-value/,
          ),
        ).toBeInTheDocument()

        expect(
          screen.getByText(
            'synthetic-type',
          ),
        ).toBeInTheDocument()

        fireEvent.change(
          screen.getByLabelText(
            'Aquaponics system',
          ),
          {
            target: {
              value:
                'system-2',
            },
          },
        )

        expect(
          selectSystem,
        ).toHaveBeenCalledWith(
          'system-2',
        )
      },
    )


    it(
      'hides mutation controls without administrator access',
      () => {
        mockedUseAuth
          .mockReturnValue({
            user:
              null,
          } as ReturnType<typeof useAuth>)

        render(
          <SettingsPage />,
        )

        expect(
          screen.queryByRole(
            'button',
            {
              name:
                'Add setting',
            },
          ),
        ).not.toBeInTheDocument()

        expect(
          screen.queryByRole(
            'button',
            {
              name:
                `Edit ${setting.setting_key}`,
            },
          ),
        ).not.toBeInTheDocument()

        expect(
          screen.queryByRole(
            'button',
            {
              name:
                `Delete ${setting.setting_key}`,
            },
          ),
        ).not.toBeInTheDocument()
      },
    )


    it(
      'creates a setting using the canonical backend string fields',
      async () => {
        render(
          <SettingsPage />,
        )

        fireEvent.click(
          screen.getByRole(
            'button',
            {
              name:
                'Add setting',
            },
          ),
        )

        fireEvent.change(
          screen.getByLabelText(
            'Setting key',
          ),
          {
            target: {
              value:
                'new_setting',
            },
          },
        )

        fireEvent.change(
          screen.getByLabelText(
            'Setting value',
          ),
          {
            target: {
              value:
                'stored exactly',
            },
          },
        )

        fireEvent.change(
          screen.getByLabelText(
            'Value type',
          ),
          {
            target: {
              value:
                'custom_type',
            },
          },
        )

        fireEvent.click(
          screen.getByRole(
            'button',
            {
              name:
                'Save setting',
            },
          ),
        )

        await waitFor(
          () => {
            expect(
              createSetting,
            ).toHaveBeenCalledWith({
              setting_key:
                'new_setting',

              setting_value:
                'stored exactly',

              value_type:
                'custom_type',
            })
          },
        )
      },
    )


    it(
      'preserves an empty setting value because the backend permits it',
      async () => {
        render(
          <SettingsPage />,
        )

        fireEvent.click(
          screen.getByRole(
            'button',
            {
              name:
                'Add setting',
            },
          ),
        )

        fireEvent.change(
          screen.getByLabelText(
            'Setting key',
          ),
          {
            target: {
              value:
                'empty_value_setting',
            },
          },
        )

        fireEvent.change(
          screen.getByLabelText(
            'Value type',
          ),
          {
            target: {
              value:
                'string',
            },
          },
        )

        fireEvent.click(
          screen.getByRole(
            'button',
            {
              name:
                'Save setting',
            },
          ),
        )

        await waitFor(
          () => {
            expect(
              createSetting,
            ).toHaveBeenCalledWith({
              setting_key:
                'empty_value_setting',

              setting_value:
                '',

              value_type:
                'string',
            })
          },
        )
      },
    )


    it(
      'updates only changed setting fields',
      async () => {
        render(
          <SettingsPage />,
        )

        fireEvent.click(
          screen.getByRole(
            'button',
            {
              name:
                `Edit ${setting.setting_key}`,
            },
          ),
        )

        fireEvent.change(
          screen.getByLabelText(
            'Setting value',
          ),
          {
            target: {
              value:
                'updated-value',
            },
          },
        )

        fireEvent.click(
          screen.getByRole(
            'button',
            {
              name:
                'Save setting',
            },
          ),
        )

        await waitFor(
          () => {
            expect(
              updateSetting,
            ).toHaveBeenCalledWith(
              setting.id,
              {
                setting_value:
                  'updated-value',
              },
            )
          },
        )
      },
    )


    it(
      'requires confirmation before deleting a setting',
      async () => {
        const confirm =
          vi.spyOn(
            window,
            'confirm',
          ).mockReturnValue(
            true,
          )

        render(
          <SettingsPage />,
        )

        fireEvent.click(
          screen.getByRole(
            'button',
            {
              name:
                `Delete ${setting.setting_key}`,
            },
          ),
        )

        expect(
          confirm,
        ).toHaveBeenCalled()

        await waitFor(
          () => {
            expect(
              deleteSetting,
            ).toHaveBeenCalledWith(
              setting.id,
            )
          },
        )

        confirm.mockRestore()
      },
    )


    it(
      'renders an honest empty state when the system has no settings',
      () => {
        mockedUseSettingsOverview
          .mockReturnValue({
            ...readyOverview(),

            settings:
              [],
          })

        render(
          <SettingsPage />,
        )

        expect(
          screen.getByText(
            'No system settings configured',
          ),
        ).toBeInTheDocument()
      },
    )
  },
)