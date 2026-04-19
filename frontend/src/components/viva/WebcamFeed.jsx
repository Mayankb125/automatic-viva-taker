import { useEffect, useRef, useState } from 'react'

function WebcamFeed({
  active,
  captureIntervalMs = 1000,
  onFrameCapture,
  onError,
}) {
  const videoRef = useRef(null)
  const streamRef = useRef(null)
  const intervalRef = useRef(null)
  const inFlightRef = useRef(false)

  const [isReady, setIsReady] = useState(false)

  useEffect(() => {
    async function startWebcam() {
      if (!active) {
        return
      }

      if (!navigator.mediaDevices?.getUserMedia) {
        onError?.('Webcam is not supported in this browser.')
        return
      }

      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 640 },
            height: { ideal: 360 },
            facingMode: 'user',
          },
          audio: false,
        })

        streamRef.current = stream
        if (videoRef.current) {
          videoRef.current.srcObject = stream
        }
        setIsReady(true)
      } catch {
        onError?.('Could not access webcam. Please allow camera permission.')
      }
    }

    startWebcam()

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
      intervalRef.current = null

      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop())
      }
      streamRef.current = null
      setIsReady(false)
    }
  }, [active, onError])

  useEffect(() => {
    if (!active || !isReady || !videoRef.current || !onFrameCapture) {
      return
    }

    const video = videoRef.current
    const canvas = document.createElement('canvas')
    const context = canvas.getContext('2d')
    if (!context) {
      onError?.('Could not initialize webcam capture canvas.')
      return
    }

    async function captureAndSend() {
      if (!video.videoWidth || !video.videoHeight) {
        return
      }
      if (inFlightRef.current) {
        return
      }

      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      context.drawImage(video, 0, 0, canvas.width, canvas.height)

      const frameDataUrl = canvas.toDataURL('image/jpeg', 0.8)
      inFlightRef.current = true
      try {
        await onFrameCapture(frameDataUrl)
      } finally {
        inFlightRef.current = false
      }
    }

    intervalRef.current = window.setInterval(captureAndSend, captureIntervalMs)

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
      intervalRef.current = null
    }
  }, [active, captureIntervalMs, isReady, onError, onFrameCapture])

  return (
    <section className="viva-webcam-card" aria-live="polite">
      <h3 className="viva-webcam-title">Proctoring Camera</h3>
      <p className="viva-webcam-caption">
        Webcam frames are checked every {Math.max(1, Math.round(captureIntervalMs / 1000))} second(s) for integrity flags.
      </p>
      <video
        ref={videoRef}
        className="viva-webcam-video"
        autoPlay
        playsInline
        muted
      />
    </section>
  )
}

export default WebcamFeed
