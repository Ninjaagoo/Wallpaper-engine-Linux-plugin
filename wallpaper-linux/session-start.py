#!/usr/bin/python3
"""Inicialização da integração em sessões com ou sem systemd de usuário."""
import shutil
import subprocess
import sys
from pathlib import Path

INTEGRACAO = Path.home() / '.local/share/wallpaper-engine/integration'
SERVICO = 'wallpaper-selection-sync.service'
sys.path.insert(0, str(INTEGRACAO))
from desktop_support import detect_desktop, read_config, allow_current_gnome_session
from paths import ESTADO


def main():
    if '--autostart' in sys.argv and not read_config().get('autostart', True):
        return
    ambiente_grafico = detect_desktop()
    if ambiente_grafico == 'gnome' and '--autostart' not in sys.argv:
        allow_current_gnome_session()
    if '--open' in sys.argv:
        if ambiente_grafico == 'gnome':
            subprocess.Popen(['gnome-extensions', 'prefs', 'wallpaperengine@waylandwe'])
        elif shutil.which('steam'):
            subprocess.Popen(['steam', '-applaunch', '431960'])
        else:
            subprocess.Popen(['flatpak', 'run', 'com.valvesoftware.Steam', '-applaunch', '431960'])
    if ambiente_grafico == 'gnome':
        subprocess.run(['gnome-extensions', 'enable', 'wallpaperengine@waylandwe'], check=False)
    if shutil.which('systemctl'):
        resultado = subprocess.run(['systemctl', '--user', 'start', SERVICO], capture_output=True)
        if resultado.returncode == 0:
            return
    estado = ESTADO
    estado.mkdir(parents=True, exist_ok=True)
    with (estado / 'selection-sync.log').open('a') as registro:
        subprocess.Popen([sys.executable, str(INTEGRACAO / 'selection-sync.py')],
                         stdout=registro, stderr=subprocess.STDOUT, start_new_session=True)


if __name__ == '__main__':
    main()
