import { apiClient } from './apiClient'

export async function getReport(sessionId) {
  const response = await apiClient.get(`/api/report/${sessionId}`)
  return response.data
}
