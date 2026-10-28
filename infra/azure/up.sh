#!/usr/bin/env bash
# Creates a benchmark VM on Azure: Ubuntu 24.04 with Docker, reachable over SSH only from this machine's
# public IP. Everything goes in one resource group, so `az group delete -n <group>` removes all of it.
# Usage: infra/azure/up.sh <vm-name> [size]
#   AZ_SUBSCRIPTION, AZ_RG (default loginstorm), AZ_LOCATION (default centralindia),
#   SSH_KEY (default ~/.ssh/loginstorm_ed25519, created if missing)
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
NAME="${1:?vm name}"; SIZE="${2:-Standard_D8as_v5}"
RG="${AZ_RG:-loginstorm}"; LOC="${AZ_LOCATION:-centralindia}"
KEY="${SSH_KEY:-$HOME/.ssh/loginstorm_ed25519}"
SUB=(); [ -z "${AZ_SUBSCRIPTION:-}" ] || SUB=(--subscription "$AZ_SUBSCRIPTION")

[ -f "$KEY" ] || ssh-keygen -q -t ed25519 -N '' -C loginstorm -f "$KEY"
MY_IP="$(curl -fsS https://api.ipify.org)"
az group create "${SUB[@]}" -n "$RG" -l "$LOC" -o none
az network nsg create "${SUB[@]}" -g "$RG" -n "$NAME-nsg" -o none
az network nsg rule create "${SUB[@]}" -g "$RG" --nsg-name "$NAME-nsg" -n ssh-from-me --priority 100 \
  --source-address-prefixes "$MY_IP/32" --destination-port-ranges 22 --protocol Tcp --access Allow -o none
az vm create "${SUB[@]}" -g "$RG" -n "$NAME" --image Ubuntu2404 --size "$SIZE" \
  --admin-username bench --ssh-key-values "$KEY.pub" --nsg "$NAME-nsg" --public-ip-sku Standard \
  --os-disk-size-gb 128 --storage-sku StandardSSD_LRS --custom-data cloud-init.yaml -o none
IP="$(az vm show "${SUB[@]}" -d -g "$RG" -n "$NAME" --query publicIps -o tsv)"
echo "$NAME is up: ssh -i $KEY bench@$IP   (cloud-init needs a minute or two to install Docker)"
