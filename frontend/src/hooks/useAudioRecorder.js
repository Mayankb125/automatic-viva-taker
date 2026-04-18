import { useCallback, useEffect, useRef, useState } from 'react'

function getPreferredMimeType() {
  const options = [
    'audio/webm;codecs=opus',
    'audio/webm',
    'audio/ogg;codecs=opus',
    'audio/ogg',
    'audio/mp4',
  ]

  if (typeof MediaRecorder === 'undefined') {
    return ''
  }

  for (const mimeType of options) {
    if (MediaRecorder.isTypeSupported(mimeType)) {
      return mimeType
    }
  }

  return ''
}

function blobToDataUrl(blob) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onloadend = () => {
      if (typeof reader.result === 'string') {
        resolve(reader.result)
        return
      }
      reject(new Error('Could not convert audio to data URL.'))
    }
    reader.onerror = () => reject(new Error('Could not read recorded audio.'))
    reader.readAsDataURL(blob)
  })
}

export default function useAudioRecorder() {
  const recorderRef = useRef(null)
  const streamRef = useRef(null)
  const chunksRef = useRef([])
  const stopResolverRef = useRef(null)

  const [isRecording, setIsRecording] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [audioBlob, setAudioBlob] = useState(null)
  const [audioDataUrl, setAudioDataUrl] = useState('')
  const [error, setError] = useState('')

  const isSupported =
    typeof navigator !== 'undefined' &&
    !!navigator.mediaDevices?.getUserMedia &&
    typeof MediaRecorder !== 'undefined'

  const releaseResources = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop())
      streamRef.current = null
    }
    recorderRef.current = null
    chunksRef.current = []
  }, [])

  useEffect(() => {
    return () => {
      releaseResources()
    }
  }, [releaseResources])

  const clearRecording = useCallback(() => {
    setAudioBlob(null)
    setAudioDataUrl('')
    setError('')
  }, [])

  const startRecording = useCallback(async () => {
    if (!isSupported || isRecording) {
      return
    }

    clearRecording()

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const mimeType = getPreferredMimeType()
      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream)

      streamRef.current = stream
      recorderRef.current = recorder
      chunksRef.current = []

      recorder.ondataavailable = (event) => {
        if (event.data?.size > 0) {
          chunksRef.current.push(event.data)
        }
      }

      recorder.onerror = () => {
        setError('Recording failed. Please try again.')
      }

      recorder.onstop = async () => {
        setIsRecording(false)
        setIsProcessing(true)

        try {
          const blobType = mimeType || recorder.mimeType || 'audio/webm'
          const recordedBlob = new Blob(chunksRef.current, { type: blobType })

          if (recordedBlob.size === 0) {
            setError('No audio captured. Please record again.')
            if (stopResolverRef.current) {
              stopResolverRef.current('')
            }
            return
          }

          const dataUrl = await blobToDataUrl(recordedBlob)
          setAudioBlob(recordedBlob)
          setAudioDataUrl(dataUrl)

          if (stopResolverRef.current) {
            stopResolverRef.current(dataUrl)
          }
        } catch {
          setError('Could not process recorded audio.')
          if (stopResolverRef.current) {
            stopResolverRef.current('')
          }
        } finally {
          stopResolverRef.current = null
          setIsProcessing(false)
          releaseResources()
        }
      }

      recorder.start()
      setIsRecording(true)
    } catch {
      setError('Microphone permission denied or unavailable.')
      releaseResources()
    }
  }, [clearRecording, isRecording, isSupported, releaseResources])

  const stopRecording = useCallback(() => {
    if (!recorderRef.current || recorderRef.current.state === 'inactive') {
      return Promise.resolve('')
    }

    return new Promise((resolve) => {
      stopResolverRef.current = resolve
      recorderRef.current.stop()
    })
  }, [])

  return {
    isSupported,
    isRecording,
    isProcessing,
    audioBlob,
    audioDataUrl,
    error,
    startRecording,
    stopRecording,
    clearRecording,
  }
}
