import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import Home from './pages/Home'
import Result from './pages/Result'
import Audit from './pages/Audit'

function Navigation() {
  const location = useLocation()

  return (
    <nav className="navbar">
      <div className="nav-container">
        <div className="nav-brand">
          <span className="brand-icon">🔐</span>
          <span className="brand-text">SecurePay</span>
          <span className="brand-badge">BETA</span>
        </div>
        <div className="nav-links">
          <Link
            to="/"
            className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}
          >
            💳 Payment
          </Link>
          <Link
            to="/audit"
            className={`nav-link ${location.pathname === '/audit' ? 'active' : ''}`}
          >
            📊 Audit
          </Link>
        </div>
      </div>
    </nav>
  )
}

function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <Navigation />
        <main className="main-content">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/result" element={<Result />} />
            <Route path="/audit" element={<Audit />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
