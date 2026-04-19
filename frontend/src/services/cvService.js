import { apiClient } from './apiClient'

export async function analyzeFrame({ sessionId, questionId, frame, capturedAt }) {
  const response = await apiClient.post('/api/cv/analyze', {
    session_id: sessionId,
    question_id: questionId,
    frame,
    captured_at: capturedAt,
  })
  return response.data
}
