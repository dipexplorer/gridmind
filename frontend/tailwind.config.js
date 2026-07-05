/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#6366f1',
        critical: '#ef4444',
        high: '#f97316',
        healthy: '#22c55e',
      }
    },
  },
  plugins: [],
}
