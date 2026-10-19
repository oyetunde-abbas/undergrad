import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import ErrorBoundary from './ErrorBoundary.jsx'
import { installGlobalErrorTracking, installPwaTracking } from './tracking.js'
import './App.css'

installGlobalErrorTracking()
installPwaTracking()

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  </React.StrictMode>
)

// Register the service worker for installability + app-shell caching.
// Wrapped defensively — should never block or break the app if registration
// fails (unsupported browser, dev server quirks, etc.)
if ('serviceWorker' in navigator) {
  if (import.meta.env.PROD) {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('/service-worker.js').catch((err) => {
        console.warn('Service worker registration failed:', err)
      })
    })
  } else {
    // Dev server: a service worker would serve stale copies of src/ files (the
    // "old design" problem). Remove any worker and cache left over from earlier runs.
    navigator.serviceWorker.getRegistrations().then((regs) => regs.forEach((r) => r.unregister())).catch(() => {})
    if (window.caches) caches.keys().then((keys) => keys.forEach((k) => caches.delete(k))).catch(() => {})
  }
}
