/**
 * main.jsx — React Application Entry Point
 * ==========================================
 * This is the first JavaScript file Vite executes.
 * It mounts the entire React app onto the <div id="root"> element
 * defined in index.html.
 *
 * React.StrictMode wraps the app to:
 *  - Detect accidental side effects in development
 *  - Warn about deprecated API usage
 *  - Double-invoke certain functions in dev to surface bugs early
 * StrictMode has NO effect in production builds.
 */

import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'

// Create the React root and attach it to the #root div in index.html.
// App.jsx contains all routing and page components.
ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
)
