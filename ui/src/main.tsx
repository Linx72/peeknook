import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { configureDesktopApi } from './api'
import DesktopStartup from './components/DesktopStartup'
import { I18nProvider } from './i18n'
import './index.css'
import App from './App.tsx'

const root = createRoot(document.getElementById('root')!)

function renderApplication() {
  root.render(
    <StrictMode>
      <I18nProvider>
        <App />
      </I18nProvider>
    </StrictMode>,
  )
}

root.render(<DesktopStartup />)
configureDesktopApi()
  .then(renderApplication)
  .catch((error) => root.render(<DesktopStartup error={error instanceof Error ? error.message : String(error)} />))
