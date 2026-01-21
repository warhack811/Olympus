import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import './styles/globals.css'
import 'katex/dist/katex.min.css'

// Hata takip sistemini initialize et
import {
  initializeSentry,
  setupGlobalErrorHandler,
  setupUnhandledRejectionHandler,
} from './lib/errorTracking'

// Sentry'yi initialize et
const sentryDsn = import.meta.env.VITE_SENTRY_DSN
const environment = import.meta.env.MODE || 'development'
initializeSentry(sentryDsn, environment)

// Global error handlers'ı ayarla
setupGlobalErrorHandler()
setupUnhandledRejectionHandler()

console.log('React Mounting started...');
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
