function IntegrityAlert({ alert }) {
  if (!alert) {
    return null
  }

  return (
    <div className="integrity-alert" role="status" aria-live="polite">
      <p className="integrity-alert-title">Integrity Notice</p>
      <p className="integrity-alert-text">{alert.message}</p>
    </div>
  )
}

export default IntegrityAlert
