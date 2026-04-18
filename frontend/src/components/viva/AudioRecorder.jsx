import useAudioRecorder from '../../hooks/useAudioRecorder'

function AudioRecorder({
  disabled,
  isSubmitting,
  onAudioReady,
}) {
  const {
    isSupported,
    isRecording,
    isProcessing,
    audioDataUrl,
    error,
    startRecording,
    stopRecording,
    clearRecording,
  } = useAudioRecorder()

  async function handleStart() {
    await startRecording()
  }

  async function handleStop() {
    const recordedDataUrl = await stopRecording()
    if (recordedDataUrl && onAudioReady) {
      onAudioReady(recordedDataUrl)
    }
  }

  function handleClear() {
    clearRecording()
    onAudioReady('')
  }

  return (
    <section className="viva-recorder-card" aria-live="polite">
      <h3 className="viva-recorder-title">Your Answer (voice)</h3>

      {!isSupported && (
        <p className="error-text">Microphone recording is not supported in this browser.</p>
      )}

      {error && <p className="error-text">{error}</p>}

      <div className="viva-recorder-actions">
        <button
          type="button"
          className="viva-btn viva-btn-primary"
          disabled={disabled || isSubmitting || isRecording || !isSupported}
          onClick={handleStart}
        >
          Start Recording
        </button>

        <button
          type="button"
          className="viva-btn viva-btn-secondary"
          disabled={disabled || isSubmitting || !isRecording}
          onClick={handleStop}
        >
          Stop Recording
        </button>

        <button
          type="button"
          className="viva-btn"
          disabled={disabled || isSubmitting || !audioDataUrl || isRecording}
          onClick={handleClear}
        >
          Clear Audio
        </button>
      </div>

      <p className="viva-recorder-status">
        {isRecording && 'Recording in progress...'}
        {!isRecording && isProcessing && 'Processing recording...'}
        {!isRecording && !isProcessing && audioDataUrl && 'Audio captured. Ready to submit.'}
        {!isRecording && !isProcessing && !audioDataUrl && 'Record your answer, then submit.'}
      </p>

      {audioDataUrl && (
        <audio className="viva-recorder-preview" controls src={audioDataUrl} preload="metadata" />
      )}
    </section>
  )
}

export default AudioRecorder
