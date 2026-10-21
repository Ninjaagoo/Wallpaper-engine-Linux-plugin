#!/usr/bin/python3
"""Geração do instalador executável com fontes, renderizador e dependências."""
import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

PROJETO = Path(__file__).resolve().parents[1]
AMBIENTE_EXECUCAO = Path.home() / '.local/share/wallpaper-engine/runtime'
IMAGEM = 'localhost/wallpaper-engine-runtime:fedora44'
NOME_ARQUIVO = 'WallpaperEngine-Linux-x86_64.run'
CABECALHO = r'''#!/bin/bash
set -eu
CAMINHO_INSTALADOR="$(readlink -f -- "$0")"
case "${1:-}" in
  --help|-h)
    printf '%s\n' 'Wallpaper Engine Linux — instalador offline x86_64' 'Uso: ./WallpaperEngine-Linux-x86_64.run [--check] [--desktop auto|gnome|kde|xfce] [--steam-root CAMINHO] [--kde-plugin] [--startup yes|no|ask] [--login-background] [--color auto|always|never] [--install-deps]' '--verify: verificar integridade do pacote sem instalar.' 'Requisitos: Steam + Wallpaper Engine, Python 3/Pillow, Podman e Node.js; PyGObject no GNOME.'
    exit 0 ;;
esac
if [ ! -t 1 ] && [ -z "${WE_INSTALLER_TERMINAL:-}" ] && [ "${1:-}" != '--check' ] && [ "${1:-}" != '--verify' ]; then
  export WE_INSTALLER_TERMINAL=1
  manter_aberto='"$@"; resultado=$?; printf "\nPressione Enter para fechar…"; read -r resposta; exit "$resultado"'
  if command -v ptyxis >/dev/null 2>&1; then exec ptyxis -- bash -c "$manter_aberto" installer "$CAMINHO_INSTALADOR" "$@"; fi
  if command -v gnome-terminal >/dev/null 2>&1; then exec gnome-terminal --wait -- bash -c "$manter_aberto" installer "$CAMINHO_INSTALADOR" "$@"; fi
  if command -v konsole >/dev/null 2>&1; then exec konsole --noclose -e "$CAMINHO_INSTALADOR" "$@"; fi
  if command -v x-terminal-emulator >/dev/null 2>&1; then exec x-terminal-emulator -e bash -c "$manter_aberto" installer "$CAMINHO_INSTALADOR" "$@"; fi
  if command -v xterm >/dev/null 2>&1; then exec xterm -hold -e "$CAMINHO_INSTALADOR" "$@"; fi
fi
for comando in python3 tar sha256sum tail awk mktemp; do
  command -v "$comando" >/dev/null 2>&1 || { printf 'Dependência ausente: %s\n' "$comando" >&2; exit 1; }
done
mostrar_progresso() {
  local cor='' restaurar_cor=''
  if [ -t 1 ] && [ -z "${NO_COLOR+x}" ] && [ "${TERM:-}" != dumb ]; then
    cor=$'\033[31m'; restaurar_cor=$'\033[0m'
  fi
  printf '%s[%3d%%]%s %s\n' "$cor" "$1" "$restaurar_cor" "$2"
}
LINHA_CONTEUDO=$(awk '/^__WALLPAPER_ENGINE_PAYLOAD__$/ { print NR+1; exit }' "$CAMINHO_INSTALADOR")
mostrar_progresso 0 'Verificando integridade do instalador…'
SOMA_ATUAL=$(tail -n +"$LINHA_CONTEUDO" "$CAMINHO_INSTALADOR" | sha256sum)
SOMA_ATUAL=${SOMA_ATUAL%% *}
[ "$SOMA_ATUAL" = '__PAYLOAD_SHA256__' ] || { printf '%s\n' 'Pacote incompleto ou corrompido.' >&2; exit 1; }
if [ "${1:-}" = '--verify' ]; then printf '%s\n' 'Integridade confirmada.'; exit 0; fi
DIRETORIO_CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/wallpaper-engine/installers"
mkdir -p "$DIRETORIO_CACHE"
DIRETORIO_TEMPORARIO=$(mktemp -d "$DIRETORIO_CACHE/wallpaper-engine-installer.XXXXXXXX")
trap 'rm -rf -- "$DIRETORIO_TEMPORARIO"' EXIT HUP INT TERM
mostrar_progresso 10 'Extraindo pacote; são necessários vários GB livres…'
tail -n +"$LINHA_CONTEUDO" "$CAMINHO_INSTALADOR" | tar -xzf - -C "$DIRETORIO_TEMPORARIO"
EXECUTAVEL_PYTHON=$(command -v python3)
if [ -x /usr/bin/python3 ]; then EXECUTAVEL_PYTHON=/usr/bin/python3; fi
"$EXECUTAVEL_PYTHON" "$DIRETORIO_TEMPORARIO/package-bootstrap.py" "$@"
exit 0
__WALLPAPER_ENGINE_PAYLOAD__
'''


def excluded(informacoes):
    partes = Path(informacoes.name).parts
    if any(parte in ('__pycache__', '.vscode', 'build', '.cache', 'backups', '.git') for parte in partes):
        return None
    if informacoes.name.endswith(('static-background-before.json', 'system-colors-before.json')):
        return None
    return informacoes


def export_runtime_image(destino):
    print('Exportando imagem de dependências…', flush=True)
    subprocess.run(['podman', 'save', '--format', 'oci-archive', '--output', str(destino), IMAGEM], check=True)


def create_payload(conteudo, imagem, trabalho, ambiente_execucao=AMBIENTE_EXECUCAO):
    manifesto = trabalho / 'manifest.json'
    manifesto.write_text(json.dumps({'machine': platform.machine(), 'image': IMAGEM, 'format': 1}, indent=2))
    print('Compactando runtime, fontes e dependências…', flush=True)
    with tarfile.open(conteudo, 'w:gz', compresslevel=3) as arquivo_compactado:
        arquivo_compactado.add(PROJETO / 'wallpaper-linux', arcname='app/wallpaper-linux', filter=excluded)
        arquivo_compactado.add(PROJETO / 'linux-wallpaperengine', arcname='app/linux-wallpaperengine', filter=excluded)
        for nome in ('README.md', 'Containerfile', 'tools', 'patches', 'docs', '.gitmodules', 'install.sh'):
            arquivo_compactado.add(PROJETO / nome, arcname='app/' + nome, filter=excluded)
        arquivo_compactado.add(PROJETO / 'tools/package-bootstrap.py', arcname='package-bootstrap.py')
        arquivo_compactado.add(ambiente_execucao, arcname='runtime')
        arquivo_compactado.add(imagem, arcname='runtime-image.tar')
        arquivo_compactado.add(manifesto, arcname='manifest.json')
        licenca_cef = Path.home() / '.cache/wallpaper-engine/intellisense/cef/LICENSE.txt'
        if licenca_cef.exists():
            arquivo_compactado.add(licenca_cef, arcname='LICENSES/CEF-LICENSE.txt')


def write_executable(conteudo, destino):
    with conteudo.open('rb') as origem:
        soma_verificacao = hashlib.file_digest(origem, 'sha256').hexdigest()
    temporario = destino.with_suffix(destino.suffix + '.new')
    try:
        with temporario.open('wb') as saida, conteudo.open('rb') as origem:
            saida.write(CABECALHO.replace('__PAYLOAD_SHA256__', soma_verificacao).encode())
            shutil.copyfileobj(origem, saida, length=4 * 1024 * 1024)
        temporario.chmod(0o755)
        temporario.replace(destino)
    finally:
        temporario.unlink(missing_ok=True)


def write_checksum(destino):
    with destino.open('rb') as origem:
        soma_verificacao = hashlib.file_digest(origem, 'sha256').hexdigest()
    destino.with_suffix('.run.sha256').write_text(f'{soma_verificacao}  {destino.name}\n')


def main():
    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument('--output', dest='saida', type=Path, default=PROJETO / 'dist' / NOME_ARQUIVO)
    analisador.add_argument('--runtime', dest='ambiente_execucao', type=Path, default=AMBIENTE_EXECUCAO, help='Runtime preparado para empacotar sem alterar a instalação em uso')
    argumentos_cli = analisador.parse_args()
    if not (argumentos_cli.ambiente_execucao / 'linux-wallpaperengine').is_file():
        analisador.error('Compile e instale o runtime antes de gerar o pacote offline.')
    if platform.machine() != 'x86_64':
        analisador.error('Este gerador está configurado para a distribuição x86_64.')
    argumentos_cli.saida.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.wallpaper-release-', dir=argumentos_cli.saida.parent) as temporario:
        trabalho = Path(temporario)
        imagem = trabalho / 'runtime-image.tar'
        conteudo = trabalho / 'payload.tar.gz'
        export_runtime_image(imagem)
        create_payload(conteudo, imagem, trabalho, argumentos_cli.ambiente_execucao)
        write_executable(conteudo, argumentos_cli.saida)
    write_checksum(argumentos_cli.saida)
    print(f'Pacote criado: {argumentos_cli.saida} ({argumentos_cli.saida.stat().st_size / 1024**3:.2f} GiB)', flush=True)


if __name__ == '__main__':
    main()
