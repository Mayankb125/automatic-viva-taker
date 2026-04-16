/**
 * VivaPage.jsx — Live Viva Examination Screen
 * =============================================
 * Phase 3 Step 3.2 implementation:
 *  - Load next question from backend
 *  - Submit typed answer for scoring
 *  - Show score breakdown + adaptive decision
 */

import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'

import QuestionDisplay from '../components/viva/QuestionDisplay'
import TopicSwitchModal from '../components/viva/TopicSwitchModal'
import { endSession, getSession } from '../services/sessionService'
import { switchTopic } from '../services/topicService'
import { getQuestion, submitAnswer } from '../services/vivaService'

function VivaPage() {
  const location = useLocation()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()

  const sessionId = useMemo(
    () =>
      location.state?.sessionId ||
      searchParams.get('session_id') ||
      localStorage.getItem('viva_session_id') ||
      '',
    [location.state?.sessionId, searchParams]
  )

  const subject =
    location.state?.subject || localStorage.getItem('viva_subject') || 'Unknown subject'

  const [questionData, setQuestionData] = useState(null)
  const [answerText, setAnswerText] = useState('')
  const [resultData, setResultData] = useState(null)
  const [topicList, setTopicList] = useState([])
  const [failedTopics, setFailedTopics] = useState([])
  const [isTopicModalOpen, setIsTopicModalOpen] = useState(false)
  const [isQuestionLoading, setIsQuestionLoading] = useState(false)
  const [isAnswerSubmitting, setIsAnswerSubmitting] = useState(false)
  const [isSwitchingTopic, setIsSwitchingTopic] = useState(false)
  const [isEndingSession, setIsEndingSession] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')

  useEffect(() => {
    // Try route state first, then localStorage fallback.
    if (Array.isArray(location.state?.topicList) && location.state.topicList.length > 0) {
      setTopicList(location.state.topicList)
      return
    }

    const raw = localStorage.getItem('viva_topic_list')
    if (!raw) {
      return
    }

    try {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed) && parsed.length > 0) {
        setTopicList(parsed)
      }
    } catch {
      // Ignore malformed local storage values.
    }
  }, [location.state?.topicList])

  useEffect(() => {
    async function loadSessionDetails() {
      if (!sessionId) {
        return
      }

      try {
        const sessionData = await getSession(sessionId)
        if (Array.isArray(sessionData.topic_list) && sessionData.topic_list.length > 0) {
          setTopicList(sessionData.topic_list)
          localStorage.setItem('viva_topic_list', JSON.stringify(sessionData.topic_list))
        }
      } catch {
        // If this fails, we still keep Step 3.2 working with existing state.
      }
    }

    loadSessionDetails()
  }, [sessionId])

  async function loadQuestion() {
    if (!sessionId) {
      return
    }

    try {
      setIsQuestionLoading(true)
      setErrorMessage('')

      const data = await getQuestion(sessionId)
      setQuestionData(data)
      setAnswerText('')
    } catch (error) {
      setErrorMessage(
        error?.response?.data?.detail ||
          'Could not load question. Please try again.'
      )
    } finally {
      setIsQuestionLoading(false)
    }
  }

  useEffect(() => {
    loadQuestion()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId])

  async function handleSubmitAnswer(event) {
    event.preventDefault()

    if (!sessionId || !questionData?.question_id || !answerText.trim()) {
      return
    }

    try {
      setIsAnswerSubmitting(true)
      setErrorMessage('')

      const data = await submitAnswer({
        sessionId,
        questionId: questionData.question_id,
        textAnswer: answerText.trim(),
      })

      setResultData(data)

      const decision = data?.adaptive?.decision
      if (decision === 'session_end' || decision === 'topic_complete') {
        await handleEndSession(true)
        return
      }

      // Step 3.3: backend asks for topic switch when checkpoint is failed.
      if (data?.adaptive?.show_topic_modal) {
        const failedTopic = data?.adaptive?.current_topic
        if (failedTopic) {
          setFailedTopics((prev) => (prev.includes(failedTopic) ? prev : [...prev, failedTopic]))
        }
        setIsTopicModalOpen(true)
      }
    } catch (error) {
      setErrorMessage(
        error?.response?.data?.detail ||
          'Could not submit answer. Please try again.'
      )
    } finally {
      setIsAnswerSubmitting(false)
    }
  }

  async function handleEndSession(isAutoEnd = false) {
    if (!sessionId || isEndingSession) {
      return
    }

    try {
      setIsEndingSession(true)
      setErrorMessage('')

      const endData = await endSession(sessionId)

      navigate(`/report/${encodeURIComponent(sessionId)}`, {
        state: {
          reportSummary: endData,
          autoEnded: isAutoEnd,
        },
      })
    } catch (error) {
      setErrorMessage(
        error?.response?.data?.detail ||
          'Could not end session. Please try again.'
      )
    } finally {
      setIsEndingSession(false)
    }
  }

  const adaptive = resultData?.adaptive
  const score = resultData?.score_breakdown
  const feedback = resultData?.feedback

  async function handleSwitchTopic(newTopic) {
    if (!sessionId || !newTopic) {
      return
    }

    try {
      setIsSwitchingTopic(true)
      setErrorMessage('')

      const switchData = await switchTopic({ sessionId, newTopic })

      setResultData((prev) => {
        if (!prev) {
          return prev
        }

        return {
          ...prev,
          adaptive: {
            ...prev.adaptive,
            current_topic: switchData.new_topic,
            current_level: switchData.current_level,
            show_topic_modal: false,
            decision: 'topic_switched',
          },
        }
      })

      setIsTopicModalOpen(false)
      await loadQuestion()
    } catch (error) {
      setErrorMessage(
        error?.response?.data?.detail ||
          'Could not switch topic. Please try another one.'
      )
    } finally {
      setIsSwitchingTopic(false)
    }
  }

  return (
    <div className="app-shell">
      <main className="glass-card viva-page-card">
        <p className="page-kicker">Automatic Viva Taker</p>
        <h1 className="page-title">Live Viva</h1>
        <p className="page-subtitle">
          Answer each question in your own words to move through adaptive levels.
        </p>

        <div className="viva-meta-box">
          <p className="viva-meta-row">
            <strong>Session ID:</strong> {sessionId || 'Not provided'}
          </p>
          <p className="viva-meta-row">
            <strong>Subject:</strong> {subject}
          </p>
        </div>

        {!sessionId && (
          <p className="error-text">
            No session ID found. Start from Topic Selection first.
          </p>
        )}

        <QuestionDisplay
          questionText={questionData?.question_text}
          topic={questionData?.topic || adaptive?.current_topic}
          level={questionData?.level || adaptive?.current_level || 1}
          isLoading={isQuestionLoading}
        />

        <form className="viva-answer-form" onSubmit={handleSubmitAnswer}>
          <label htmlFor="answer" className="form-label">
            Your Answer (text for Phase 3)
          </label>
          <textarea
            id="answer"
            className="viva-answer-input"
            value={answerText}
            onChange={(event) => setAnswerText(event.target.value)}
            placeholder="Type your technical answer here..."
            rows={6}
            disabled={!questionData || isQuestionLoading || isAnswerSubmitting}
          />

          <div className="viva-actions">
            <button
              type="submit"
              className="viva-btn viva-btn-primary"
              disabled={
                !answerText.trim() ||
                !questionData?.question_id ||
                isQuestionLoading ||
                isAnswerSubmitting
              }
            >
              {isAnswerSubmitting ? 'Submitting...' : 'Submit Answer'}
            </button>

            <button
              type="button"
              className="viva-btn viva-btn-secondary"
              onClick={loadQuestion}
              disabled={!sessionId || isQuestionLoading || isAnswerSubmitting}
            >
              {isQuestionLoading ? 'Loading...' : 'Get Next Question'}
            </button>

            <Link to="/topics" className="action-link viva-back-link">
              Back to Topics
            </Link>

            <button
              type="button"
              className="viva-btn viva-btn-danger"
              onClick={() => handleEndSession(false)}
              disabled={!sessionId || isQuestionLoading || isAnswerSubmitting || isSwitchingTopic || isEndingSession}
            >
              {isEndingSession ? 'Ending...' : 'End Viva and View Report'}
            </button>
          </div>
        </form>

        {errorMessage && <p className="error-text">{errorMessage}</p>}

        {resultData && (
          <section className="viva-results" aria-live="polite">
            <h2 className="section-heading">Score Breakdown</h2>
            <div className="viva-score-grid">
              <p><strong>Semantic:</strong> {score.semantic_score}</p>
              <p><strong>Keyword:</strong> {score.keyword_score}</p>
              <p><strong>Depth:</strong> {score.depth_score}</p>
              <p><strong>Completeness:</strong> {score.completeness_score}</p>
              <p><strong>Confidence:</strong> {score.confidence_score}</p>
              <p><strong>Weighted:</strong> {score.weighted_score}</p>
              <p><strong>Level Bonus:</strong> {score.level_bonus}</p>
              <p><strong>Switch Penalty:</strong> {score.switch_penalty}</p>
              <p className="viva-final-score"><strong>Final Score:</strong> {score.final_score}</p>
            </div>

            <h2 className="section-heading">Adaptive Decision</h2>
            <div className="viva-adaptive-box">
              <p><strong>Decision:</strong> {adaptive.decision}</p>
              <p><strong>Current Topic:</strong> {adaptive.current_topic}</p>
              <p><strong>Current Level:</strong> {adaptive.current_level}</p>
              <p><strong>Total Questions:</strong> {adaptive.total_questions}</p>
              <p><strong>Show Topic Modal:</strong> {String(adaptive.show_topic_modal)}</p>
            </div>

            <h2 className="section-heading">Feedback</h2>
            <div className="viva-feedback-box">
              <p><strong>Depth:</strong> {feedback.depth_reason}</p>
              <p><strong>Completeness:</strong> {feedback.completeness_reason}</p>
            </div>
          </section>
        )}

        <TopicSwitchModal
          isOpen={isTopicModalOpen}
          topicList={topicList}
          failedTopics={failedTopics}
          onSwitch={handleSwitchTopic}
          onClose={() => setIsTopicModalOpen(false)}
          isSwitching={isSwitchingTopic}
        />
      </main>
    </div>
  )
}

export default VivaPage
