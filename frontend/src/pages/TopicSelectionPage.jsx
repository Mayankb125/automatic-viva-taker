/**
 * TopicSelectionPage.jsx — Subject and Topic Picker
 * ===================================================
 * Phase 3 (Step 3.1):
 *  - Loads subjects from GET /api/topics
 *  - Shows subject dropdown and topic buttons
 *  - Starts a session immediately when a topic is clicked
 */

import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { startSession } from '../services/sessionService'
import { getTopics } from '../services/topicService'

function TopicSelectionPage() {
  const navigate = useNavigate()

  const [subjectsMap, setSubjectsMap] = useState({})
  const [selectedSubject, setSelectedSubject] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [startingTopic, setStartingTopic] = useState('')
  const [errorMessage, setErrorMessage] = useState('')

  useEffect(() => {
    let isMounted = true

    async function loadTopics() {
      try {
        setIsLoading(true)
        setErrorMessage('')

        const data = await getTopics()
        const subjects = data?.subjects || {}

        if (!isMounted) {
          return
        }

        setSubjectsMap(subjects)

        const firstSubject = Object.keys(subjects)[0] || ''
        setSelectedSubject(firstSubject)
      } catch (error) {
        if (!isMounted) {
          return
        }

        setErrorMessage(
          error?.response?.data?.detail ||
          'Could not load subjects. Please check backend and try again.'
        )
      } finally {
        if (isMounted) {
          setIsLoading(false)
        }
      }
    }

    loadTopics()

    return () => {
      isMounted = false
    }
  }, [])

  const subjectNames = useMemo(() => Object.keys(subjectsMap), [subjectsMap])
  const topicsForSubject = selectedSubject ? (subjectsMap[selectedSubject] || []) : []

  async function handleTopicClick(clickedTopic) {
    if (!selectedSubject || !clickedTopic || startingTopic) {
      return
    }

    try {
      setStartingTopic(clickedTopic)
      setErrorMessage('')

      // The backend starts from topic_list[0], so place clicked topic first.
      const orderedTopicList = [
        clickedTopic,
        ...topicsForSubject.filter((topic) => topic !== clickedTopic),
      ]

      const sessionData = await startSession({
        studentId: 'test-user',
        subject: selectedSubject,
        topicList: orderedTopicList,
      })

      const sessionId = sessionData.session_id

      // Keep a local copy so VivaPage can recover on browser refresh.
      localStorage.setItem('viva_session_id', sessionId)
      localStorage.setItem('viva_subject', selectedSubject)
      localStorage.setItem('viva_topic_list', JSON.stringify(orderedTopicList))

      navigate(`/viva?session_id=${encodeURIComponent(sessionId)}`, {
        state: {
          sessionId,
          subject: selectedSubject,
          topicList: orderedTopicList,
        },
      })
    } catch (error) {
      setErrorMessage(
        error?.response?.data?.detail ||
        'Could not start session. Please try a different topic.'
      )
      setStartingTopic('')
    }
  }

  return (
    <div className="app-shell">
      <main className="glass-card">
        <p className="page-kicker">Automatic Viva Taker</p>
        <h1 className="page-title">Choose Subject and Start Viva</h1>
        <p className="page-subtitle">
          Select one subject, then click a topic. The clicked topic starts first.
        </p>

        {isLoading && <p className="info-text">Loading subjects...</p>}

        {!isLoading && subjectNames.length === 0 && (
          <p className="error-text">No subjects found in /api/topics response.</p>
        )}

        {!isLoading && subjectNames.length > 0 && (
          <>
            <label htmlFor="subject" className="form-label">
              Subject
            </label>
            <select
              id="subject"
              value={selectedSubject}
              onChange={(event) => setSelectedSubject(event.target.value)}
              className="form-control"
            >
              {subjectNames.map((subject) => (
                <option key={subject} value={subject}>
                  {subject}
                </option>
              ))}
            </select>

            <h2 className="section-heading">Topics</h2>
            <div className="topic-selection-grid">
              {topicsForSubject.map((topic) => {
                const isStartingThisTopic = startingTopic === topic

                return (
                  <button
                    key={topic}
                    type="button"
                    className="topic-selection-btn"
                    onClick={() => handleTopicClick(topic)}
                    disabled={Boolean(startingTopic)}
                  >
                    {isStartingThisTopic ? 'Starting...' : topic}
                  </button>
                )
              })}
            </div>
          </>
        )}

        {errorMessage && <p className="error-text">{errorMessage}</p>}
      </main>
    </div>
  )
}

export default TopicSelectionPage
