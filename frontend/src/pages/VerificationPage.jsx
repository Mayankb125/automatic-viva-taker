/**
 * VerificationPage.jsx — Live Face Verification
 * ================================================
 * Shown after login and before every viva session. The student must pass
 * face verification to prove they are who they registered as.
 *
 * TODO (Phase 3 — Frontend):
 *  - Display a live webcam feed
 *  - Capture a frame and send it to POST /api/auth/verify-face
 *  - Show "Verified ✓" overlay on match, "Face not recognised" on failure
 *  - On success: redirect to /topics
 *  - On 3 failed attempts: log out and redirect to /login
 */

function VerificationPage() {
  // Placeholder UI — webcam capture + face check will be built in Phase 3
  return <div><h1>Verification Page</h1></div>
}

export default VerificationPage
