import { Link, useLocation } from "react-router-dom";

// Páginas onde a barra não aparece: a inicial (o protótipo tem-na, a organização não a quer), as de compra
// e os estados do sistema (no protótipo também faltava).
const HIDDEN_ON = [
  "/",
  "/bilhetes",
  "/conta/por-verificar",
  "/conta/link-expirado",
  "/conta/demasiadas-tentativas",
  "/conta/sessao-terminada",
];

/**
 * Barra fixa com o botão «Bilhetes», só no telemóvel (`ui-ux`: `.mobile-ticket`). O CSS esconde-a acima
 * de 620 px; nas páginas de compra e nos estados do sistema não existe.
 */
export default function MobileTicketBar() {
  const { pathname } = useLocation();
  if (HIDDEN_ON.some((path) => pathname === path || (path !== "/" && pathname.startsWith(`${path}/`)))) return null;

  return (
    <aside className="mobile-ticket" aria-label="Bilhetes">
      <span>
        <strong>ENEI 2027</strong>Bilhetes
      </span>
      <Link className="btn btn--primary" to="/bilhetes">
        Bilhetes
      </Link>
    </aside>
  );
}
