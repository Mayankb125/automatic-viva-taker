/**
 * VivaPage.jsx — Live Viva Examination Screen
 * =============================================
 * Phase 4 Step 4.3 implementation:
 *  - Load next question from backend
 *  - Submit voice answer for scoring
 *  - Show score breakdown + adaptive decision
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useLocation, useNavigate, useSearchParams } from 'react-router-dom'

import AudioRecorder from '../components/viva/AudioRecorder'
import ComparisonView from '../components/viva/ComparisonView'
import GroundedScoreBreakdown from '../components/viva/GroundedScoreBreakdown'
import IntegrityAlert from '../components/viva/IntegrityAlert'
import QuestionDisplay from '../components/viva/QuestionDisplay'
import TopicSwitchModal from '../components/viva/TopicSwitchModal'
import WebcamFeed from '../components/viva/WebcamFeed'
import { analyzeFrame } from '../services/cvService'
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

  const [pipelineMode, setPipelineMode] = useState(
    location.state?.pipelineMode || localStorage.getItem('viva_pipeline_mode') || 'dual_compare'
  )

  const [questionData, setQuestionData] = useState(null)
  const [audioBlob, setAudioBlob] = useState('')
  const [resultData, setResultData] = useState(null)
  const [topicList, setTopicList] = useState([])
  const [failedTopics, setFailedTopics] = useState([])
  const [isTopicModalOpen, setIsTopicModalOpen] = useState(false)
  const [isQuestionLoading, setIsQuestionLoading] = useState(false)
  const [isAnswerSubmitting, setIsAnswerSubmitting] = useState(false)
  const [isSwitchingTopic, setIsSwitchingTopic] = useState(false)
  const [isEndingSession, setIsEndingSession] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [cvErrorMessage, setCvErrorMessage] = useState('')
  const [integrityAlert, setIntegrityAlert] = useState(null)
  const [integrityFlagHistory, setIntegrityFlagHistory] = useState([])
  const [gazeLiveState, setGazeLiveState] = useState(null)

  const currentQuestionAudioRef = useRef(null)
  const integrityAlertTimerRef = useRef(null)
  const hasShownCvErrorRef = useRef(false)

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
        if (sessionData.pipeline_mode) {
          setPipelineMode(sessionData.pipeline_mode)
          localStorage.setItem('viva_pipeline_mode', sessionData.pipeline_mode)
        }
      } catch {
        // If this fails, we still keep Step 3.2 working with existing state.
      }
    }

    loadSessionDetails()
  }, [sessionId])

  useEffect(() => {
    return () => {
      if (currentQuestionAudioRef.current) {
        currentQuestionAudioRef.current.pause()
      }
      if (integrityAlertTimerRef.current) {
        clearTimeout(integrityAlertTimerRef.current)
      }
    }
  }, [])

  const handleCvError = useCallback((message) => {
    if (!hasShownCvErrorRef.current) {
      setCvErrorMessage(message)
      hasShownCvErrorRef.current = true
    }
  }, [])

  const handleFrameCapture = useCallback(
    async (frameDataUrl) => {
      if (!sessionId || !questionData?.question_id) {
        return
      }

      try {
        const cvData = await analyzeFrame({
          sessionId,
          questionId: questionData.question_id,
          frame: frameDataUrl,
          capturedAt: Date.now() / 1000,
        })

        const persistedFlags = Array.isArray(cvData?.flags) ? cvData.flags : []
        const liveFlags = Array.isArray(cvData?.live_flags) ? cvData.live_flags : []
        const flags = [...new Set([...liveFlags, ...persistedFlags])]
        const reasons = Array.isArray(cvData?.live_flag_reasons) ? cvData.live_flag_reasons : []
        const gazeReason = reasons.find((item) => item?.flag_type === 'gaze_deviation')?.reason
        const gazeRaw = cvData?.details?.gaze_check?.raw
        setGazeLiveState(gazeRaw || null)

        if (flags.length > 0) {
          const uniqueFlags = [...new Set(flags)]
          const label = uniqueFlags.join(', ')
          const alertMessage =
            uniqueFlags.includes('gaze_deviation')
              ? `Please look at the screen/camera. ${gazeReason || 'Gaze deviation detected.'}`
              : `Please stay focused on screen. Detected: ${label}`

          setIntegrityFlagHistory((prev) => [...new Set([...prev, ...uniqueFlags])])
          setIntegrityAlert({ message: alertMessage, createdAt: Date.now() })

          if (integrityAlertTimerRef.current) {
            clearTimeout(integrityAlertTimerRef.current)
          }
          integrityAlertTimerRef.current = setTimeout(() => {
            setIntegrityAlert(null)
          }, 3500)
          return
        }

        // Soft real-time warning before hard violation threshold is reached.
        const gazeDirection = gazeRaw?.gaze_direction
        const softAwayDuration = Number(gazeRaw?.away_duration_seconds || 0)
        const shouldShowSoftWarning =
          gazeDirection === 'no_face' || gazeDirection === 'no_eyes'
            ? softAwayDuration >= 1.0
            : softAwayDuration >= 0.8
        if (
          gazeDirection &&
          !['center', 'unknown', 'unavailable'].includes(gazeDirection) &&
          shouldShowSoftWarning
        ) {
          const softMessage =
            gazeDirection === 'no_face'
              ? 'Face not visible. Please stay in camera frame.'
              : gazeDirection === 'no_eyes'
                ? 'Eyes not visible clearly. Please face camera and look at screen.'
              : `Eyes look away (${gazeDirection}). Please focus on screen.`

          setIntegrityAlert({ message: softMessage, createdAt: Date.now() })

          if (integrityAlertTimerRef.current) {
            clearTimeout(integrityAlertTimerRef.current)
          }
          integrityAlertTimerRef.current = setTimeout(() => {
            setIntegrityAlert(null)
          }, 1500)
        }
      } catch (error) {
        if (!hasShownCvErrorRef.current) {
          const detail = error?.response?.data?.detail || 'Proctoring analysis unavailable.'
          setCvErrorMessage(detail)
          hasShownCvErrorRef.current = true
        }
      }
    },
    [questionData?.question_id, sessionId]
  )

  async function playQuestionAudio(questionAudio, questionAudioMime) {
    if (!questionAudio) {
      return
    }

    const mimeType = questionAudioMime || 'audio/wav'
    const src = `data:${mimeType};base64,${questionAudio}`

    try {
      if (currentQuestionAudioRef.current) {
        currentQuestionAudioRef.current.pause()
      }

      const audio = new Audio(src)
      currentQuestionAudioRef.current = audio
      await audio.play()
    } catch {
      // Browsers may block autoplay. User can manually replay.
    }
  }

  async function loadQuestion() {
    if (!sessionId) {
      return
    }

    try {
      setIsQuestionLoading(true)
      setErrorMessage('')

      const data = await getQuestion(sessionId)
      setQuestionData(data)
      setAudioBlob('')
      await playQuestionAudio(data?.question_audio, data?.question_audio_mime)
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

    if (!sessionId || !questionData?.question_id || !audioBlob) {
      return
    }

    try {
      setIsAnswerSubmitting(true)
      setErrorMessage('')

      const data = await submitAnswer({
        sessionId,
        questionId: questionData.question_id,
        audioBlob,
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
        return
      }

      // Auto-progress to the next adaptive question after every scored answer.
      // This covers follow_up, checkpoint, level_up, and return_to_original decisions.
      await loadQuestion()
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
          <p className="viva-meta-row">
            <strong>Pipeline:</strong> {pipelineMode}
          </p>
        </div>

        <WebcamFeed
          active={Boolean(sessionId && questionData?.question_id)}
          captureIntervalMs={1000}
          onFrameCapture={handleFrameCapture}
          onError={handleCvError}
        />

        <IntegrityAlert alert={integrityAlert} />

        {cvErrorMessage && (
          <p className="info-text">
            Proctoring note: {cvErrorMessage}
          </p>
        )}

        {integrityFlagHistory.length > 0 && (
          <p className="info-text">
            Integrity flags seen: {integrityFlagHistory.join(', ')}
          </p>
        )}

        {gazeLiveState && (
          <p className="info-text">
            Gaze live: {String(gazeLiveState.gaze_direction || 'unknown')} |
            duration: {Number(gazeLiveState.away_duration_seconds || 0).toFixed(1)}s |
            engine: {String(gazeLiveState.engine || 'unknown')} |
            eyes: {String(gazeLiveState.eyes_detected ?? 'n/a')} |
            confident: {String(gazeLiveState.eyes_confident ?? 'n/a')} |
            ratio: {String(gazeLiveState.avg_eye_ratio ?? 'n/a')} |
            baseline: {String(gazeLiveState.eye_baseline ?? 'n/a')} |
            samples: {String(gazeLiveState.eye_baseline_samples ?? 'n/a')}
          </p>
        )}

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
          <label className="form-label">
            Your Answer (voice for Phase 4)
          </label>

          <AudioRecorder
            disabled={!questionData || isQuestionLoading || isSwitchingTopic || isEndingSession}
            isSubmitting={isAnswerSubmitting}
            onAudioReady={setAudioBlob}
          />

          <div className="viva-actions">
            <button
              type="submit"
              className="viva-btn viva-btn-primary"
              disabled={
                !audioBlob ||
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
              onClick={() =>
                playQuestionAudio(questionData?.question_audio, questionData?.question_audio_mime)
              }
              disabled={!questionData?.question_audio || isAnswerSubmitting}
            >
              Replay Question Audio
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
            {/* Show comparison view if available (Phase 5.2 Step 5.2) */}
            {resultData?.compare_mode_enabled && resultData?.comparison && (
              <>
                <ComparisonView comparison={resultData.comparison} />
                <GroundedScoreBreakdown grounded={resultData.comparison.grounded} />
              </>
            )}

            {/* Fallback to legacy view if comparison not available */}
            {!resultData?.compare_mode_enabled && (
              <>
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
              </>
            )}

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
