"""Regressões dos caminhos compartilhados de instalação, sem alterar a sessão."""
import argparse
import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJETO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJETO))
from installation import gdm, offline, requirements, runtime
from installation.options import add_install_arguments

ESPECIFICACAO = importlib.util.spec_from_file_location('instalador', PROJETO / 'install.py')
INSTALADOR = importlib.util.module_from_spec(ESPECIFICACAO)
ESPECIFICACAO.loader.exec_module(INSTALADOR)


class TestesInstalacao(unittest.TestCase):
    def test_opcoes_compartilhadas(self):
        valores = []
        for pacote_offline in (False, True):
            analisador = argparse.ArgumentParser()
            add_install_arguments(analisador, pacote_offline=pacote_offline)
            argumentos = analisador.parse_args(['--check', '--desktop', 'kde', '--startup', 'no', '--color', 'never'])
            valores.append((argumentos.verificar, argumentos.ambiente_grafico, argumentos.inicio_automatico, argumentos.cor))
        self.assertEqual(valores[0], valores[1])

    def test_validacao_kde_antes_de_instalar(self):
        with self.assertRaises(SystemExit):
            requirements.check_host_requirements('gnome', False, PROJETO / 'extension', plugin_kde=True)

    def test_versao_gnome_incompativel(self):
        with patch.object(requirements.shutil, 'which', return_value='/usr/bin/tool'), \
             patch.object(requirements.importlib.util, 'find_spec', return_value=object()), \
             patch.object(requirements.subprocess, 'check_output', return_value='GNOME Shell 99.0'):
            with self.assertRaises(SystemExit):
                requirements.check_host_requirements('gnome', False, PROJETO / 'extension')

    def test_runtime_preserva_arquivo_em_uso(self):
        with tempfile.TemporaryDirectory() as temporario:
            raiz = Path(temporario)
            origem, destino = raiz / 'novo', raiz / 'runtime'
            origem.mkdir(); destino.mkdir()
            (origem / 'linux-wallpaperengine').write_text('novo')
            (destino / 'linux-wallpaperengine').write_text('anterior')
            with (destino / 'linux-wallpaperengine').open() as arquivo:
                runtime.install_runtime(origem, destino)
                self.assertEqual(arquivo.read(), 'anterior')
            self.assertEqual((destino / 'linux-wallpaperengine').read_text(), 'novo')
            self.assertEqual(len(list(raiz.glob('runtime-backup-*'))), 1)

    def test_runtime_invalido_nao_substitui_anterior(self):
        with tempfile.TemporaryDirectory() as temporario:
            raiz = Path(temporario)
            origem, destino = raiz / 'novo', raiz / 'runtime'
            origem.mkdir(); destino.mkdir()
            (destino / 'linux-wallpaperengine').write_text('anterior')
            with self.assertRaises(SystemExit):
                runtime.install_runtime(origem, destino)
            self.assertEqual((destino / 'linux-wallpaperengine').read_text(), 'anterior')
            self.assertFalse(list(raiz.glob('.runtime-new-*')))

    def test_offline_encaminha_opcoes_e_ambiente_para_instalador(self):
        with tempfile.TemporaryDirectory() as temporario:
            destino = Path(temporario)
            (destino / 'wallpaper-linux').mkdir()
            (destino / 'wallpaper-linux/install.py').write_text(
                'import json,os,sys\nfrom pathlib import Path\n'
                'Path(__file__).with_suffix(".json").write_text(json.dumps([sys.argv[1:],os.environ["WE_PROGRESS_START"]]))\n')
            analisador = argparse.ArgumentParser()
            add_install_arguments(analisador, pacote_offline=True)
            argumentos = analisador.parse_args(['--startup', 'no', '--login-background'])
            with patch.object(offline, 'DESTINO', destino):
                offline.run_integration_installer(argumentos, destino / 'Steam Library')
            argumentos_salvos, progresso = json.loads((destino / 'wallpaper-linux/install.json').read_text())
            self.assertIn('--login-background', argumentos_salvos)
            self.assertIn(str(destino / 'Steam Library'), argumentos_salvos)
            self.assertEqual(progresso, '70')

    def test_check_offline_nao_instala(self):
        with contextlib.ExitStack() as pilha:
            pilha.enter_context(patch.object(sys, 'argv', ['package-bootstrap.py', '--check']))
            pilha.enter_context(patch.object(offline, 'check_package', return_value=Path('/steam')))
            imagem = pilha.enter_context(patch.object(offline, 'import_runtime_image'))
            arquivos = pilha.enter_context(patch.object(offline, 'install_package_files'))
            pilha.enter_context(contextlib.redirect_stdout(io.StringIO()))
            offline.main(Path('/pacote'))
            imagem.assert_not_called()
            arquivos.assert_not_called()

    def test_extensao_env_usa_nome_exigido_pelo_subprocess(self):
        def executar(comando, check=False, env=None):
            if comando[0] == 'gsettings':
                self.assertIn('GSETTINGS_SCHEMA_DIR', env)
            return subprocess.CompletedProcess(comando, 0)
        with tempfile.TemporaryDirectory() as temporario, contextlib.ExitStack() as pilha:
            pilha.enter_context(patch.object(INSTALADOR, 'EXTENSAO', Path(temporario) / 'extension'))
            pilha.enter_context(patch.object(INSTALADOR, 'AMBIENTE_GRAFICO', 'gnome'))
            pilha.enter_context(patch.object(INSTALADOR, 'install_launchers'))
            pilha.enter_context(patch.object(INSTALADOR.subprocess, 'run', side_effect=executar))
            pilha.enter_context(patch.object(INSTALADOR.subprocess, 'check_output', return_value="'123'"))
            INSTALADOR.install_extension()

    def test_auxiliar_gdm_recusa_execucao_sem_administrador(self):
        with patch.object(gdm.os, 'geteuid', return_value=1000):
            with self.assertRaises(SystemExit):
                gdm.main()

    def test_runtime_restaura_anterior_se_troca_falhar(self):
        with tempfile.TemporaryDirectory() as temporario:
            raiz = Path(temporario)
            origem, destino = raiz / 'novo', raiz / 'runtime'
            origem.mkdir(); destino.mkdir()
            (origem / 'linux-wallpaperengine').write_text('novo')
            (destino / 'linux-wallpaperengine').write_text('anterior')
            renomear = Path.rename

            def trocar(caminho, alvo):
                if caminho.name.startswith('.runtime-new-'):
                    raise OSError('Falha simulada na troca')
                return renomear(caminho, alvo)

            with patch.object(Path, 'rename', trocar):
                with self.assertRaises(OSError):
                    runtime.install_runtime(origem, destino)
            self.assertEqual((destino / 'linux-wallpaperengine').read_text(), 'anterior')
            self.assertFalse(list(raiz.glob('.runtime-new-*')))

    def test_patch_renderizador_aplicado_uma_unica_vez(self):
        with tempfile.TemporaryDirectory() as temporario:
            raiz = Path(temporario)
            fonte = raiz / 'linux-wallpaperengine'
            fonte.mkdir()
            subprocess.run(['git', 'init', '-q', str(fonte)], check=True)
            (fonte / 'teste.txt').write_text('original\n')
            (raiz / 'patches').mkdir()
            (raiz / 'patches/teste.patch').write_text(
                'diff --git a/teste.txt b/teste.txt\n--- a/teste.txt\n+++ b/teste.txt\n'
                '@@ -1 +1,2 @@\n original\n+adaptado\n')
            runtime.apply_renderer_patches(raiz)
            runtime.apply_renderer_patches(raiz)
            self.assertEqual((fonte / 'teste.txt').read_text(), 'original\nadaptado\n')

    def test_gerador_produz_executavel_com_verificacao_de_integridade(self):
        especificacao = importlib.util.spec_from_file_location('gerador', PROJETO.parent / 'tools/build-release.py')
        gerador = importlib.util.module_from_spec(especificacao)
        especificacao.loader.exec_module(gerador)
        with tempfile.TemporaryDirectory() as temporario:
            raiz = Path(temporario)
            conteudo, destino = raiz / 'payload', raiz / 'teste.run'
            conteudo.write_bytes(b'conteudo de teste')
            gerador.write_executable(conteudo, destino)
            resultado = subprocess.run([str(destino), '--verify'], capture_output=True, text=True)
            self.assertEqual(resultado.returncode, 0, resultado.stderr)
            destino.write_bytes(destino.read_bytes() + b'alterado')
            resultado = subprocess.run([str(destino), '--verify'], capture_output=True, text=True)
            self.assertNotEqual(resultado.returncode, 0)


if __name__ == '__main__':
    unittest.main()
