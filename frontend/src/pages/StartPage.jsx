/**
 * StartPage.jsx — Knowledge Upload and Chunk Preview
 * ==================================================
 * Dedicated landing page for uploading source material before viva.
 */

import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { getKnowledgeAsset, uploadKnowledgeSource } from '../services/knowledgeService'
import { getTopics } from '../services/topicService'

function StartPage() {
  const navigate = useNavigate()

  const [subjectsMap, setSubjectsMap] = useState({})
  const [selectedSubject, setSelectedSubject] = useState('')
  const [selectedTopic, setSelectedTopic] = useState('')
  const [selectedFile, setSelectedFile] = useState(null)
  const [isLoadingTopics, setIsLoadingTopics] = useState(true)
  const [isBuildingKnowledge, setIsBuildingKnowledge] = useState(false)
  const [knowledgeAsset, setKnowledgeAsset] = useState(null)
  const [chunkPreview, setChunkPreview] = useState([])
  const [extractedTopics, setExtractedTopics] = useState([])
  const [errorMessage, setErrorMessage] = useState('')

  useEffect(() => {
    let isMounted = true

    async function loadTopics() {
      try {
        setIsLoadingTopics(true)
        setErrorMessage('')

        const data = await getTopics()
        const subjects = data?.subjects || {}

        if (!isMounted) {
          return
        }

        setSubjectsMap(subjects)

        const subjectNames = Object.keys(subjects)
        const firstSubject = subjectNames[0] || ''
        const firstTopic = firstSubject ? (subjects[firstSubject]?.[0] || '') : ''

        setSelectedSubject(firstSubject)
        setSelectedTopic(firstTopic)
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
          setIsLoadingTopics(false)
        }
      }
    }

    loadTopics()

    return () => {
      isMounted = false
    }
  }, [])

  const subjectNames = useMemo(() => Object.keys(subjectsMap), [subjectsMap])
  const topicNames = selectedSubject ? (subjectsMap[selectedSubject] || []) : []

  useEffect(() => {
    if (!selectedSubject) {
      return
    }

    const availableTopics = subjectsMap[selectedSubject] || []
    if (!availableTopics.includes(selectedTopic)) {
      setSelectedTopic(availableTopics[0] || '')
    }
  }, [selectedSubject, selectedTopic, subjectsMap])

  async function handleCreateKnowledge() {
    if (!selectedSubject || !selectedTopic) {
      setErrorMessage('Please choose a subject and topic first.')
      return
    }

    if (!selectedFile) {
      setErrorMessage('Please upload a PDF, DOCX, TXT, or MD file.')
      return
    }

    try {
      setIsBuildingKnowledge(true)
      setErrorMessage('')
      setKnowledgeAsset(null)
      setChunkPreview([])

      const uploadResult = await uploadKnowledgeSource({
        subject: selectedSubject,
        topic: selectedTopic,
        file: selectedFile,
      })

      const assetId = uploadResult?.asset_id
      if (!assetId) {
        throw new Error('Knowledge build completed without an asset ID.')
      }

      const assetDetails = await getKnowledgeAsset(assetId)
      setKnowledgeAsset({
        ...assetDetails,
        chunk_count: assetDetails?.chunk_count ?? uploadResult?.chunk_count ?? 0,
        concept_count: assetDetails?.concept_count ?? uploadResult?.concept_count ?? 0,
      })
      setChunkPreview(assetDetails?.chunk_preview || [])
      setExtractedTopics(assetDetails?.extracted_topics || [])

      localStorage.setItem('knowledge_asset_id', assetId)
      localStorage.setItem('knowledge_subject', selectedSubject)
      localStorage.setItem('knowledge_topic', selectedTopic)
      localStorage.setItem('knowledge_topics', JSON.stringify(assetDetails?.extracted_topics || []))
    } catch (error) {
      setErrorMessage(
        error?.response?.data?.detail ||
        'Could not create knowledge from the uploaded file.'
      )
    } finally {
      setIsBuildingKnowledge(false)
    }
  }

  return (
    <div className="app-shell">
      <main className="glass-card start-page-card">
        <p className="page-kicker">Automatic Viva Taker</p>
        <h1 className="page-title">Upload Source Material</h1>
        <p className="page-subtitle">
          Build knowledge from a PDF first, then inspect how the document was split into chunks.
        </p>

        {isLoadingTopics && <p className="info-text">Loading subjects...</p>}

        {!isLoadingTopics && subjectNames.length > 0 && (
          <div className="start-page-form-grid">
            <div className="start-page-form-column">
              <label htmlFor="start-subject" className="form-label">Subject</label>
              <select
                id="start-subject"
                className="form-control"
                value={selectedSubject}
                onChange={(event) => setSelectedSubject(event.target.value)}
              >
                {subjectNames.map((subject) => (
                  <option key={subject} value={subject}>{subject}</option>
                ))}
              </select>

              <label htmlFor="start-topic" className="form-label">Topic</label>
              <select
                id="start-topic"
                className="form-control"
                value={selectedTopic}
                onChange={(event) => setSelectedTopic(event.target.value)}
              >
                {topicNames.map((topic) => (
                  <option key={topic} value={topic}>{topic}</option>
                ))}
              </select>

              <label htmlFor="knowledge-file" className="form-label">Upload PDF / DOCX / TXT / MD</label>
              <input
                id="knowledge-file"
                type="file"
                accept=".pdf,.docx,.txt,.md"
                className="form-control"
                onChange={(event) => {
                  setSelectedFile(event.target.files?.[0] || null)
                }}
              />

              {selectedFile && (
                <p className="info-text">Selected source: {selectedFile.name}</p>
              )}

              <div className="start-page-actions">
                <button
                  type="button"
                  className="viva-btn viva-btn-primary"
                  onClick={handleCreateKnowledge}
                  disabled={isBuildingKnowledge}
                >
                  {isBuildingKnowledge ? 'Creating Knowledge...' : 'Create Knowledge'}
                </button>

                <button
                  type="button"
                  className="viva-btn viva-btn-secondary"
                  onClick={() => navigate('/topics', {
                    state: {
                      subject: selectedSubject,
                      knowledgeAssetId: knowledgeAsset?.asset_id,
                    },
                  })}
                >
                  Continue to Teacher Topics
                </button>
              </div>

              {knowledgeAsset && (
                <section className="start-page-summary">
                  <h2 className="section-heading">Knowledge Built</h2>
                  <div className="start-page-summary-grid">
                    <div className="start-page-summary-card">
                      <p className="report-summary-label">Asset ID</p>
                      <p className="start-page-summary-value">{knowledgeAsset.asset_id}</p>
                    </div>
                    <div className="start-page-summary-card">
                      <p className="report-summary-label">Chunks</p>
                      <p className="start-page-summary-value">{knowledgeAsset.chunk_count}</p>
                    </div>
                    <div className="start-page-summary-card">
                      <p className="report-summary-label">Concepts</p>
                      <p className="start-page-summary-value">{knowledgeAsset.concept_count}</p>
                    </div>
                    <div className="start-page-summary-card">
                      <p className="report-summary-label">Extraction</p>
                      <p className="start-page-summary-value">{knowledgeAsset.manifest?.extraction_mode || 'unknown'}</p>
                    </div>
                  </div>
                </section>
              )}

              {extractedTopics.length > 0 && (
                <section className="start-page-topics">
                  <h2 className="section-heading">Extracted Topics</h2>
                  <div className="start-page-topic-pills">
                    {extractedTopics.map((topic) => (
                      <span key={topic} className="start-page-topic-pill">
                        {topic}
                      </span>
                    ))}
                  </div>
                </section>
              )}
            </div>

            <aside className="start-page-preview-panel">
              <h2 className="section-heading">How the PDF was chunked</h2>
              <p className="info-text">
                The backend splits on headings first, then groups text into roughly 150-300 word chunks with light overlap.
              </p>

              {knowledgeAsset && (
                <p className="info-text">
                  Showing all {chunkPreview.length} chunk objects returned by the backend.
                </p>
              )}

              {!knowledgeAsset && (
                <p className="info-text">
                  Build knowledge to see chunk previews here.
                </p>
              )}

              {chunkPreview.length > 0 && (
                <div className="chunk-preview-list">
                  {chunkPreview.map((chunk) => (
                    <article key={chunk.chunk_id} className="chunk-preview-card">
                      <div className="chunk-preview-header">
                        <div>
                          <p className="chunk-preview-id">{chunk.chunk_id}</p>
                          <h3 className="chunk-preview-heading">{chunk.heading || 'General'}</h3>
                        </div>
                        <span className="chunk-preview-badge">{chunk.word_count} words</span>
                      </div>
                      <p className="chunk-preview-meta">{chunk.source_page_range || 'source page: unknown'}</p>
                      <p className="chunk-preview-text">{chunk.text}</p>
                      <pre className="chunk-preview-json">{JSON.stringify(chunk, null, 2)}</pre>
                    </article>
                  ))}
                </div>
              )}
            </aside>
          </div>
        )}

        {!isLoadingTopics && subjectNames.length === 0 && (
          <p className="error-text">No subjects found in /api/topics response.</p>
        )}

        {errorMessage && <p className="error-text">{errorMessage}</p>}
      </main>
    </div>
  )
}

export default StartPage