"""Progresso por etapa, com resultado persistente e motivo de falhas."""
import os
import shutil
import subprocess
import sys


class Progress:
    def __init__(self, cor='auto', inicio=0, fim=100, fluxo=None):
        self.fluxo = fluxo if fluxo is not None else sys.stdout
        self.interativo = bool(getattr(self.fluxo, 'isatty', lambda: False)()) and os.environ.get('TERM') != 'dumb'
        self.cor = cor == 'always' or (cor == 'auto' and self.interativo and 'NO_COLOR' not in os.environ)
        self.inicio, self.fim = inicio, fim
        self.porcentagem = inicio
        self.etapa = None

    def _write(self, texto, codigo, finalizar=False):
        prefixo, restaurar = (f'\033[{codigo}m', '\033[0m') if self.cor else ('', '')
        if self.interativo:
            largura = max(1, shutil.get_terminal_size((80, 24)).columns - 1)
            texto = texto if len(texto) <= largura else texto[:max(0, largura - 1)] + '…'
        print(('\r\033[2K' if self.interativo else '') + prefixo + texto + restaurar,
              end='\n' if finalizar or not self.interativo else '', file=self.fluxo, flush=True)

    def complete(self, mensagem=None):
        if self.etapa is None:
            return
        resultado = mensagem or ('Instalado com sucesso!' if self.etapa.startswith('Instalando') else 'Concluído!')
        descricao = self.etapa.rstrip('.… ')
        if self.interativo:
            espaco = max(1, shutil.get_terminal_size((80, 24)).columns - len(resultado) - 6)
            if len(descricao) > espaco:
                descricao = descricao[:max(0, espaco - 1)] + '…'
        self._write(f'✓ {descricao} — {resultado}', '32', finalizar=True)
        self.etapa = None

    def update(self, porcentagem, mensagem):
        # A new stage is announced only after the preceding operation returns.
        if self.etapa is not None and self.etapa != mensagem:
            self.complete()
        self.porcentagem = max(self.porcentagem, round(self.inicio + (self.fim - self.inicio) * porcentagem / 100))
        if self.porcentagem >= 100:
            self._write(mensagem, '32', finalizar=True)
            self.etapa = None
            return
        self.etapa = mensagem
        codigo = '31' if self.porcentagem < 50 else '38;5;208' if self.porcentagem < 80 else '32'
        preenchido = self.porcentagem // 5
        self._write(f'[{"#" * preenchido}{"-" * (20 - preenchido)}] {self.porcentagem:3d}% {mensagem}', codigo)

    def error(self, erro):
        etapa = self.etapa or 'Instalação'
        self._write(f'✗ {etapa.rstrip(".… ")} — Falhou!', '31', finalizar=True)
        # Do not truncate the reason: command diagnostics can span several lines.
        motivo = str(erro)
        if isinstance(erro, subprocess.CalledProcessError):
            detalhes = erro.stderr or erro.stdout
            if isinstance(detalhes, bytes):
                detalhes = detalhes.decode(errors='replace')
            motivo = f'Comando {erro.cmd!r} terminou com código {erro.returncode}.'
            if detalhes:
                motivo += '\n' + detalhes.strip()
        prefixo, restaurar = ('\033[31m', '\033[0m') if self.cor else ('', '')
        print(f'{prefixo}Motivo: {motivo}{restaurar}', file=self.fluxo, flush=True)
        self.etapa = None
