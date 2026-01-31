/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Status colors
        status: {
          running: '#eab308',
          completed: '#22c55e',
          failed: '#ef4444',
          timeout: '#f97316',
        },
        // Role colors
        role: {
          planner: '#8b5cf6',
          executor: '#10b981',
          reviewer: '#f59e0b',
          coder: '#3b82f6',
          researcher: '#ec4899',
          default: '#6b7280',
        },
      },
    },
  },
  plugins: [],
}
