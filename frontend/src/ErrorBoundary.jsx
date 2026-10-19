import { Component } from 'react'
import { reportError } from './tracking.js'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  componentDidCatch(error, info) {
    reportError(error.message, error.stack || info?.componentStack || null)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{
          minHeight: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center',
          justifyContent: 'center', background: '#14101F', color: '#F5F3FA', padding: 24, textAlign: 'center',
          fontFamily: 'inherit',
        }}>
          <div style={{ fontSize: 40, marginBottom: 16 }}>⚠️</div>
          <div style={{ fontSize: 16, fontWeight: 800, marginBottom: 8 }}>Something went wrong</div>
          <div style={{ fontSize: 13, color: '#A29CB8', marginBottom: 24, maxWidth: 280, lineHeight: 1.5 }}>
            This has been reported automatically. Try reloading the app.
          </div>
          <button
            onClick={() => window.location.reload()}
            style={{
              background: 'linear-gradient(180deg, #E7F56E, #DFF25C)', border: 'none', color: '#16190A',
              borderRadius: 14, padding: '12px 28px', fontSize: 14, fontWeight: 800, cursor: 'pointer',
            }}
          >
            Reload
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
