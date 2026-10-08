/** @type {import("tailwindcss").Config} */
export default {
  content: [
    "./index.html",
    "./agenda/**/*.html",
    "./bilhetes/**/*.html",
    "./conta/**/*.html",
    "./equipa/**/*.html",
    "./informacao-ajuda/**/*.html",
    "./parcerias/**/*.html",
    "./sobre/**/*.html",
  ],
  // The existing ENEI stylesheet already defines the project reset. Keeping
  // Tailwind Preflight enabled changes native heading, button, form and list
  // styles and therefore breaks the pre-migration layout.
  corePlugins: {
    preflight: false,
  },
  theme: {
    extend: {
      colors: {
        enei: {
          "institutional-navy": "#000D36",
          black: "#000000",
          "cyan-700": "#006FA6",
          "cyan-500": "#00AAFF",
          "cyan-400": "#00C5FF",
          "ink-950": "#02101C",
          "bg-deep": "#030710",
          "ink-900": "#03101D",
          bg: "#050D21",
          surface: "#081126",
          "surface-alt": "#081526",
          panel: "#0A172F",
          "panel-alt": "#0A1930",
          "panel-strong": "#0D1A34",
          accent: "#1AB2FF",
          success: "#22C55E",
          "accent-strong": "#23CAFF",
          "cyan-300": "#28C2FF",
          mint: "#5BD6C4",
          subtle: "#8796A9",
          periwinkle: "#8F9CFF",
          lavender: "#AAB4FF",
          "muted-alt": "#AAB7C9",
          muted: "#B1BCCD",
          bronze: "#B68157",
          "neutral-200": "#C8D0DA",
          copper: "#D18B53",
          line: "#D7E3F4",
          gold: "#E5BF78",
          ice: "#E8F1FF",
          coral: "#EE9185",
          "neutral-50": "#EEF3F7",
          peach: "#F0D4BD",
          "gold-light": "#F2D99F",
          yellow: "#F4C542",
          error: "#FF8F84",
          white: "#FFFFFF",
        },
      },
      fontFamily: {
        display: ["Montserrat", "system-ui", "sans-serif"],
        sans: ["Poppins", "system-ui", "sans-serif"],
      },
      borderRadius: {
        card: "16px",
        panel: "24px",
      },
      boxShadow: {
        panel: "0 28px 70px rgb(0 0 0 / 0.32)",
      },
      maxWidth: {
        content: "1180px",
      },
    },
  },
  plugins: [],
};
