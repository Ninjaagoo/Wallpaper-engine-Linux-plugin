#!/usr/bin/python3
"""Entrada interna do pacote extraído; delega ao instalador compartilhado."""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / 'app/wallpaper-linux'))

from installation.offline import main

if __name__ == '__main__':
    main(RAIZ)
