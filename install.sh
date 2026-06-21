#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  Octopus — standalone installer
#  Usage: curl -fsSL https://raw.githubusercontent.com/pkill-mydaemons/octopus/main/install.sh | bash
# ─────────────────────────────────────────────────────────────
set -euo pipefail

REPO="https://github.com/pkill-mydaemons/octopus"
INSTALL_DIR="$HOME/.octopus"
CONFIG_DIR="$HOME/.config/octopus"
CYAN='\033[0;36m'
AMBER='\033[0;33m'
GREEN='\033[0;32m'
RED='\033[0;31m'
BOLD='\033[1m'
RESET='\033[0m'

banner() {
  echo ""
  echo -e "${AMBER}${BOLD}"
  echo "   ___      _"
  echo "  / _ \\  __| |_ ___  _ __  _   _ ___"
  echo " | | | |/ _\` __/ _ \\| '_ \\| | | / __|"
  echo " | |_| | (_| || (_) | |_) | |_| \\__ \\"
  echo "  \\___/ \\__,_|\\___/| .__/ \\__,_|___/"
  echo "                   |_|"
  echo -e "${RESET}"
  echo -e "  ${CYAN}8-armed AI personal assistant${RESET}"
  echo ""
}

step() { echo -e "  ${CYAN}→${RESET} $1"; }
ok()   { echo -e "  ${GREEN}✓${RESET} $1"; }
err()  { echo -e "  ${RED}✗${RESET} $1"; exit 1; }
warn() { echo -e "  ${AMBER}⚠${RESET} $1"; }

banner

# ── Check Python ──────────────────────────────────────────────
step "Checking Python (3.11+ required)…"
PYTHON=""
for cmd in python3.13 python3.12 python3.11 python3; do
  if command -v "$cmd" &>/dev/null; then
    ver=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    major=$(echo "$ver" | cut -d. -f1)
    minor=$(echo "$ver" | cut -d. -f2)
    if [ "$major" -ge 3 ] && [ "$minor" -ge 11 ]; then
      PYTHON="$cmd"
      ok "Found $cmd ($ver)"
      break
    fi
  fi
done
[ -z "$PYTHON" ] && err "Python 3.11+ not found. Install it from https://python.org"

# ── Check Git ─────────────────────────────────────────────────
step "Checking git…"
command -v git &>/dev/null || err "git not found. Install it first."
ok "git found"

# ── Clone or update ───────────────────────────────────────────
if [ -d "$INSTALL_DIR/.git" ]; then
  step "Updating existing installation at ${INSTALL_DIR}…"
  git -C "$INSTALL_DIR" pull --quiet
  ok "Updated"
else
  step "Cloning Octopus to ${INSTALL_DIR}…"
  git clone --quiet "$REPO" "$INSTALL_DIR"
  ok "Cloned"
fi

# ── Create virtualenv ─────────────────────────────────────────
VENV="$INSTALL_DIR/.venv"
step "Creating virtual environment…"
"$PYTHON" -m venv "$VENV"
ok "Virtual environment created"

PIP="$VENV/bin/pip"
OCTOPUS_BIN="$VENV/bin/octopus"

# ── Install dependencies ──────────────────────────────────────
step "Installing Octopus and dependencies (this may take a minute)…"
"$PIP" install --quiet --upgrade pip
"$PIP" install --quiet -e "$INSTALL_DIR"
ok "Dependencies installed"

# ── Config directory ──────────────────────────────────────────
step "Setting up config directory at ${CONFIG_DIR}…"
mkdir -p "$CONFIG_DIR/workflows" "$CONFIG_DIR/memory"
if [ ! -f "$CONFIG_DIR/settings.yaml" ]; then
  cp "$INSTALL_DIR/config/settings.yaml" "$CONFIG_DIR/settings.yaml"
  ok "Default config copied to $CONFIG_DIR/settings.yaml"
else
  ok "Config already exists — skipping"
fi
for wf in "$INSTALL_DIR/workflows/"*.yaml; do
  dest="$CONFIG_DIR/workflows/$(basename "$wf")"
  if [ ! -f "$dest" ]; then
    cp "$wf" "$dest"
  fi
done
ok "Workflows available at $CONFIG_DIR/workflows/"

# ── Shell wrapper ─────────────────────────────────────────────
WRAPPER="/usr/local/bin/octopus"
step "Installing octopus command to ${WRAPPER}…"
if [ -w "/usr/local/bin" ] || sudo -n true 2>/dev/null; then
  cat > /tmp/octopus_wrapper << EOF
#!/usr/bin/env bash
exec "$OCTOPUS_BIN" "\$@"
EOF
  if [ -w "/usr/local/bin" ]; then
    mv /tmp/octopus_wrapper "$WRAPPER"
    chmod +x "$WRAPPER"
  else
    sudo mv /tmp/octopus_wrapper "$WRAPPER"
    sudo chmod +x "$WRAPPER"
  fi
  ok "Installed to $WRAPPER"
else
  # Detect shell profile and inject PATH
  if [ -n "${ZSH_VERSION:-}" ] || [ "$(basename "${SHELL:-}")" = "zsh" ]; then
    PROFILE="$HOME/.zshrc"
  elif [ -n "${BASH_VERSION:-}" ] || [ "$(basename "${SHELL:-}")" = "bash" ]; then
    PROFILE="$HOME/.bashrc"
  else
    PROFILE="$HOME/.profile"
  fi
  PATH_LINE="export PATH=\"$VENV/bin:\$PATH\""
  if grep -qF "$VENV/bin" "$PROFILE" 2>/dev/null; then
    ok "PATH already set in $PROFILE"
  else
    printf '\n%s\n' "$PATH_LINE" >> "$PROFILE"
    ok "Added octopus to PATH in $PROFILE — run: source $PROFILE"
  fi
fi

# ── .env template ─────────────────────────────────────────────
ENV_FILE="$CONFIG_DIR/.env"
if [ ! -f "$ENV_FILE" ]; then
  step "Creating .env template at ${ENV_FILE}…"
  cat > "$ENV_FILE" << 'EOF'
# Octopus environment variables
# Uncomment and fill in the keys for the providers you want to use.

# ── LLM Providers (set at least one) ──────────────────────────
# ANTHROPIC_API_KEY=sk-ant-...
# GROQ_API_KEY=gsk_...
# GEMINI_API_KEY=AIza...
# OPENAI_API_KEY=sk-...
# OLLAMA_BASE_URL=http://localhost:11434/v1   # default, no key needed

# ── Email (Gmail OAuth — see README for setup) ─────────────────
# No key needed — OAuth flow runs on first use.

# ── Tasks ─────────────────────────────────────────────────────
# ASANA_TOKEN=...

# ── Web Search (optional) ─────────────────────────────────────
# SEARCH_API_KEY=...   # Brave Search API key
EOF
  ok ".env template created"
fi

# ── Done ──────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}  Octopus installed successfully!${RESET}"
echo ""
echo -e "  ${BOLD}Next steps:${RESET}"
echo ""
echo -e "  1. Edit your config:   ${CYAN}$CONFIG_DIR/settings.yaml${RESET}"
echo -e "  2. Set your API keys:  ${CYAN}$ENV_FILE${RESET}"
echo -e "  3. Launch the UI:      ${CYAN}octopus ui${RESET}"
echo -e "  4. Or use the CLI:     ${CYAN}octopus chat${RESET}"
echo ""
echo -e "  Docs & source: ${CYAN}$REPO${RESET}"
echo ""
