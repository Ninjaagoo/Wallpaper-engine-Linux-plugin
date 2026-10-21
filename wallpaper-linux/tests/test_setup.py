"""Migração para a pasta privada e instalação de requisitos sem operações de administrador."""
import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJETO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJETO))
import paths
from installation import dependencies


class TestesPreparacao(unittest.TestCase):
    def test_migracao_preserva_selecao_e_links(self):
        with tempfile.TemporaryDirectory() as temporario:
            usuario = Path(temporario)
            anterior = usuario / '.local/state/wallpaper-engine'
            anterior.mkdir(parents=True)
            (anterior / 'selection-token').write_text('token-teste')
            (anterior / 'last-selection.json').write_text('{"id":"123"}')
            paths.migrate_legacy_paths(usuario)
            paths.migrate_legacy_paths(usuario)
            destino = usuario / '.local/share/wallpaper-engine/state'
            self.assertTrue(anterior.is_symlink())
            self.assertEqual((anterior / 'selection-token').read_text(), 'token-teste')
            self.assertEqual((destino / 'last-selection.json').read_text(), '{"id":"123"}')
            self.assertFalse(list(destino.parent.glob('migration-backup-*')))

    def test_migracao_nao_sobrescreve_conflitos(self):
        with tempfile.TemporaryDirectory() as temporario:
            usuario = Path(temporario)
            anterior = usuario / '.config/wallpaper-engine'
            destino = usuario / '.local/share/wallpaper-engine/config'
            anterior.mkdir(parents=True); destino.mkdir(parents=True)
            (anterior / 'config.json').write_text('anterior')
            (anterior / 'extra.json').write_text('preservado')
            (destino / 'config.json').write_text('atual')
            paths.migrate_legacy_paths(usuario)
            self.assertEqual((destino / 'config.json').read_text(), 'atual')
            self.assertEqual((destino / 'extra.json').read_text(), 'preservado')
            backup = next(destino.parent.glob('migration-backup-*'))
            self.assertEqual((backup / 'config/config.json').read_text(), 'anterior')

    def test_pacotes_por_distribuicao(self):
        with patch.object(dependencies.shutil, 'which', return_value=None), \
             patch.object(dependencies.importlib.util, 'find_spec', return_value=None):
            self.assertIn('python3-pil', dependencies.missing_packages('gnome', True, 'apt-get'))
            self.assertIn('python3-pillow', dependencies.missing_packages('gnome', True, 'rpm-ostree'))
            self.assertIn('python-pillow', dependencies.missing_packages('gnome', True, 'pacman'))

    def test_dependencias_existentes_nao_pedem_senha(self):
        with patch.object(dependencies, 'package_manager', return_value='dnf'), \
             patch.object(dependencies, 'missing_packages', return_value=[]), \
             patch.object(dependencies, 'authenticate_once') as autenticar, \
             contextlib.redirect_stdout(io.StringIO()):
            dependencies.install_dependencies('gnome', True)
            autenticar.assert_not_called()

    def test_imutavel_pede_reinicio_sem_reiniciar(self):
        with patch.object(dependencies, 'package_manager', return_value='rpm-ostree'), \
             patch.object(dependencies, 'missing_packages', return_value=['nodejs']), \
             patch.object(dependencies, 'authenticate_once'), \
             patch.object(dependencies.subprocess, 'run') as executar, \
             contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(SystemExit, 'Reinicie'):
                dependencies.install_dependencies('gnome', True)
            executar.assert_called_once_with(['sudo', '-n', 'rpm-ostree', 'install', '--idempotent', '-y', 'nodejs'], check=True)

    def test_autenticacao_existente_nao_pede_novamente(self):
        with patch.dict(os.environ, {'WE_SUDO_AUTHENTICATED': '1'}), \
             patch.object(dependencies.shutil, 'which', return_value='/usr/bin/sudo'), \
             patch.object(dependencies.subprocess, 'run') as executar:
            dependencies.authenticate_once()
            executar.assert_called_once_with(['sudo', '-n', 'true'], check=True)

    def test_primeira_autenticacao_e_reutilizada(self):
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(dependencies.shutil, 'which', return_value='/usr/bin/sudo'), \
             patch.object(dependencies.subprocess, 'run') as executar, \
             patch.object(dependencies.threading, 'Thread') as tarefa, \
             patch.object(dependencies.atexit, 'register'), \
             contextlib.redirect_stdout(io.StringIO()):
            dependencies.authenticate_once()
            dependencies.authenticate_once()
            self.assertEqual(executar.call_args_list[0].args[0], ['sudo', '-v'])
            self.assertEqual(executar.call_args_list[1].args[0], ['sudo', '-n', 'true'])
            self.assertEqual(executar.call_count, 2)
            tarefa.return_value.start.assert_called_once()

    def test_bootstrap_baixa_confere_limpa_e_encaminha_opcoes(self):
        with tempfile.TemporaryDirectory() as temporario:
            raiz = Path(temporario)
            comandos = raiz / 'bin'; comandos.mkdir()
            (comandos / 'id').write_text('#!/bin/sh\necho 1000\n')
            (comandos / 'id').chmod(0o755)
            (comandos / 'curl').write_text('#!' + sys.executable + '\n' + '''import hashlib,sys
from pathlib import Path
saida=Path(sys.argv[sys.argv.index('-o')+1])
conteudo=b'#!/bin/bash\\nprintf "%s\\\\n" "$@" > "$TEST_RESULT"\\n'
if saida.name.endswith('.sha256'):
    saida.write_text(hashlib.sha256(conteudo).hexdigest()+'  WallpaperEngine-Linux-x86_64.run\\n')
else: saida.write_bytes(conteudo)
''')
            (comandos / 'curl').chmod(0o755)
            ambiente = dict(os.environ, PATH=str(comandos) + ':' + os.environ['PATH'],
                            XDG_CACHE_HOME=str(raiz / 'cache'), TEST_RESULT=str(raiz / 'resultado'))
            resultado = subprocess.run(['bash', str(PROJETO.parent / 'install.sh'), '--startup', 'no'], env=ambiente, capture_output=True, text=True)
            self.assertEqual(resultado.returncode, 0, resultado.stderr)
            self.assertEqual((raiz / 'resultado').read_text().splitlines(), ['--install-deps', '--startup', 'no'])
            self.assertFalse(list((raiz / 'cache/wallpaper-engine').glob('download.*')))


if __name__ == '__main__':
    unittest.main()
