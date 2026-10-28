#!/usr/bin/env bash
set -euo pipefail

echo '== Listening TCP ports =='
sudo ss -ltnp
echo '== Apache virtual-host names and listeners =='
sudo apachectl -S 2>&1 || true
echo '== Docker containers (names, images, ports, networks) =='
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Networks}}'
echo '== Docker networks =='
docker network ls
echo '== Docker volumes =='
docker volume ls
echo '== CPU, memory, disk =='
nproc; free -h; df -h / /var /srv 2>/dev/null || df -h
echo '== Cloudflared installation and service state =='
command -v cloudflared || true
systemctl status cloudflared --no-pager -n 20 2>/dev/null || true
echo '== Candidate deployment directories =='
find /srv /opt -maxdepth 2 -type d -printf '%p\n' 2>/dev/null | sort
