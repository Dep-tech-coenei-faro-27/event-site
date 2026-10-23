# ruff: noqa: E501
import re
from html import escape
from pathlib import Path

import app.core.config as config

VERIFICATION_EMAIL_SUBJECT = "Confirma o teu email"
PASSWORD_RESET_SUBJECT = "Recuperação de Password"
PASSWORD_CHANGED_SUBJECT = "A tua password foi alterada"
TICKET_EMAIL_SUBJECT = "O teu bilhete para o ENEI 2027"
TICKET_QR_CID = "ticket-qr"
TICKET_PATH = "/perfil"
EVENT_DATES = "1–4 abril 2027"
EVENT_LOCATION = "Faro, Algarve"
MARKER_PATTERN = re.compile(r"\[([A-Z][A-Z_]*)\]")
_TICKET_HTML = Path(__file__).with_name("ticket_email.html")
_TICKET_TEXT = Path(__file__).with_name("ticket_email.txt")


def build_verification_email_html(first_name: str, verify_url: str) -> str:
    safe_name = escape(first_name)
    safe_url = escape(verify_url, quote=True)
    return f"""\
<html>
  <body style="margin:0;padding:0;background-color:#f4f4f5;font-family:Arial,Helvetica,sans-serif;">
    <div style="max-width:560px;margin:0 auto;padding:32px 16px;">
      <div style="background-color:#ffffff;border-radius:12px;padding:32px;">
        <h1 style="margin:0 0 16px;font-size:22px;color:#18181b;">Olá {safe_name},</h1>
        <p style="margin:0 0 24px;font-size:16px;line-height:1.6;color:#3f3f46;">
          Obrigado por criares uma conta. Confirma o teu email para sabermos que te pertence.
        </p>
        <a href="{safe_url}" style="display:inline-block;padding:12px 24px;border-radius:8px;
           background-color:#18181b;color:#ffffff;text-decoration:none;font-size:16px;">
          Confirmar email
        </a>
        <p style="margin:24px 0 0;font-size:14px;line-height:1.6;color:#71717a;">
          Se o botão não funcionar, abre este link no browser:<br />
          <a href="{safe_url}" style="color:#71717a;word-break:break-all;">{safe_url}</a>
        </p>
      </div>
    </div>
  </body>
</html>
"""


def build_password_reset_email_html(first_name: str, reset_url: str) -> str:
    safe_name = escape(first_name)
    safe_url = escape(reset_url, quote=True)
    return f"""\
<html>
  <body style="margin:0;padding:0;background-color:#f4f4f5;font-family:Arial,Helvetica,sans-serif;">
    <div style="max-width:560px;margin:0 auto;padding:32px 16px;">
      <div style="background-color:#ffffff;border-radius:12px;padding:32px;">
        <h1 style="margin:0 0 16px;font-size:22px;color:#18181b;">Olá {safe_name},</h1>
        <p style="margin:0 0 24px;font-size:16px;line-height:1.6;color:#3f3f46;">
          Recebemos um pedido para repor a tua password. Clica no botão abaixo para escolher uma nova.
        </p>
        <a href="{safe_url}" style="display:inline-block;padding:12px 24px;border-radius:8px;
           background-color:#18181b;color:#ffffff;text-decoration:none;font-size:16px;">
          Repor Password
        </a>
        <p style="margin:24px 0 0;font-size:14px;line-height:1.6;color:#71717a;">
          Se não fizeste este pedido, podes ignorar este email com segurança.<br /><br />
          Ou copia este link para o browser:<br />
          <a href="{safe_url}" style="color:#71717a;word-break:break-all;">{safe_url}</a>
        </p>
      </div>
    </div>
  </body>
</html>
"""


def build_password_changed_email_html(first_name: str) -> str:
    safe_name = escape(first_name)
    return f"""\
<html>
  <body style="margin:0;padding:0;background-color:#f4f4f5;font-family:Arial,Helvetica,sans-serif;">
    <div style="max-width:560px;margin:0 auto;padding:32px 16px;">
      <div style="background-color:#ffffff;border-radius:12px;padding:32px;">
        <h1 style="margin:0 0 16px;font-size:22px;color:#18181b;">Olá {safe_name},</h1>
        <p style="margin:0 0 16px;font-size:16px;line-height:1.6;color:#3f3f46;">
          A password da tua conta foi alterada.
        </p>
        <p style="margin:0;font-size:14px;line-height:1.6;color:#71717a;">
          Se foste tu, não precisas de fazer nada. Se não foste tu, usa a opção de recuperar a password no site para escolheres uma nova e fala connosco.
        </p>
      </div>
    </div>
  </body>
</html>
"""


def render_template(template: str, values: dict[str, str], *, html: bool = True) -> str:
    """Fill the ``[MARKER]`` placeholders of a designed email in a single pass.

    HTML values are escaped. A marker without a value, or a value without a
    marker, raises: a renamed field must never reach a customer as ``[TICKET_URL]``.
    The values are not scanned again, so a name written as ``[X]`` stays as typed.
    """
    found = set(MARKER_PATTERN.findall(template))
    if found != set(values):
        raise ValueError(
            "template markers and values differ: "
            f"{sorted(found.symmetric_difference(values))}"
        )

    def fill(match: re.Match[str]) -> str:
        value = values[match.group(1)]
        return escape(value, quote=True) if html else value

    return MARKER_PATTERN.sub(fill, template)


def ticket_url() -> str:
    """The page of the account where the ticket shows, with or without a final /."""
    return f"{config.settings.FRONTEND_URL.rstrip('/')}{TICKET_PATH}"


def build_ticket_email(
    attendee_name: str, tier_name: str, reference: str
) -> tuple[str, str]:
    """The ticket email as ``(html, plain text)``, with the same data in both."""
    parts = attendee_name.split()
    values = {
        "FIRST_NAME": parts[0] if parts else attendee_name,
        "ATTENDEE_NAME": attendee_name,
        "TICKET_TYPE": tier_name,
        "TICKET_REFERENCE": reference,
        "EVENT_DATES": EVENT_DATES,
        "EVENT_LOCATION": EVENT_LOCATION,
        "TICKET_URL": ticket_url(),
    }
    html = render_template(_TICKET_HTML.read_text(encoding="utf-8"), values)
    text = render_template(_TICKET_TEXT.read_text(encoding="utf-8"), values, html=False)
    return html, text
