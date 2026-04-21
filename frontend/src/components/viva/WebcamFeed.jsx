import { useEffect, useRef, useState } from 'react'

const FRAME_WIDTH = 640
const FRAME_HEIGHT = 360

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
            width: { ideal: FRAME_WIDTH },
            height: { ideal: FRAME_HEIGHT },
            aspectRatio: { ideal: FRAME_WIDTH / FRAME_HEIGHT },
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

      // Keep outbound CV frames stable for deterministic backend processing.
      canvas.width = FRAME_WIDTH
      canvas.height = FRAME_HEIGHT
      context.drawImage(video, 0, 0, FRAME_WIDTH, FRAME_HEIGHT)

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
        width={FRAME_WIDTH}
        height={FRAME_HEIGHT}
        autoPlay
        playsInline
        muted
      />
    </section>
  )
}

export default WebcamFeed
