/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'pure-black': '#000000',
        'cream': '#F8F4EC',
        'cream-transparent': 'rgba(248, 244, 236, 0.8)',
      },
      fontFamily: {
        'departure': ['Departure Mono', 'JetBrains Mono', 'Monaco', 'Consolas', 'monospace'],
      },
      backdropBlur: {
        'xs': '2px',
      },
    },
  },
  plugins: [],
}
