"""Local único dos dados privados da integração e compatibilidade com versões antigas."""
import shutil
import tempfile
from pathlib import Path

DIRETORIO_USUARIO = Path.home().resolve()
BASE = DIRETORIO_USUARIO / '.local/share/wallpaper-engine'
CONFIGURACAO = BASE / 'config'
ARQUIVO_CONFIGURACAO = CONFIGURACAO / 'config.json'
ESTADO = BASE / 'state'
FUNDOS = BASE / 'backgrounds'
EXECUTAVEIS = BASE / 'bin'
INTEGRACAO = BASE / 'integration'
AMBIENTE_EXECUCAO = BASE / 'runtime'
PACOTE = BASE / 'package'
CONFIGURACAO_ANTIGA = DIRETORIO_USUARIO / '.config/wallpaper-engine/config.json'


def migrate_legacy_paths(diretorio_usuario=None):
    diretorio_usuario = diretorio_usuario or DIRETORIO_USUARIO
    base = diretorio_usuario / '.local/share/wallpaper-engine'
    base.mkdir(parents=True, exist_ok=True)
    pares = [('.config/wallpaper-engine', 'config'),
             ('.local/state/wallpaper-engine', 'state'),
             ('.local/share/backgrounds/wallpaper-engine', 'backgrounds')]
    for relativo, nome in pares:
        anterior, destino = diretorio_usuario / relativo, base / nome
        if anterior.is_symlink():
            if anterior.resolve() != destino.resolve():
                raise SystemExit(f'Link personalizado preservado; ajuste o caminho antes de continuar: {anterior}')
            destino.mkdir(parents=True, exist_ok=True)
            continue
        if anterior.exists():
            if destino.exists():
                # Bring missing legacy files into the canonical directory; preserve conflicts.
                for arquivo in anterior.rglob('*'):
                    alvo = destino / arquivo.relative_to(anterior)
                    if arquivo.is_dir():
                        alvo.mkdir(parents=True, exist_ok=True)
                    elif not alvo.exists():
                        alvo.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(arquivo, alvo)
                backup = Path(tempfile.mkdtemp(prefix='migration-backup-', dir=base))
                shutil.move(str(anterior), str(backup / nome))
            else:
                destino.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(anterior), str(destino))
        destino.mkdir(parents=True, exist_ok=True)
        anterior.parent.mkdir(parents=True, exist_ok=True)
        anterior.symlink_to(destino, target_is_directory=True)
