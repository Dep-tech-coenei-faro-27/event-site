# ENEI 2027 — UI/UX submission

Static HTML presentation for the ENEI 2027 interface, built with Tailwind CSS.

## Development

```powershell
npm install
npm run dev
```

Tailwind watches every HTML page and compiles `src/tailwind.css` to
`styles.css`. The generated stylesheet is committed so the prototype can be
opened or served without installing dependencies.

## Production build

```powershell
npm run build
```

## Formatting

```powershell
npm run format
npm run format:check
```

## Architecture

- `tailwind.config.js` is the single source of truth for the complete ENEI palette,
  typography, radii, shadows, and content discovery.
- `src/tailwind.css` declares Tailwind's base, component, and utility layers.
- `src/core.css`, `src/auth.css`, and `src/checkout.css` keep component rules separated by domain.
- `scripts/build-css.mjs` compiles Tailwind first, then appends component modules in deterministic cascade order.
- `scripts/build-css.mjs` compiles Tailwind first, then appends component modules in deterministic cascade order.
- `scripts/build-css.mjs` compiles Tailwind first, then appends component modules in deterministic cascade order.
- `scripts/build-css.mjs` compiles Tailwind first, then appends component modules in deterministic cascade order.
- `styles.css` is generated output. Do not edit it directly.
- HTML pages keep descriptive component classes instead of repeating long utility lists.

## Scope

This directory is a UI/UX deliverable. It contains no backend, database,
authentication, or live payment processing. Controls that require application
logic are presented as interface states.

## Preview

After building, run:

```powershell
python -m http.server 4174 --bind 127.0.0.1
```

Then open `http://127.0.0.1:4174/`.

## Routes

- `/` — landing page
- `/sobre/` — event and location
- `/agenda/` — schedule and activities
- `/parcerias/` — partnerships
- `/equipa/` — team
- `/informacao-ajuda/` — FAQ and support
- `/bilhetes/` — ticket options
- `/bilhetes/checkout/` — ticket selection and MB Way checkout
- `/bilhetes/checkout/aguardar/` — pending payment
- `/bilhetes/checkout/sucesso/` — successful payment
- `/bilhetes/checkout/erro/` — failed payment
- `/conta/` — login
- `/conta/criar/` — registration
- `/conta/recuperar/` — password recovery
- `/conta/redefinir/` — password reset
- `/conta/verificar/` — email verification
- `/conta/perfil/` — profile interface
