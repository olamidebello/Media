#!/usr/bin/env bash
set -euo pipefail
if [[ ${EUID} -ne 0 ]]; then
  echo 'Run as root: sudo bash scripts/deploy-tv-install.sh [PACKAGE_DIRECTORY]' >&2
  exit 1
fi
package_directory=${1:-}
if [[ -n "$package_directory" && ! -d "$package_directory" ]]; then
  echo 'Package directory must already exist on this server.' >&2
  exit 1
fi
apt-get update
apt-get install -y ansible git python3
arguments=()
if [[ -n "$package_directory" ]]; then
  package_directory=$(realpath -- "$package_directory")
  arguments+=(-e "$(python3 -c 'import json,sys; print(json.dumps({"media_package_dir":sys.argv[1]}))' "$package_directory")")
fi
ansible-pull -U https://github.com/olamidebello/Media.git -C main \
  -d /opt/africa-media-tv-bootstrap -i localhost, -c local \
  ansible/deploy-tv-install.yml "${arguments[@]}"
