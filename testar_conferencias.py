"""Testa o registro da conferência e o prazo de retenção, sem modelo e sem chave de API.

[1] O registro grava a decisão ao lado da sugestão e exige o motivo quando divergem.
[2] Os indicadores (total, discordâncias, taxa, instruções que não chegaram à tela) batem com a
    conta feita à mão, e o registro não guarda nome nem matrícula.
[3] O expurgo apaga só as sessões cujo prazo venceu: 30 dias depois do último registro do
    conferente, ou da última execução quando não há registro.

Usa bancos de teste próprios em bancos/, apagados no início.
Uso: python testar_conferencias.py | tee resultados/teste_conferencias.txt
"""
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from agno.db.sqlite import SqliteDb
from agno.session.agent import AgentSession

from conferencias import exportar_csv, indicadores, listar, registrar
from eliminacao import elegiveis_ao_expurgo, expurgar, sessoes

PASTA = Path(__file__).parent / "bancos"
REGISTRO = PASTA / "teste_conferencias.db"
AGENTE = PASTA / "teste_expurgo.db"
falhas: list[str] = []


def conferir(condicao: bool, descricao: str) -> None:
    print(f"  [{'ok' if condicao else 'FALHOU'}] {descricao}")
    if not condicao:
        falhas.append(descricao)


for arquivo in (REGISTRO, AGENTE):
    if arquivo.exists():
        arquivo.unlink()
PASTA.mkdir(exist_ok=True)

print("[1] Registro da conferência\n")
registrar("DIA-2026-0101", "pedido", "entregue", "apto_para_autorizacao",
          "apto_para_autorizacao", banco=REGISTRO)
conferir(True, "0101: servidor concordou com o agente (apto); motivo dispensado")
registrar("DIA-2026-0105", "pedido", "entregue", "nao_recomendado", "diligencia",
          motivo="Solicitar à servidora a comprovação da data da reunião.", minuta_editada=True,
          banco=REGISTRO)
conferir(True, "0105: servidor divergiu (diligência em vez de não recomendado), com motivo")
try:
    registrar("DIA-2026-0108", "pedido", "entregue", "nao_recomendado",
              "apto_para_autorizacao", banco=REGISTRO)
    conferir(False, "0108: divergência sem motivo deveria ser recusada")
except ValueError as erro:
    conferir(True, f"0108: divergência sem motivo recusada ({erro})")
registrar("DIA-2026-0107", "pedido", "erro", None, "analise_manual", banco=REGISTRO)
conferir(True, "0107: execução com erro, devolvida à análise manual (sem sugestão do agente)")

print("\n[2] Indicadores e minimização\n")
numeros = indicadores(REGISTRO)
print(f"  {numeros}")
conferir(numeros["total"] == 3, "3 conferências registradas (a recusada por falta de motivo não conta)")
conferir(numeros["divergencias"] == 1, "1 discordância (0105)")
conferir(abs(numeros["taxa_divergencia"] - 1 / 3) < 1e-9, "taxa de discordância = 1/3")
conferir(numeros["sem_instrucao"] == 1, "1 instrução não chegou ao conferente (0107)")
with sqlite3.connect(REGISTRO) as conexao:
    colunas = [c[1] for c in conexao.execute("PRAGMA table_info(conferencias)")]
conferir(not {"nome", "matricula", "minuta"} & set(colunas),
         f"o registro não tem colunas de nome, matrícula ou minuta: {colunas}")
csv = exportar_csv(PASTA / "teste_conferencias.csv", REGISTRO)
conferir(len(csv.read_text(encoding="utf-8").splitlines()) == 4, "CSV exportado com cabeçalho + 3 linhas")
csv.unlink()   # o CSV de teste não fica no repositório

print("\n[3] Prazo de retenção (30 dias)\n")
# Três sessões gravadas agora no banco do agente. O "agora" da verificação é daqui a 35 dias:
#   A: registro do conferente hoje            → 35 dias depois → vence
#   B: registro do conferente daqui a 30 dias → 5 dias depois  → fica
#   C: sem registro; última execução hoje     → 35 dias depois → vence
db = SqliteDb(db_file=str(AGENTE))
for numero, matricula in (("DIA-TESTE-A", "100001"), ("DIA-TESTE-B", "100002"), ("DIA-TESTE-C", "100003")):
    db.upsert_session(AgentSession(session_id=numero, agent_id="teste", user_id=matricula,
                                   created_at=int(time.time())))
hoje = datetime.now()
registrar("DIA-TESTE-A", "pedido", "entregue", "apto_para_autorizacao", "apto_para_autorizacao",
          banco=REGISTRO, agora=hoje)
registrar("DIA-TESTE-B", "pedido", "entregue", "diligencia", "diligencia",
          banco=REGISTRO, agora=hoje + timedelta(days=30))
daqui_35 = hoje + timedelta(days=35)
previa = elegiveis_ao_expurgo(banco=AGENTE, banco_conferencias=REGISTRO, agora=daqui_35)
for sessao in previa:
    print(f"  elegível: {sessao['session_id']} · {sessao['origem']} em {sessao['referencia']}")
conferir({s["session_id"] for s in previa} == {"DIA-TESTE-A", "DIA-TESTE-C"},
         "elegíveis: A (registro há 35 dias) e C (sem registro, execução há 35 dias)")
conferir(not elegiveis_ao_expurgo(banco=AGENTE, banco_conferencias=REGISTRO, agora=hoje),
         "hoje, nenhuma sessão está vencida")
expurgar(banco=AGENTE, banco_conferencias=REGISTRO, agora=daqui_35)
restantes = {s["session_id"] for s in sessoes(AGENTE)}
conferir(restantes == {"DIA-TESTE-B"}, f"depois do expurgo, só resta B: {restantes}")
conferir(len(listar(REGISTRO)) == 5, "o registro das conferências não é expurgado")

print(f"\nResultado: {'todas as conferências passaram' if not falhas else f'{len(falhas)} falha(s)'}")
for falha in falhas:
    print(f"  - {falha}")
sys.exit(1 if falhas else 0)
