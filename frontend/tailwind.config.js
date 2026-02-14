/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{js,jsx,ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef7ff",
          100: "#d9edff",
          200: "#bce0ff",
          300: "#8eceff",
          400: "#59b3ff",
          500: "#3391ff",
          600: "#1a6ff5",
          700: "#1359e1",
          800: "#1649b6",
          900: "#183f8f",
          950: "#142857",
        },
      },
    },
  },
  plugins: [],
};
