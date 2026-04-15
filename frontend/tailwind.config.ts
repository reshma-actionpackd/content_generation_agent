import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        surface: "rgba(255, 255, 255, 0.62)",
        glow: "#39b7ff",
        accent: "#0f6fff",
        ink: "#0c1a34",
      },
      boxShadow: {
        glow: "0 0 30px rgba(57, 183, 255, 0.35)",
      },
      backgroundImage: {
        "soft-grid": "radial-gradient(circle at 1px 1px, rgba(12, 26, 52, 0.06) 1px, transparent 0)",
      },
    },
  },
  plugins: [],
};

export default config;
