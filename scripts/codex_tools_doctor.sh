#!/usr/bin/env bash
# Check presence of recommended CLI tools and suggest installs per OS.
set -euo pipefail

detect_os() {
  case "${OSTYPE:-}" in
    darwin*) echo "macos" ;;
    linux*)  
      if [ -f /etc/os-release ]; then
        . /etc/os-release
        case "${ID:-}" in
          ubuntu|debian) echo "debian" ;;
          arch)          echo "arch" ;;
          fedora)        echo "fedora" ;;
          *)             echo "linux" ;;
        esac
      else
        echo "linux"
      fi
      ;;
    *) echo "unknown" ;;
  esac
}

have() { command -v "$1" >/dev/null 2>&1; }

os=$(detect_os)
ok=0

say_install() {
  local tool=$1
  case "$os" in
    macos)
      echo "  brew install $tool" ;;
    debian)
      case "$tool" in
        fd) echo "  sudo apt install fd-find && sudo ln -s \$(command -v fdfind) /usr/local/bin/fd" ;;
        bat) echo "  sudo apt install bat && sudo update-alternatives --set bat \$(command -v batcat) || echo 'Use batcat'" ;;
        ripgrep) echo "  sudo apt install ripgrep" ;;
        fzf) echo "  sudo apt install fzf" ;;
        jq) echo "  sudo apt install jq" ;;
        yq) echo "  sudo apt install yq" ;;
        eza) echo "  sudo apt install eza" ;;
        zoxide) echo "  sudo apt install zoxide" ;;
        httpie) echo "  sudo apt install httpie" ;;
        git-delta) echo "  sudo apt install git-delta" ;;
        difftastic) echo "  sudo apt install difftastic" ;;
        *) echo "  sudo apt install $tool" ;;
      esac
      ;;
    arch)
      echo "  sudo pacman -S $tool" ;;
    fedora)
      echo "  sudo dnf install $tool" ;;
    *)
      echo "  Install $tool via your package manager." ;;
  esac
}

check() {
  local name=$1
  local alt=${2:-}
  if have "$name"; then
    printf "[ok] %-12s %s\n" "$name" "$(command -v "$name")"
    return
  fi
  if [ -n "$alt" ] && have "$alt"; then
    printf "[ok] %-12s %s (alt: %s)\n" "$name" "$alt" "$(command -v "$alt")"
    return
  fi
  printf "[missing] %-12s\n" "$name"
  say_install "$name"
  ok=1
}

echo "Detecting tools (OS: $os)"
check fd fdfind
check ripgrep
check sg
check jq
check yq
check fzf
check bat batcat
check eza
check zoxide
check http
check delta
check difftastic
check tree

if ! have sg; then
  echo "\nTo install ast-grep (sg) via npm:"
  echo "  npm install -g @ast-grep/cli"
fi

echo "\nAdd local bin to PATH (for wrappers) before launching Codex:"
echo "  export PATH=\"$(pwd)/bin:\$PATH\""

if [ "$ok" -eq 0 ]; then
  echo "\nAll set or minor aliases found."
else
  echo "\nSome tools are missing. Install suggestions are shown above."
fi

