"""Instalação das dependências ausentes com uma autenticação por execução."""
import atexit
import importlib.util
import os
import platform
import shutil
import subprocess
import threading
from pathlib import Path

PACOTES = {
    'apt-get': {'PIL': 'python3-pil', 'gi': 'python3-gi', 'glib': 'libglib2.0-bin', 'Xwayland': 'xwayland', 'dconf': 'dconf-cli'},
    'dnf': {'PIL': 'python3-pillow', 'gi': 'python3-gobject', 'glib': 'glib2', 'Xwayland': 'xorg-x11-server-Xwayland', 'dconf': 'dconf'},
    'pacman': {'PIL': 'python-pillow', 'gi': 'python-gobject', 'glib': 'glib2', 'Xwayland': 'xorg-xwayland', 'dconf': 'dconf'},
}
PARADA_AUTENTICACAO = threading.Event()


def package_manager():
    if Path('/run/ostree-booted').exists():
        if shutil.which('rpm-ostree'):
            return 'rpm-ostree'
        raise SystemExit('Sistema imutável sem rpm-ostree: instale os requisitos pelo gerenciador do sistema.')
    dados = platform.freedesktop_os_release()
    familias = (dados.get('ID', '') + ' ' + dados.get('ID_LIKE', '')).split()
    for familias_aceitas, comando in [(('debian', 'ubuntu'), 'apt-get'), (('fedora', 'rhel', 'centos'), 'dnf'), (('arch', 'manjaro'), 'pacman')]:
        if any(familia in familias for familia in familias_aceitas) and shutil.which(comando):
            return comando
    raise SystemExit('Instalação automática de dependências disponível para Debian/Ubuntu, Fedora, Arch e rpm-ostree. Consulte os requisitos no README.')


def missing_packages(ambiente_grafico, precisa_conteiner, gerenciador, fundo_login=False):
    nomes = PACOTES['dnf' if gerenciador == 'rpm-ostree' else gerenciador]
    pacotes = []
    for comando, pacote in [('node', 'nodejs')] + ([('podman', 'podman'), ('Xwayland', nomes['Xwayland'])] if precisa_conteiner else []):
        if not shutil.which(comando):
            pacotes.append(pacote)
    for modulo in ['PIL'] + (['gi'] if ambiente_grafico == 'gnome' else []):
        if importlib.util.find_spec(modulo) is None:
            pacotes.append(nomes[modulo])
    if ambiente_grafico == 'gnome':
        if not shutil.which('gnome-extensions') or not shutil.which('gnome-shell'):
            pacotes.append('gnome-shell')
        if not shutil.which('gsettings') or not shutil.which('glib-compile-schemas'):
            pacotes.append(nomes['glib'])
    elif ambiente_grafico == 'xfce' and not shutil.which('xfconf-query'):
        pacotes.append('xfconf')
    elif ambiente_grafico == 'kde' and not any(shutil.which(nome) for nome in ('qdbus6', 'qdbus-qt6', 'qdbus', 'gdbus')):
        pacotes.append(nomes['glib'])
    if fundo_login and not shutil.which('dconf'):
        pacotes.append(nomes['dconf'])
    return list(dict.fromkeys(pacotes))


def authenticate_once():
    if not shutil.which('sudo'):
        raise SystemExit('sudo não encontrado. Instale as dependências pelo administrador do sistema.')
    if os.environ.get('WE_SUDO_AUTHENTICATED') == '1':
        subprocess.run(['sudo', '-n', 'true'], check=True)
        return
    print('Autentique uma vez para instalar os pacotes necessários.', flush=True)
    subprocess.run(['sudo', '-v'], check=True)
    os.environ['WE_SUDO_AUTHENTICATED'] = '1'

    def manter_autenticacao():
        while not PARADA_AUTENTICACAO.wait(40):
            if subprocess.run(['sudo', '-n', '-v'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode:
                return

    threading.Thread(target=manter_autenticacao, daemon=True).start()
    atexit.register(PARADA_AUTENTICACAO.set)


def install_dependencies(ambiente_grafico, precisa_conteiner, fundo_login=False):
    gerenciador = package_manager()
    pacotes = missing_packages(ambiente_grafico, precisa_conteiner, gerenciador, fundo_login)
    if not pacotes:
        print('Dependências já disponíveis; nenhum pacote do sistema será instalado.', flush=True)
        return
    print('Instalando dependências: ' + ', '.join(pacotes), flush=True)
    authenticate_once()
    if gerenciador == 'apt-get':
        subprocess.run(['sudo', '-n', 'apt-get', 'update'], check=True)
        comando = ['sudo', '-n', 'apt-get', 'install', '-y', *pacotes]
    elif gerenciador == 'dnf':
        comando = ['sudo', '-n', 'dnf', 'install', '-y', *pacotes]
    elif gerenciador == 'pacman':
        comando = ['sudo', '-n', 'pacman', '-S', '--needed', '--noconfirm', *pacotes]
    else:
        comando = ['sudo', '-n', 'rpm-ostree', 'install', '--idempotent', '-y', *pacotes]
    subprocess.run(comando, check=True)
    importlib.invalidate_caches()
    if gerenciador == 'rpm-ostree':
        raise SystemExit('Pacotes preparados no sistema imutável. Reinicie o computador e execute o mesmo comando para concluir; não reiniciamos automaticamente.')
