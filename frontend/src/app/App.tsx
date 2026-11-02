import { BrowserRouter } from 'react-router-dom'

import {
  AuthProvider,
} from '../contexts/AuthProvider'
import { AppRoutes } from './router'

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </AuthProvider>
  )
}