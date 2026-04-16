import TopicBadge from './TopicBadge'
import LevelIndicator from './LevelIndicator'

function QuestionDisplay({ questionText, topic, level, isLoading }) {
  return (
    <section className="viva-question-card" aria-live="polite">
      <div className="viva-question-meta">
        <TopicBadge topic={topic} />
        <LevelIndicator currentLevel={level} maxLevel={5} />
      </div>

      <h2 className="viva-question-title">Current Question</h2>
      <p className="viva-question-text">
        {isLoading
          ? 'Generating your next question...'
          : questionText || 'Question will appear here.'}
      </p>
    </section>
  )
}

export default QuestionDisplay
