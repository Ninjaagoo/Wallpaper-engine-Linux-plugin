#!/usr/bin/python3
"""Sincronização local da seleção no Wallpaper Engine com a área de trabalho."""
import colorsys
import json
import logging
import re
import secrets
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from PIL import Image

from desktop_support import (detect_desktop, workshop_folder, wallpaper_app,
                             apply_static, kde_live_available, apply_kde_live, allow_current_gnome_session)

DIRETORIO_USUARIO = Path.home().resolve()
from paths import ESTADO, FUNDOS
UUID = 'wallpaperengine@waylandwe'
EXTENSAO = DIRETORIO_USUARIO / '.local/share/gnome-shell/extensions' / UUID
ESQUEMA = 'org.gnome.shell.extensions.wallpaperengine'
PORTA = 49367
ARQUIVO_TOKEN = ESTADO / 'selection-token'
ULTIMA_SELECAO = ESTADO / 'last-selection.json'
FUNDO_LOGIN = Path('/var/lib/wallpaper-engine-login/background.png')
ENDERECO_LOCAL = '127.0.0.1'
INTERVALO_SELECAO_SEGUNDOS = 0.3
TAMANHO_AMOSTRA = (80, 80)
SATURACAO_MINIMA = 0.28
BRILHO_MINIMO = 0.20
COR_DESTAQUE_PADRAO = 'slate'
COR_FUNDO = '#161616'
TIPOS_SUPORTADOS = ('scene', 'video')
PADRAO_WORKSHOP = re.compile(r'(?:^|/)workshop/content/431960/(\d+)(?:/|$)', re.I)
PALETA = {'blue': '#3584e4', 'teal': '#2190a4', 'green': '#3a944a',
           'yellow': '#c88800', 'orange': '#ed5b00', 'red': '#e62d42',
           'pink': '#d56199', 'purple': '#9141ac', 'slate': '#6f8396'}


def resolve_selection(arquivo):
    normalizado = arquivo.replace('\\', '/')
    correspondencia = PADRAO_WORKSHOP.search(normalizado)
    if not correspondencia:
        raise ValueError('Seleção fora da biblioteca Workshop do Wallpaper Engine')
    pasta = workshop_folder(correspondencia.group(1))
    projeto = json.loads((pasta / 'project.json').read_text())
    tipo = projeto.get('type', '').lower()
    if tipo not in TIPOS_SUPORTADOS:
        raise ValueError(f'Tipo de wallpaper não suportado: {tipo}')
    midia = (pasta / projeto.get('file', '')).resolve()
    if not midia.is_relative_to(pasta.resolve()):
        raise ValueError('Caminho fora da pasta do wallpaper')
    if tipo == 'video' and not midia.is_file():
        raise ValueError('Arquivo de vídeo ainda não foi baixado')
    return pasta, projeto, tipo, midia


def choose_accent(pasta, projeto):
    previa = (pasta / projeto.get('preview', 'preview.jpg')).resolve()
    if not previa.is_relative_to(pasta.resolve()):
        return COR_DESTAQUE_PADRAO
    try:
        with Image.open(previa) as imagem:
            imagem.thumbnail(TAMANHO_AMOSTRA)
            rgb = imagem.convert('RGB')
            pixels = [rgb.getpixel((x, y)) for y in range(rgb.height) for x in range(rgb.width)]
    except (OSError, ValueError):
        return COR_DESTAQUE_PADRAO
    votos = {nome: 0.0 for nome in PALETA if nome != COR_DESTAQUE_PADRAO}
    matizes = {nome: colorsys.rgb_to_hsv(*(int(cor[i:i+2], 16)/255 for i in (1, 3, 5)))[0]
            for nome, cor in PALETA.items() if nome != COR_DESTAQUE_PADRAO}
    for rgb in pixels:
        matiz, saturacao, valor = colorsys.rgb_to_hsv(*(componente / 255 for componente in rgb))
        if saturacao < SATURACAO_MINIMA or valor < BRILHO_MINIMO:
            continue
        mais_proximo = min(matizes, key=lambda nome: min(abs(matizes[nome] - matiz), 1 - abs(matizes[nome] - matiz)))
        votos[mais_proximo] += saturacao * valor
    return max(votos, key=votos.get) if max(votos.values(), default=0) > 0 else COR_DESTAQUE_PADRAO


def gset(chave, valor):
    subprocess.run(['gsettings', '--schemadir', str(EXTENSAO / 'schemas'),
                    'set', ESQUEMA, chave, json.dumps(valor)], check=True)


def sync_static_background(pasta, projeto, ambiente_grafico="gnome"):
    previa = (pasta / projeto.get('preview', 'preview.jpg')).resolve()
    if not previa.is_relative_to(pasta.resolve()):
        raise ValueError('Prévia fora da pasta do wallpaper')
    destino = FUNDOS / (pasta.name + '.png')
    destino.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(previa) as imagem:
        temporario = destino.with_suffix('.tmp')
        imagem.convert('RGB').save(temporario, format='PNG')
        temporario.replace(destino)
    if ambiente_grafico == 'gnome' and FUNDO_LOGIN.parent.is_dir():
        try:
            import shutil
            temporario_login = FUNDO_LOGIN.with_suffix('.tmp')
            shutil.copyfile(destino, temporario_login)
            temporario_login.chmod(0o644)
            temporario_login.replace(FUNDO_LOGIN)
        except OSError:
            logging.exception('Não foi possível atualizar o fundo da tela de login')
    if ambiente_grafico != "gnome":
        apply_static(ambiente_grafico, destino)
        return destino
    uri = destino.as_uri()
    for esquema, valores in {
        'org.gnome.desktop.background': {
            'picture-uri': uri, 'picture-uri-dark': uri, 'picture-options': 'zoom',
            'primary-color': COR_FUNDO, 'secondary-color': COR_FUNDO,
            'color-shading-type': 'solid'},
        'org.gnome.desktop.screensaver': {'picture-uri': uri, 'picture-options': 'zoom',
                                        'primary-color': COR_FUNDO, 'secondary-color': COR_FUNDO},
    }.items():
        for chave, valor in valores.items():
            subprocess.run(['gsettings', 'set', esquema, chave, json.dumps(valor)], check=True)


def apply_selection(arquivo):
    pasta, projeto, tipo, midia = resolve_selection(arquivo)
    destaque = choose_accent(pasta, projeto)
    ambiente_grafico = detect_desktop()
    if ambiente_grafico != 'gnome':
        if ambiente_grafico == 'kde' and kde_live_available():
            recursos = wallpaper_app() / 'assets'
            apply_kde_live(pasta, recursos)
            modo = 'animated-experimental'
        else:
            sync_static_background(pasta, projeto, ambiente_grafico)
            modo = 'static-preview'
            logging.warning('%s: applied static preview; animated renderer unavailable for this desktop.', ambiente_grafico)
        resultado = {'id': pasta.name, 'title': projeto.get('title'), 'type': tipo,
                  'accent': None, 'desktop': ambiente_grafico, 'mode': modo}
        ULTIMA_SELECAO.write_text(json.dumps(resultado, ensure_ascii=False, indent=2))
        logging.info('Selection applied: %s', resultado)
        return
    # Batch settings changes; the extension serializes renderer shutdown/start.
    # Disabling/re-enabling the extension here would race its asynchronous stop.
    allow_current_gnome_session()
    try:
        sync_static_background(pasta, projeto)
    except (OSError, ValueError):
        logging.exception('Não foi possível sincronizar a prévia estática')
    gset('workshop-path', str(pasta.parent))
    gset('wallpaper-id', pasta.name)
    gset('engine', 'wallpaperengine' if tipo == 'scene' else 'mpv')
    if tipo == 'video':
        gset('video-path', str(midia))
    gset('enabled', True)
    subprocess.run(['gnome-extensions', 'enable', UUID], check=True)
    subprocess.run(['gsettings', 'set', 'org.gnome.desktop.interface', 'accent-color', destaque], check=True)
    resultado = {'id': pasta.name, 'title': projeto.get('title'), 'type': tipo, 'accent': destaque}
    ULTIMA_SELECAO.write_text(json.dumps(resultado, ensure_ascii=False, indent=2))
    logging.info('Seleção aplicada: %s', resultado)


class PendingSelection:
    def __init__(self):
        self.trava = threading.Lock()
        self.pendente = None
        self.alterado = threading.Event()

    def submit(self, arquivo):
        with self.trava:
            self.pendente = arquivo
        self.alterado.set()

    def run(self):
        while True:
            self.alterado.wait()
            self.alterado.clear()
            # Coalesce rapid clicks; always apply the last selection.
            while self.alterado.wait(INTERVALO_SELECAO_SEGUNDOS):
                self.alterado.clear()
            with self.trava:
                arquivo, self.pendente = self.pendente, None
            try:
                apply_selection(arquivo)
            except Exception:
                logging.exception('Não foi possível aplicar a seleção')


def main():
    ESTADO.mkdir(parents=True, exist_ok=True)
    if not ARQUIVO_TOKEN.exists():
        ARQUIVO_TOKEN.write_text(secrets.token_urlsafe(32))
        ARQUIVO_TOKEN.chmod(0o600)
    token = ARQUIVO_TOKEN.read_text().strip()
    fila = PendingSelection()
    threading.Thread(target=fila.run, daemon=True).start()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            url = urlsplit(self.path)
            consulta = parse_qs(url.query)
            if url.path != '/select' or not secrets.compare_digest(consulta.get('token', [''])[0], token):
                self.send_error(403)
                return
            try:
                arquivo = consulta['file'][0]
                resolve_selection(arquivo)
            except (KeyError, ValueError, OSError) as erro:
                logging.warning('Seleção recusada: %s', erro)
                self.send_error(400)
                return
            fila.submit(arquivo)
            self.send_response(204)
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()

        def log_message(self, *_):
            pass  # Never put the local authorization token in logs.

    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
    servidor = ThreadingHTTPServer((ENDERECO_LOCAL, PORTA), Handler)
    logging.info('Sincronização de seleção ativa em localhost:%d', PORTA)
    if detect_desktop() != 'gnome' and ULTIMA_SELECAO.exists():
        anterior = json.loads(ULTIMA_SELECAO.read_text())
        try:
            fila.submit(str(workshop_folder(anterior['id'])))
        except (ValueError, KeyError):
            logging.warning('Previous wallpaper is no longer available.')
    servidor.serve_forever()


if __name__ == '__main__':
    main()
