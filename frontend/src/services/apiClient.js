import axios from 'axios'

const apiHost = window.location.hostname === 'localhost' ? '127.0.0.1' : window.location.hostname
const DEFAULT_API_BASE_URL = `${window.location.protocol}//${apiHost}:8000`
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})
