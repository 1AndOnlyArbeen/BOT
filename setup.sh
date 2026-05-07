#!/usr/bin/env bash
# Ultron MAX setup — system + Python + models + all extras
set -e

cd "$(dirname "$0")"

echo "==> System packages"
sudo apt update
sudo apt install -y \
    ffmpeg portaudio19-dev espeak \
    python3-venv python3-pip \
    xdotool ydotool wmctrl xclip wl-clipboard \
    gnome-screenshot scrot grim \
    libnotify-bin playerctl pulseaudio-utils \
    tesseract-ocr \
    brightnessctl \
    fd-find ripgrep \
    network-manager iputils-ping \
    pandoc \
    git \
    piper \
    jq

echo "==> Python venv + deps"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install langchain-chroma==0.1.4

echo "==> Playwright browser"
python -m playwright install chromium

echo "==> Ollama models"
if ! command -v ollama >/dev/null; then
    echo "Installing Ollama..."
    curl -fsSL https://ollama.com/install.sh | sh
fi
ollama pull deepseek-r1:1.5b
ollama pull nomic-embed-text

echo "==> Frontend dependencies"
if command -v npm >/dev/null; then
    (cd frontend && npm install)
else
    echo "[warn] npm not installed — install Node.js then run: cd frontend && npm install"
fi

echo
echo "✅ Ultron v3 is ready."
echo "   ./run.sh           # backend + frontend"
echo "   Open: http://localhost:5173"
echo
echo "   Or legacy Streamlit: streamlit run app.py  →  http://localhost:8501"
echo
echo "Optional upgrades when you have RAM:"
echo "   ollama pull qwen2.5:7b-instruct       # better tool use"
echo "   ollama pull qwen2.5-coder:7b          # best for coder mode"
echo "   ollama pull moondream                  # vision model (image understanding)"
echo
echo "Run as a system service (auto-start at login):"
echo "   ./deployment/install_service.sh"
