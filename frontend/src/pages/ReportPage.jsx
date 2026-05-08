/**
 * ReportPage.jsx — Post-Viva Performance Report
 * ================================================
 * Phase 3.4 basic report UI.
 */

import { useEffect, useMemo, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'

import { downloadReportPdf, getReport } from '../services/reportService'

function ReportPage() {
  const location = useLocation()
  const { sessionId } = useParams()

  const [report, setReport] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [errorMessage, setErrorMessage] = useState('')
  const [isDownloading, setIsDownloading] = useState(false)

  const reportSummary = location.state?.reportSummary

  const totalQuestionsFromSummary = reportSummary?.total_questions

  const hasSummaryPayload = useMemo(
    () => Boolean(reportSummary && typeof reportSummary === 'object'),
    [reportSummary]
  )

  useEffect(() => {
    let isMounted = true

    async function loadReport() {
      if (!sessionId) {
        setIsLoading(false)
        setErrorMessage('Missing session ID in route.')
        return
      }

      try {
        setIsLoading(true)
        setErrorMessage('')

        const data = await getReport(sessionId)
        if (!isMounted) {
          return
        }
        setReport(data)
      } catch (error) {
        if (!isMounted) {
          return
        }
        setErrorMessage(
          error?.response?.data?.detail ||
            'Could not load report. Please try again.'
        )
      } finally {
        if (isMounted) {
          setIsLoading(false)
        }
      }
    }

    loadReport()

    return () => {
      isMounted = false
    }
  }, [sessionId])

  const topicScores = report?.topic_scores || reportSummary?.topic_scores || {}
  const topicQuestionCounts = report?.topic_question_counts || reportSummary?.topic_question_counts || {}
  const switchedTopics = report?.switched_topics || []
  const overallScore = report?.overall_score ?? reportSummary?.overall_score ?? 0
  const totalQuestions = report?.total_questions ?? totalQuestionsFromSummary ?? 0
  const integritySummary = report?.integrity_summary
  const integrityByType = integritySummary?.by_type || {}
  const recentIntegrityFlags = integritySummary?.recent_flags || []

  async function handlePdfDownload() {
    if (!sessionId) {
      return
    }

    try {
      setIsDownloading(true)
      const pdfBlob = await downloadReportPdf(sessionId)
      const downloadUrl = window.URL.createObjectURL(pdfBlob)
      const anchor = document.createElement('a')
      anchor.href = downloadUrl
      anchor.download = `viva-report-${sessionId}.pdf`
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      window.URL.revokeObjectURL(downloadUrl)
    } finally {
      setIsDownloading(false)
    }
  }

  return (
    <div className="app-shell">
      <main className="glass-card report-page-card">
        <p className="page-kicker">Automatic Viva Taker</p>
        <h1 className="page-title">Session Report</h1>
        <p className="page-subtitle">
          Basic report view for Phase 3 with real backend session aggregates.
        </p>

        {location.state?.autoEnded && (
          <p className="info-text">Session auto-ended by adaptive decision.</p>
        )}

        {isLoading && <p className="info-text">Loading report...</p>}
        {errorMessage && <p className="error-text">{errorMessage}</p>}

        {!isLoading && !errorMessage && (
          <>
            <section className="report-summary-grid">
              <div className="report-summary-item">
                <p className="report-summary-label">Session ID</p>
                <p className="report-summary-value">{sessionId}</p>
              </div>

              <div className="report-summary-item">
                <p className="report-summary-label">Subject</p>
                <p className="report-summary-value">{report?.subject || 'N/A'}</p>
              </div>

              <div className="report-summary-item">
                <p className="report-summary-label">Overall Score</p>
                <p className="report-summary-value">{overallScore}</p>
              </div>

              <div className="report-summary-item">
                <p className="report-summary-label">Total Questions</p>
                <p className="report-summary-value">{totalQuestions}</p>
              </div>

              <div className="report-summary-item">
                <p className="report-summary-label">Current Level</p>
                <p className="report-summary-value">{report?.current_level ?? 'N/A'}</p>
              </div>

              <div className="report-summary-item">
                <p className="report-summary-label">Status</p>
                <p className="report-summary-value">{report?.status || 'N/A'}</p>
              </div>
            </section>

            <h2 className="section-heading">Per Topic Scores</h2>
            {Object.keys(topicScores).length === 0 ? (
              <p className="info-text">No topic scores available yet.</p>
            ) : (
              <div className="report-topic-grid">
                {Object.entries(topicScores).map(([topic, score]) => (
                  <article className="report-topic-card" key={topic}>
                    <h3 className="report-topic-title">{topic}</h3>
                    <p className="report-topic-score">Score: {score}</p>
                    <p className="report-topic-count">
                      Questions: {topicQuestionCounts[topic] ?? 0}
                    </p>
                  </article>
                ))}
              </div>
            )}

            <h2 className="section-heading">Switched Topics</h2>
            {switchedTopics.length === 0 ? (
              <p className="info-text">No topic switches in this session.</p>
            ) : (
              <ul className="report-switched-list">
                {switchedTopics.map((topic) => (
                  <li key={topic}>{topic}</li>
                ))}
              </ul>
            )}

            <h2 className="section-heading">Integrity Flags</h2>
            {integritySummary && integritySummary.total_flags > 0 ? (
              <>
                <p className="info-text">Total Flags: {integritySummary.total_flags}</p>
                <div className="report-topic-grid">
                  {Object.entries(integrityByType).map(([flagType, count]) => (
                    <article className="report-topic-card" key={flagType}>
                      <h3 className="report-topic-title">{flagType}</h3>
                      <p className="report-topic-score">Count: {count}</p>
                    </article>
                  ))}
                </div>

                {recentIntegrityFlags.length > 0 && (
                  <ul className="report-switched-list">
                    {recentIntegrityFlags.map((flag, index) => (
                      <li key={`${flag.flag_type}-${flag.timestamp}-${index}`}>
                        {flag.flag_type}
                        {flag.description ? ` - ${flag.description}` : ''}
                      </li>
                    ))}
                  </ul>
                )}
              </>
            ) : (
              <p className="info-text">No integrity flags recorded in this session.</p>
            )}
          </>
        )}

        <div className="report-actions">
          <Link to="/topics" className="action-link">
            Start Another Session
          </Link>

          <button type="button" className="action-link" onClick={handlePdfDownload} disabled={isDownloading}>
            {isDownloading ? 'Preparing PDF...' : 'Download PDF Report'}
          </button>

          {hasSummaryPayload && (
            <p className="info-text report-inline-note">
              Summary data was passed from session end and refreshed from report API.
            </p>
          )}
        </div>
      </main>
    </div>
  )
}

export default ReportPage
