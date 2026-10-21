"""Compilação, importação e substituição segura do renderizador."""
import shutil
import subprocess
import tempfile
from pathlib import Path

IMAGEM = 'localhost/wallpaper-engine-runtime:fedora44'
AMBIENTE_EXECUCAO = Path.home() / '.local/share/wallpaper-engine/runtime'


def install_runtime(origem, destino):
    """Preserva arquivos em uso e restaura a versão anterior se a troca falhar."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    preparado = Path(tempfile.mkdtemp(prefix='.runtime-new-', dir=destino.parent))
    anterior = None
    try:
        subprocess.run(['cp', '-a', '--reflink=auto', str(origem) + '/.', str(preparado)], check=True)
        if not (preparado / 'linux-wallpaperengine').is_file():
            raise SystemExit('O runtime não contém o executável linux-wallpaperengine.')
        if destino.exists():
            anterior = destino.parent / ('runtime-backup-' + preparado.name.removeprefix('.runtime-new-'))
            destino.rename(anterior)
        try:
            preparado.rename(destino)
        except OSError:
            if anterior is not None:
                anterior.rename(destino)
            raise
        if anterior is not None:
            print(f'Runtime anterior preservado em {anterior}', flush=True)
    finally:
        if preparado.exists():
            shutil.rmtree(preparado)


def import_runtime_image(arquivo, imagem=IMAGEM):
    if subprocess.run(['podman', 'image', 'exists', imagem]).returncode != 0:
        subprocess.run(['podman', 'load', '-i', str(arquivo)], check=True)


def apply_renderer_patches(projeto):
    pasta = projeto / 'linux-wallpaperengine'
    for arquivo in sorted((projeto / 'patches').glob('*.patch')):
        if subprocess.run(['git', '-C', str(pasta), 'apply', '--reverse', '--check', str(arquivo)],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            continue
        subprocess.run(['git', '-C', str(pasta), 'apply', '--check', str(arquivo)], check=True)
        subprocess.run(['git', '-C', str(pasta), 'apply', str(arquivo)], check=True)


def build_runtime(projeto, destino=AMBIENTE_EXECUCAO, imagem=IMAGEM):
    if not shutil.which('podman') or not shutil.which('git'):
        raise SystemExit('Instale Podman e Git antes de usar --build-runtime.')
    subprocess.run(['git', '-C', str(projeto / 'linux-wallpaperengine'), 'submodule', 'update', '--init', '--recursive'], check=True)
    apply_renderer_patches(projeto)
    subprocess.run(['podman', 'build', '-t', imagem, '-f', str(projeto / 'Containerfile'), str(projeto)], check=True)
    conteiner = subprocess.check_output(['podman', 'create', imagem], text=True).strip()
    try:
        destino.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.runtime-build-', dir=destino.parent) as temporario:
            subprocess.run(['podman', 'cp', f'{conteiner}:/opt/runtime/.', temporario], check=True)
            install_runtime(Path(temporario), destino)
    finally:
        subprocess.run(['podman', 'rm', conteiner], check=True)
