import {
  useEffect,
  useMemo,
  useState,
} from 'react'

import {
  listSystems,
} from '../services/dashboardService'

import {
  createSystemSetting,
  deleteSystemSetting,
  listSystemSettings,
  updateSystemSetting,
} from '../services/settingsService'

import type {
  SystemSetting,
  SystemSettingInput,
  SystemSettingUpdateInput,
} from '../types/settings'

import type {
  AquaponicsSystem,
} from '../types/dashboard'


type LoadStatus =
  | 'loading'
  | 'ready'
  | 'error'


type MutationStatus =
  | 'idle'
  | 'saving'
  | 'deleting'
  | 'error'


interface SettingsState {
  systemId: string
  revision: number
  status: LoadStatus
  data: SystemSetting[]
}


interface MutationState {
  systemId: string
  status: MutationStatus
  errorMessage: string | null
}


function mutationErrorMessage(
  action: 'save' | 'delete',
): string {
  return action === 'save'
    ? 'Unable to save system setting.'
    : 'Unable to delete system setting.'
}


export function useSettingsOverview() {
  const [
    systems,
    setSystems,
  ] = useState<AquaponicsSystem[]>(
    [],
  )

  const [
    systemsStatus,
    setSystemsStatus,
  ] = useState<LoadStatus>(
    'loading',
  )

  const [
    selectedSystemId,
    setSelectedSystemId,
  ] = useState<string | null>(
    null,
  )

  const [
    revision,
    setRevision,
  ] = useState(
    0,
  )

  const [
    settingsState,
    setSettingsState,
  ] = useState<SettingsState | null>(
    null,
  )

  const [
    mutationState,
    setMutationState,
  ] = useState<MutationState | null>(
    null,
  )


  // ==========================================================
  // SYSTEMS
  // ==========================================================

  useEffect(
    () => {
      let active =
        true

      async function load() {
        try {
          const result =
            await listSystems()

          if (!active) {
            return
          }

          const ordered =
            [...result].sort(
              (left, right) =>
                left.name.localeCompare(
                  right.name,
                ),
            )

          setSystems(
            ordered,
          )

          setSelectedSystemId(
            ordered[0]?.id ??
            null,
          )

          setSystemsStatus(
            'ready',
          )
        } catch {
          if (!active) {
            return
          }

          setSystems(
            [],
          )

          setSelectedSystemId(
            null,
          )

          setSystemsStatus(
            'error',
          )
        }
      }

      void load()

      return () => {
        active =
          false
      }
    },
    [],
  )


  // ==========================================================
  // SETTINGS FOR SELECTED SYSTEM
  // ==========================================================

  useEffect(
    () => {
      if (
        selectedSystemId ===
        null
      ) {
        return
      }

      const systemId =
        selectedSystemId

      const currentRevision =
        revision

      let active =
        true

      async function load() {
        try {
          const settings =
            await listSystemSettings(
              systemId,
            )

          if (!active) {
            return
          }

          setSettingsState({
            systemId,

            revision:
              currentRevision,

            status:
              'ready',

            data:
              settings,
          })
        } catch {
          if (!active) {
            return
          }

          setSettingsState({
            systemId,

            revision:
              currentRevision,

            status:
              'error',

            data:
              [],
          })
        }
      }

      void load()

      return () => {
        active =
          false
      }
    },
    [
      selectedSystemId,
      revision,
    ],
  )


  // ==========================================================
  // CURRENT SYSTEM STATE
  // ==========================================================

  const selectedSystem =
    systems.find(
      (system) =>
        system.id ===
        selectedSystemId,
    ) ?? null


  const settingsStateIsCurrent =
    settingsState?.systemId ===
      selectedSystemId &&
    settingsState.revision ===
      revision


  const settings =
    useMemo(
      () =>
        settingsStateIsCurrent
          ? settingsState?.data ??
            []
          : [],
      [
        settingsState,
        settingsStateIsCurrent,
      ],
    )


  const settingsStatus:
    LoadStatus =
    settingsStateIsCurrent
      ? settingsState?.status ??
        'loading'
      : selectedSystemId ===
          null
        ? 'ready'
        : 'loading'


  const mutationStatus:
    MutationStatus =
    mutationState?.systemId ===
      selectedSystemId
      ? mutationState.status
      : 'idle'


  const mutationError =
    mutationState?.systemId ===
      selectedSystemId
      ? mutationState.errorMessage
      : null


  function refresh() {
    setRevision(
      (current) =>
        current + 1,
    )
  }


  // ==========================================================
  // CREATE
  // ==========================================================

  async function createSetting(
    input: SystemSettingInput,
  ): Promise<boolean> {
    if (
      selectedSystemId ===
      null
    ) {
      return false
    }

    const systemId =
      selectedSystemId

    setMutationState({
      systemId,

      status:
        'saving',

      errorMessage:
        null,
    })

    try {
      await createSystemSetting(
        systemId,
        input,
      )

      setMutationState({
        systemId,

        status:
          'idle',

        errorMessage:
          null,
      })

      refresh()

      return true
    } catch {
      setMutationState({
        systemId,

        status:
          'error',

        errorMessage:
          mutationErrorMessage(
            'save',
          ),
      })

      return false
    }
  }


  // ==========================================================
  // UPDATE
  // ==========================================================

  async function updateSetting(
    settingId: string,
    input:
      SystemSettingUpdateInput,
  ): Promise<boolean> {
    if (
      selectedSystemId ===
      null
    ) {
      return false
    }

    const systemId =
      selectedSystemId

    setMutationState({
      systemId,

      status:
        'saving',

      errorMessage:
        null,
    })

    try {
      await updateSystemSetting(
        settingId,
        input,
      )

      setMutationState({
        systemId,

        status:
          'idle',

        errorMessage:
          null,
      })

      refresh()

      return true
    } catch {
      setMutationState({
        systemId,

        status:
          'error',

        errorMessage:
          mutationErrorMessage(
            'save',
          ),
      })

      return false
    }
  }


  // ==========================================================
  // DELETE
  // ==========================================================

  async function deleteSetting(
    settingId: string,
  ): Promise<boolean> {
    if (
      selectedSystemId ===
      null
    ) {
      return false
    }

    const systemId =
      selectedSystemId

    setMutationState({
      systemId,

      status:
        'deleting',

      errorMessage:
        null,
    })

    try {
      await deleteSystemSetting(
        settingId,
      )

      setMutationState({
        systemId,

        status:
          'idle',

        errorMessage:
          null,
      })

      refresh()

      return true
    } catch {
      setMutationState({
        systemId,

        status:
          'error',

        errorMessage:
          mutationErrorMessage(
            'delete',
          ),
      })

      return false
    }
  }


  // ==========================================================
  // PUBLIC API
  // ==========================================================

  return {
    systems,
    systemsStatus,

    selectedSystemId,
    selectedSystem,

    settings,
    settingsStatus,

    mutationStatus,
    mutationError,

    selectSystem(
      systemId: string,
    ) {
      if (
        systemId ===
        selectedSystemId
      ) {
        return
      }

      setMutationState(
        null,
      )

      setSelectedSystemId(
        systemId,
      )
    },

    createSetting,
    updateSetting,
    deleteSetting,

    refresh,
  }
}