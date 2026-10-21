#!/usr/bin/python3
"""Instalador da integração Wallpaper Engine para GNOME, KDE e XFCE."""
import argparse
import json
import os
import secrets
import shutil
import subprocess
from pathlib import Path

from install_progress import Progress
from paths import ESTADO, EXECUTAVEIS, INTEGRACAO, migrate_legacy_paths
from installation.options import add_install_arguments
from installation.dependencies import install_dependencies, authenticate_once
from installation.requirements import check_host_requirements
from installation.runtime import IMAGEM, AMBIENTE_EXECUCAO, build_runtime as build_container_runtime

from desktop_support import (ARQUIVO_CONFIGURACAO, detect_desktop, steam_root,
                             wallpaper_app, read_config, PLUGIN_KDE, kde_live_available, workshop_folder)

DIRETORIO_USUARIO = Path.home().resolve()
PROJETO = Path(__file__).resolve().parent
UUID = 'wallpaperengine@waylandwe'
ESQUEMA = 'org.gnome.shell.extensions.wallpaperengine'
STEAM = DIRETORIO_USUARIO / '.local/share/Steam/steamapps'
EXTENSAO = DIRETORIO_USUARIO / '.local/share/gnome-shell/extensions' / UUID
DIRETORIO_EXECUTAVEIS = DIRETORIO_USUARIO / '.local/bin'
UNIDADES = DIRETORIO_USUARIO / '.config/systemd/user'
SCRIPTS_INTERFACE = STEAM / 'common/wallpaper_engine/ui/dist/scripts/scripts.js'
NOME_SERVICO = 'wallpaper-selection-sync.service'
WALLPAPER_PADRAO = '1817699663'
PORTA_SINCRONIZACAO = 49367
CHAMADA_SELECAO_INTERFACE = 'j.callDeferred("browseWallpaperObject","selectWallpaper",e.file,t,e.overridetype)'
MARCADOR_INTERFACE = '/*linux-selection-sync-v1*/'
AMBIENTE_GRAFICO = 'gnome'
RENDERIZADOR_NATIVO = None
PRECISA_RENDERIZADOR = True
PROGRESSO = None


def check_requirements(plugin_kde=False):
    check_host_requirements(AMBIENTE_GRAFICO, PRECISA_RENDERIZADOR and not RENDERIZADOR_NATIVO, PROJETO / 'extension', plugin_kde)
    for caminho in (PROJETO / 'extension/metadata.json', PROJETO / 'extension/extension.js',
                 PROJETO / 'extension/prefs.js', PROJETO / 'extension/schemas',
                 PROJETO / 'selection-sync.py', PROJETO / 'wallpaper-renderer',
                 PROJETO / 'desktop_support.py', PROJETO / 'session-start.py', PROJETO / 'paths.py',
                 PROJETO / 'installation/options.py', PROJETO / 'installation/gdm.py',
                 SCRIPTS_INTERFACE):
        if not caminho.exists():
            raise SystemExit(f'Arquivo necessário não encontrado: {caminho}')
    if PRECISA_RENDERIZADOR and not RENDERIZADOR_NATIVO and not (AMBIENTE_EXECUCAO / 'linux-wallpaperengine').is_file():
        raise SystemExit('Renderizador ausente. Execute novamente com --build-runtime ou --renderer /caminho/linux-wallpaperengine.')
    if PRECISA_RENDERIZADOR and not RENDERIZADOR_NATIVO:
        subprocess.run(['podman', 'image', 'exists', IMAGEM], check=True)


def install_extension():
    if AMBIENTE_GRAFICO != 'gnome':
        install_launchers()
        return
    EXTENSAO.mkdir(parents=True, exist_ok=True)
    shutil.copytree(PROJETO / 'extension', EXTENSAO, dirs_exist_ok=True)
    subprocess.run(['glib-compile-schemas', str(EXTENSAO / 'schemas')], check=True)
    install_launchers()
    # Keep the chosen wallpaper, FPS, volume and other user preferences.
    variaveis_ambiente = dict(os.environ, GSETTINGS_SCHEMA_DIR=str(EXTENSAO / 'schemas'))
    configuracoes = {'wallpaperengine-path': str(DIRETORIO_EXECUTAVEIS / 'wallpaper-renderer'),
                'mpv-path': str(DIRETORIO_EXECUTAVEIS / 'wallpaper-mpv'),
                'assets-path': str(STEAM / 'common/wallpaper_engine/assets'),
                'workshop-path': str(STEAM / 'workshop/content/431960'), 'enabled': True}
    selecionado = subprocess.check_output(['gsettings', 'get', ESQUEMA, 'wallpaper-id'], env=variaveis_ambiente, text=True).strip()
    if selecionado in ("''", '""'):
        configuracoes['wallpaper-id'] = WALLPAPER_PADRAO
    for chave, valor in configuracoes.items():
        subprocess.run(['gsettings', 'set', ESQUEMA, chave, json.dumps(valor)], env=variaveis_ambiente, check=True)
    subprocess.run(['gnome-extensions', 'enable', UUID], check=False)


def install_launchers():
    DIRETORIO_EXECUTAVEIS.mkdir(parents=True, exist_ok=True)
    EXECUTAVEIS.mkdir(parents=True, exist_ok=True)
    for nome in ('wallpaper-renderer', 'wallpaper-mpv'):
        destino = EXECUTAVEIS / nome
        shutil.copy2(PROJETO / 'wallpaper-renderer', destino)
        destino.chmod(0o755)
        entrada = DIRETORIO_EXECUTAVEIS / nome
        entrada.unlink(missing_ok=True)
        entrada.symlink_to(destino)


def install_desktop_entries():
    aplicativos = DIRETORIO_USUARIO / '.local/share/applications'
    aplicativos.mkdir(parents=True, exist_ok=True)
    (aplicativos / 'wallpaper-engine-linux.desktop').write_text(
        '[Desktop Entry]\nType=Application\nName=Wallpaper Engine Linux\n'
        f'Exec="{DIRETORIO_EXECUTAVEIS / "wallpaper-engine-start"}" --open\nIcon=preferences-desktop-wallpaper\n'
        'Categories=Settings;DesktopSettings;\nTerminal=false\n')
    inicio_automatico = DIRETORIO_USUARIO / '.config/autostart'
    inicio_automatico.mkdir(parents=True, exist_ok=True)
    (inicio_automatico / 'wallpaper-engine-linux.desktop').write_text(
        '[Desktop Entry]\nType=Application\nName=Wallpaper Engine Linux\n'
        f'Exec="{DIRETORIO_EXECUTAVEIS / "wallpaper-engine-start"}" --autostart\n'
        'X-GNOME-Autostart-enabled=true\nTerminal=false\nStartupNotify=false\n')


def patch_wallpaper_interface():
    ESTADO.mkdir(parents=True, exist_ok=True)
    arquivo_token = ESTADO / 'selection-token'
    if not arquivo_token.exists():
        arquivo_token.write_text(secrets.token_urlsafe(32))
        arquivo_token.chmod(0o600)
    origem = SCRIPTS_INTERFACE.read_text()
    if MARCADOR_INTERFACE not in origem:
        if origem.count(CHAMADA_SELECAO_INTERFACE) != 1:
            raise SystemExit('A interface mudou; nenhuma alteração foi feita no aplicativo.')
        backup = ESTADO / 'wallpaper-ui-original.js'
        if not backup.exists():
            shutil.copy2(SCRIPTS_INTERFACE, backup)
        url = f'http://127.0.0.1:{PORTA_SINCRONIZACAO}/select?token=' + arquivo_token.read_text().strip() + '&file='
        sinalizador = (MARCADOR_INTERFACE + '(function(f){try{var i=new Image();i.src='
                  + json.dumps(url) + '+encodeURIComponent(f)+"&t="+Date.now();}catch(_){}})(e.file),')
        modificado = origem.replace(CHAMADA_SELECAO_INTERFACE, sinalizador + CHAMADA_SELECAO_INTERFACE)
        candidato = ESTADO / 'wallpaper-ui-patched.js'
        candidato.write_text(modificado)
        subprocess.run(['node', '--check', str(candidato)], check=True)
        shutil.copyfile(candidato, SCRIPTS_INTERFACE)
        print('Interface conectada à seleção imediata; backup original preservado.')
    else:
        print('A interface já está conectada à sincronização.')



def install_sync_files():
    INTEGRACAO.mkdir(parents=True, exist_ok=True)
    for nome in ('selection-sync.py', 'desktop_support.py', 'paths.py'):
        shutil.copy2(PROJETO / nome, INTEGRACAO / nome)
    EXECUTAVEIS.mkdir(parents=True, exist_ok=True)
    destino = EXECUTAVEIS / 'wallpaper-engine-start'
    shutil.copy2(PROJETO / 'session-start.py', destino)
    destino.chmod(0o755)
    entrada = DIRETORIO_EXECUTAVEIS / 'wallpaper-engine-start'
    entrada.unlink(missing_ok=True)
    entrada.symlink_to(destino)
    install_desktop_entries()



def install_user_service():
    UNIDADES.mkdir(parents=True, exist_ok=True)
    servico = UNIDADES / NOME_SERVICO
    servico.write_text(f'''[Unit]
Description=Wallpaper Engine live selection
After=graphical-session-pre.target
PartOf=graphical-session.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 "{INTEGRACAO}/selection-sync.py"
Restart=on-failure
RestartSec=3

[Install]
WantedBy=graphical-session.target
''')
    if shutil.which('systemctl') and subprocess.run(['systemctl', '--user', 'daemon-reload'], capture_output=True).returncode == 0:
        subprocess.run(['systemctl', '--user', 'start', servico.name], check=True)
    else:
        print('systemd de usuário indisponível; a sessão usará o autostart XDG.')
    print('Sincronização instalada e iniciada nesta sessão; início automático será definido ao final.')


def install_selection_sync():
    patch_wallpaper_interface()
    install_sync_files()
    install_user_service()


def build_runtime():
    build_container_runtime(PROJETO.parent, AMBIENTE_EXECUCAO, IMAGEM)


def install_kde_plugin():
    pacote = PROJETO / 'vendor/plasma-application/package'
    instalado = any((raiz / 'plasma/wallpapers' / PLUGIN_KDE).is_dir()
                    for raiz in (DIRETORIO_USUARIO / '.local/share', Path('/usr/share'), Path('/usr/local/share')))
    subprocess.run(['kpackagetool6', '-t', 'Plasma/Wallpaper', '-u' if instalado else '-i', str(pacote)], check=True)


def configure_login_background():
    from PIL import Image
    arquivo_selecionado = ESTADO / 'last-selection.json'
    if arquivo_selecionado.exists():
        selecionado = json.loads(arquivo_selecionado.read_text())['id']
    else:
        selecionado = subprocess.check_output(['gsettings', '--schemadir', str(EXTENSAO / 'schemas'),
                                           'get', ESQUEMA, 'wallpaper-id'], text=True).strip().strip("'\"")
    pasta = workshop_folder(selecionado)
    projeto = json.loads((pasta / 'project.json').read_text())
    previa = (pasta / projeto.get('preview', 'preview.jpg')).resolve()
    if not previa.is_relative_to(pasta.resolve()):
        raise ValueError('Prévia fora da pasta do wallpaper')
    ESTADO.mkdir(parents=True, exist_ok=True)
    destino = ESTADO / 'login-background.png'
    with Image.open(previa) as imagem:
        imagem.convert('RGB').save(destino, format='PNG')
    compartilhado = Path('/var/lib/wallpaper-engine-login/background.png')
    if compartilhado.parent.is_dir() and os.access(compartilhado.parent, os.W_OK):
        temporario = compartilhado.with_suffix('.tmp')
        shutil.copyfile(destino, temporario)
        temporario.chmod(0o644)
        temporario.replace(compartilhado)
    else:
        print('Configurando o fundo do GDM: será solicitada autenticação de administrador.', flush=True)
        if os.environ.get('WE_SUDO_AUTHENTICATED') == '1':
            comando = ['sudo', '-n', 'env', f'PKEXEC_UID={os.getuid()}', '/usr/bin/python3']
        else:
            comando = ['pkexec', '/usr/bin/python3']
        subprocess.run(comando + [str(PROJETO / 'installation/gdm.py'), '--image', str(destino)], check=True)
    print('Tela de login sincronizada com a prévia selecionada (imagem estática).')


def configure_startup(escolha, configuracao):
    if escolha == 'ask':
        if not os.sys.stdin.isatty():
            raise SystemExit('Para instalação sem interação, informe --startup yes ou --startup no.')
        while True:
            resposta = input('Deseja que o Wallpaper Engine inicie junto com o sistema? [s/n]: ').strip().lower()
            if resposta in ('s', 'sim', 'y', 'yes', 'n', 'nao', 'não', 'no'):
                escolha = 'yes' if resposta in ('s', 'sim', 'y', 'yes') else 'no'
                break
            print('Digite s para sim ou n para não.')
    ativado = escolha == 'yes'
    configuracao['autostart'] = ativado
    ARQUIVO_CONFIGURACAO.write_text(json.dumps(configuracao, indent=2))
    entrada = DIRETORIO_USUARIO / '.config/autostart/wallpaper-engine-linux.desktop'
    if ativado:
        install_desktop_entries()
    else:
        entrada.unlink(missing_ok=True)
    if shutil.which('systemctl'):
        resultado = subprocess.run(['systemctl', '--user', 'enable' if ativado else 'disable', NOME_SERVICO], capture_output=True)
        if resultado.returncode != 0:
            print('A preferência será aplicada pelo autostart XDG; systemd de usuário indisponível.')
    if AMBIENTE_GRAFICO == 'gnome':
        # GNOME itself restores enabled extensions at the next login.
        resultado = subprocess.run(['gnome-extensions', 'enable' if ativado else 'disable', UUID], check=False)
        if resultado.returncode != 0:
            print('O GNOME ainda não carregou a extensão. Saia e entre na sessão para concluir a ativação.')
    print('Início automático ativado.' if ativado else 'Início automático desativado. Abra pelo menu quando desejar.')


def main():
    global AMBIENTE_GRAFICO, STEAM, SCRIPTS_INTERFACE, RENDERIZADOR_NATIVO, PRECISA_RENDERIZADOR, PROGRESSO
    analisador = argparse.ArgumentParser(description=__doc__)
    add_install_arguments(analisador)
    argumentos_cli = analisador.parse_args()
    progresso = Progress(argumentos_cli.cor, int(os.environ.get("WE_PROGRESS_START", "0")), 100)
    PROGRESSO = progresso
    progresso.update(0, "Identificando desktop e instalação da Steam…")
    try:
        AMBIENTE_GRAFICO = detect_desktop(argumentos_cli.ambiente_grafico)
        raiz = steam_root(argumentos_cli.raiz_steam)
        aplicativo = wallpaper_app(raiz)
    except ValueError as erro:
        analisador.error(str(erro))
    if argumentos_cli.plugin_kde and AMBIENTE_GRAFICO != 'kde':
        analisador.error('--kde-plugin só pode ser usado com --desktop kde')
    configuracao = read_config()
    RENDERIZADOR_NATIVO = str(argumentos_cli.renderizador.expanduser().resolve()) if argumentos_cli.renderizador else configuracao.get('renderer') or shutil.which('linux-wallpaperengine')
    if RENDERIZADOR_NATIVO and not os.access(RENDERIZADOR_NATIVO, os.X_OK):
        analisador.error('O renderizador nativo informado não é executável.')
    STEAM = raiz / 'steamapps'
    SCRIPTS_INTERFACE = aplicativo / 'ui/dist/scripts/scripts.js'
    PRECISA_RENDERIZADOR = AMBIENTE_GRAFICO == 'gnome' or (AMBIENTE_GRAFICO == 'kde' and (argumentos_cli.plugin_kde or kde_live_available()))
    if argumentos_cli.instalar_dependencias and not argumentos_cli.verificar:
        install_dependencies(AMBIENTE_GRAFICO, PRECISA_RENDERIZADOR and not RENDERIZADOR_NATIVO, argumentos_cli.fundo_login)
    if argumentos_cli.compilar_ambiente and not argumentos_cli.verificar:
        progresso.update(10, "Compilando renderizador e dependências no contêiner (pode demorar)…")
        build_runtime()
    progresso.update(40 if argumentos_cli.compilar_ambiente and not argumentos_cli.verificar else 10, "Verificando arquivos e dependências…")
    check_requirements(argumentos_cli.plugin_kde)
    print(f'Ambiente: {AMBIENTE_GRAFICO}; Steam: {raiz}')
    if argumentos_cli.verificar:
        progresso.update(100, 'Verificação concluída. Nenhuma instalação realizada.')
        print('KDE/XFCE precisam de validação no ambiente de destino.')
        return
    migrate_legacy_paths()
    progresso.update(45, "Salvando configuração da integração…")
    configuracao.update(desktop=argumentos_cli.ambiente_grafico, steam_root=str(raiz), renderer=RENDERIZADOR_NATIVO)
    ARQUIVO_CONFIGURACAO.parent.mkdir(parents=True, exist_ok=True)
    ARQUIVO_CONFIGURACAO.write_text(json.dumps(configuracao, indent=2))
    if argumentos_cli.plugin_kde:
        progresso.update(50, "Instalando addon de animação do KDE Plasma…")
        install_kde_plugin()
    progresso.update(60, f"Instalando integração com {AMBIENTE_GRAFICO.upper()} e atalhos…")
    install_extension()
    progresso.update(80, "Conectando seleção de wallpapers e configurando início automático…")
    install_selection_sync()
    if argumentos_cli.fundo_login and argumentos_cli.instalar_dependencias:
        authenticate_once()
    if AMBIENTE_GRAFICO == 'gnome' and (argumentos_cli.fundo_login or Path('/usr/local/share/gnome-shell/extensions/firewatch-login@local').is_dir()):
        progresso.update(90, 'Atualizando imagem da tela de login…')
        configure_login_background()
    progresso.update(95, 'Arquivos instalados. Configurando preferência de inicialização…')
    configure_startup(argumentos_cli.inicio_automatico, configuracao)
    progresso.update(100, 'Concluído! Integração instalada.')
    if AMBIENTE_GRAFICO == 'xfce' or (AMBIENTE_GRAFICO == 'kde' and not kde_live_available()):
        print('Modo compatível: prévia estática sincronizada. Animação não foi ativada neste ambiente.')
    elif AMBIENTE_GRAFICO == 'kde':
        print('Animação Plasma 6 instalada em modo experimental; requer QtWayland.Compositor e validação visual.')
    print('Instalação concluída. Reabra o Wallpaper Engine. No GNOME, saia e entre após atualizar a extensão.')


if __name__ == '__main__':
    try:
        main()
    except (OSError, subprocess.CalledProcessError) as erro:
        (PROGRESSO or Progress()).error(str(erro))
        raise SystemExit(1)
    except SystemExit as erro:
        if isinstance(erro.code, str):
            (PROGRESSO or Progress()).error(erro.code)
            raise SystemExit(1)
        raise
    except KeyboardInterrupt:
        print('\nInstalação interrompida; não foi concluída.')
        raise SystemExit(130)
