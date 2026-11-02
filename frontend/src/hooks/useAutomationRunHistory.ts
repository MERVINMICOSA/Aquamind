import {
  useEffect,
  useState,
} from 'react'

import {
  AUTOMATION_RUN_HISTORY_PAGE_SIZE,
  loadAutomationRunHistoryPage,
} from '../services/automationService'

import type {
  AutomationRunHistoryPage,
} from '../services/automationService'

import type {
  AutomationRule,
} from '../types/automation'


type LoadStatus =
  | 'loading'
  | 'ready'
  | 'error'


interface PageState {
  ruleId: string | null
  offset: number
}


interface HistoryState {
  ruleId: string
  offset: number
  data: AutomationRunHistoryPage | null
  status: LoadStatus
}


export function useAutomationRunHistory(
  rules: AutomationRule[],
) {
  const [
    page,
    setPage,
  ] = useState<PageState>({
    ruleId:
      null,

    offset:
      0,
  })

  const [
    history,
    setHistory,
  ] = useState<HistoryState | null>(
    null,
  )


  /*
   * Keep the selected rule valid without synchronously
   * setting state from an effect.
   *
   * If the stored selection does not belong to the current
   * rule collection, the first current rule becomes the
   * effective selection and pagination returns to page one.
   */
  const pageRuleIsCurrent =
    page.ruleId !==
      null &&
    rules.some(
      (rule) =>
        rule.id ===
        page.ruleId,
    )


  const selectedRuleId =
    pageRuleIsCurrent
      ? page.ruleId
      : rules[0]?.id ??
        null


  const selectedRule =
    rules.find(
      (rule) =>
        rule.id ===
        selectedRuleId,
    ) ?? null


  const offset =
    page.ruleId ===
      selectedRuleId
      ? page.offset
      : 0


  // ==========================================================
  // HISTORY LOAD
  // ==========================================================

  useEffect(
    () => {
      if (
        selectedRuleId ===
        null
      ) {
        return
      }

      const ruleId =
        selectedRuleId

      let active =
        true

      async function load() {
        try {
          const data =
            await loadAutomationRunHistoryPage(
              ruleId,
              offset,
            )

          if (!active) {
            return
          }

          setHistory({
            ruleId,
            offset,
            data,
            status:
              'ready',
          })
        } catch {
          if (!active) {
            return
          }

          setHistory({
            ruleId,
            offset,
            data:
              null,
            status:
              'error',
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
      selectedRuleId,
      offset,
    ],
  )


  /*
   * Never expose history belonging to a previous rule or
   * page while another request is in flight.
   */
  const currentHistory =
    history?.ruleId ===
      selectedRuleId &&
    history.offset ===
      offset
      ? history
      : null


  const historyStatus:
    LoadStatus =
    selectedRuleId ===
      null
      ? 'ready'
      : currentHistory?.status ??
        'loading'


  const hasNext =
    currentHistory
      ?.data
      ?.hasNext ??
    false


  const hasPrevious =
    offset >
    0


  const runs =
    currentHistory
      ?.data
      ?.runs ??
    []


  const pageNumber =
    Math.floor(
      offset /
        AUTOMATION_RUN_HISTORY_PAGE_SIZE,
    ) + 1


  // ==========================================================
  // PUBLIC API
  // ==========================================================

  return {
    selectedRuleId,
    selectedRule,

    runs,
    historyStatus,

    hasNext,
    hasPrevious,
    pageNumber,

    selectRule(
      ruleId: string,
    ) {
      const exists =
        rules.some(
          (rule) =>
            rule.id ===
            ruleId,
        )

      if (!exists) {
        return
      }

      setPage({
        ruleId,
        offset:
          0,
      })
    },

    nextPage() {
      if (
        selectedRuleId ===
          null ||
        historyStatus !==
          'ready' ||
        !hasNext
      ) {
        return
      }

      setPage({
        ruleId:
          selectedRuleId,

        offset:
          offset +
          AUTOMATION_RUN_HISTORY_PAGE_SIZE,
      })
    },

    previousPage() {
      if (
        selectedRuleId ===
          null ||
        historyStatus ===
          'loading' ||
        offset <=
          0
      ) {
        return
      }

      setPage({
        ruleId:
          selectedRuleId,

        offset:
          Math.max(
            0,
            offset -
              AUTOMATION_RUN_HISTORY_PAGE_SIZE,
          ),
      })
    },
  }
}