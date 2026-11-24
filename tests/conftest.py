"""Preparacao comum dos testes.

Todo teste roda contra um SQLite temporario e descartavel. Nenhum teste toca
a internet nem o banco de verdade em data/radar.db.
"""
import atexit
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from radar import config, db

# Copia PMSC: o .env aponta RADAR_CONFIG_DIR para pmsc/config, e o config.py o
# carrega no import. Os testes leem o cronograma REAL da raiz (datas da Policia
# Penal) - inclusive em fixture de modulo, que roda antes de qualquer
# monkeypatch -, entao a troca e feita aqui, uma vez, antes de tudo.
os.environ["RADAR_CONFIG_DIR"] = str(config.RAIZ / "config")

# Copia PRF (Etapa 1, decisao PRF-9): o data/conteudos.json de verdade virou a
# arvore do edital da PRF, e o cronograma da raiz aponta para nos da arvore
# antiga - o cronograma confere isso ao ler. Os testes leem entao um ESPELHO do
# data/, com a arvore antiga fixa em tests/fixtures/conteudos_da_raiz.json:
# nenhum teste depende da arvore que o radar de verdade usa (regra 6), e o que
# um teste gravar no data/ cai no espelho, que some no fim.
_ESPELHO_DO_DATA = Path(tempfile.mkdtemp(prefix="radar-testes-data-"))
atexit.register(shutil.rmtree, _ESPELHO_DO_DATA, ignore_errors=True)
for _arquivo in (config.RAIZ / "data").glob("*.json"):
    shutil.copy2(_arquivo, _ESPELHO_DO_DATA / _arquivo.name)
shutil.copy2(Path(__file__).parent / "fixtures" / "conteudos_da_raiz.json",
             _ESPELHO_DO_DATA / "conteudos.json")
os.environ["RADAR_DATA_DIR"] = str(_ESPELHO_DO_DATA)


@pytest.fixture
def banco_temporario(tmp_path, monkeypatch):
    """Aponta o radar para um banco novo, vazio, dentro de tmp_path."""
    monkeypatch.setenv("RADAR_DATABASE_URL", f"sqlite:///{tmp_path / 'teste.db'}")
    monkeypatch.setenv("RADAR_DATA_DIR", str(tmp_path))
    db.resetar_engine()          # esquece a conexao anterior
    db.criar_tabelas()
    yield
    db.resetar_engine()          # e nao deixa vazar para o proximo teste
