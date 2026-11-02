import type {
  AutomationRule,
  AutomationRuleUpdateInput,
  AutomationRun,
  SensorThresholdAutomationRuleInput,
} from '../types/automation'

import {
  apiRequest,
} from './apiClient'


export const AUTOMATION_RUN_HISTORY_PAGE_SIZE =
  50


export interface AutomationRunHistoryPage {
  runs: AutomationRun[]
  hasNext: boolean
  hasPrevious: boolean
  offset: number
}


export async function listAutomationRules(
  systemId: string,
): Promise<AutomationRule[]> {
  const encodedSystemId =
    encodeURIComponent(
      systemId,
    )

  return apiRequest<AutomationRule[]>(
    `automation-rules?system_id=${encodedSystemId}`,
  )
}


export async function createAutomationRule(
  systemId: string,
  input:
    SensorThresholdAutomationRuleInput,
): Promise<AutomationRule> {
  return apiRequest<AutomationRule>(
    'automation-rules',
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


export async function updateAutomationRule(
  ruleId: string,
  input:
    AutomationRuleUpdateInput,
): Promise<AutomationRule> {
  return apiRequest<AutomationRule>(
    `automation-rules/${encodeURIComponent(ruleId)}`,
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


export async function deleteAutomationRule(
  ruleId: string,
): Promise<void> {
  await apiRequest<void>(
    `automation-rules/${encodeURIComponent(ruleId)}`,
    {
      method:
        'DELETE',
    },
  )
}


export async function loadAutomationRunHistoryPage(
  ruleId: string,
  offset: number,
): Promise<AutomationRunHistoryPage> {
  const normalizedOffset =
    Math.max(
      0,
      Math.trunc(
        offset,
      ),
    )

  const encodedRuleId =
    encodeURIComponent(
      ruleId,
    )

  const result =
    await apiRequest<
      AutomationRun[]
    >(
      `automation-runs/history?rule_id=${encodedRuleId}` +
      `&limit=${AUTOMATION_RUN_HISTORY_PAGE_SIZE + 1}` +
      `&offset=${normalizedOffset}`,
    )

  return {
    runs:
      result.slice(
        0,
        AUTOMATION_RUN_HISTORY_PAGE_SIZE,
      ),

    hasNext:
      result.length >
      AUTOMATION_RUN_HISTORY_PAGE_SIZE,

    hasPrevious:
      normalizedOffset >
      0,

    offset:
      normalizedOffset,
  }
}