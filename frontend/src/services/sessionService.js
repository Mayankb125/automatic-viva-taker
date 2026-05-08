import { apiClient } from './apiClient'

export async function startSession({ studentId, subject, topicList, pipelineMode }) {
  const response = await apiClient.post('/api/session/start', {
    student_id: studentId,
    subject,
    topic_list: topicList,
    pipeline_mode: pipelineMode,
  })
  return response.data
}

export async function getSession(sessionId) {
  const response = await apiClient.get(`/api/session/${sessionId}`)
  return response.data
}

export async function endSession(sessionId) {
  const response = await apiClient.post('/api/session/end', {
    session_id: sessionId,
  })
  return response.data
}
