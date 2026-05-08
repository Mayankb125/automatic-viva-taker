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
import StartPage from './pages/StartPage'
import LoginPage from './pages/LoginPage'
import RegistrationPage from './pages/RegistrationPage'
import VerificationPage from './pages/VerificationPage'
import TopicSelectionPage from './pages/TopicSelectionPage'
import VivaPage from './pages/VivaPage'
import ReportPage from './pages/ReportPage'
import TeacherReviewPage from './pages/TeacherReviewPage'

function App() {
  return (
    // BrowserRouter enables HTML5 history-based routing (clean URLs, no hash)
    <BrowserRouter
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true,
      }}
    >
      <Routes>
        {/* Phase 3: route root to the knowledge start page. */}
        <Route path="/" element={<Navigate to="/start" replace />} />

        {/* Start — upload source material and preview chunking. */}
        <Route path="/start" element={<StartPage />} />

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

        {/* Teacher Review — review flagged answers and adjust scores (Phase 5 Step 5.3) */}
        <Route path="/teacher/review" element={<TeacherReviewPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
