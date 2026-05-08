import { apiClient } from './apiClient'

export async function uploadKnowledgeSource({ subject, topic, file }) {
  const formData = new FormData()
  formData.append('subject', subject)
  formData.append('topic', topic)
  formData.append('source_file', file)

  const response = await apiClient.post('/api/knowledge/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })

  return response.data
}

export async function getKnowledgeAsset(assetId) {
  const response = await apiClient.get(`/api/knowledge/${assetId}`)
  return response.data
}
