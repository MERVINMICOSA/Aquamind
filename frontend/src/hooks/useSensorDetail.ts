import {
  useEffect,
  useState,
} from 'react'

import {
  getSensor,
  loadSensorHistoryPage,
  SENSOR_HISTORY_PAGE_SIZE,
} from '../services/sensorService'

import type {
  DashboardSensor,
  DashboardSensorReading,
} from '../types/dashboard'


type LoadStatus =
  | 'idle'
  | 'loading'
  | 'ready'
  | 'error'


interface PageState {
  sensorId: string | null
  offset: number
}


export function useSensorDetail(
  sensorId: string | undefined,
) {
  const currentSensorId =
    sensorId ?? null


  const [
    sensor,
    setSensor,
  ] = useState<DashboardSensor | null>(
    null,
  )


  const [
    readings,
    setReadings,
  ] = useState<
    DashboardSensorReading[]
  >(
    [],
  )


  const [
    latestReading,
    setLatestReading,
  ] = useState<
    DashboardSensorReading | null
  >(
    null,
  )


  const [
    sensorStatus,
    setSensorStatus,
  ] = useState<LoadStatus>(
    'idle',
  )


  const [
    historyStatus,
    setHistoryStatus,
  ] = useState<LoadStatus>(
    'idle',
  )


  const [
    sensorErrorMessage,
    setSensorErrorMessage,
  ] = useState<string | null>(
    null,
  )


  const [
    historyErrorMessage,
    setHistoryErrorMessage,
  ] = useState<string | null>(
    null,
  )


  const [
    hasNext,
    setHasNext,
  ] = useState(
    false,
  )


  const [
    hasPrevious,
    setHasPrevious,
  ] = useState(
    false,
  )


  /*
   * Associate the pagination state with the sensor ID.
   *
   * If React ever reuses this component for another
   * sensor route, the effective offset automatically
   * becomes zero without needing a synchronous state
   * reset inside an effect.
   */
  const [
    pageState,
    setPageState,
  ] = useState<PageState>({
    sensorId:
      currentSensorId,

    offset:
      0,
  })


  const offset =
    pageState.sensorId ===
    currentSensorId
      ? pageState.offset
      : 0


  // =========================================================
  // SENSOR
  // =========================================================


  useEffect(() => {
    if (
      currentSensorId === null
    ) {
      return
    }

    const activeSensorId =
      currentSensorId

    let active =
      true


    async function loadSensor():
      Promise<void> {
      try {
        setSensorStatus(
          'loading',
        )

        setSensorErrorMessage(
          null,
        )

        const result =
          await getSensor(
            activeSensorId,
          )

        if (!active) {
          return
        }

        setSensor(
          result,
        )

        setSensorStatus(
          'ready',
        )
      } catch {
        if (!active) {
          return
        }

        setSensor(
          null,
        )

        setSensorErrorMessage(
          'Unable to load this sensor.',
        )

        setSensorStatus(
          'error',
        )
      }
    }


    void loadSensor()


    return () => {
      active = false
    }
  }, [
    currentSensorId,
  ])


  // =========================================================
  // HISTORY
  // =========================================================


  useEffect(() => {
    if (
      currentSensorId === null
    ) {
      return
    }

    const activeSensorId =
      currentSensorId

    const activeOffset =
      offset

    let active =
      true


    async function loadHistory():
      Promise<void> {
      try {
        setHistoryStatus(
          'loading',
        )

        setHistoryErrorMessage(
          null,
        )

        /*
         * The newest persisted reading is learned from
         * the first history page only.
         */
        if (
          activeOffset === 0
        ) {
          setLatestReading(
            null,
          )
        }

        const result =
          await loadSensorHistoryPage(
            activeSensorId,
            activeOffset,
          )

        if (!active) {
          return
        }

        setReadings(
          result.readings,
        )

        setHasNext(
          result.hasNext,
        )

        setHasPrevious(
          result.hasPrevious,
        )

        if (
          activeOffset === 0
        ) {
          setLatestReading(
            result.readings[0] ??
              null,
          )
        }

        setHistoryStatus(
          'ready',
        )
      } catch {
        if (!active) {
          return
        }

        setReadings(
          [],
        )

        setHasNext(
          false,
        )

        setHasPrevious(
          activeOffset > 0,
        )

        if (
          activeOffset === 0
        ) {
          setLatestReading(
            null,
          )
        }

        setHistoryErrorMessage(
          'Unable to load sensor reading history.',
        )

        setHistoryStatus(
          'error',
        )
      }
    }


    void loadHistory()


    return () => {
      active = false
    }
  }, [
    currentSensorId,
    offset,
  ])


  // =========================================================
  // PAGINATION
  // =========================================================


  function nextPage():
    void {
    if (
      currentSensorId === null ||
      !hasNext
    ) {
      return
    }

    setPageState({
      sensorId:
        currentSensorId,

      offset:
        offset +
        SENSOR_HISTORY_PAGE_SIZE,
    })
  }


  function previousPage():
    void {
    if (
      currentSensorId === null ||
      offset === 0
    ) {
      return
    }

    setPageState({
      sensorId:
        currentSensorId,

      offset:
        Math.max(
          0,
          offset -
            SENSOR_HISTORY_PAGE_SIZE,
        ),
    })
  }


  const pageNumber =
    Math.floor(
      offset /
        SENSOR_HISTORY_PAGE_SIZE,
    ) +
    1


  return {
    sensor,
    latestReading,
    readings,

    sensorStatus,
    historyStatus,

    sensorErrorMessage,
    historyErrorMessage,

    hasNext,
    hasPrevious,

    offset,
    pageNumber,

    nextPage,
    previousPage,
  }
}