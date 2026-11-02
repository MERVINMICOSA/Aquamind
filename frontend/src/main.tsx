import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

import { App } from './app/App'
import './styles/index.css'

const rootElement = document.getElementById('root')

if (rootElement === null) {
  throw new Error(
    'AquaMind root element was not found.',
  )
}

createRoot(rootElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
)