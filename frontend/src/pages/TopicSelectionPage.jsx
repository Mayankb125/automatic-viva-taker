/**
 * TopicSelectionPage.jsx — Subject and Topic Picker
 * ===================================================
 * After identity verification, the student chooses what they want to
 * be examined on before the viva begins.
 *
 * TODO (Phase 3 — Frontend):
 *  - On mount: GET /api/topics to load all subjects and their topic lists
 *  - Subject dropdown (e.g. "Computer Science", "Electronics")
 *  - Checkboxes for topics under the chosen subject
 *  - Require at least 1 topic selected before enabling "Start Viva"
 *  - On submit: POST /api/session/start with selected topics, redirect to /viva
 */

function TopicSelectionPage() {
  // Placeholder UI — subject/topic selection UI will be built in Phase 3
  return <div><h1>Topic Selection Page</h1></div>
}

export default TopicSelectionPage
