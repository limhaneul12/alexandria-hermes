import type { Config } from "tailwindcss";
import tailwindcssAnimate from "tailwindcss-animate";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./src/app/**/*.{ts,tsx}",
    "./src/components/**/*.{ts,tsx}",
    "./src/lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        archive: {
          950: "#0b0b0b",
          900: "#111111",
          850: "#161616",
          800: "#1d1a16",
          700: "#2b2418",
        },
        gold: {
          50: "#fff7db",
          100: "#f9e9b3",
          200: "#e8cc79",
          300: "#d6ad45",
          400: "#b98b2f",
          500: "#9c6f22",
          600: "#76521b",
          700: "#533a16",
        },
        bronze: "#8f6337",
        parchment: "#d8c59a",
      },
      fontFamily: {
        serif: ["var(--font-display)", "Georgia", "serif"],
        sans: ["var(--font-body)", "Inter", "system-ui", "sans-serif"],
      },
      boxShadow: {
        gold: "0 18px 50px rgba(185, 139, 47, 0.14)",
        book: "0 20px 60px rgba(0, 0, 0, 0.38)",
      },
      backgroundImage: {
        "radial-gold": "radial-gradient(circle at top left, rgba(214, 173, 69, 0.16), transparent 36%)",
        "archive-panel": "linear-gradient(145deg, rgba(31, 28, 23, 0.96), rgba(10, 10, 10, 0.92))",
      },
    },
  },
  plugins: [tailwindcssAnimate],
};

export default config;
