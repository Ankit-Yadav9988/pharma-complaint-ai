import { useEffect, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import AIInsights from './components/AIInsights'
import ComplaintForm from './components/ComplaintForm'
import ComplaintRegister from './components/ComplaintRegister'
import IntakePanel from './components/IntakePanel'
import { fetchCapabilities } from './store/intakeSlice'
import { fetchComplaint } from './store/registerSlice'

export default function App() {
  const dispatch = useDispatch()
  const [view, setView] = useState('intake')
  const { analysis, capabilities } = useSelector((s) => s.intake)

  useEffect(() => {
    dispatch(fetchCapabilities())
  }, [dispatch])

  const openDuplicate = (id) => {
    dispatch(fetchComplaint(id))
    setView('register')
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">M</span>
          <div>
            Meridian QA
            <small>Complaint Intelligence Platform</small>
          </div>
        </div>

        <nav className="nav">
          <button
            type="button"
            onClick={() => setView('intake')}
            aria-current={view === 'intake' ? 'page' : undefined}
          >
            Intake
          </button>
          <button
            type="button"
            onClick={() => setView('register')}
            aria-current={view === 'register' ? 'page' : undefined}
          >
            Register
          </button>
        </nav>

      </header>

      {view === 'intake' ? (
        <main className="workspace">
          <div>
            <ComplaintForm />
            {analysis && <AIInsights analysis={analysis} onOpenDuplicate={openDuplicate} />}
          </div>
          <IntakePanel />
        </main>
      ) : (
        <ComplaintRegister />
      )}
    </div>
  )
}
