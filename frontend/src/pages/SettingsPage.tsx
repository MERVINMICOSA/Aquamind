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
  useSettingsOverview,
} from '../hooks/useSettingsOverview'

import type {
  SystemSetting,
  SystemSettingInput,
  SystemSettingUpdateInput,
} from '../types/settings'


interface SettingDraft {
  settingKey: string
  settingValue: string
  valueType: string
}


interface SettingEditor {
  systemId: string
  mode: 'create' | 'edit'
  settingId: string | null
  original: SystemSetting | null
  draft: SettingDraft
}


function displayNullable(
  value: string | null,
): string {
  return value ??
    'Not recorded'
}


export function SettingsPage() {
  const auth =
    useAuth()

  const overview =
    useSettingsOverview()

  const [
    editor,
    setEditor,
  ] = useState<SettingEditor | null>(
    null,
  )

  const [
    formError,
    setFormError,
  ] = useState<string | null>(
    null,
  )


  const canManageSettings =
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


  function openCreateEditor() {
    if (
      overview.selectedSystemId ===
      null
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

      settingId:
        null,

      original:
        null,

      draft: {
        settingKey:
          '',

        settingValue:
          '',

        valueType:
          '',
      },
    })
  }


  function openEditEditor(
    setting: SystemSetting,
  ) {
    if (
      overview.selectedSystemId ===
        null
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

      settingId:
        setting.id,

      original:
        setting,

      draft: {
        settingKey:
          setting.setting_key,

        settingValue:
          setting.setting_value,

        valueType:
          setting.value_type,
      },
    })
  }


  function updateDraft(
    update:
      Partial<SettingDraft>,
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
    draft: SettingDraft,
  ): SystemSettingInput | null {
    /*
     * The backend only requires setting_key and value_type
     * to contain at least one character. setting_value is
     * allowed to be an empty string, so do not reject or
     * normalize it here.
     */
    if (
      draft.settingKey.length <
        1 ||
      draft.settingKey.length >
        150 ||
      draft.valueType.length <
        1 ||
      draft.valueType.length >
        32
    ) {
      return null
    }

    return {
      setting_key:
        draft.settingKey,

      setting_value:
        draft.settingValue,

      value_type:
        draft.valueType,
    }
  }


  function buildUpdate(
    original: SystemSetting,
    input: SystemSettingInput,
  ): SystemSettingUpdateInput {
    const update:
      SystemSettingUpdateInput =
      {}

    if (
      original.setting_key !==
      input.setting_key
    ) {
      update.setting_key =
        input.setting_key
    }

    if (
      original.setting_value !==
      input.setting_value
    ) {
      update.setting_value =
        input.setting_value
    }

    if (
      original.value_type !==
      input.value_type
    ) {
      update.value_type =
        input.value_type
    }

    return update
  }


  async function saveSetting(
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
        'Setting key and value type are required and must fit the backend length limits.',
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
        await overview.createSetting(
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
      currentEditor.settingId ===
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
      await overview.updateSetting(
        currentEditor.settingId,
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


  async function removeSetting(
    setting: SystemSetting,
  ) {
    const confirmed =
      window.confirm(
        `Delete system setting "${setting.setting_key}"?`,
      )

    if (
      !confirmed
    ) {
      return
    }

    const deleted =
      await overview.deleteSetting(
        setting.id,
      )

    if (
      deleted &&
      currentEditor?.settingId ===
        setting.id
    ) {
      setEditor(
        null,
      )
    }
  }


  return (
    <section
      className="section-page settings-page"
    >
      <div
        className="page-heading-row"
      >
        <div>
          <p
            className="eyebrow"
          >
            Configuration
          </p>

          <h1>
            Settings
          </h1>

          <p
            className="page-description"
          >
            Manage system-level saved configuration notes and values.
            Hardware setup, sensor calibration, and servo feeding are
            configured separately.
          </p>
        </div>

        <label
          className="select-field"
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

      <section className="surface-panel" aria-labelledby="settings-guide-heading">
        <div>
          <p className="eyebrow">Page guide</p>
          <h2 id="settings-guide-heading">What Settings is for</h2>
          <p>
            Save and review application key/value records associated with
            the selected AquaMind system. These stored values are not
            automatically applied to the Raspberry Pi hardware or the
            ESP32 firmware.
          </p>
          <h3>Setup checklist</h3>
          <ul>
            <li>Configure the Raspberry Pi's ESP32 USB serial connection
              in backend runtime environment settings, including its
              port, baud rate, device ID, and system ID.</li>
            <li>Verify the pH and TDS calibration before making
              water-quality decisions from those measurements.</li>
            <li>Use Feeding to configure the fish-feeder record,
              schedule, servo dispenser calibration, and fish population.</li>
            <li>Use Alerts to review warnings; configure
              sensor thresholds through the supported alert-threshold
              backend, not by inventing generic setting keys.</li>
          </ul>
          <p>
            The external water-circulation pump operates independently;
            no saved setting here can start or stop it. Do not store
            API secrets, passwords, or device credentials in the
            general key/value settings table.
          </p>
        </div>
      </section>


      {
        overview.systemsStatus ===
          'loading' && (
          <p
            className="status-message"
          >
            Loading aquaponics systemsâ€¦
          </p>
        )
      }


      {
        overview.systemsStatus ===
          'error' && (
          <p
            className="status-message status-message--error"
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
                  className="status-message status-message--error"
                  role="alert"
                >
                  {
                    overview
                      .mutationError
                  }
                </p>
              )
            }


            <section
              className="surface-panel"
            >
              <div>
                <p
                  className="eyebrow"
                >
                  System configuration
                </p>

                <h2>
                  System settings
                </h2>

                <p
                  className="page-description"
                >
                  Values are stored exactly as strings together
                  with their persisted value-type label. The
                  backend does not define a fixed value-type
                  vocabulary. Adding a key alone does not
                  activate any feature or configure a device.
                </p>
              </div>


              {
                canManageSettings && (
                  <button
                    type="button"
                    className="primary-button"
                    disabled={
                      mutationBusy
                    }
                    onClick={
                      openCreateEditor
                    }
                  >
                    Add setting
                  </button>
                )
              }


              {
                currentEditor !==
                  null && (
                  <form
                    className="stack-form"
                    onSubmit={
                      saveSetting
                    }
                  >
                    <h3>
                      {
                        currentEditor.mode ===
                          'create'
                          ? 'Add setting'
                          : 'Edit setting'
                      }
                    </h3>


                    <label
                      className="control-field"
                    >
                      <span>
                        Setting key
                      </span>

                      <input
                        value={
                          currentEditor
                            .draft
                            .settingKey
                        }
                        maxLength={
                          150
                        }
                        onChange={
                          (event) =>
                            updateDraft({
                              settingKey:
                                event
                                  .target
                                  .value,
                            })
                        }
                      />
                    </label>


                    <label
                      className="control-field"
                    >
                      <span>
                        Setting value
                      </span>

                      <textarea
                        value={
                          currentEditor
                            .draft
                            .settingValue
                        }
                        onChange={
                          (event) =>
                            updateDraft({
                              settingValue:
                                event
                                  .target
                                  .value,
                            })
                        }
                      />
                    </label>


                    <label
                      className="control-field"
                    >
                      <span>
                        Value type
                      </span>

                      <input
                        value={
                          currentEditor
                            .draft
                            .valueType
                        }
                        maxLength={
                          32
                        }
                        onChange={
                          (event) =>
                            updateDraft({
                              valueType:
                                event
                                  .target
                                  .value,
                            })
                        }
                      />
                    </label>


                    {
                      formError !==
                        null && (
                        <p
                          role="alert"
                          className="status-message status-message--error"
                        >
                          {formError}
                        </p>
                      )
                    }


                    <div
                      className="button-row"
                    >
                      <button
                        type="submit"
                        className="primary-button"
                        disabled={
                          mutationBusy
                        }
                      >
                        Save setting
                      </button>

                      <button
                        type="button"
                        className="secondary-button"
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
            </section>


            {
              overview.settingsStatus ===
                'loading' && (
                <p
                  className="status-message"
                >
                  Loading system settingsâ€¦
                </p>
              )
            }


            {
              overview.settingsStatus ===
                'error' && (
                <p
                  className="status-message status-message--error"
                  role="alert"
                >
                  Unable to load system settings.
                </p>
              )
            }


            {
              overview.settingsStatus ===
                'ready' &&
              overview.settings.length ===
                0 && (
                <div
                  className="empty-state"
                >
                  No system settings configured
                </div>
              )
            }


            {
              overview.settings.map(
                (setting) => (
                  <article
                    key={
                      setting.id
                    }
                    className="surface-panel"
                  >
                    <div>
                      <p
                        className="eyebrow"
                      >
                        {
                          setting
                            .value_type
                        }
                      </p>

                      <h3>
                        {
                          setting
                            .setting_key
                        }
                      </h3>

                      <p>
                        Value:{' '}
                        {
                          setting
                            .setting_value ===
                          ''
                            ? 'Empty string'
                            : setting
                                .setting_value
                        }
                      </p>

                      <p>
                        Created:{' '}
                        {
                          setting
                            .created_at
                        }
                      </p>

                      <p>
                        Updated:{' '}
                        {
                          setting
                            .updated_at
                        }
                      </p>

                      <p>
                        Updated by:{' '}
                        {
                          displayNullable(
                            setting
                              .updated_by_user_id,
                          )
                        }
                      </p>
                    </div>


                    {
                      canManageSettings && (
                        <div
                          className="button-row"
                        >
                          <button
                            type="button"
                            className="secondary-button"
                            aria-label={
                              `Edit ${setting.setting_key}`
                            }
                            disabled={
                              mutationBusy
                            }
                            onClick={
                              () =>
                                openEditEditor(
                                  setting,
                                )
                            }
                          >
                            Edit
                          </button>

                          <button
                            type="button"
                            className="danger-button"
                            aria-label={
                              `Delete ${setting.setting_key}`
                            }
                            disabled={
                              mutationBusy
                            }
                            onClick={
                              () => {
                                void removeSetting(
                                  setting,
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
                ),
              )
            }
          </>
        )
      }
    </section>
  )
}