/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{html,js,ts,jsx,tsx,vue}",
  ],
  theme: {
    extend: {
      colors: {
        /* Paleta 01/03: Identidade e superfícies */
        'azul-identidade': '#000D36',
        'azul-noite': '#030710',
        'azul-base': '#050D21',
        'azul-superficie': '#081126',
        'azul-superficie-2': '#081526',
        'azul-painel': '#0A172F',
        'azul-faq': '#0A1930',
        'azul-elevado': '#0D1A34',
        'texto-sobre-ciano': '#02101C',
        'texto-de-acao': '#03101D',
        'branco': '#FFFFFF',
        'ciano-profundo': '#006FA6',

        /* Paleta 02/03: Azuis, cianos e leitura */
        'ciano-digital': '#00AAFF',
        'ciano-vivo': '#00C5FF',
        'acento-principal': '#1AB2FF',
        'acento-forte': '#23CAFF',
        'ciano-icone': '#28C2FF',
        'verde-agua': '#5BD6C4',
        'indigo-beneficio': '#8F9CFF',
        'pervinca': '#AAB4FF',
        'cinza-subtil': '#8796A9',
        'nevoa-azul': '#AAB7C9',
        'cinza-texto': '#B1BCCD',
        'gelo': '#D7E3F4',

        /* Paleta 03/03: Estados e acentos quentes */
        'verde-sucesso': '#22C55E',
        'terracota-algarve': '#B68157',
        'prata': '#C8D0DA',
        'bronze': '#D18B53',
        'areia': '#E5BF78',
        'ouro': '#F4C542',
        'coral-suave': '#EE9185',
        'coral-vivo': '#FF8F84',
        'pessego-claro': '#F0D4BD',
        'areia-clara': '#F2D99F',
        'azul-gelo': '#E8F1FF',
        'superficie-clara': '#EEF3F7',
      },
      fontFamily: {
        poppins: ['Poppins', 'sans-serif'],
        montserrat: ['Montserrat', 'sans-serif'],
      },
    },
  },
  plugins: [],
};