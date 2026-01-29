export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        'up-red': '#ff333a',
        'down-green': '#00b060', // A-share specific green
      }
    },
  },
  plugins: [],
}
