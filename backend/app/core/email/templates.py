# ruff: noqa: E501
from html import escape

VERIFICATION_EMAIL_SUBJECT = "Confirm your email"


def build_verification_email_html(first_name: str, verify_url: str) -> str:
    safe_name = escape(first_name)
    safe_url = escape(verify_url, quote=True)
    return f"""\
<html>
  <body style="margin:0;padding:0;background-color:#f4f4f5;font-family:Arial,Helvetica,sans-serif;">
    <div style="max-width:560px;margin:0 auto;padding:32px 16px;">
      <div style="background-color:#ffffff;border-radius:12px;padding:32px;">
        <h1 style="margin:0 0 16px;font-size:22px;color:#18181b;">Hi {safe_name},</h1>
        <p style="margin:0 0 24px;font-size:16px;line-height:1.6;color:#3f3f46;">
          Thanks for creating an account. Please confirm your email address so we know
          it really belongs to you.
        </p>
        <a href="{safe_url}" style="display:inline-block;padding:12px 24px;border-radius:8px;
           background-color:#18181b;color:#ffffff;text-decoration:none;font-size:16px;">
          Confirm your email
        </a>
        <p style="margin:24px 0 0;font-size:14px;line-height:1.6;color:#71717a;">
          If the button does not work, open this link in your browser:<br />
          <a href="{safe_url}" style="color:#71717a;word-break:break-all;">{safe_url}</a>
        </p>
      </div>
    </div>
  </body>
</html>
"""
