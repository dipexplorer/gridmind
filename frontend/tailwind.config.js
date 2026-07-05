/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        heading: ['Space Grotesk', 'sans-serif'],
        body: ['DM Sans', 'sans-serif'],
      },
      colors: {
        background: "#F8FAFC", // Clean Off-White
        foreground: "#1E293B", // Deep Slate
        primary: "#3B82F6", // Electric Blue
        secondary: "#60A5FA", // Light Blue
        border: "#E2E8F0", // Soft Gray
        risk: {
          healthy: "#10B981", // Emerald Green
          high: "#F59E0B", // Amber
          critical: "#EF4444", // Crimson Red
        }
      },
      boxShadow: {
        'bento': '0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03)',
        'bento-hover': '0 10px 15px -3px rgba(0, 0, 0, 0.08), 0 4px 6px -2px rgba(0, 0, 0, 0.04)',
      },
      transitionProperty: {
        'bento': 'transform, box-shadow, border-color',
      },
    },
  },
  plugins: [],
}
