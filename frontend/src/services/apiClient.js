import axios from 'axios'

const DEFAULT_API_BASE_URL = `${window.location.protocol}//${window.location.hostname}:8000`
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})
