/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          primary: "#0f172a",
          secondary: "#f97316",
        },
      },
    },
  },
  plugins: [],
};
