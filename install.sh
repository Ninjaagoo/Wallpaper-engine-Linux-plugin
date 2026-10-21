#!/usr/bin/env bash
# Baixa a edição correspondente, prepara requisitos e executa como usuário.
set -euo pipefail
REPOSITORIO='Ninjaagoo/Wallpaper-engine-Linux-plugin'
VERSAO='v0.2.2-rc.2'
NOME='WallpaperEngine-Linux-x86_64.run'
CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/wallpaper-engine"
TEMPORARIO=''
PID_AUTENTICACAO=''

limpar() {
    if [ -n "$PID_AUTENTICACAO" ]; then kill "$PID_AUTENTICACAO" 2>/dev/null || true; fi
    if [ -n "$TEMPORARIO" ]; then rm -rf -- "$TEMPORARIO"; fi
}
trap limpar EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

preparar_python() {
    if command -v python3 >/dev/null 2>&1; then return; fi
    command -v sudo >/dev/null 2>&1 || { printf '%s\n' 'Instale Python 3 e sudo antes de continuar.' >&2; exit 1; }
    printf '%s\n' 'Python 3 ausente. Autentique uma vez para preparar o sistema.'
    sudo -v
    export WE_SUDO_AUTHENTICATED=1
    (while sleep 40; do sudo -n -v >/dev/null 2>&1 || exit; done) &
    PID_AUTENTICACAO=$!
    if [ -e /run/ostree-booted ]; then
        sudo -n rpm-ostree install --idempotent -y python3
        printf '%s\n' 'Reinicie o sistema imutável e execute o mesmo comando para concluir.'
        exit 75
    elif command -v apt-get >/dev/null 2>&1; then
        sudo -n apt-get update
        sudo -n apt-get install -y python3
    elif command -v dnf >/dev/null 2>&1; then
        sudo -n dnf install -y python3
    elif command -v pacman >/dev/null 2>&1; then
        sudo -n pacman -S --needed --noconfirm python
    else
        printf '%s\n' 'Gerenciador não suportado: instale Python 3 antes de continuar.' >&2
        exit 1
    fi
}

main() {
    case "${1:-}" in
        --help|-h)
            printf '%s\n' 'Instalação completa do Wallpaper Engine Linux.' 'Uso: bash install.sh [opções do instalador]' 'Instala dependências ausentes, confere o SHA-256 e instala em ~/.local/share/wallpaper-engine.' 'Steam e Wallpaper Engine devem estar instalados. Execute sem sudo.'
            return ;;
    esac
    [ "$(id -u)" -ne 0 ] || { printf '%s\n' 'Execute como usuário normal, sem sudo.' >&2; exit 1; }
    [ "$(uname -s)" = Linux ] && [ "$(uname -m)" = x86_64 ] || { printf '%s\n' 'Este pacote é para Linux x86_64.' >&2; exit 1; }
    if [[ " $* " == *" --check "* ]] && ! command -v python3 >/dev/null 2>&1; then
        printf '%s\n' 'Python 3 ausente; nenhuma dependência será instalada no modo --check.' >&2
        exit 1
    fi
    preparar_python
    for comando in curl tar sha256sum awk mktemp; do
        command -v "$comando" >/dev/null 2>&1 || { printf 'Comando necessário: %s\n' "$comando" >&2; exit 1; }
    done
    mkdir -p "$CACHE"
    TEMPORARIO=$(mktemp -d "$CACHE/download.XXXXXXXX")
    printf '%s\n' 'Baixando instalador e verificação de integridade…'
    curl --fail --location --retry 3 "https://github.com/$REPOSITORIO/releases/download/$VERSAO/$NOME" -o "$TEMPORARIO/$NOME"
    curl --fail --location --retry 3 "https://github.com/$REPOSITORIO/releases/download/$VERSAO/$NOME.sha256" -o "$TEMPORARIO/$NOME.sha256"
    (cd "$TEMPORARIO" && sha256sum -c "$NOME.sha256")
    bash "$TEMPORARIO/$NOME" --install-deps "$@"
}

main "$@"
