Codex CLI Tooling Integration

Goal
- Make modern CLI tools available to Codex CLI sessions and normalize cross‑distro names so the agent prefers them (fd, rg, sg, jq, yq, fzf, bat, eza, zoxide, httpie, delta, difftastic, tree).

What we provide in this repo
- `bin/fd`: shim that falls back to `fdfind` on Debian/Ubuntu.
- `bin/bat`: shim that falls back to `batcat` on Debian/Ubuntu.
- `scripts/codex_tools_doctor.sh`: checks tool availability and prints OS‑specific install suggestions.

Quick start
- Add project shims to PATH, then run the doctor:

```
export PATH="$(pwd)/bin:$PATH"
bash scripts/codex_tools_doctor.sh
```

- Launch Codex CLI from the project root so it inherits PATH and prefers these tools:

```
codex -C "$(pwd)" -c 'shell_environment_policy.inherit=["PATH"]'
```

Why PATH matters
- Codex CLI runs shell commands in your environment. Prepending `./bin` ensures consistent names across distros (e.g., `fd` and `bat` exist even when only `fdfind`/`batcat` is installed). This avoids fragile conditionals inside prompts or AGENTS.md and lets the agent just call `fd`, `bat`, etc.

Recommended installs (manual)
- macOS (Homebrew):
  - `brew install fd ripgrep jq yq fzf bat eza zoxide httpie git-delta difftastic tree`
  - `npm install -g @ast-grep/cli` (provides `sg`)

- Ubuntu/Debian (APT):
  - `sudo apt update`
  - `sudo apt install fd-find ripgrep jq yq fzf bat eza zoxide httpie git-delta difftastic tree`
  - `sudo ln -s $(command -v fdfind) /usr/local/bin/fd` (or use `bin/fd` shim)
  - `sudo update-alternatives --set bat $(command -v batcat)` (or use `bin/bat` shim)
  - `npm install -g @ast-grep/cli`

- Arch (pacman):
  - `sudo pacman -S fd ripgrep jq yq fzf bat eza zoxide httpie git-delta difftastic tree`
  - `npm install -g @ast-grep/cli`

- Fedora (dnf):
  - `sudo dnf install fd-find ripgrep jq yq fzf bat eza zoxide httpie git-delta difftastic tree`
  - `npm install -g @ast-grep/cli`

Using with our MCP server
- If you are using the included MCP server (`spice_mcp_beta`), combine the PATH inheritance with Dune API key inheritance:

```
export PATH="$(pwd)/bin:$PATH"
export DUNE_API_KEY=YOUR_KEY
codex -C "$(pwd)" \
  -c 'mcp_servers=["spice_mcp_beta"]' \
  -c 'shell_environment_policy.inherit=["PATH","DUNE_API_KEY"]'
```

Notes
- Codex CLI will automatically prefer `rg` over `grep` and `fd` over `find` when available; the shims ensure these names are present on all distros.
- `sg` (ast‑grep) comes from npm (`@ast-grep/cli`); ensure your global npm bin dir is on PATH (e.g., `~/.npm-global/bin` or `~/.nvm/versions/node/*/bin`).
- Consider setting `PATH` in your shell profile for permanence if you always want the shims available in this project.

