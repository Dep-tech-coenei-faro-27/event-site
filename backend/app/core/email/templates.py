# ruff: noqa: E501
from html import escape

VERIFICATION_EMAIL_SUBJECT = "Confirma o teu email"
PASSWORD_RESET_SUBJECT = "Recuperação de Password"
PASSWORD_CHANGED_SUBJECT = "A tua password foi alterada"


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
