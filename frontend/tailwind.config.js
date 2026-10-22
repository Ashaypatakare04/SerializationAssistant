/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        studio: {
          900: "#0F1117",
          850: "#141722",
          800: "#1A1D2A",
          750: "#222638",
          700: "#2B3147",
          600: "#3D4460",
          500: "#586288",
          400: "#8B95B8",
          300: "#B8C1DD",
          200: "#DCE1F2",
          100: "#F0F3FC",
          accent: "#D97706",
          accentHover: "#B45309",
          cyan: "#06B6D4",
          emerald: "#10B981",
          rose: "#F43F5E"
        }
      }
    },
  },
  plugins: [],
};
