import {
  Navigate,
  Route,
  Routes,
} from 'react-router-dom'

import {
  ProtectedRoute,
} from '../components/auth/ProtectedRoute'
import {
  PublicOnlyRoute,
} from '../components/auth/PublicOnlyRoute'

import {
  AppLayout,
} from '../layouts/AppLayout'

import {
  DashboardPage,
} from '../pages/DashboardPage'
import {
  LoginPage,
} from '../pages/LoginPage'
import {
  NotFoundPage,
} from '../pages/NotFoundPage'
import {
  SensorDetailPage,
} from '../pages/SensorDetailPage'
import {
  SensorsPage,
} from '../pages/SensorsPage'
import { SensorHistoryPage } from '../pages/SensorHistoryPage'
import {
  SettingsPage,
} from '../pages/SettingsPage'
import { WaterFlowPage } from '../pages/WaterFlowPage'


export function AppRoutes() {
  return (
    <Routes>
      {/* ====================================================
          PUBLIC-ONLY ROUTES
          ==================================================== */}

      <Route
        element={
          <PublicOnlyRoute />
        }
      >
        <Route
          path="/login"
          element={
            <LoginPage />
          }
        />
      </Route>


      {/* ====================================================
          AUTHENTICATED APPLICATION
          ==================================================== */}

      <Route
        element={
          <ProtectedRoute />
        }
      >
        <Route
          element={
            <AppLayout />
          }
        >
          <Route
            index
            element={
              <DashboardPage />
            }
          />


          <Route
            path="sensors"
            element={
              <SensorsPage />
            }
          />


          <Route
            path="sensors/:sensorId"
            element={
              <SensorDetailPage />
            }
          />

          <Route path="history" element={<SensorHistoryPage />} />


          <Route path="actuators" element={<Navigate to="/water-flow" replace />} />
          <Route path="actuators/:actuatorId" element={<Navigate to="/water-flow" replace />} />

          {/* Retired Feeding page; old bookmarks return to the dashboard. */}
          <Route path="feeding" element={<Navigate to="/" replace />} />

          <Route path="refill" element={<Navigate to="/water-flow" replace />} />
          <Route path="automation" element={<Navigate to="/water-flow" replace />} />

          <Route
            path="water-flow"
            element={<WaterFlowPage />}
          />

          {/* Alerts are now indicated inline on current readings and archived History. */}
          <Route path="alerts" element={<Navigate to="/sensors" replace />} />


          <Route
            path="settings"
            element={
              <SettingsPage />
            }
          />


          <Route
            path="*"
            element={
              <NotFoundPage />
            }
          />
        </Route>
      </Route>
    </Routes>
  )
}
