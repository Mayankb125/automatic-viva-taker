/**
 * GroundedScoreBreakdown.jsx
 * ============================
 * Phase 5 Step 5.2 - Display grounded scoring details
 * Shows matched/missing concepts, phrases, features, and penalties
 */

import './GroundedScoreBreakdown.css'

function GroundedScoreBreakdown({ grounded }) {
  if (!grounded) {
    return null
  }

  const {
    score,
    band,
    breakdown,
    feedback,
    feature_breakdown,
    penalties,
    matched_must_concepts,
    missing_must_concepts,
    matched_optional_concepts,
    matched_phrases,
    missing_phrases,
  } = grounded

  return (
    <section className="grounded-score-section">
      <h2 className="section-heading">Grounded Score Analysis</h2>

      {/* Score Summary */}
      <div className="grounded-summary-box">
        <div className="score-card">
          <h3>Final Score</h3>
          <p className={`final-score score-band-${band}`}>{score.toFixed(2)}</p>
          <p className="score-band-label">{band.toUpperCase()}</p>
        </div>

        <div className="sub-scores-grid">
          <div className="sub-score">
            <label>Semantic</label>
            <span>{breakdown?.semantic_score?.toFixed(2) || '0'}</span>
          </div>
          <div className="sub-score">
            <label>Keyword</label>
            <span>{breakdown?.keyword_score?.toFixed(2) || '0'}</span>
          </div>
          <div className="sub-score">
            <label>Depth</label>
            <span>{breakdown?.depth_score?.toFixed(2) || '0'}</span>
          </div>
          <div className="sub-score">
            <label>Completeness</label>
            <span>{breakdown?.completeness_score?.toFixed(2) || '0'}</span>
          </div>
          <div className="sub-score">
            <label>Confidence</label>
            <span>{breakdown?.confidence_score?.toFixed(2) || '0'}</span>
          </div>
          <div className="sub-score">
            <label>Weighted</label>
            <span>{breakdown?.weighted_score?.toFixed(2) || '0'}</span>
          </div>
        </div>
      </div>

      {/* Concept Coverage */}
      {(matched_must_concepts?.length > 0 || missing_must_concepts?.length > 0) && (
        <div className="concepts-box">
          <h3>Must-Have Concepts</h3>
          {matched_must_concepts?.length > 0 && (
            <div className="concept-group">
              <h4 className="matched-label">✓ Matched</h4>
              <ul className="concept-list matched">
                {matched_must_concepts.map((concept, idx) => (
                  <li key={`matched-${idx}`}>{concept}</li>
                ))}
              </ul>
            </div>
          )}
          {missing_must_concepts?.length > 0 && (
            <div className="concept-group">
              <h4 className="missing-label">✗ Missing</h4>
              <ul className="concept-list missing">
                {missing_must_concepts.map((concept, idx) => (
                  <li key={`missing-${idx}`}>{concept}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Optional Concepts */}
      {matched_optional_concepts?.length > 0 && (
        <div className="concepts-box">
          <h3>Optional Concepts</h3>
          <div className="concept-group">
            <ul className="concept-list matched">
              {matched_optional_concepts.map((concept, idx) => (
                <li key={`optional-${idx}`}>{concept}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Key Phrases */}
      {(matched_phrases?.length > 0 || missing_phrases?.length > 0) && (
        <div className="phrases-box">
          <h3>Key Phrases</h3>
          {matched_phrases?.length > 0 && (
            <div className="phrase-group">
              <h4 className="matched-label">✓ Found</h4>
              <div className="phrase-list matched">
                {matched_phrases.map((phrase, idx) => (
                  <span key={`phrase-matched-${idx}`} className="phrase-tag">
                    {phrase}
                  </span>
                ))}
              </div>
            </div>
          )}
          {missing_phrases?.length > 0 && (
            <div className="phrase-group">
              <h4 className="missing-label">✗ Missing</h4>
              <div className="phrase-list missing">
                {missing_phrases.map((phrase, idx) => (
                  <span key={`phrase-missing-${idx}`} className="phrase-tag">
                    {phrase}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Feature Breakdown */}
      {feature_breakdown && Object.keys(feature_breakdown).length > 0 && (
        <div className="features-box">
          <h3>Feature Values</h3>
          <div className="features-grid">
            {Object.entries(feature_breakdown).map(([key, value]) => (
              <div key={key} className="feature-item">
                <label>{key.replace(/_/g, ' ')}</label>
                <span className="feature-value">
                  {typeof value === 'number' ? value.toFixed(3) : String(value)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Penalties */}
      {penalties && penalties.length > 0 && (
        <div className="penalties-box">
          <h3>Penalties Applied</h3>
          <div className="penalty-list">
            {penalties.map((penalty, idx) => (
              <div key={idx} className="penalty-item">
                <div className="penalty-type">{penalty.type || 'Penalty'}</div>
                <div className="penalty-amount">-{penalty.amount?.toFixed(2) || '0'}</div>
                <div className="penalty-reason">{penalty.reason || 'No reason specified'}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Feedback */}
      {feedback && (
        <div className="feedback-box">
          <h3>Feedback</h3>
          {feedback.depth_reason && (
            <p>
              <strong>Depth:</strong> {feedback.depth_reason}
            </p>
          )}
          {feedback.completeness_reason && (
            <p>
              <strong>Completeness:</strong> {feedback.completeness_reason}
            </p>
          )}
          {feedback.summary && (
            <p>
              <strong>Summary:</strong> {feedback.summary}
            </p>
          )}
          {feedback.recommendation && (
            <p className="recommendation">
              <strong>Recommendation:</strong> {feedback.recommendation}
            </p>
          )}
        </div>
      )}
    </section>
  )
}

export default GroundedScoreBreakdown
