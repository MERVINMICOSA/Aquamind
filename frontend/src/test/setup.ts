import '@testing-library/jest-dom/vitest'

import {
  cleanup,
} from '@testing-library/react'
import {
  afterEach,
} from 'vitest'


class ResizeObserverMock implements ResizeObserver {
  observe(): void {}

  unobserve(): void {}

  disconnect(): void {}
}


globalThis.ResizeObserver = ResizeObserverMock


afterEach(() => {
  cleanup()
})