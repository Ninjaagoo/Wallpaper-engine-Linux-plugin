#!/usr/bin/python3
"""Instalação da prévia selecionada na tela de login do GDM."""
import argparse
import ast
import datetime
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

UUID = 'firewatch-login@local'
ORIGEM = Path(__file__).resolve().parents[1] / 'login-screen' / UUID
DESTINO = Path('/usr/local/share/gnome-shell/extensions') / UUID
CONFIGURACAO = Path('/etc/dconf/db/gdm.d/90-firewatch-login')
RAIZ_BACKUP = Path('/var/lib/firewatch-login-backup')


def install_login_image(origem_imagem, uid):
    compartilhado = Path('/var/lib/wallpaper-engine-login')
    if compartilhado.is_symlink():
        raise SystemExit('Diretório de fundo não pode ser um link simbólico.')
    compartilhado.mkdir(mode=0o755, exist_ok=True)
    # Only this image directory is writable; extension code remains owned by root.
    os.chown(compartilhado, uid, -1)
    compartilhado.chmod(0o755)
    # Image paths are user-controlled, so read/write them without root privileges.
    os.seteuid(uid)
    try:
        imagem = compartilhado / 'background.png'
        dados = origem_imagem.read_bytes()
        if not dados.startswith(b'\x89PNG\r\n\x1a\n'):
            raise SystemExit('A imagem precisa estar no formato PNG.')
        with tempfile.NamedTemporaryFile(dir=compartilhado, delete=False) as saida:
            temporario = Path(saida.name)
            saida.write(dados)
        temporario.chmod(0o644)
        temporario.replace(imagem)
    finally:
        os.seteuid(0)

    return compartilhado


def backup_login_configuration():

    backup = RAIZ_BACKUP / datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    backup.mkdir(parents=True, mode=0o755)
    for caminho in (DESTINO, CONFIGURACAO):
        if caminho.is_dir():
            shutil.copytree(caminho, backup / caminho.name)
        elif caminho.is_file():
            shutil.copy2(caminho, backup / caminho.name)


    return backup


def install_gdm_extension(compartilhado):
    # Query the system GDM database alone, preserving any other enabled extensions.
    with tempfile.NamedTemporaryFile(mode='w', prefix='firewatch-gdm-profile-') as perfil:
        perfil.write('system-db:gdm\n')
        perfil.flush()
        variaveis_ambiente = dict(os.environ, DCONF_PROFILE=perfil.name, GSETTINGS_BACKEND='dconf')
        valor = subprocess.check_output(['gsettings', 'get', 'org.gnome.shell', 'enabled-extensions'], env=variaveis_ambiente, text=True)
        ativado = ast.literal_eval(valor.strip().removeprefix('@as '))
        if UUID not in ativado:
            ativado.append(UUID)
        DESTINO.mkdir(parents=True, exist_ok=True, mode=0o755)
        for nome in ('metadata.json', 'extension.js', 'firewatch.png'):
            destino = DESTINO / nome
            shutil.copyfile(ORIGEM / nome, destino)
            destino.chmod(0o644)
        CONFIGURACAO.parent.mkdir(parents=True, exist_ok=True)
        CONFIGURACAO.write_text('[org/gnome/shell]\nenabled-extensions=' + repr(ativado) + '\ndisable-user-extensions=false\n')
        CONFIGURACAO.chmod(0o644)
        if shutil.which('restorecon'):
            subprocess.run(['restorecon', '-RF', str(DESTINO), str(compartilhado)], check=True)
        subprocess.run(['dconf', 'update'], check=True)
        atual = subprocess.check_output(['gsettings', 'get', 'org.gnome.shell', 'enabled-extensions'], env=variaveis_ambiente, text=True)
        if UUID not in atual:
            raise SystemExit('A configuração não foi confirmada no banco GDM.')


def main():
    if os.geteuid() != 0:
        raise SystemExit('Execute com autenticação de administrador (pkexec).')

    analisador = argparse.ArgumentParser(description=__doc__)
    analisador.add_argument('--image', dest='imagem', type=Path, required=True, help='Prévia PNG preparada pelo usuário')
    argumentos_cli = analisador.parse_args()
    uid = int(os.environ.get('PKEXEC_UID', '-1'))
    if uid <= 0:
        raise SystemExit('Execute usando pkexec a partir da sessão do usuário.')
    compartilhado = install_login_image(argumentos_cli.imagem, uid)
    backup = backup_login_configuration()
    install_gdm_extension(compartilhado)
    print('Wallpaper selecionado instalado na tela de login. Será aplicado na próxima inicialização do GDM.')
    print('Backup:', backup)


if __name__ == '__main__':
    main()
