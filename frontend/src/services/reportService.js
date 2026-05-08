import { apiClient } from './apiClient'

export async function getReport(sessionId) {
  const response = await apiClient.get(`/api/report/${sessionId}`)
  return response.data
}

export async function downloadReportPdf(sessionId) {
  const response = await apiClient.get(`/api/report/${sessionId}/pdf`, {
    responseType: 'blob',
  })
  return response.data
}
