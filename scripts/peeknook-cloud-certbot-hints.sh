#!/usr/bin/env bash
# Let's Encrypt hints after nginx + cloud prod on VPS.
cat <<'EOF'
== PeekNook Cloud TLS (certbot) ==

1. Point DNS A record: cloud.example.com → your VPS IP
2. Copy cloud/deploy/nginx.peeknook.conf.example → /etc/nginx/sites-available/peeknook-cloud
3. Start cloud: ./scripts/peeknook-cloud-prod-up.sh (on VPS)
4. Install certbot:
     sudo apt install certbot python3-certbot-nginx
5. Issue cert:
     sudo certbot --nginx -d cloud.example.com
6. Desktop Settings → Cloud URL: https://cloud.example.com

Renewal: certbot renew (cron usually installed by certbot package)
EOF
