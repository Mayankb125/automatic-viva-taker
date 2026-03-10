/**
 * ReportPage.jsx — Post-Viva Performance Report
 * ================================================
 * Shown after the viva session ends. Displays a full breakdown of the
 * student's performance for review by both the student and the examiner.
 *
 * The session ID comes from the URL parameter: /report/:sessionId
 * (set by App.jsx routing, extracted via React Router's useParams hook)
 *
 * TODO (Phase 5 — Frontend):
 *  - On mount: GET /api/report/:sessionId to load full report JSON
 *  - Display session summary: student name, subject, topics, duration, overall score
 *  - Per-question table: question text, student answer, all 5 pillar scores, final score
 *  - Integrity timeline: list of all flags with timestamps and descriptions
 *  - "Download PDF" button: GET /api/report/:sessionId/pdf
 *  - Score visualisations: radar chart per question, bar chart of overall scores
 */

function ReportPage() {
  // Placeholder UI — full report display will be built in Phase 5
  return <div><h1>Report Page</h1></div>
}

export default ReportPage
