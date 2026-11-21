"""Testa a rotina de eliminação com as duas servidoras que passaram por diligência.

Monta um banco com a configuração que mais guarda (histórico + memórias do usuário) e três
titulares:

- Beatriz Moraes Cunha (206689): DIA-2026-0111 e a complementação, na própria matrícula;
- Carla Regina Souza (207418): DIA-2026-0112 e a complementação; o pedido foi protocolado com a
  matrícula 207481, de outro servidor, e a sessão fica gravada sob esse identificador;
- Heitor Vasconcelos Lima (200941): DIA-2026-0104, testemunha. Os dados dele não podem ser
  apagados, e o CPF e a conta que ele colou na justificativa não podem estar no banco.

Depois elimina Beatriz e Carla e confere o banco tabela por tabela.

Custo: cerca de US$ 0,03 (cinco execuções e a extração de memórias).
Uso: python testar_eliminacao.py | tee resultados/teste_eliminacao.txt
"""
import shutil
import sys
from pathlib import Path

from agente import construir_agente, instruir
from dados import COMPLEMENTACOES, PEDIDOS
from eliminacao import eliminar_titular, memorias, mostrar, ocorrencias, sessoes, tabelas

BANCO = Path(__file__).parent / "bancos" / "eliminacao.db"
falhas: list[str] = []


def conferir(condicao: bool, descricao: str) -> None:
    print(f"  [{'ok' if condicao else 'FALHOU'}] {descricao}")
    if not condicao:
        falhas.append(descricao)


def inventario(titulo: str) -> None:
    print(f"\n{titulo}")
    print(f"  tabelas: {tabelas(BANCO)}")
    for s in sessoes(BANCO):
        print(f"  sessão {s['session_id']}: user_id {s['user_id']}, {s['execucoes']} execução(ões)")
    for m in memorias(BANCO):
        print(f"  memória (user_id {m['user_id']}): {m['memoria']}")


if __name__ == "__main__":
    if BANCO.exists():
        BANCO.unlink()
    BANCO.parent.mkdir(exist_ok=True)

    print("[1] Montando o banco: 0104 (testemunha), 0111 e 0112 com as complementações")
    agente = construir_agente(memoria="historico_e_usuario", banco=BANCO)
    for numero in ("DIA-2026-0104", "DIA-2026-0111", "DIA-2026-0112"):
        resultado = instruir(PEDIDOS[numero], agente=agente)
        print(f"  {numero}: {resultado.situacao}")
        if numero in COMPLEMENTACOES:
            resultado = instruir(PEDIDOS[numero], COMPLEMENTACOES[numero], agente=agente)
            print(f"  {numero} (complementação): {resultado.situacao}")
    inventario("[2] O que o agente guardou")

    print("\n[3] O CPF e a conta do DIA-2026-0104 chegaram ao banco?")
    vazou = ocorrencias(BANCO, ["052.318.947-20", "98765-4", "1234-5"])
    conferir(not vazou, f"CPF e dados bancários ausentes do banco {vazou or ''}")

    print("\n[4] Matrícula da Beatriz (206689) com o nome da Carla: a eliminação é recusada?")
    try:
        eliminar_titular("206689", "Carla Regina Souza", BANCO)
        conferir(False, "a matrícula de outra pessoa com outro nome deveria ser recusada")
    except ValueError as erro:
        conferir(True, f"recusada: {erro}")
    conferir(any(s["session_id"] == "DIA-2026-0111" for s in sessoes(BANCO)),
             "os dados da Beatriz continuam no banco")

    print("\n[5] Eliminação de Beatriz Moraes Cunha (matrícula 206689)")
    beatriz = eliminar_titular("206689", "Beatriz Moraes Cunha", BANCO)
    mostrar(beatriz)
    conferir(bool(beatriz.antes), "antes da eliminação, os dados dela estavam no banco")
    conferir("DIA-2026-0111" in beatriz.sessoes_apagadas, "a sessão DIA-2026-0111 foi achada pelo user_id")
    conferir(beatriz.nada_restou, "depois da eliminação, nada restou dela no banco")

    print("\n[6] Eliminação de Carla Regina Souza (matrícula 207418)")
    print("  primeiro, só pelo user_id da titular:")
    carla = eliminar_titular("207418", "Carla Regina Souza", BANCO)
    mostrar(carla)
    conferir(not carla.sessoes_apagadas,
             "a busca pelo user_id 207418 não acha a sessão DIA-2026-0112, gravada sob 207481")
    conferir(any(e["id"] == "DIA-2026-0112" for e in carla.encontradas_na_varredura),
             "a conferência tabela por tabela acha a sessão pelo nome e pela matrícula")
    conferir(not carla.nada_restou, "sem a varredura, os dados dela teriam ficado no banco")
    print("\n  depois, confirmando a exclusão do que a varredura encontrou:")
    carla = eliminar_titular("207418", "Carla Regina Souza", BANCO, apagar_encontradas=True)
    mostrar(carla)
    conferir(carla.nada_restou, "depois da eliminação confirmada, nada restou dela no banco")
    conferir(not ocorrencias(BANCO, ["207481"]),
             "a matrícula 207481, digitada por engano, também saiu do banco")

    print("\n[7] A testemunha continua intacta?")
    heitor = ocorrencias(BANCO, ["200941", "Heitor Vasconcelos Lima"])
    conferir(bool(heitor), f"os dados de Heitor continuam no banco {heitor}")
    conferir(any(s["session_id"] == "DIA-2026-0104" for s in sessoes(BANCO)),
             "a sessão DIA-2026-0104 continua no banco")
    inventario("[8] O que restou no banco")

    print(f"\nResultado: {'todas as conferências passaram' if not falhas else f'{len(falhas)} falha(s)'}")
    for falha in falhas:
        print(f"  - {falha}")
    sys.exit(1 if falhas else 0)
