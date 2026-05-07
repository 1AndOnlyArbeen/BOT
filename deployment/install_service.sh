#!/usr/bin/env bash
# Install Ultron as a user systemd service (autostart at login).
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="$HOME/.config/systemd/user"
mkdir -p "$TARGET"

# Substitute $HOME (sed-friendly path), then install.
sed "s|%h|$HOME|g" "$SCRIPT_DIR/ultron.service" > "$TARGET/ultron.service"

systemctl --user daemon-reload
systemctl --user enable ultron.service
systemctl --user start ultron.service

echo "✓ Ultron installed as user service. Status:"
systemctl --user status ultron.service --no-pager || true
echo
echo "Manage with:"
echo "  systemctl --user start|stop|restart|status ultron"
echo "  journalctl --user -u ultron -f      # follow logs"
