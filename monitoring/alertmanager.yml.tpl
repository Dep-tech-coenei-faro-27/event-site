global:
  smtp_smarthost: ${SMTP_HOST}:587
  smtp_from: ${EMAIL_SENDER}
  smtp_auth_username: ${SMTP_USER}
  smtp_auth_password: ${SMTP_PASSWORD}
  smtp_require_tls: true

route:
  receiver: team
  group_wait: 30s
  repeat_interval: 6h

receivers:
  - name: team
    discord_configs:
      - webhook_url_file: ${ALERT_DISCORD_WEBHOOK}
    email_configs:
      - to: ${ALERT_EMAIL_TO}
        send_resolved: true