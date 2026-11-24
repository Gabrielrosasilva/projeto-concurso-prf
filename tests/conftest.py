"""Preparacao comum dos testes.

Todo teste roda contra um SQLite temporario e descartavel. Nenhum teste toca
a internet nem o banco de verdade em data/radar.db.
"""
import os

import pytest

from radar import config, db

# Copia PMSC: o .env aponta RADAR_CONFIG_DIR para pmsc/config, e o config.py o
# carrega no import. Os testes leem o cronograma REAL da raiz (datas da Policia
# Penal) - inclusive em fixture de modulo, que roda antes de qualquer
# monkeypatch -, entao a troca e feita aqui, uma vez, antes de tudo.
os.environ["RADAR_CONFIG_DIR"] = str(config.RAIZ / "config")


@pytest.fixture
def banco_temporario(tmp_path, monkeypatch):
    """Aponta o radar para um banco novo, vazio, dentro de tmp_path."""
    monkeypatch.setenv("RADAR_DATABASE_URL", f"sqlite:///{tmp_path / 'teste.db'}")
    monkeypatch.setenv("RADAR_DATA_DIR", str(tmp_path))
    db.resetar_engine()          # esquece a conexao anterior
    db.criar_tabelas()
    yield
    db.resetar_engine()          # e nao deixa vazar para o proximo teste
