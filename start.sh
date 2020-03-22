#!/usr/bin/env bash
set -e

if [[ $* == *--update* ]]; then
  echo "[APP] Updating git repository"
  git pull
  echo "[APP] Pulling new docker images"
  docker-compose pull
  echo "[APP] Restarting core services"
  docker-compose up -d
  echo "[APP] Removing old images"
  docker image prune -f -a
fi

if [[ $# -eq 0 ]]; then
  echo "[APP] No arguments given"
  exit 1
fi
