/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        forest: "#15372d",
        leaf: "#38966e",
        mint: "#e7f4ec",
        canvas: "#f5f7f5",
        ink: "#1d2c25",
        muted: "#77827b",
      },
      boxShadow: {
        card: "0 8px 28px rgba(27, 55, 42, .055)",
        float: "0 18px 55px rgba(24, 49, 37, .16)",
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
