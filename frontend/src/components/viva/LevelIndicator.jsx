function LevelIndicator({ currentLevel = 1, maxLevel = 5 }) {
  const safeLevel = Math.max(1, Math.min(maxLevel, currentLevel))

  return (
    <section className="viva-level-indicator" aria-label="Difficulty level">
      <div className="viva-level-header">
        <p className="viva-level-title">Difficulty Level</p>
        <p className="viva-level-value">
          {safeLevel}/{maxLevel}
        </p>
      </div>

      <div className="viva-level-steps" role="list" aria-label="Level progress">
        {Array.from({ length: maxLevel }, (_, index) => {
          const level = index + 1
          const isActive = level <= safeLevel

          return (
            <span
              key={level}
              role="listitem"
              className={`viva-level-dot ${isActive ? 'is-active' : ''}`}
              aria-label={`Level ${level}`}
            />
          )
        })}
      </div>
    </section>
  )
}

export default LevelIndicator
