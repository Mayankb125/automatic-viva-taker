/**
 * ComparisonView.jsx
 * ====================
 * Phase 5 Step 5.2 - Show legacy vs ground scores side-by-side
 * Displays both scoring approaches for transparency
 */

import './ComparisonView.css'

function ComparisonView({ comparison }) {
  if (!comparison) {
    return null
  }

  const { legacy, grounded, difference } = comparison

  const metricGraphRows = [
    {
      label: 'Final',
      legacy: Number(legacy?.score || 0),
      grounded: Number(grounded?.score || 0),
    },
    {
      label: 'Semantic',
      legacy: Number(legacy?.breakdown?.semantic_score || 0),
      grounded: Number(grounded?.breakdown?.semantic_score || 0),
    },
    {
      label: 'Keyword',
      legacy: Number(legacy?.breakdown?.keyword_score || 0),
      grounded: Number(grounded?.breakdown?.keyword_score || 0),
    },
    {
      label: 'Depth',
      legacy: Number(legacy?.breakdown?.depth_score || 0),
      grounded: Number(grounded?.breakdown?.depth_score || 0),
    },
    {
      label: 'Completeness',
      legacy: Number(legacy?.breakdown?.completeness_score || 0),
      grounded: Number(grounded?.breakdown?.completeness_score || 0),
    },
    {
      label: 'Confidence',
      legacy: Number(legacy?.breakdown?.confidence_score || 0),
      grounded: Number(grounded?.breakdown?.confidence_score || 0),
    },
  ]

  const scaleMax = 10

  return (
    <section className="comparison-view-section">
      <h2 className="section-heading">Scoring Comparison</h2>
      <p className="comparison-intro">
        Both legacy and ground scoring methods are shown below. The ground approach
        provides more detailed concept and phrase analysis.
      </p>

      <div className="comparison-graph-box">
        <div className="comparison-graph-header">
          <h3>Per-Question Model Comparison Graph</h3>
          <p className="comparison-graph-subtitle">
            One graph for both models after each submitted answer.
          </p>
        </div>

        <div className="comparison-graph-legend">
          <span className="legend-item">
            <span className="legend-dot legend-dot-legacy" /> Legacy
          </span>
          <span className="legend-item">
            <span className="legend-dot legend-dot-grounded" /> Ground
          </span>
        </div>

        <div className="comparison-graph-grid">
          {metricGraphRows.map((row) => {
            const legacyPercent = Math.max(0, Math.min(100, (row.legacy / scaleMax) * 100))
            const groundedPercent = Math.max(0, Math.min(100, (row.grounded / scaleMax) * 100))

            return (
              <div className="comparison-graph-row" key={row.label}>
                <div className="comparison-graph-metric">{row.label}</div>

                <div className="comparison-graph-bars">
                  <div className="bar-track" aria-label={`${row.label} legacy score`}>
                    <div className="bar-fill bar-fill-legacy" style={{ width: `${legacyPercent}%` }} />
                  </div>
                  <div className="bar-track" aria-label={`${row.label} ground score`}>
                    <div className="bar-fill bar-fill-grounded" style={{ width: `${groundedPercent}%` }} />
                  </div>
                </div>

                <div className="comparison-graph-values">
                  <span>{row.legacy.toFixed(2)}</span>
                  <span>{row.grounded.toFixed(2)}</span>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      <div className="comparison-grid">
        {/* Legacy Column */}
        <div className="comparison-column legacy-column">
          <div className="column-header">
            <h3>Legacy Scoring</h3>
            <div className="score-display">
              <span className="score-value">{legacy?.score?.toFixed(2)}</span>
              <span className={`score-band score-band-${legacy?.band}`}>
                {legacy?.band?.toUpperCase()}
              </span>
            </div>
          </div>

          <div className="breakdown-section">
            <h4>Component Scores</h4>
            <div className="score-rows">
              <div className="score-row">
                <span className="label">Semantic</span>
                <span className="value">{legacy?.breakdown?.semantic_score?.toFixed(2)}</span>
              </div>
              <div className="score-row">
                <span className="label">Keyword</span>
                <span className="value">{legacy?.breakdown?.keyword_score?.toFixed(2)}</span>
              </div>
              <div className="score-row">
                <span className="label">Depth</span>
                <span className="value">{legacy?.breakdown?.depth_score?.toFixed(2)}</span>
              </div>
              <div className="score-row">
                <span className="label">Completeness</span>
                <span className="value">{legacy?.breakdown?.completeness_score?.toFixed(2)}</span>
              </div>
              <div className="score-row">
                <span className="label">Confidence</span>
                <span className="value">{legacy?.breakdown?.confidence_score?.toFixed(2)}</span>
              </div>
              <div className="score-row separator">
                <span className="label">
                  <strong>Weighted</strong>
                </span>
                <span className="value">
                  <strong>{legacy?.breakdown?.weighted_score?.toFixed(2)}</strong>
                </span>
              </div>
            </div>
          </div>

          {legacy?.feedback && (
            <div className="feedback-section">
              <h4>Feedback</h4>
              <p className="feedback-text">
                <strong>Summary:</strong> {legacy.feedback.summary}
              </p>
              <p className="feedback-text recommendation">
                <strong>Suggestion:</strong> {legacy.feedback.recommendation}
              </p>
            </div>
          )}
        </div>

        {/* Grounded Column */}
        <div className="comparison-column grounded-column">
          <div className="column-header">
            <h3>Ground Scoring</h3>
            <div className="score-display">
              <span className="score-value">{grounded?.score?.toFixed(2)}</span>
              <span className={`score-band score-band-${grounded?.band}`}>
                {grounded?.band?.toUpperCase()}
              </span>
            </div>
          </div>

          <div className="breakdown-section">
            <h4>Component Scores</h4>
            <div className="score-rows">
              <div className="score-row">
                <span className="label">Semantic</span>
                <span className="value">{grounded?.breakdown?.semantic_score?.toFixed(2)}</span>
              </div>
              <div className="score-row">
                <span className="label">Keyword</span>
                <span className="value">{grounded?.breakdown?.keyword_score?.toFixed(2)}</span>
              </div>
              <div className="score-row">
                <span className="label">Depth</span>
                <span className="value">{grounded?.breakdown?.depth_score?.toFixed(2)}</span>
              </div>
              <div className="score-row">
                <span className="label">Completeness</span>
                <span className="value">{grounded?.breakdown?.completeness_score?.toFixed(2)}</span>
              </div>
              <div className="score-row">
                <span className="label">Confidence</span>
                <span className="value">{grounded?.breakdown?.confidence_score?.toFixed(2)}</span>
              </div>
              <div className="score-row separator">
                <span className="label">
                  <strong>Weighted</strong>
                </span>
                <span className="value">
                  <strong>{grounded?.breakdown?.weighted_score?.toFixed(2)}</strong>
                </span>
              </div>
            </div>
          </div>

          {grounded?.feedback && (
            <div className="feedback-section">
              <h4>Feedback</h4>
              <p className="feedback-text">
                <strong>Summary:</strong> {grounded.feedback.summary}
              </p>
              <p className="feedback-text recommendation">
                <strong>Suggestion:</strong> {grounded.feedback.recommendation}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Difference Summary */}
      {difference && (
        <div className="difference-summary">
          <h3>Score Analysis</h3>
          <div className="difference-content">
            <div className="difference-item">
              <span className="difference-label">Difference:</span>
              <span
                className={`difference-value ${
                  difference.score_delta > 0 ? 'positive' : difference.score_delta < 0 ? 'negative' : 'equal'
                }`}
              >
                {difference.score_delta > 0 ? '+' : ''}
                {difference.score_delta.toFixed(2)}
              </span>
            </div>
            <div className="difference-item">
              <span className="difference-label">Higher Score:</span>
              <span className="difference-value">
                {difference.higher_score === 'grounded'
                  ? 'Ground'
                  : difference.higher_score === 'legacy'
                    ? 'Legacy'
                    : 'Equal'}
              </span>
            </div>
          </div>
          <p className="difference-note">
            Note: The system uses the selected scoring method for adaptive decisions. Both scores
            are provided for transparency and teacher review.
          </p>
        </div>
      )}
    </section>
  )
}

export default ComparisonView
