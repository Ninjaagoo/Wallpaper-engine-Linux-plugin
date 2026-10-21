"""Progresso por etapas concluídas, compartilhado pelos instaladores."""
import os
import sys


class Progress:
    def __init__(self, cor='auto', inicio=0, fim=100, fluxo=None):
        self.fluxo = fluxo if fluxo is not None else sys.stdout
        self.cor = cor == 'always' or (cor == 'auto' and self.fluxo.isatty()
                                         and 'NO_COLOR' not in os.environ
                                         and os.environ.get('TERM') != 'dumb')
        self.inicio, self.fim = inicio, fim
        self.porcentagem = inicio

    def update(self, porcentagem, mensagem):
        self.porcentagem = max(self.porcentagem, round(self.inicio + (self.fim - self.inicio) * porcentagem / 100))
        codigo = '31' if self.porcentagem < 50 else '38;5;208' if self.porcentagem < 80 else '32'
        prefixo, restaurar_cor = (f'\033[{codigo}m', '\033[0m') if self.cor else ('', '')
        preenchido = self.porcentagem // 5
        print(f'{prefixo}[{"#" * preenchido}{"-" * (20 - preenchido)}] {self.porcentagem:3d}%{restaurar_cor} {mensagem}',
              file=self.fluxo, flush=True)

    def error(self, mensagem):
        prefixo, restaurar_cor = ('\033[31m', '\033[0m') if self.cor else ('', '')
        print(f'{prefixo}ERRO ({self.porcentagem}%): {mensagem}{restaurar_cor}', file=self.fluxo, flush=True)
