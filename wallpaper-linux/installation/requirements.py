"""Verificações do hospedeiro utilizadas pelos dois caminhos de instalação."""
import importlib.util
import json
import re
import shutil
import subprocess

COMANDOS_GNOME = ('gnome-shell', 'gnome-extensions', 'gsettings', 'glib-compile-schemas')
COMANDOS_DBUS = ('qdbus6', 'qdbus-qt6', 'qdbus', 'gdbus')


def check_host_requirements(ambiente_grafico, precisa_conteiner, origem_extensao, plugin_kde=False):
    comandos = ['node']
    if precisa_conteiner:
        comandos.extend(('podman', 'Xwayland'))
    if ambiente_grafico == 'gnome':
        comandos.extend(COMANDOS_GNOME)
    elif ambiente_grafico == 'xfce':
        comandos.append('xfconf-query')
    elif not any(shutil.which(ferramenta) for ferramenta in COMANDOS_DBUS):
        raise SystemExit('Instale qdbus6 ou gdbus para controlar o Plasma.')
    if plugin_kde:
        if ambiente_grafico != 'kde':
            raise SystemExit('--kde-plugin só pode ser usado com --desktop kde')
        comandos.extend(('kpackagetool6', 'xwayland-run'))
    ausentes = [comando for comando in comandos if not shutil.which(comando)]
    for modulo in ['PIL'] + (['gi'] if ambiente_grafico == 'gnome' else []):
        if importlib.util.find_spec(modulo) is None:
            ausentes.append('módulo Python ' + modulo)
    if ausentes:
        raise SystemExit('Dependências ausentes: ' + ', '.join(ausentes))
    if ambiente_grafico == 'gnome':
        versao = subprocess.check_output(['gnome-shell', '--version'], text=True)
        correspondencia = re.search(r'\b(\d+)\.', versao)
        suportados = json.loads((origem_extensao / 'metadata.json').read_text())['shell-version']
        if not correspondencia or correspondencia.group(1) not in suportados:
            raise SystemExit(f'Versão GNOME não declarada compatível: {versao.strip()}; suportadas: {suportados}')
