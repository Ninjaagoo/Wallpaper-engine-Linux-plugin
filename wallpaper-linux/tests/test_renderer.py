"""Regressões de enquadramento e metadados de vídeos, sem abrir janelas."""
import importlib.machinery
import importlib.util
import unittest
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

CAMINHO = Path(__file__).resolve().parents[1] / 'wallpaper-renderer'
CARREGADOR = importlib.machinery.SourceFileLoader('renderizador', str(CAMINHO))
ESPECIFICACAO = importlib.util.spec_from_loader(CARREGADOR.name, CARREGADOR)
RENDERIZADOR = importlib.util.module_from_spec(ESPECIFICACAO)
CARREGADOR.exec_module(RENDERIZADOR)


def matrix(a, b, c, d):
    return f'00000000: {a} {b} 0\n00000001: {c} {d} 0\n00000002: 0 0 1073741824\n'


class TestesVideo(unittest.TestCase):
    def test_ciclo_de_vida_sem_processos_sobrepostos(self):
        subprocess.run(['node', str(CAMINHO.parents[1] / 'tools/test-renderer-lifecycle.mjs')],
                       check=True, capture_output=True, text=True)

    def test_selecao_nao_desativa_extensao_durante_troca(self):
        sys.path.insert(0, str(CAMINHO.parent))
        especificacao = importlib.util.spec_from_file_location('sincronizacao_teste', CAMINHO.parent / 'selection-sync.py')
        modulo = importlib.util.module_from_spec(especificacao)
        especificacao.loader.exec_module(modulo)
        with patch.multiple(modulo, resolve_selection=MagicMock(return_value=(Path('/biblioteca/123'),
                            {'title': 'Teste'}, 'scene', Path('/biblioteca/123/scene.json'))),
                            choose_accent=MagicMock(return_value='slate'),
                            detect_desktop=MagicMock(return_value='gnome'),
                            allow_current_gnome_session=MagicMock(),
                            sync_static_background=MagicMock(), gset=MagicMock(),
                            ULTIMA_SELECAO=MagicMock()), patch.object(modulo.subprocess, 'run') as executar:
            modulo.apply_selection('/biblioteca/123/project.json')
            comandos = [chamada.args[0] for chamada in executar.call_args_list]
            self.assertNotIn(['gnome-extensions', 'disable', modulo.UUID], comandos)
            self.assertIn(['gnome-extensions', 'enable', modulo.UUID], comandos)
            modulo.gset.assert_any_call('wallpaper-id', '123')

    def test_resolucao_fisica_4k_com_escala_fracionada(self):
        monitor = ('DP-1', 'vendor', 'model', 'serial')
        estado = (1, [(monitor, [('4k', 3840, 2160, 60, 1, [], {'is-current': True})])],
                  [(0, 0, 1.5, 0, True, [monitor])])
        argumentos = ['--window', '0x0x2560x1440', 'cena']
        self.assertEqual(RENDERIZADOR.physical_geometry(argumentos, estado)[1], '0x0x3840x2160')

    def test_monitor_vertical_2k(self):
        monitor = ('DP-1', 'vendor', 'model', 'serial')
        estado = (1, [(monitor, [('2k', 2560, 1440, 60, 1, [], {'is-current': True})])],
                  [(0, 0, 1, 1, True, [monitor])])
        argumentos = ['--window', '0x0x1440x2560', 'cena']
        self.assertEqual(RENDERIZADOR.physical_geometry(argumentos, estado)[1], '0x0x1440x2560')

    def test_subaru_com_cisalhamento_invalido(self):
        dados = {'streams': [{'side_data_list': [
            {'displaymatrix': matrix(65536, 16777216, 0, 65536)}]}]}
        argumentos = RENDERIZADOR.video_arguments(['--vf=fps=60', 'Subaru.mp4'], dados, (3840, 2160))
        self.assertIn('--video-rotate=no', argumentos)
        self.assertIn('--geometry=3840x2160', argumentos)
        self.assertNotIn('--vf=fps=60', argumentos)
        self.assertEqual(argumentos[-1], 'Subaru.mp4')

    def test_rotacoes_validas_preservadas(self):
        for valores in ((65536, 0, 0, 65536), (0, -65536, 65536, 0),
                        (46341, -46341, 46341, 46341)):
            self.assertFalse(RENDERIZADOR.invalid_display_matrix(matrix(*valores)))

    def test_rotacao_explicita_e_monitor_secundario_preservados(self):
        argumentos = ['--video-rotate=90', '--geometry=2560x1440', '--vf=scale=1920:1080', 'video.mp4']
        dados = {'streams': [{'side_data_list': [{'displaymatrix': matrix(1, 256, 0, 1)}]}]}
        resultado = RENDERIZADOR.video_arguments(argumentos, dados, (1920, 1080))
        self.assertNotIn('--video-rotate=no', resultado)
        self.assertNotIn('--geometry=1920x1080', resultado)
        self.assertIn('--vf=scale=1920:1080', resultado)

    def test_sem_metadados_nao_impoe_rotacao(self):
        resultado = RENDERIZADOR.video_arguments(['video.mp4'])
        self.assertFalse(any(argumento.startswith('--video-rotate=') for argumento in resultado))
        self.assertIn('--auto-window-resize=no', resultado)
        self.assertIn('--keepaspect-window=no', resultado)


if __name__ == '__main__':
    unittest.main()
