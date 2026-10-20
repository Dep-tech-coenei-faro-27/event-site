import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './home.css'
import './checkout.css'
import './checkout.overrides.css'
import './estado.css'
import './motion.css'
import App from './App.tsx'
import ErrorBoundary from './components/ErrorBoundary.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary standalone>
      <App />
    </ErrorBoundary>
  </StrictMode>,
)
