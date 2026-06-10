"""Agente asíncrono de notificaciones — Email (Gmail SMTP) + WhatsApp hook."""
import os
import logging
from email.message import EmailMessage

log = logging.getLogger("notifier")

_OTP_HTML = """\
<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;font-family:'Segoe UI',Arial,sans-serif;background:#f8fafc;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;padding:40px 0;">
    <tr><td align="center">
      <table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:16px;overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,.08);">
        <!-- Header -->
        <tr>
          <td style="background:#0f172a;padding:28px 40px;">
            <p style="margin:0;font-size:20px;font-weight:700;color:#fff;letter-spacing:-.3px;">
              CO.DE <span style="color:#e11d48;">Aerospace</span>
            </p>
            <p style="margin:4px 0 0;font-size:12px;color:#94a3b8;">Job Hunter Platform</p>
          </td>
        </tr>
        <!-- Body -->
        <tr>
          <td style="padding:36px 40px 28px;">
            <p style="margin:0 0 8px;font-size:22px;font-weight:700;color:#0f172a;">Verifica tu cuenta</p>
            <p style="margin:0 0 28px;font-size:14px;color:#64748b;line-height:1.6;">
              Gracias por registrarte en <strong>Job Hunter</strong>. Usa el siguiente código de seguridad
              de un solo uso para activar tu cuenta:
            </p>
            <!-- OTP Box -->
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td align="center" style="padding:24px;background:#f1f5f9;border-radius:12px;border:1px solid #e2e8f0;">
                  <p style="margin:0 0 6px;font-size:11px;font-weight:600;letter-spacing:2px;color:#94a3b8;text-transform:uppercase;">
                    Código de verificación
                  </p>
                  <p style="margin:0;font-size:40px;font-weight:800;letter-spacing:10px;color:#0f172a;font-family:monospace;">
                    {code}
                  </p>
                  <p style="margin:12px 0 0;font-size:12px;color:#94a3b8;">Expira en 15 minutos</p>
                </td>
              </tr>
            </table>
            <p style="margin:28px 0 0;font-size:13px;color:#94a3b8;line-height:1.6;">
              Si no solicitaste este código, ignora este mensaje. Tu cuenta permanecerá inactiva.
            </p>
          </td>
        </tr>
        <!-- Footer -->
        <tr>
          <td style="padding:20px 40px;border-top:1px solid #f1f5f9;">
            <p style="margin:0;font-size:11px;color:#cbd5e1;">
              © 2026 CO.DE Aerospace · Job Hunter Platform · Mensaje automático, no responder.
            </p>
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>
"""


class NotificationAgent:
    def __init__(self):
        self.smtp_host  = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port  = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user  = os.getenv("SMTP_USER", "")
        self.smtp_pass  = os.getenv("SMTP_PASS", "")
        self.from_addr  = os.getenv("EMAIL_FROM", self.smtp_user)
        self.from_name  = os.getenv("EMAIL_FROM_NAME", "Job Hunter")
        self.wa_number  = os.getenv("WHATSAPP_BOT_NUMBER", "")

    async def send_email_otp(self, to_email: str, code: str) -> bool:
        if not self.smtp_user or not self.smtp_pass:
            log.warning("SMTP no configurado — OTP %s para %s", code, to_email)
            return False
        try:
            import aiosmtplib
            msg = EmailMessage()
            msg["Subject"] = f"Tu código de verificación Job Hunter: {code}"
            msg["From"]    = f"{self.from_name} <{self.from_addr}>"
            msg["To"]      = to_email
            msg.set_content(
                f"Tu código de verificación Job Hunter es: {code}\n"
                f"Ingresa este código en la pantalla de registro para activar tu cuenta.\n"
                f"Expira en 15 minutos.",
                subtype="plain",
            )
            msg.add_alternative(_OTP_HTML.format(code=code), subtype="html")
            await aiosmtplib.send(
                msg,
                hostname=self.smtp_host,
                port=self.smtp_port,
                start_tls=True,
                username=self.smtp_user,
                password=self.smtp_pass,
                timeout=15,
            )
            log.info("OTP email enviado a %s", to_email)
            return True
        except Exception as exc:
            log.error("Error enviando OTP email a %s: %s", to_email, exc)
            return False

    async def trigger_whatsapp_bot(self, to_phone: str, code: str) -> bool:
        """
        Hook para bot de WhatsApp local (Chromium/Baileys).
        Envía petición HTTP al agente local en http://localhost:3001/send.
        Configura WHATSAPP_API_URL en .env para apuntar a tu instancia.
        """
        wa_url = os.getenv("WHATSAPP_API_URL", "http://localhost:3001/send")
        try:
            import aiohttp  # type: ignore
            payload = {
                "phone": to_phone,
                "message": (
                    f"*Job Hunter — Código de verificación*\n\n"
                    f"Tu código es: *{code}*\n"
                    f"Expira en 15 minutos.\n\n"
                    f"_CO.DE Aerospace_"
                ),
            }
            async with aiohttp.ClientSession() as session:
                async with session.post(wa_url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as r:
                    ok = r.status < 300
                    if ok:
                        log.info("WhatsApp OTP encolado para %s", to_phone)
                    return ok
        except Exception as exc:
            log.warning("WhatsApp bot no disponible (%s): %s", to_phone, exc)
            return False
