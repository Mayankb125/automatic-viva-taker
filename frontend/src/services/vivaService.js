import { apiClient } from './apiClient'

export async function getQuestion(sessionId) {
  const response = await apiClient.get('/api/viva/question', {
    params: { session_id: sessionId },
  })
  return response.data
}

export async function submitAnswer({ sessionId, questionId, textAnswer }) {
  const response = await apiClient.post('/api/viva/answer', {
    session_id: sessionId,
    question_id: questionId,
    text_answer: textAnswer,
  })
  return response.data
}
