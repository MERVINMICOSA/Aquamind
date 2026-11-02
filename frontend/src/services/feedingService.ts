import type {
  FeederCalibration,
  FeederCalibrationInput,
  FeederCalibrationUpdateInput,
  FeedingEvent,
  FeedingSchedule,
  FeedingScheduleInput,
  FeedingScheduleUpdateInput,
  FishPopulationInput,
  FishPopulationRecord,
  FishPopulationUpdateInput,
} from '../types/feeding'

import {
  apiRequest,
} from './apiClient'


export const FEEDING_HISTORY_PAGE_SIZE = 50

export const CALIBRATION_HISTORY_PAGE_SIZE = 50

export const POPULATION_HISTORY_PAGE_SIZE = 50


export interface FeedingEventHistoryPage {
  events: FeedingEvent[]
  hasNext: boolean
  hasPrevious: boolean
  offset: number
}


export interface FeederCalibrationHistoryPage {
  calibrations: FeederCalibration[]
  hasNext: boolean
  hasPrevious: boolean
  offset: number
}

export interface FishPopulationHistoryPage {
  records: FishPopulationRecord[]
  hasNext: boolean
  hasPrevious: boolean
  offset: number
}


export async function listFeedingSchedules(
  systemId: string,
): Promise<FeedingSchedule[]> {
  const encodedSystemId =
    encodeURIComponent(
      systemId,
    )

  return apiRequest<FeedingSchedule[]>(
    `feeding/schedules?system_id=${encodedSystemId}`,
  )
}


export async function createFeedingSchedule(
  systemId: string,
  input: FeedingScheduleInput,
): Promise<FeedingSchedule> {
  return apiRequest<FeedingSchedule>(
    'feeding/schedules',
    {
      method: 'POST',

      body: JSON.stringify({
        system_id: systemId,
        ...input,
      }),
    },
  )
}


export async function updateFeedingSchedule(
  scheduleId: string,
  input: FeedingScheduleUpdateInput,
): Promise<FeedingSchedule> {
  return apiRequest<FeedingSchedule>(
    `feeding/schedules/${encodeURIComponent(scheduleId)}`,
    {
      method: 'PATCH',
      body: JSON.stringify(input),
    },
  )
}


export async function deleteFeedingSchedule(
  scheduleId: string,
): Promise<void> {
  await apiRequest<void>(
    `feeding/schedules/${encodeURIComponent(scheduleId)}`,
    {
      method: 'DELETE',
    },
  )
}


export async function loadFeederCalibrationHistoryPage(
  actuatorId: string,
  offset: number,
): Promise<FeederCalibrationHistoryPage> {
  const normalizedOffset =
    Math.max(
      0,
      Math.trunc(offset),
    )

  const encodedActuatorId =
    encodeURIComponent(
      actuatorId,
    )

  const calibrations =
    await apiRequest<FeederCalibration[]>(
      `feeding/calibrations/history?actuator_id=${encodedActuatorId}` +
      `&limit=${CALIBRATION_HISTORY_PAGE_SIZE + 1}` +
      `&offset=${normalizedOffset}`,
    )

  return {
    calibrations:
      calibrations.slice(
        0,
        CALIBRATION_HISTORY_PAGE_SIZE,
      ),

    hasNext:
      calibrations.length >
      CALIBRATION_HISTORY_PAGE_SIZE,

    hasPrevious:
      normalizedOffset > 0,

    offset:
      normalizedOffset,
  }
}


export async function createFeederCalibration(
  actuatorId: string,
  input: FeederCalibrationInput,
): Promise<FeederCalibration> {
  return apiRequest<FeederCalibration>(
    'feeding/calibrations',
    {
      method: 'POST',

      body: JSON.stringify({
        actuator_id: actuatorId,
        ...input,
      }),
    },
  )
}


export async function updateFeederCalibration(
  calibrationId: string,
  input: FeederCalibrationUpdateInput,
): Promise<FeederCalibration> {
  return apiRequest<FeederCalibration>(
    `feeding/calibrations/${encodeURIComponent(calibrationId)}`,
    {
      method: 'PATCH',
      body: JSON.stringify(input),
    },
  )
}


export async function deleteFeederCalibration(
  calibrationId: string,
): Promise<void> {
  await apiRequest<void>(
    `feeding/calibrations/${encodeURIComponent(calibrationId)}`,
    {
      method: 'DELETE',
    },
  )
}


export async function loadFeedingEventHistoryPage(
  systemId: string,
  offset: number,
): Promise<FeedingEventHistoryPage> {
  const normalizedOffset =
    Math.max(
      0,
      Math.trunc(offset),
    )

  const encodedSystemId =
    encodeURIComponent(
      systemId,
    )

  const events =
    await apiRequest<FeedingEvent[]>(
      `feeding/events/history?system_id=${encodedSystemId}` +
      `&limit=${FEEDING_HISTORY_PAGE_SIZE + 1}` +
      `&offset=${normalizedOffset}`,
    )

  return {
    events:
      events.slice(
        0,
        FEEDING_HISTORY_PAGE_SIZE,
      ),

    hasNext:
      events.length >
      FEEDING_HISTORY_PAGE_SIZE,

    hasPrevious:
      normalizedOffset > 0,

    offset:
      normalizedOffset,
  }
}

export async function loadFishPopulationHistoryPage(
  tankId: string,
  offset: number,
): Promise<FishPopulationHistoryPage> {
  const normalizedOffset =
    Math.max(
      0,
      Math.trunc(offset),
    )

  const encodedTankId =
    encodeURIComponent(
      tankId,
    )

  const records =
    await apiRequest<FishPopulationRecord[]>(
      `feeding/population/history?tank_id=${encodedTankId}` +
      `&limit=${POPULATION_HISTORY_PAGE_SIZE + 1}` +
      `&offset=${normalizedOffset}`,
    )

  return {
    records:
      records.slice(
        0,
        POPULATION_HISTORY_PAGE_SIZE,
      ),

    hasNext:
      records.length >
      POPULATION_HISTORY_PAGE_SIZE,

    hasPrevious:
      normalizedOffset > 0,

    offset:
      normalizedOffset,
  }
}


export async function createFishPopulationRecord(
  tankId: string,
  input: FishPopulationInput,
): Promise<FishPopulationRecord> {
  return apiRequest<FishPopulationRecord>(
    'feeding/population',
    {
      method: 'POST',

      body: JSON.stringify({
        tank_id: tankId,
        ...input,
      }),
    },
  )
}


export async function updateFishPopulationRecord(
  recordId: string,
  input: FishPopulationUpdateInput,
): Promise<FishPopulationRecord> {
  return apiRequest<FishPopulationRecord>(
    `feeding/population/${encodeURIComponent(recordId)}`,
    {
      method: 'PATCH',
      body: JSON.stringify(input),
    },
  )
}


export async function deleteFishPopulationRecord(
  recordId: string,
): Promise<void> {
  await apiRequest<void>(
    `feeding/population/${encodeURIComponent(recordId)}`,
    {
      method: 'DELETE',
    },
  )
}