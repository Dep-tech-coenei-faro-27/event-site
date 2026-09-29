# ENEI 2027 — UI/UX submission

Static HTML and CSS submission for the ENEI 2027 interface.

## Included

- Responsive landing page, event-information pages, FAQ and footer
- Login, registration and password-recovery interface screens
- Brand colours, typography, components and optimized visual assets
- Static page-to-page navigation

## Scope

This folder is a UI/UX deliverable. It contains no JavaScript, backend, database,
authentication, checkout or other application logic. Controls that would require
application logic are presented only as interface states.

## Preview

No installation or build step is required. From this folder, run:

```powershell
python -m http.server 4173 --bind 127.0.0.1
```

Then open `http://127.0.0.1:4173/`.

## Pages

- `/` — landing page
- `/sobre/` — event and location
- `/agenda/` — schedule and activities
- `/parcerias/` — partnerships
- `/equipa/` — team
- `/informacao-ajuda/` — FAQ and support
- `/bilhetes/` — ticket interface
- `/conta/` — login
- `/conta/criar/` — registration
- `/conta/recuperar/` — password recovery
- `/conta/redefinir/` — password reset
- `/conta/verificar/` — email verification
- `/conta/perfil/` — profile interface
