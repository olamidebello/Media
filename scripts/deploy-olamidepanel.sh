#!/usr/bin/env bash
set -euo pipefail
if [[ ${EUID} -ne 0 ]]; then
  echo 'Run as root: sudo bash scripts/deploy-olamidepanel.sh DOMAIN EMAIL' >&2
  exit 1
fi
media_domain=${1:-media.olamidepanel.com}
media_contact=${2:-}
if [[ ! "$media_domain" =~ ^[a-z0-9][a-z0-9.-]+[a-z0-9]$ ]] || [[ ! "$media_contact" =~ ^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$ ]]; then
  echo 'Usage: sudo bash scripts/deploy-olamidepanel.sh media.olamidepanel.com admin@example.com' >&2
  exit 1
fi
apt-get update
apt-get install -y git ansible python3
ansible-pull -U https://github.com/olamidebello/Media.git -C main \
  -d /opt/africa-media-bootstrap -i localhost, -c local \
  ansible/pull-and-deploy.yml \
  -e "media_domain=$media_domain" -e 'media_tls=true' -e "media_email=$media_contact"
echo "Deployment completed: https://$media_domain"
echo 'Set administrator credentials using the interactive command shown by the playbook.'
