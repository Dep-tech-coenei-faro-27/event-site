global:
  smtp_smarthost: ${SMTP_HOST}:${ALERT_SMTP_PORT}
  smtp_from: ${EMAIL_SENDER}
  smtp_auth_username: ${SMTP_USER}
  smtp_auth_password_file: /etc/alertmanager/smtp_password
  smtp_require_tls: ${ALERT_SMTP_REQUIRE_TLS}

route:
  receiver: team
  group_wait: 30s
  repeat_interval: 6h

receivers:
  - name: team
    discord_configs:
      - webhook_url_file: /etc/alertmanager/discord_webhook
    email_configs:
      - to: ${ALERT_EMAIL_TO}
        send_resolved: true