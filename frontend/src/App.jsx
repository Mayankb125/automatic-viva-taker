import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import RegistrationPage from './pages/RegistrationPage'
import VerificationPage from './pages/VerificationPage'
import TopicSelectionPage from './pages/TopicSelectionPage'
import VivaPage from './pages/VivaPage'
import ReportPage from './pages/ReportPage'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegistrationPage />} />
        <Route path="/verify" element={<VerificationPage />} />
        <Route path="/topics" element={<TopicSelectionPage />} />
        <Route path="/viva" element={<VivaPage />} />
        <Route path="/report/:sessionId" element={<ReportPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
