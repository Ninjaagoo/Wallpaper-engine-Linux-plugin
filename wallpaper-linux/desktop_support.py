"""Descoberta do desktop e da Steam, compartilhada pela integração."""
import json
import os
import re
import shlex
import shutil
import subprocess
from pathlib import Path

DIRETORIO_USUARIO = Path.home().resolve()
DIRETORIO_DADOS = Path(os.environ.get('XDG_DATA_HOME', DIRETORIO_USUARIO / '.local/share'))
from paths import ARQUIVO_CONFIGURACAO, CONFIGURACAO_ANTIGA
PLUGIN_KDE = 'net.dosowisko.PlasmaApplicationWallpaper'
AMBIENTES_SUPORTADOS = ('gnome', 'kde', 'xfce')


def read_config():
    if ARQUIVO_CONFIGURACAO.exists():
        return json.loads(ARQUIVO_CONFIGURACAO.read_text())
    if CONFIGURACAO_ANTIGA.exists():
        return json.loads(CONFIGURACAO_ANTIGA.read_text())
    return {}


def detect_desktop(substituicao=None, ambiente=None):
    ambiente = os.environ if ambiente is None else ambiente
    configurado = substituicao or read_config().get('desktop', 'auto')
    if configurado != 'auto':
        if configurado not in AMBIENTES_SUPORTADOS:
            raise ValueError(f'Ambiente não suportado: {configurado}')
        return configurado
    valor = (ambiente.get('XDG_CURRENT_DESKTOP', '') + ':' + ambiente.get('DESKTOP_SESSION', '')).lower()
    for nome, apelidos in {'gnome': ('gnome', 'ubuntu'), 'kde': ('kde', 'plasma'), 'xfce': ('xfce', 'xubuntu')}.items():
        if any(apelido in valor for apelido in apelidos):
            return nome
    raise ValueError('Ambiente não reconhecido. Use --desktop gnome, kde ou xfce.')


def steam_root(substituicao=None):
    configurado = substituicao or read_config().get('steam_root')
    if configurado:
        candidato = Path(configurado).expanduser().resolve()
        if not (candidato / 'steamapps').is_dir():
            raise ValueError(f'Biblioteca Steam não encontrada: {candidato}')
        return candidato
    for candidato in (DIRETORIO_DADOS / 'Steam', DIRETORIO_USUARIO / '.steam/steam', DIRETORIO_USUARIO / '.steam/root',
                      DIRETORIO_USUARIO / '.var/app/com.valvesoftware.Steam/.local/share/Steam'):
        if (candidato / 'steamapps').is_dir():
            return candidato.resolve()
    raise ValueError('Steam não encontrada. Informe --steam-root /caminho/Steam.')


def steam_libraries(raiz=None):
    raiz = raiz or steam_root()
    bibliotecas = [raiz]
    for arquivo in (raiz / 'steamapps/libraryfolders.vdf', raiz / 'config/libraryfolders.vdf'):
        if not arquivo.exists():
            continue
        for valor in re.findall(r'"path"\s*"((?:\\.|[^"\\])*)"', arquivo.read_text()):
            caminho = Path(valor.replace('\\\\', '\\')).expanduser().resolve()
            if caminho not in bibliotecas and (caminho / 'steamapps').is_dir():
                bibliotecas.append(caminho)
    return bibliotecas


def wallpaper_app(raiz=None):
    for biblioteca in steam_libraries(raiz):
        aplicativo = biblioteca / 'steamapps/common/wallpaper_engine'
        if (aplicativo / 'ui/dist/scripts/scripts.js').exists():
            return aplicativo
    raise ValueError('Instale o Wallpaper Engine em uma biblioteca Steam.')


def workshop_folder(id_item):
    for biblioteca in steam_libraries():
        pasta = biblioteca / 'steamapps/workshop/content/431960' / id_item
        if (pasta / 'project.json').is_file():
            return pasta
    raise ValueError(f'Wallpaper {id_item} ainda não foi baixado nas bibliotecas Steam.')


def plasma_script(codigo_script):
    for ferramenta in ('qdbus6', 'qdbus-qt6', 'qdbus'):
        if shutil.which(ferramenta):
            return subprocess.run([ferramenta, 'org.kde.plasmashell', '/PlasmaShell',
                                   'org.kde.PlasmaShell.evaluateScript', codigo_script], check=True)
    if shutil.which('gdbus'):
        return subprocess.run(['gdbus', 'call', '--session', '--dest', 'org.kde.plasmashell',
                               '--object-path', '/PlasmaShell', '--method',
                               'org.kde.PlasmaShell.evaluateScript', codigo_script], check=True)
    raise ValueError('Instale qdbus6 ou gdbus para controlar o Plasma.')


def apply_static(ambiente_grafico, imagem):
    if ambiente_grafico == 'kde':
        uri = Path(imagem).as_uri()
        codigo_script = ('var ds=desktops(); for(var i=0;i<ds.length;i++){var d=ds[i];'
                  'd.wallpaperPlugin="org.kde.image";d.currentConfigGroup=["Wallpaper","org.kde.image","General"];'
                  f'd.writeConfig("Image",{json.dumps(uri)});' + '}')
        plasma_script(codigo_script)
    elif ambiente_grafico == 'xfce':
        resultado = subprocess.check_output(['xfconf-query', '-c', 'xfce4-desktop', '-l'], text=True)
        propriedades = [propriedade for propriedade in resultado.splitlines() if propriedade.startswith('/backdrop/') and propriedade.endswith('/last-image')]
        if not propriedades:
            raise ValueError('O xfdesktop não informou propriedades last-image para os monitores.')
        for nome_propriedade in propriedades:
            subprocess.run(['xfconf-query', '-c', 'xfce4-desktop', '-p', nome_propriedade,
                            '-s', str(imagem)], check=True)


def kde_live_available():
    raizes = [DIRETORIO_DADOS, Path('/usr/local/share'), Path('/usr/share')]
    return (shutil.which('xwayland-run') is not None
            and any((raiz / 'plasma/wallpapers' / PLUGIN_KDE).is_dir() for raiz in raizes))


def apply_kde_live(pasta, recursos):
    configuracao = read_config()
    largura, altura = configuracao.get('render_size', [1920, 1080])
    fps = configuracao.get('fps', 30)
    iniciador = DIRETORIO_USUARIO / '.local/bin/wallpaper-renderer'
    # The native engine handles scenes and videos; the Plasma addon embeds its
    # XWayland surface and supplies the desktop/window lifecycle.
    comando = shlex.join(['xwayland-run', '--', str(iniciador), '--window', f'0x0x{largura}x{altura}',
                          '--fps', str(fps), '--silent', '--assets-dir', str(recursos), str(pasta)])
    codigo_script = ('var ds=desktops();for(var i=0;i<ds.length;i++){var d=ds[i];'
              f'd.wallpaperPlugin={json.dumps(PLUGIN_KDE)};'
              f'd.currentConfigGroup=["Wallpaper",{json.dumps(PLUGIN_KDE)},"General"];'
              f'd.writeConfig("command",{json.dumps(comando)});d.writeConfig("allowInput",false);'
              'd.writeConfig("unscaled",true);' + f'd.writeConfig("fps",{fps});' + '}')
    plasma_script(codigo_script)


def allow_current_gnome_session():
    """A manual launch applies to this shell process, never a future login."""
    ambiente_execucao = os.environ.get('XDG_RUNTIME_DIR')
    if not ambiente_execucao:
        return
    processos_shell = []
    for processo in Path('/proc').iterdir():
        if not processo.name.isdigit():
            continue
        try:
            if processo.stat().st_uid == os.getuid() and (processo / 'comm').read_text().strip() == 'gnome-shell':
                processos_shell.append(processo.name)
        except OSError:
            continue
    (Path(ambiente_execucao) / 'wallpaper-engine-manual-session').write_text(' '.join(processos_shell))
