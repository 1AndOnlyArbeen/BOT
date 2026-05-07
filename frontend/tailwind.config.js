/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0b0d12",
        panel: "#13161e",
        panel2: "#181c25",
        border: "#262b38",
        text: "#e8eaf0",
        muted: "#7d8492",
        accent: "#ff3b3b",
        accent2: "#00d4ff",
        glow: "#ff3b3b66",
      },
      fontFamily: {
        mono: ["'JetBrains Mono'", "Menlo", "ui-monospace", "monospace"],
      },
      animation: {
        "pulse-glow": "pulse-glow 1.5s ease-in-out infinite",
      },
      keyframes: {
        "pulse-glow": {
          "0%, 100%": { opacity: "1", boxShadow: "0 0 12px #ff3b3b" },
          "50%": { opacity: "0.5", boxShadow: "0 0 4px #ff3b3b" },
        },
      },
    },
  },
  plugins: [],
};
