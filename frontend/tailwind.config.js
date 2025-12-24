/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: ["./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "hsl(0 0% 7%)",
        foreground: "hsl(0 0% 95%)",
        primary: {
          DEFAULT: "hsl(173 80% 40%)",
          foreground: "hsl(0 0% 5%)",
        },
        secondary: {
          DEFAULT: "hsl(0 0% 12%)",
          foreground: "hsl(0 0% 95%)",
        },
        muted: {
          DEFAULT: "hsl(0 0% 15%)",
          foreground: "hsl(0 0% 55%)",
        },
        accent: {
          DEFAULT: "hsl(142 70% 45%)",
          foreground: "hsl(0 0% 95%)",
        },
        destructive: {
          DEFAULT: "hsl(0 72% 51%)",
          foreground: "hsl(0 0% 95%)",
        },
        warning: {
          DEFAULT: "hsl(38 92% 50%)",
          foreground: "hsl(0 0% 5%)",
        },
        border: "hsl(0 0% 18%)",
        card: "hsl(0 0% 10%)",
        glow: {
          primary: "hsl(173 80% 40% / 0.15)",
          accent: "hsl(142 70% 45% / 0.15)",
        },
      },
      fontFamily: {
        sans: ["Outfit", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "Fira Code", "monospace"],
      },
      boxShadow: {
        'glow-sm': '0 0 20px -5px hsl(173 80% 40% / 0.3)',
        'glow-md': '0 0 40px -10px hsl(173 80% 40% / 0.4)',
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
        'mesh': 'radial-gradient(at 40% 20%, hsl(173 80% 40% / 0.05) 0px, transparent 50%), radial-gradient(at 80% 0%, hsl(142 70% 45% / 0.03) 0px, transparent 50%), radial-gradient(at 0% 50%, hsl(173 80% 40% / 0.03) 0px, transparent 50%)',
      },
    },
  },
  plugins: [require("@tailwindcss/typography")],
};
