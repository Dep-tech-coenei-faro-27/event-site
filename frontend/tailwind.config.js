/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx,html}"
  ],
  theme: {
    extend: {
        colors:{
            primary: '#2D6CDF', // Primary Blue 
            secondary: '#6B6B6B', // Off White
            background: '#F9F9F7', // Charcoal
            body: '#1A1A1A', // Warm Gray

        },

        fontFamily:{
            sans: ['"Inter"', 'sans-serif'],

        },

        fontSize: {
            'h1': ['48px', { fontWeight: '700'}],
            'h2': ['32px', { fontWeight: '700'}],
            'h3': ['24px', { fontWeight: '700'}],
            'body': ['16px', {lineHeight: '1.6', fontWeight: '400'}],
            'caption': ['12px', {letterSpacing: '0.08em', fontWeight: '500'}]
        }


    },
  },
  plugins: [],
}

