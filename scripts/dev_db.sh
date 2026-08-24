#!/usr/bin/env bash
# Local PostgreSQL dev container helper (podman — no docker on this machine).
#
# Usage: scripts/dev_db.sh {start|stop|reset|status}

set -euo pipefail

CONTAINER_NAME="ohmy-pg"
VOLUME_NAME="ohmy-pg-data"
IMAGE="postgres:16-alpine"
HOST_PORT="5433"
DB_USER="ohmy"
DB_PASSWORD="ohmy"
DB_NAME="ohmyenglish"

usage() {
  echo "Usage: $0 {start|stop|reset|status}" >&2
  exit 1
}

start() {
  if podman container exists "$CONTAINER_NAME"; then
    echo "Container ${CONTAINER_NAME} already exists — starting it."
    podman start "$CONTAINER_NAME"
    return
  fi
  podman volume create "$VOLUME_NAME" >/dev/null
  podman run -d \
    --name "$CONTAINER_NAME" \
    -p "${HOST_PORT}:5432" \
    -e POSTGRES_USER="$DB_USER" \
    -e POSTGRES_PASSWORD="$DB_PASSWORD" \
    -e POSTGRES_DB="$DB_NAME" \
    -v "${VOLUME_NAME}:/var/lib/postgresql/data" \
    "$IMAGE"
  echo "Started ${CONTAINER_NAME} on port ${HOST_PORT}."
}

stop() {
  podman stop "$CONTAINER_NAME" 2>/dev/null || echo "Container ${CONTAINER_NAME} is not running."
}

reset() {
  echo "Dropping ${CONTAINER_NAME} and its data volume..."
  podman rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
  podman volume rm -f "$VOLUME_NAME" >/dev/null 2>&1 || true
  start
}

status() {
  podman ps -a --filter "name=${CONTAINER_NAME}"
}

case "${1:-}" in
  start) start ;;
  stop) stop ;;
  reset) reset ;;
  status) status ;;
  *) usage ;;
esac
