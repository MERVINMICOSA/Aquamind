import { describe, expect, it } from 'vitest'
import { philippineDayStart, philippineDayEnd, philippineIso } from './esp32HistoryTime'

describe('Philippine history dates', () => {
  it('uses Manila midnight independent of browser timezone', () => {
    expect(philippineDayStart('2026-11-12')).toBe('2026-11-11T16:00:00.000Z')
    expect(philippineDayEnd('2026-11-12')).toBe('2026-11-12T16:00:00.000Z')
  })
  it('exports an explicit Philippine offset', () => {
    expect(philippineIso('2026-11-12T00:00:01Z')).toBe('2026-11-12T08:00:01.000+08:00')
  })
})
