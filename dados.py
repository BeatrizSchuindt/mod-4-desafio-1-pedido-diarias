"""Leitura dos dados do órgão, uma única vez, a partir de exemplos/dados/.

O acervo é hipotético e foi gerado por exemplos/gerar_dados.py. Este módulo é a única porta
de entrada para os dados: as ferramentas, os testes e a aplicação importam daqui.

Minimização desde a leitura: o cadastro tem CPF e e-mail, que a instrução não usa. Os dois
campos são descartados aqui mesmo, de modo que nenhuma ferramenta consegue devolvê-los ao
modelo, nem por engano.

O gabarito.json não é lido por este módulo. Só o script de medição o abre, porque um agente
que alcança a resposta esperada não está sendo medido.
"""
import csv
import json
from datetime import date
from pathlib import Path

PASTA_DADOS = Path(__file__).parent / "exemplos" / "dados"

# Campos do cadastro funcional que a instrução usa. CPF e e-mail ficam de fora.
CAMPOS_DO_CADASTRO = ("matricula", "nome", "cargo", "grupo_diaria", "unidade", "municipio_sede")


def _ler_json(nome: str):
    return json.loads((PASTA_DADOS / nome).read_text(encoding="utf-8"))


def _ler_csv(nome: str) -> list[dict]:
    with open(PASTA_DADOS / nome, encoding="utf-8", newline="") as arquivo:
        return list(csv.DictReader(arquivo))


SERVIDORES = {
    linha["matricula"]: {campo: linha[campo] for campo in CAMPOS_DO_CADASTRO}
    for linha in _ler_csv("servidores.csv")
}

HISTORICO = [
    {**linha, "quantidade": float(linha["quantidade"]), "valor": float(linha["valor"])}
    for linha in _ler_csv("historico_diarias.csv")
]

UNIDADES = _ler_json("unidades.json")

_TABELA = _ler_json("tabela_diarias.json")
VALORES = _TABELA["valores"]                                  # R$ por grupo e classe de destino
DATA_DA_ANALISE = date.fromisoformat(_TABELA["data_da_analise"])   # fixa: 2026-10-09
ANTECEDENCIA_MINIMA = _TABELA["antecedencia_minima_dias"]      # dias corridos (art. 5º)
LIMITE_MENSAL = _TABELA["limite_mensal_diarias"]               # diárias por mês (art. 6º)
PRAZO_PRESTACAO = _TABELA["prazo_prestacao_dias_uteis"]        # dias úteis (art. 7º)

# Entradas do processo: o que chega protocolado. Lidas pelos testes, pela medição e pela
# aplicação, nunca pelas ferramentas.
PEDIDOS = {p["numero"]: p for p in _ler_json("pedidos.json")}
COMPLEMENTACOES = {c["numero"]: c for c in _ler_json("complementacoes.json")}
