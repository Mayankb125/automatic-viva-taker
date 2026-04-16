import { apiClient } from './apiClient'

export async function getTopics() {
  const response = await apiClient.get('/api/topics')
  return response.data
}

export async function switchTopic({ sessionId, newTopic }) {
  const response = await apiClient.post('/api/session/switch-topic', {
    session_id: sessionId,
    new_topic: newTopic,
  })
  return response.data
}
