function TopicSwitchModal({
  isOpen,
  topicList,
  failedTopics,
  onSwitch,
  onClose,
  isSwitching,
}) {
  if (!isOpen) {
    return null
  }

  const failedSet = new Set(failedTopics)
  const selectableTopics = topicList.filter((topic) => !failedSet.has(topic))

  return (
    <div className="viva-modal-overlay" role="dialog" aria-modal="true" aria-labelledby="topic-switch-title">
      <div className="viva-modal-card">
        <h2 id="topic-switch-title" className="viva-modal-title">
          Pick a New Topic
        </h2>
        <p className="viva-modal-text">
          The last checkpoint was not passed. Please continue with a new topic.
        </p>

        <div className="viva-modal-topics">
          {topicList.map((topic) => {
            const isFailed = failedSet.has(topic)

            return (
              <button
                key={topic}
                type="button"
                className={`viva-modal-topic-btn ${isFailed ? 'is-disabled' : ''}`}
                disabled={isFailed || isSwitching}
                onClick={() => onSwitch(topic)}
              >
                {topic}
                {isFailed ? ' (unavailable)' : ''}
              </button>
            )
          })}
        </div>

        {selectableTopics.length === 0 && (
          <p className="error-text">
            No alternate topics left to switch. End this session and start a new one.
          </p>
        )}

        <div className="viva-modal-actions">
          <button
            type="button"
            className="viva-btn viva-btn-secondary"
            onClick={onClose}
            disabled={isSwitching}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

export default TopicSwitchModal
