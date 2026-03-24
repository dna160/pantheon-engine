import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        bg: "#0a0a0f",
        card: "#13131f",
        border: "#1e1e30",
        "border-hover": "#3a3a58",
        purple: {
          DEFAULT: "#7b61ff",
          dim: "rgba(123,97,255,0.15)",
          border: "rgba(123,97,255,0.3)",
          deep: "#4f3bcc",
        },
        green: {
          DEFAULT: "#10b981",
          dim: "rgba(16,185,129,0.15)",
          border: "rgba(16,185,129,0.3)",
          deep: "#059669",
        },
        amber: {
          DEFAULT: "#f59e0b",
          dim: "rgba(245,158,11,0.15)",
          border: "rgba(245,158,11,0.3)",
        },
        red: {
          DEFAULT: "#dc2626",
          deep: "#991b1b",
        },
        text: {
          primary: "#e8e8f0",
          muted: "#b0b0c8",
          dim: "#7878a0",
          very_dim: "#5a5a80",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Consolas", "monospace"],
      },
      animation: {
        pulse_slow: "pulse 3s ease-in-out infinite",
        spin_slow: "spin 4s linear infinite",
        fadeIn: "fadeIn 0.4s ease-out forwards",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
