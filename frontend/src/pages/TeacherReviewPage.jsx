/**
 * TeacherReviewPage.jsx
 * ======================
 * Phase 5 Step 5.3 - Teacher review panel for flagged answers
 * Shows flagged answers with comparison view and manual override options
 */

import { useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'

import '../styles/TeacherReviewPage.css'

function TeacherReviewPage() {
  const location = useLocation()
  const [sessions, setSessions] = useState([])
  const [selectedSession, setSelectedSession] = useState(null)
  const [flaggedAnswers, setFlaggedAnswers] = useState([])
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [expandedAnswerId, setExpandedAnswerId] = useState(null)
  const [overrides, setOverrides] = useState({})
  const [overrideNotes, setOverrideNotes] = useState({})

  const sessionIdFromState = location.state?.sessionId

  // In a real app, these would come from the backend
  const mockFlaggedAnswers = [
    {
      id: 'answer_001',
      question_id: 'q_001',
      question_text: 'Explain the carbon cycle.',
      student_answer: 'Carbon goes into the air from plants and animals.',
      original_score: 5.5,
      overridden_score: null,
      override_reason: null,
      comparison: {
        legacy: {
          score: 5.5,
          band: 'partial',
          breakdown: {
            semantic_score: 6.0,
            keyword_score: 5.0,
            depth_score: 5.5,
            completeness_score: 4.5,
            confidence_score: 6.0,
            weighted_score: 5.4,
          },
          feedback: {
            summary: 'Partial understanding shown.',
            recommendation: 'Add more detail about fossil fuels and ocean storage.',
          },
        },
        grounded: {
          score: 6.2,
          band: 'partial',
          breakdown: {
            semantic_score: 6.5,
            keyword_score: 5.5,
            depth_score: 6.0,
            completeness_score: 5.5,
            confidence_score: 6.0,
            weighted_score: 6.1,
          },
          feedback: {
            summary: 'Good concept foundation with room for expansion.',
            recommendation: 'Include geological processes and human impact.',
          },
        },
        difference: {
          score_delta: 0.7,
          higher_score: 'grounded',
        },
      },
      flags: ['incomplete_answer', 'missing_key_concepts'],
      flagged_at: '2024-04-20T14:30:00Z',
    },
    {
      id: 'answer_002',
      question_id: 'q_002',
      question_text: 'What is photosynthesis?',
      student_answer: 'Its when plants use light to make food.',
      original_score: 4.2,
      overridden_score: null,
      override_reason: null,
      comparison: {
        legacy: {
          score: 4.2,
          band: 'weak',
          feedback: {
            summary: 'Minimal understanding indicated.',
            recommendation: 'Cover chemical equation and chlorophyll role.',
          },
        },
        grounded: {
          score: 5.1,
          band: 'partial',
          feedback: {
            summary: 'Basic concept present but terminology lacking.',
            recommendation: 'Add ATP, glucose, and water details.',
          },
        },
        difference: {
          score_delta: 0.9,
          higher_score: 'grounded',
        },
      },
      flags: ['terminology_mismatch', 'low_depth'],
      flagged_at: '2024-04-20T14:35:00Z',
    },
  ]

  useEffect(() => {
    // Load sessions when component mounts
    if (sessionIdFromState) {
      setSelectedSession(sessionIdFromState)
      // Load flagged answers for this session
      loadFlaggedAnswers(sessionIdFromState)
    }
  }, [sessionIdFromState])

  const loadFlaggedAnswers = async (sessionId) => {
    try {
      setIsLoading(true)
      setErrorMessage('')
      // In a real app, this would fetch from backend
      // const response = await getFlaggedAnswers(sessionId)
      setFlaggedAnswers(mockFlaggedAnswers)
    } catch (error) {
      setErrorMessage('Could not load flagged answers. Please try again.')
    } finally {
      setIsLoading(false)
    }
  }

  const handleOverride = (answerId, newScore) => {
    setOverrides((prev) => ({
      ...prev,
      [answerId]: newScore,
    }))
  }

  const handleOverrideNoteChange = (answerId, note) => {
    setOverrideNotes((prev) => ({
      ...prev,
      [answerId]: note,
    }))
  }

  const handleSaveOverride = async (answerId) => {
    try {
      const score = overrides[answerId]
      const reason = overrideNotes[answerId]

      if (score === undefined || score === null) {
        setErrorMessage('Please enter a score.')
        return
      }

      if (score < 0 || score > 10) {
        setErrorMessage('Score must be between 0 and 10.')
        return
      }

      // In a real app, this would save to backend
      // await saveScoreOverride(answerId, score, reason)

      // Update local state
      setFlaggedAnswers((prev) =>
        prev.map((answer) =>
          answer.id === answerId
            ? {
                ...answer,
                overridden_score: score,
                override_reason: reason,
              }
            : answer
        )
      )

      setOverrides((prev) => {
        const newOverrides = { ...prev }
        delete newOverrides[answerId]
        return newOverrides
      })

      setOverrideNotes((prev) => {
        const newNotes = { ...prev }
        delete newNotes[answerId]
        return newNotes
      })

      alert('Score override saved successfully.')
    } catch (error) {
      setErrorMessage('Could not save override. Please try again.')
    }
  }

  return (
    <div className="teacher-review-container">
      <header className="teacher-review-header">
        <h1>Teacher Review Panel</h1>
        <p className="subtitle">Review flagged answers and adjust scores if needed</p>
        <Link to="/" className="back-link">
          ← Back to Home
        </Link>
      </header>

      <main className="teacher-review-main">
        {errorMessage && <div className="error-message">{errorMessage}</div>}

        <section className="session-selector">
          <h2>Select Session</h2>
          <p className="session-info">
            {selectedSession
              ? `Reviewing session: ${selectedSession}`
              : 'Pass a session ID to view flagged answers'}
          </p>
        </section>

        {isLoading && <p className="loading-text">Loading flagged answers...</p>}

        {!isLoading && flaggedAnswers.length === 0 && (
          <div className="no-data">
            <p>No flagged answers found for this session.</p>
          </div>
        )}

        {!isLoading && flaggedAnswers.length > 0 && (
          <section className="flagged-answers-section">
            <h2>Flagged Answers ({flaggedAnswers.length})</h2>

            <div className="answers-list">
              {flaggedAnswers.map((answer) => (
                <div
                  key={answer.id}
                  className={`answer-card ${expandedAnswerId === answer.id ? 'expanded' : ''}`}
                >
                  <div
                    className="answer-header"
                    onClick={() =>
                      setExpandedAnswerId(
                        expandedAnswerId === answer.id ? null : answer.id
                      )
                    }
                  >
                    <div className="header-content">
                      <h3>{answer.question_text}</h3>
                      <div className="answer-meta">
                        <span className="original-score">
                          Original: {answer.original_score.toFixed(1)}
                        </span>
                        {answer.overridden_score !== null && (
                          <span className="overridden-score">
                            Override: {answer.overridden_score.toFixed(1)}
                          </span>
                        )}
                        <span className="flag-count">
                          {answer.flags.length} flag(s)
                        </span>
                      </div>
                    </div>
                    <div className="expand-icon">
                      {expandedAnswerId === answer.id ? '▼' : '▶'}
                    </div>
                  </div>

                  {expandedAnswerId === answer.id && (
                    <div className="answer-details">
                      {/* Student Answer */}
                      <div className="student-answer-section">
                        <h4>Student Answer</h4>
                        <p className="student-answer-text">{answer.student_answer}</p>
                      </div>

                      {/* Flags */}
                      <div className="flags-section">
                        <h4>Flags</h4>
                        <div className="flags-list">
                          {answer.flags.map((flag) => (
                            <span key={flag} className="flag-tag">
                              {flag}
                            </span>
                          ))}
                        </div>
                      </div>

                      {/* Score Comparison */}
                      <div className="comparison-summary">
                        <h4>Score Comparison</h4>
                        <div className="score-comparison-grid">
                          <div className="score-col">
                            <h5>Legacy</h5>
                            <p className="score-value legacy">
                              {answer.comparison.legacy.score.toFixed(1)}
                            </p>
                            <p className="score-band">
                              {answer.comparison.legacy.band.toUpperCase()}
                            </p>
                          </div>
                          <div className="score-col">
                            <h5>Ground</h5>
                            <p className="score-value grounded">
                              {answer.comparison.grounded.score.toFixed(1)}
                            </p>
                            <p className="score-band">
                              {answer.comparison.grounded.band.toUpperCase()}
                            </p>
                          </div>
                          <div className="score-col">
                            <h5>Difference</h5>
                            <p className="score-value delta">
                              {answer.comparison.difference.score_delta > 0 ? '+' : ''}
                              {answer.comparison.difference.score_delta.toFixed(1)}
                            </p>
                            <p className="score-band">
                              {answer.comparison.difference.higher_score === 'grounded'
                                ? 'Ground Higher'
                                : answer.comparison.difference.higher_score === 'legacy'
                                  ? 'Legacy Higher'
                                  : 'Equal'}
                            </p>
                          </div>
                        </div>
                      </div>

                      {/* Feedback */}
                      <div className="feedback-summary">
                        <h4>Feedback Summary</h4>
                        <div className="feedback-grid">
                          <div className="feedback-col">
                            <h5>Legacy</h5>
                            <p className="feedback-text">
                              {answer.comparison.legacy.feedback.summary}
                            </p>
                            <p className="recommendation">
                              {answer.comparison.legacy.feedback.recommendation}
                            </p>
                          </div>
                          <div className="feedback-col">
                            <h5>Ground</h5>
                            <p className="feedback-text">
                              {answer.comparison.grounded.feedback.summary}
                            </p>
                            <p className="recommendation">
                              {answer.comparison.grounded.feedback.recommendation}
                            </p>
                          </div>
                        </div>
                      </div>

                      {/* Override Section */}
                      {answer.overridden_score === null && (
                        <div className="override-section">
                          <h4>Manual Score Override</h4>
                          <div className="override-form">
                            <div className="form-group">
                              <label htmlFor={`score-${answer.id}`}>
                                New Score (0-10):
                              </label>
                              <input
                                id={`score-${answer.id}`}
                                type="number"
                                min="0"
                                max="10"
                                step="0.5"
                                placeholder="Enter new score"
                                value={overrides[answer.id] ?? ''}
                                onChange={(e) =>
                                  handleOverride(answer.id, parseFloat(e.target.value))
                                }
                              />
                            </div>
                            <div className="form-group">
                              <label htmlFor={`notes-${answer.id}`}>
                                Reason for Override:
                              </label>
                              <textarea
                                id={`notes-${answer.id}`}
                                placeholder="Why are you adjusting this score?"
                                value={overrideNotes[answer.id] ?? ''}
                                onChange={(e) =>
                                  handleOverrideNoteChange(answer.id, e.target.value)
                                }
                                rows="3"
                              />
                            </div>
                            <button
                              className="btn-save-override"
                              onClick={() => handleSaveOverride(answer.id)}
                            >
                              Save Override
                            </button>
                          </div>
                        </div>
                      )}

                      {/* Override Confirmed */}
                      {answer.overridden_score !== null && (
                        <div className="override-confirmed">
                          <h4>✓ Score Override Applied</h4>
                          <p className="override-info">
                            New Score: <strong>{answer.overridden_score.toFixed(1)}</strong>
                          </p>
                          <p className="override-reason">
                            Reason: {answer.override_reason}
                          </p>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </section>
        )}
      </main>
    </div>
  )
}

export default TeacherReviewPage
