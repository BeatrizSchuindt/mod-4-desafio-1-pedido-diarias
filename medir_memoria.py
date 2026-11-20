"""Mede o custo da memória com as duas complementações, em três configurações.

Os pedidos DIA-2026-0111 (data de retorno ausente) e DIA-2026-0112 (matrícula de outro
servidor) voltam em diligência. Cada um é instruído em dois turnos na mesma sessão: o pedido e,
depois, a complementação, que chega sozinha, sem repetir o pedido. Para cada configuração,
registra a entrada do primeiro turno, a do turno da complementação e se ela foi aplicada ao
pedido certo, conferindo o resultado com as complementações do gabarito.

A  sem memória: sem banco; a complementação chega sem o pedido;
B  histórico da sessão: SqliteDb + add_history_to_context, com teto (a configuração do sistema);
C  histórico + memórias do usuário: B com update_memory_on_run;
D  armadilha do 0112: B, mas a complementação é enviada com o user_id da matrícula corrigida
   (207418), e não com o da matrícula do pedido (207481), com que a sessão foi aberta.

Observação de custo: em C, o Agno faz chamadas extras ao modelo para extrair as memórias. A Aula
07 (Seção 3.1) observou que elas não apareciam nas métricas do turno; aqui isso é medido, e não
suposto: a coluna "fora" é a entrada total do turno menos a soma da entrada das chamadas do
agente. Se for maior que zero, a extração entrou na conta.

Cada execução começa com os bancos apagados. Custo: cerca de US$ 0,05.
Uso: python medir_memoria.py | tee resultados/memoria_custo_por_turno.txt
"""
import json
import shutil
from pathlib import Path

from agente import construir_agente, instruir
from barreira import pedido_efetivo
from dados import COMPLEMENTACOES, PEDIDOS
from eliminacao import memorias, sessoes, tabelas

BASE = Path(__file__).parent
PASTA_BANCOS = BASE / "bancos"
GABARITO = json.loads((BASE / "exemplos" / "gabarito.json").read_text(encoding="utf-8"))

CONFIGURACOES = [
    ("A", "sem memória", "nenhuma", None),
    ("B", "histórico da sessão", "historico", None),
    ("C", "histórico + memórias do usuário", "historico_e_usuario", None),
    ("D", "B com user_id da matrícula corrigida", "historico", "207418"),
]
CASOS = ["DIA-2026-0111", "DIA-2026-0112"]


def resumo(resultado) -> dict:
    instrucao = resultado.instrucao or resultado.instrucao_recusada
    m = resultado.medidas
    return {"situacao": resultado.situacao,
            "recomendacao": instrucao.recomendacao if instrucao else None,
            "matricula": instrucao.matricula if instrucao else None,
            "quantidade": instrucao.quantidade_diarias if instrucao else None,
            "valor": instrucao.valor_total if instrucao else None,
            "entrada_1a_chamada": (m.get("entrada_por_chamada") or [0])[0],
            "entrada_por_chamada": m.get("entrada_por_chamada", []),
            "entrada_total": m.get("tokens_entrada", 0),
            "entrada_fora_das_chamadas": (m.get("tokens_entrada", 0)
                                          - sum(m.get("entrada_por_chamada", []))),
            "saida_total": m.get("tokens_saida", 0),
            "chamadas": m.get("chamadas_ao_modelo", 0),
            "custo_usd": m.get("custo_usd", 0.0),
            "segundos": m.get("segundos", 0.0),
            "motivos": resultado.motivos}


def aplicada_ao_pedido_certo(numero: str, resultado) -> bool:
    """A complementação foi aplicada ao pedido certo e a instrução é a do gabarito?"""
    esperado = GABARITO["complementacoes"][numero]
    efetivo = pedido_efetivo(PEDIDOS[numero], COMPLEMENTACOES[numero])
    i = resultado.instrucao
    return bool(resultado.situacao == "entregue" and i.numero_pedido == numero
                and i.matricula == efetivo["matricula"]
                and i.recomendacao == esperado["recomendacao"]
                and abs((i.valor_total or 0) - esperado["valor_total"]) < 0.01)


def executar(letra, rotulo, memoria, user_id_complementacao) -> dict:
    banco = PASTA_BANCOS / f"memoria_{letra}.db"
    agente = construir_agente(memoria=memoria, banco=banco)
    casos = CASOS if letra != "D" else ["DIA-2026-0112"]
    linhas = []
    for numero in casos:
        pedido = PEDIDOS[numero]
        turno1 = instruir(pedido, agente=agente)
        turno2 = instruir(pedido, COMPLEMENTACOES[numero], agente=agente,
                          user_id=user_id_complementacao)
        linhas.append({"pedido": numero, "turno_pedido": resumo(turno1),
                       "turno_complementacao": resumo(turno2),
                       "aplicada_ao_pedido_certo": aplicada_ao_pedido_certo(numero, turno2)})
    return {"configuracao": letra, "rotulo": rotulo, "memoria": memoria,
            "user_id_na_complementacao": user_id_complementacao or "matrícula do pedido",
            "casos": linhas,
            "banco": {"tabelas": tabelas(banco), "sessoes": sessoes(banco),
                      "memorias": memorias(banco)}}


def imprimir(resultados: list[dict]) -> None:
    print(f"{'':3} {'pedido':14} | {'turno 1: pedido':^30} | {'turno 2: complementação':^38} | "
          f"{'aplicada':^9} | {'US$':>8}")
    print(f"{'':3} {'':14} | {'situação':10} {'1ª cham.':>9} {'total':>8} | "
          f"{'situação':10} {'1ª cham.':>9} {'total':>8} {'cham.':>6} | {'certo?':^9} | {'T1+T2':>8}")
    print("-" * 112)
    for r in resultados:
        for c in r["casos"]:
            t1, t2 = c["turno_pedido"], c["turno_complementacao"]
            print(f"{r['configuracao']:3} {c['pedido']:14} | {t1['situacao']:10} "
                  f"{t1['entrada_1a_chamada']:>9} {t1['entrada_total']:>8} | {t2['situacao']:10} "
                  f"{t2['entrada_1a_chamada']:>9} {t2['entrada_total']:>8} {t2['chamadas']:>6} | "
                  f"{'SIM' if c['aplicada_ao_pedido_certo'] else 'não':^9} | "
                  f"{t1['custo_usd'] + t2['custo_usd']:>8.5f}")
    print("\nLegenda: A sem memória · B histórico da sessão · C histórico + memórias do usuário · "
          "D = B com user_id da matrícula corrigida no turno 2")

    print("\nDetalhe por turno (entrada de cada chamada do agente; 'fora' = entrada total menos a")
    print("soma das chamadas, isto é, o que o Agno gastou fora do agente, como a extração de memórias)")
    for r in resultados:
        for c in r["casos"]:
            for rotulo, t in (("pedido", c["turno_pedido"]), ("complementação", c["turno_complementacao"])):
                print(f"  {r['configuracao']} {c['pedido']} {rotulo:15} chamadas {t['entrada_por_chamada']} · "
                      f"fora {t['entrada_fora_das_chamadas']} · {t['segundos']} s")
    print("\nO turno da complementação")
    for r in resultados:
        for c in r["casos"]:
            t2 = c["turno_complementacao"]
            print(f"  {r['configuracao']} {c['pedido']}: {t2['situacao']} · recomendação "
                  f"{t2['recomendacao']} · matrícula {t2['matricula']} · valor {t2['valor']}")
            for motivo in t2["motivos"][:3]:
                print(f"      motivo: {motivo}")

    print("\nO que ficou gravado em cada banco")
    for r in resultados:
        banco = r["banco"]
        print(f"  {r['configuracao']} · {r['rotulo']}")
        if not banco["tabelas"]:
            print("      nenhum banco (configuração sem memória)")
            continue
        print(f"      tabelas: {banco['tabelas']}")
        for s in banco["sessoes"]:
            print(f"      sessão {s['session_id']}: user_id {s['user_id']}, "
                  f"{s['execucoes']} execução(ões) gravada(s)")
        for m in banco["memorias"]:
            print(f"      memória do user_id {m['user_id']}: {m['memoria']}")


if __name__ == "__main__":
    if PASTA_BANCOS.exists():
        shutil.rmtree(PASTA_BANCOS)          # cada medição começa do zero
    resultados = []
    for configuracao in CONFIGURACOES:
        print(f"[{configuracao[0]} · {configuracao[1]}] executando...")
        resultados.append(executar(*configuracao))
    print()
    imprimir(resultados)
    destino = BASE / "resultados" / "memoria_custo_por_turno.json"
    destino.write_text(json.dumps(resultados, ensure_ascii=False, indent=2, default=str),
                       encoding="utf-8")
    custo = sum(c[t]["custo_usd"] for r in resultados for c in r["casos"]
                for t in ("turno_pedido", "turno_complementacao"))
    print(f"\nCusto total: US$ {custo:.5f} · resultados em resultados/{destino.name}")
