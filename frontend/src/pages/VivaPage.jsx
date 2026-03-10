/**
 * VivaPage.jsx — Live Viva Examination Screen
 * =============================================
 * The main exam screen. This is the most complex page in the app.
 * It runs the full question-answer loop with proctoring running in parallel.
 *
 * TODO (Phase 3 — Frontend):
 *
 * Question panel:
 *  - On mount: GET /api/viva/question to fetch the first question
 *  - Display question text (also spoken aloud via TTS if enabled)
 *  - Show current difficulty level and topic
 *
 * Answer input:
 *  - Voice recording via MediaRecorder API (speech-to-text for the answer)
 *  - OR typed text input as fallback
 *  - Submit button: POST /api/viva/answer with the transcribed answer text
 *  - After submit: display score breakdown, then auto-fetch next question
 *
 * Proctoring (runs in background every 2 seconds):
 *  - Capture webcam frame → POST /api/cv/analyze
 *  - If flag returned: show warning overlay on screen
 *
 * Session controls:
 *  - "End Viva" button: POST /api/session/end → redirect to /report/:sessionId
 *  - "Switch Topic" button: POST /api/session/switch-topic
 */

function VivaPage() {
  // Placeholder UI — full Q&A + proctoring UI will be built in Phase 3
  return <div><h1>Viva Page</h1></div>
}

export default VivaPage
