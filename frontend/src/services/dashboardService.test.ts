import {
  beforeEach,
  describe,
  expect,
  it,
  vi,
} from 'vitest'

import {
  apiRequest,
} from './apiClient'

import {
  listSystems,
  loadSystemDashboardOverview,
} from './dashboardService'


vi.mock(
  './apiClient',
  () => ({
    apiRequest: vi.fn(),
  }),
)


describe(
  'dashboard service',
  () => {
    beforeEach(() => {
      vi.clearAllMocks()
    })


    it(
      'loads AquaMind systems',
      async () => {
        vi.mocked(
          apiRequest,
        ).mockResolvedValueOnce(
          [],
        )

        await listSystems()

        expect(
          apiRequest,
        ).toHaveBeenCalledWith(
          'systems',
        )
      },
    )


    it(
      'loads system dashboard resources using the selected system id',
      async () => {
        vi.mocked(
          apiRequest,
        )
          .mockResolvedValueOnce(
            [],
          )
          .mockResolvedValueOnce(
            [],
          )
          .mockResolvedValueOnce(
            [],
          )
          .mockResolvedValueOnce(
            [],
          )

        await loadSystemDashboardOverview(
          'system-1',
        )

        expect(
          apiRequest,
        ).toHaveBeenCalledWith(
          'sensors?system_id=system-1',
        )

        expect(
          apiRequest,
        ).toHaveBeenCalledWith(
          'actuators?system_id=system-1',
        )

        expect(
          apiRequest,
        ).toHaveBeenCalledWith(
          'alerts?system_id=system-1',
        )

        expect(
          apiRequest,
        ).toHaveBeenCalledWith(
          'sensor-readings/latest?system_id=system-1',
        )
        
      },
    )
  },
)