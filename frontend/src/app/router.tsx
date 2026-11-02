import { ActuatorDetailPage } from '../pages/ActuatorDetailPage'
import {
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
  ActuatorsPage,
} from '../pages/ActuatorsPage'
import {
  AlertsPage,
} from '../pages/AlertsPage'
import {
  AutomationPage,
} from '../pages/AutomationPage'
import {
  DashboardPage,
} from '../pages/DashboardPage'
import {
  FeedingPage,
} from '../pages/FeedingPage'
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
import {
  SettingsPage,
} from '../pages/SettingsPage'
import {
  RefillPage,
} from '../pages/RefillPage'


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


          <Route
            path="actuators"
            element={
              <ActuatorsPage />
            }
          />


          <Route
            path="actuators/:actuatorId"
            element={<ActuatorDetailPage />}
          />

          <Route
            path="feeding"
            element={
              <FeedingPage />
            }
          />

          <Route
            path="refill"
            element={
              <RefillPage />
            }
          />

          <Route
            path="automation"
            element={
              <AutomationPage />
            }
          />


          <Route
            path="alerts"
            element={
              <AlertsPage />
            }
          />


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
