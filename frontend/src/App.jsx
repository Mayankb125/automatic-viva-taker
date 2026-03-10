/**
 * App.jsx — Root Component with Client-Side Routing
 * ===================================================
 * Defines all URL routes for the application using React Router DOM v6.
 *
 * Student journey through the app (in order):
 *   /login      → Student enters email + password
 *   /register   → New students create an account and upload a face photo
 *   /verify     → Live face verification before each viva (identity check)
 *   /topics     → Student picks subject and topics they want to be examined on
 *   /viva       → The actual viva session (questions + answers + proctoring)
 *   /report/:id → Post-viva performance report for a specific session
 *
 * The default route "/" redirects to "/login" so visiting the app root
 * always takes the user to the login page.
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import RegistrationPage from './pages/RegistrationPage'
import VerificationPage from './pages/VerificationPage'
import TopicSelectionPage from './pages/TopicSelectionPage'
import VivaPage from './pages/VivaPage'
import ReportPage from './pages/ReportPage'

function App() {
  return (
    // BrowserRouter enables HTML5 history-based routing (clean URLs, no hash)
    <BrowserRouter>
      <Routes>
        {/* Default redirect: visiting "/" goes straight to the login page */}
        <Route path="/" element={<Navigate to="/login" replace />} />

        {/* Login — existing students sign in here */}
        <Route path="/login" element={<LoginPage />} />

        {/* Registration — new students create an account + upload face photo */}
        <Route path="/register" element={<RegistrationPage />} />

        {/* Face Verification — confirm student identity before viva starts */}
        <Route path="/verify" element={<VerificationPage />} />

        {/* Topic Selection — choose subject + topics to be examined on */}
        <Route path="/topics" element={<TopicSelectionPage />} />

        {/* Viva — the live exam session with questions and proctoring */}
        <Route path="/viva" element={<VivaPage />} />

        {/* Report — view session results after the viva ends.
            :sessionId is a URL parameter, e.g. /report/abc-123 */}
        <Route path="/report/:sessionId" element={<ReportPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
