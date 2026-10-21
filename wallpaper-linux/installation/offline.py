"""Preparação do pacote offline antes de chamar o instalador principal."""
import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from desktop_support import detect_desktop, steam_root, wallpaper_app
from install_progress import Progress
from .options import add_install_arguments
from .requirements import check_host_requirements
from .dependencies import install_dependencies
from .runtime import AMBIENTE_EXECUCAO, IMAGEM, import_runtime_image, install_runtime

DESTINO = Path.home() / '.local/share/wallpaper-engine/package'


def check_package(raiz, argumentos_cli):
    if os.geteuid() == 0:
        raise SystemExit('Execute com seu usuário normal, sem sudo.')
    manifesto = json.loads((raiz / 'manifest.json').read_text())
    if platform.machine() != manifesto['machine']:
        raise SystemExit(f"Pacote para {manifesto['machine']}; computador atual: {platform.machine()}")
    ambiente_grafico = detect_desktop(argumentos_cli.ambiente_grafico)
    steam = steam_root(argumentos_cli.raiz_steam)
    wallpaper_app(steam)
    if argumentos_cli.instalar_dependencias and not argumentos_cli.verificar:
        install_dependencies(ambiente_grafico, True, argumentos_cli.fundo_login)
    check_host_requirements(ambiente_grafico, True, raiz / 'app/wallpaper-linux/extension', argumentos_cli.plugin_kde)
    subprocess.run(['podman', 'info', '--format', '{{.Host.Arch}}'], check=True, stdout=subprocess.DEVNULL)
    print(f'Pacote verificado: {ambiente_grafico}, {manifesto["machine"]}, Steam em {steam}', flush=True)
    return steam


def install_package_files(raiz):
    DESTINO.mkdir(parents=True, exist_ok=True)
    shutil.copytree(raiz / 'app', DESTINO, dirs_exist_ok=True)


def run_integration_installer(argumentos_cli, steam):
    comando = [sys.executable, str(DESTINO / 'wallpaper-linux/install.py'),
               '--desktop', argumentos_cli.ambiente_grafico, '--steam-root', str(steam),
               '--color', argumentos_cli.cor, '--startup', argumentos_cli.inicio_automatico]
    if argumentos_cli.fundo_login:
        comando.append('--login-background')
    if argumentos_cli.plugin_kde:
        comando.append('--kde-plugin')
    subprocess.run(comando, check=True, env=dict(os.environ, WE_PROGRESS_START='70'))


def main(raiz):
    analisador = argparse.ArgumentParser(description='Instalador offline Wallpaper Engine Linux')
    add_install_arguments(analisador, pacote_offline=True)
    argumentos_cli = analisador.parse_args()
    progresso = Progress(argumentos_cli.cor)
    try:
        progresso.update(20, 'Verificando ambiente e dependências do sistema…')
        steam = check_package(raiz, argumentos_cli)
        if argumentos_cli.verificar:
            progresso.update(100, 'Verificação concluída. Nenhuma instalação realizada.')
            return
        progresso.update(30, 'Preparando imagem de dependências…')
        import_runtime_image(raiz / 'runtime-image.tar', IMAGEM)
        progresso.update(45, 'Instalando renderizador compilado…')
        install_runtime(raiz / 'runtime', AMBIENTE_EXECUCAO)
        progresso.update(60, 'Instalando scripts, extensão e documentação…')
        install_package_files(raiz)
        run_integration_installer(argumentos_cli, steam)
    except (OSError, ValueError, subprocess.CalledProcessError) as erro:
        progresso.error(str(erro))
        raise SystemExit(1)
    print('O aplicativo Wallpaper Engine Linux está no menu. Reabra o Wallpaper Engine da Steam.', flush=True)
