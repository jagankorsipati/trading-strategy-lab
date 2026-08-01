/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        ink: '#102024',
        paper: '#f4f2eb',
        teal: '#0d766e',
        amber: '#c88735',
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui'],
        mono: ['IBM Plex Mono', 'ui-monospace', 'monospace'],
      },
      boxShadow: { panel: '0 1px 2px rgba(16,32,36,.06), 0 16px 50px rgba(16,32,36,.06)' },
    },
  },
  plugins: [],
}
