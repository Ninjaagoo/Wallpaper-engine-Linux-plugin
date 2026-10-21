"""Opções comuns às instalações por fonte e pelo pacote offline."""
from pathlib import Path


def add_install_arguments(analisador, pacote_offline=False):
    analisador.add_argument('--check', dest='verificar', action='store_true', help='Verificar sem instalar')
    analisador.add_argument('--desktop', dest='ambiente_grafico', choices=('auto', 'gnome', 'kde', 'xfce'), default='auto')
    analisador.add_argument('--steam-root', dest='raiz_steam', type=Path, help='Diretório Steam que contém steamapps')
    analisador.add_argument('--kde-plugin', dest='plugin_kde', action='store_true', help='Instalar addon Plasma 6 experimental')
    analisador.add_argument('--color', dest='cor', choices=('auto', 'always', 'never'), default='auto')
    analisador.add_argument('--startup', dest='inicio_automatico', choices=('yes', 'no', 'ask'), default='ask', help='Iniciar com a sessão (padrão: perguntar)')
    analisador.add_argument('--login-background', dest='fundo_login', action='store_true', help='Configurar o GDM com autenticação de administrador')
    if not pacote_offline:
        analisador.add_argument('--renderer', dest='renderizador', type=Path, help='Renderizador nativo executável')
        analisador.add_argument('--build-runtime', dest='compilar_ambiente', action='store_true', help='Compilar renderizador e dependências no contêiner')
