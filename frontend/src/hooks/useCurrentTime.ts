import {
  useEffect,
  useState,
} from 'react'


const CLOCK_INTERVAL_MS =
  1000


export function useCurrentTime():
  number {
  const [
    nowMs,
    setNowMs,
  ] = useState(
    () =>
      Date.now(),
  )


  useEffect(
    () => {
      const intervalId =
        window.setInterval(
          () => {
            setNowMs(
              Date.now(),
            )
          },
          CLOCK_INTERVAL_MS,
        )


      return () => {
        window.clearInterval(
          intervalId,
        )
      }
    },
    [],
  )


  return nowMs
}