/**
 * TopicSelectionPage.jsx — Teacher Topic Picker
 * ============================================
 * Shows topics extracted from the uploaded PDF when available.
 * Falls back to the static topic list if no uploaded asset is present.
 */

import { useEffect, useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'

import { getKnowledgeAsset } from '../services/knowledgeService'
import { startSession } from '../services/sessionService'
import { getTopics } from '../services/topicService'

const PIPELINE_OPTIONS = [
  {
    value: 'dual_compare',
    label: 'Dual Compare (Recommended)',
  },
  {
    value: 'grounded_only',
    label: 'Ground Only',
  },
  {
    value: 'legacy_only',
    label: 'Legacy Only',
  },
]

function TopicSelectionPage() {
  const navigate = useNavigate()
  const location = useLocation()

  const knowledgeAssetId =
    location.state?.knowledgeAssetId ||
    localStorage.getItem('knowledge_asset_id') ||
    ''

  const [subjectsMap, setSubjectsMap] = useState({})
  const [selectedSubject, setSelectedSubject] = useState('')
  const [isLoadingSubjects, setIsLoadingSubjects] = useState(true)
  const [knowledgeAsset, setKnowledgeAsset] = useState(null)
  const [extractedTopics, setExtractedTopics] = useState([])
  const [selectedTopics, setSelectedTopics] = useState([])
  const [isLoadingAsset, setIsLoadingAsset] = useState(Boolean(knowledgeAssetId))
  const [startingTopic, setStartingTopic] = useState('')
  const [isStarting, setIsStarting] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [selectedPipelineMode, setSelectedPipelineMode] = useState(
    localStorage.getItem('viva_pipeline_mode') || 'dual_compare'
  )

  const isKnowledgeMode = Boolean(knowledgeAssetId)
  const hasExtractedTopics = extractedTopics.length > 0

  useEffect(() => {
    let isMounted = true

    async function loadSubjects() {
      try {
        setIsLoadingSubjects(true)
        setErrorMessage('')

        const data = await getTopics()
        const subjects = data?.subjects || {}

        if (!isMounted) {
          return
        }

        setSubjectsMap(subjects)

        const preferredSubject =
          knowledgeAsset?.manifest?.subject ||
          location.state?.subject ||
          localStorage.getItem('knowledge_subject') ||
          ''
        const firstSubject = Object.keys(subjects)[0] || ''

        if (preferredSubject && subjects[preferredSubject]) {
          setSelectedSubject(preferredSubject)
        } else if (firstSubject) {
          setSelectedSubject(firstSubject)
        }
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
          setIsLoadingSubjects(false)
        }
      }
    }

    loadSubjects()

    return () => {
      isMounted = false
    }
  }, [knowledgeAsset?.manifest?.subject, location.state?.subject])

  useEffect(() => {
    let isMounted = true

    async function loadKnowledgeAsset() {
      if (!knowledgeAssetId) {
        setIsLoadingAsset(false)
        return
      }

      try {
        setIsLoadingAsset(true)

        const asset = await getKnowledgeAsset(knowledgeAssetId)
        if (!isMounted) {
          return
        }

        setKnowledgeAsset(asset)
        setExtractedTopics(asset?.extracted_topics || [])
        localStorage.setItem('knowledge_topics', JSON.stringify(asset?.extracted_topics || []))

        if (asset?.manifest?.subject) {
          setSelectedSubject(asset.manifest.subject)
        }
      } catch (error) {
        if (!isMounted) {
          return
        }

        setErrorMessage(
          error?.response?.data?.detail ||
          'Could not load extracted topics from the uploaded PDF.'
        )
      } finally {
        if (isMounted) {
          setIsLoadingAsset(false)
        }
      }
    }

    loadKnowledgeAsset()

    return () => {
      isMounted = false
    }
  }, [knowledgeAssetId])

  const subjectNames = useMemo(() => Object.keys(subjectsMap), [subjectsMap])
  const staticTopicsForSubject = selectedSubject ? (subjectsMap[selectedSubject] || []) : []
  const topicOptions = hasExtractedTopics ? extractedTopics : staticTopicsForSubject

  useEffect(() => {
    if (!selectedSubject) {
      return
    }

    const availableTopics = subjectsMap[selectedSubject] || []
    if (!hasExtractedTopics && !availableTopics.includes(selectedSubject)) {
      // no-op: keeps the current fallback topic state stable
    }
  }, [hasExtractedTopics, selectedSubject, subjectsMap])

  async function handleStaticTopicClick(clickedTopic) {
    if (!selectedSubject || !clickedTopic || isStarting) {
      return
    }

    try {
      setIsStarting(true)
      setStartingTopic(clickedTopic)
      setErrorMessage('')

      const orderedTopicList = [
        clickedTopic,
        ...staticTopicsForSubject.filter((topic) => topic !== clickedTopic),
      ]

      const sessionData = await startSession({
        studentId: 'test-user',
        subject: selectedSubject,
        topicList: orderedTopicList,
        pipelineMode: selectedPipelineMode,
      })

      const sessionId = sessionData.session_id
      localStorage.setItem('viva_session_id', sessionId)
      localStorage.setItem('viva_subject', selectedSubject)
      localStorage.setItem('viva_topic_list', JSON.stringify(orderedTopicList))
      localStorage.setItem('viva_pipeline_mode', sessionData.pipeline_mode || selectedPipelineMode)

      navigate(`/viva?session_id=${encodeURIComponent(sessionId)}`, {
        state: {
          sessionId,
          subject: selectedSubject,
          topicList: orderedTopicList,
          pipelineMode: sessionData.pipeline_mode || selectedPipelineMode,
        },
      })
    } catch (error) {
      setErrorMessage(
        error?.response?.data?.detail ||
        'Could not start session. Please try again.'
      )
    } finally {
      setIsStarting(false)
      setStartingTopic('')
    }
  }

  function toggleExtractedTopic(topic) {
    setSelectedTopics((current) => {
      if (current.includes(topic)) {
        return current.filter((item) => item !== topic)
      }

      return [...current, topic]
    })
  }

  async function handleStartFromExtractedTopics() {
    if (!selectedSubject || selectedTopics.length === 0 || isStarting) {
      if (selectedTopics.length === 0) {
        setErrorMessage('Please select one or more topics from the uploaded PDF.')
      }
      return
    }

    try {
      setIsStarting(true)
      setErrorMessage('')

      const sessionData = await startSession({
        studentId: 'test-user',
        subject: selectedSubject,
        topicList: selectedTopics,
        pipelineMode: selectedPipelineMode,
      })

      const sessionId = sessionData.session_id
      localStorage.setItem('viva_session_id', sessionId)
      localStorage.setItem('viva_subject', selectedSubject)
      localStorage.setItem('viva_topic_list', JSON.stringify(selectedTopics))
      localStorage.setItem('viva_pipeline_mode', sessionData.pipeline_mode || selectedPipelineMode)

      navigate(`/viva?session_id=${encodeURIComponent(sessionId)}`, {
        state: {
          sessionId,
          subject: selectedSubject,
          topicList: selectedTopics,
          pipelineMode: sessionData.pipeline_mode || selectedPipelineMode,
        },
      })
    } catch (error) {
      setErrorMessage(
        error?.response?.data?.detail ||
        'Could not start viva from the selected PDF topics.'
      )
    } finally {
      setIsStarting(false)
    }
  }

  return (
    <div className="app-shell">
      <main className="glass-card topic-selection-card">
        <p className="page-kicker">Automatic Viva Taker</p>
        <h1 className="page-title">
          {isKnowledgeMode ? 'Select Topics From Uploaded PDF' : 'Choose Subject and Start Viva'}
        </h1>
        <p className="page-subtitle">
          {isKnowledgeMode
            ? 'Select one or more topics extracted from the uploaded PDF, then start the viva.'
            : 'Select one subject, then click a topic. Upload and knowledge building now happen on the start page.'}
        </p>

        {isLoadingSubjects && <p className="info-text">Loading subjects...</p>}
        {isLoadingAsset && <p className="info-text">Loading extracted PDF topics...</p>}

        {!isLoadingSubjects && subjectNames.length === 0 && (
          <p className="error-text">No subjects found in /api/topics response.</p>
        )}

        {knowledgeAsset && (
          <section className="topic-selection-asset-card">
            <div>
              <p className="topic-selection-asset-label">Uploaded PDF</p>
              <h2 className="topic-selection-asset-title">
                {knowledgeAsset.manifest?.source_file_path?.split(/[/\\]/).pop() || 'Unknown source file'}
              </h2>
              <p className="topic-selection-asset-meta">
                Subject: {knowledgeAsset.manifest?.subject || 'N/A'} | Extracted topics: {topicOptions.length}
              </p>
            </div>
            <button
              type="button"
              className="viva-btn viva-btn-secondary"
              onClick={() => navigate('/start')}
            >
              Back to Upload
            </button>
          </section>
        )}

        {!isLoadingSubjects && subjectNames.length > 0 && !isKnowledgeMode && (
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

            <label htmlFor="pipeline_mode" className="form-label">
              Scoring Pipeline
            </label>
            <select
              id="pipeline_mode"
              value={selectedPipelineMode}
              onChange={(event) => setSelectedPipelineMode(event.target.value)}
              className="form-control"
              disabled={isStarting}
            >
              {PIPELINE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>

            <h2 className="section-heading">Topics</h2>
            <p className="info-text">
              Use the start page to upload a source PDF and inspect chunking first.
            </p>

            <div className="topic-selection-grid">
              {topicOptions.map((topic) => {
                const isStartingThisTopic = startingTopic === topic

                return (
                  <button
                    key={topic}
                    type="button"
                    className="topic-selection-btn"
                    onClick={() => handleStaticTopicClick(topic)}
                    disabled={Boolean(startingTopic) || isStarting}
                  >
                    {isStartingThisTopic ? 'Starting...' : topic}
                  </button>
                )
              })}
            </div>

            <div style={{ marginTop: 'var(--space-5)' }}>
              <button
                type="button"
                className="viva-btn viva-btn-secondary"
                onClick={() => navigate('/start')}
              >
                Go to Start Page
              </button>
            </div>
          </>
        )}

        {isKnowledgeMode && hasExtractedTopics && (
          <>
            <label htmlFor="subject" className="form-label">
              Subject
            </label>
            <select
              id="subject"
              value={selectedSubject}
              onChange={(event) => setSelectedSubject(event.target.value)}
              className="form-control"
              disabled={Boolean(knowledgeAsset)}
            >
              {subjectNames.includes(selectedSubject) ? null : (
                <option value={selectedSubject || ''}>{selectedSubject || 'Select subject'}</option>
              )}
              {subjectNames.map((subject) => (
                <option key={subject} value={subject}>
                  {subject}
                </option>
              ))}
            </select>

            <label htmlFor="pipeline_mode_knowledge" className="form-label">
              Scoring Pipeline
            </label>
            <select
              id="pipeline_mode_knowledge"
              value={selectedPipelineMode}
              onChange={(event) => setSelectedPipelineMode(event.target.value)}
              className="form-control"
              disabled={isStarting}
            >
              {PIPELINE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>

            <div className="topic-selection-toolbar">
              <button
                type="button"
                className="viva-btn viva-btn-secondary"
                onClick={() => setSelectedTopics(topicOptions)}
              >
                Select All
              </button>
              <button
                type="button"
                className="viva-btn viva-btn-secondary"
                onClick={() => setSelectedTopics([])}
              >
                Clear
              </button>
              <span className="topic-selection-count">
                Selected {selectedTopics.length} of {topicOptions.length}
              </span>
            </div>

            <div className="topic-selection-topic-grid">
              {topicOptions.map((topic) => {
                const isChecked = selectedTopics.includes(topic)

                return (
                  <label key={topic} className={`topic-selection-topic-card ${isChecked ? 'is-selected' : ''}`}>
                    <input
                      type="checkbox"
                      checked={isChecked}
                      onChange={() => toggleExtractedTopic(topic)}
                    />
                    <span>{topic}</span>
                  </label>
                )
              })}
            </div>

            <div className="topic-selection-actions">
              <button
                type="button"
                className="viva-btn viva-btn-primary"
                onClick={handleStartFromExtractedTopics}
                disabled={isStarting || selectedTopics.length === 0}
              >
                {isStarting ? 'Starting Viva...' : 'Start Viva'}
              </button>
              <button
                type="button"
                className="viva-btn viva-btn-secondary"
                onClick={() => navigate('/start')}
              >
                Back to Upload
              </button>
            </div>
          </>
        )}

        {isKnowledgeMode && !isLoadingAsset && !hasExtractedTopics && (
          <>
            <p className="info-text">
              No extracted topics were found for this PDF. You can go back and upload a different file.
            </p>
            <div className="topic-selection-actions">
              <button
                type="button"
                className="viva-btn viva-btn-secondary"
                onClick={() => navigate('/start')}
              >
                Back to Upload
              </button>
            </div>
          </>
        )}

        {errorMessage && <p className="error-text">{errorMessage}</p>}
      </main>
    </div>
  )
}

export default TopicSelectionPage