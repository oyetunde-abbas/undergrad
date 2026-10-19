const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Fire-and-forget on purpose — tracking/error-reporting should never block
// the UI or throw if the network happens to be down.
export function trackEvent(eventName, eventData = null) {
  fetch(`${API_BASE}/track/event`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include', // sends the httpOnly auth cookie if logged in; fine either way, backend treats this as optional
    body: JSON.stringify({ event_name: eventName, event_data: eventData }),
  }).catch(() => {})
}

export function reportError(message, stack = null, path = null, severity = 'error') {
  fetch(`${API_BASE}/track/error`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ message, stack, path: path || window.location.pathname, severity }),
  }).catch(() => {})
}

// Catches errors that happen outside React's render cycle — e.g. inside
// event handlers, timers, or a rejected promise that nobody awaited.
// React render errors are handled separately by ErrorBoundary.jsx, since
// window.onerror doesn't catch those.
export function installGlobalErrorTracking() {
  window.addEventListener('error', (event) => {
    reportError(event.message, event.error?.stack || null)
  })
  window.addEventListener('unhandledrejection', (event) => {
    const reason = event.reason
    reportError(
      typeof reason === 'string' ? reason : reason?.message || 'Unhandled promise rejection',
      reason?.stack || null,
      null,
      'warning'
    )
  })
}

// PWA install tracking — fires once, whenever the browser reports the app
// was actually added to the home screen (not just that the prompt showed).
export function installPwaTracking() {
  window.addEventListener('appinstalled', () => {
    trackEvent('pwa_installed')
  })
}
