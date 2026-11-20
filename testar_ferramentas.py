"""Testa as ferramentas sem agente e sem chave de API.

Um erro dentro de uma ferramenta aparece depois como resposta estranha do agente, difícil de
localizar (Aula 06, Seção 3.2). Por isso as contas são conferidas aqui, antes de o modelo
entrar, em três partes:

[1] os casos pedidos no enunciado: a matrícula trocada do DIA-2026-0112, a prestação vencida
    do DIA-2026-0108, a meia diária do DIA-2026-0103 e o saldo do DIA-2026-0110;
[2] os 12 pedidos e as 2 complementações, com as ferramentas encadeadas como o agente deve
    encadeá-las, conferidos contra o gabarito.json;
[3] a minimização: nenhuma saída de ferramenta, em todo o teste, contém CPF ou e-mail.

Uso: python testar_ferramentas.py | tee resultados/teste_ferramentas.txt
O script termina com código de saída 1 se alguma conferência falhar.
"""
import json
import re
import sys
from pathlib import Path

from dados import COMPLEMENTACOES, PEDIDOS
from ferramentas import (FERRAMENTAS, calcular_diarias, consultar_historico_diarias,
                         consultar_saldo_diarias, consultar_servidor)

GABARITO = json.loads((Path(__file__).parent / "exemplos" / "gabarito.json")
                      .read_text(encoding="utf-8"))

# A urgência é julgamento sobre o texto da justificativa (art. 5º, § 1º) e, no sistema, cabe
# ao modelo. Aqui ela é declarada, como faz o gerar_dados.py, para isolar o teste das contas.
URGENCIA_DECLARADA = {"DIA-2026-0106"}

CPF = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")
EMAIL = re.compile(r"[\w.\-]+@[\w\-]+\.[\w.]+")
VEREDITO = re.compile(r"Critério (\w+): (ATENDE|NÃO ATENDE)\.")

saidas: list[str] = []      # tudo o que as ferramentas devolveram, para o teste [3]
falhas: list[str] = []


def chamar(ferramenta, *argumentos) -> str:
    """Executa a ferramenta, guarda a saída e a imprime como o modelo a receberia."""
    saida = ferramenta(*argumentos)
    saidas.append(saida)
    print(f"  {ferramenta.__name__}{argumentos}\n    → {saida}\n")
    return saida


def conferir(condicao: bool, descricao: str) -> None:
    print(f"  [{'ok' if condicao else 'FALHOU'}] {descricao}\n")
    if not condicao:
        falhas.append(descricao)


def nao_atendidos(*textos: str) -> set[str]:
    return {criterio for texto in textos for criterio, situacao in VEREDITO.findall(texto)
            if situacao == "NÃO ATENDE"}


def numero(padrao: str, texto: str) -> float:
    return float(re.search(padrao, texto).group(1))


# ------------------------------------------------------------------ [1] casos do enunciado

def casos_do_enunciado() -> None:
    print("[1] Casos pedidos no enunciado\n")

    print("DIA-2026-0112: matrícula de outro servidor, por troca de dois algarismos")
    saida = chamar(consultar_servidor, "207481", "Carla Regina Souza")
    conferir("Critério cadastro: NÃO ATENDE." in saida, "207481 não é da Carla: cadastro não atendido")
    conferir("Rafael" not in saida, "o nome do titular real (terceiro) não é revelado")
    saida = chamar(consultar_servidor, "207418", "Carla Regina Souza")
    conferir("Critério cadastro: ATENDE." in saida and "Grupo da diária: C" in saida,
             "com a matrícula corrigida (207418), cadastro atendido e grupo C")

    print("DIA-2026-0108: prestação de contas vencida")
    saida = chamar(consultar_historico_diarias, "203648", "2026-11-03", 3.5)
    conferir("venceu em 2026-09-25" in saida and "Critério prestacao_contas: NÃO ATENDE." in saida,
             "retorno em 2026-09-18 + 5 dias úteis = 2026-09-25, antes de 2026-10-09: vencida")
    print("DIA-2026-0102 (contraste): prestação pendente, mas ainda no prazo")
    saida = chamar(consultar_historico_diarias, "205882", "2026-11-09", 3.5)
    conferir("vai até 2026-10-13" in saida and "Critério prestacao_contas: ATENDE." in saida,
             "retorno em 2026-10-06 + 5 dias úteis = 2026-10-13, depois de 2026-10-09: no prazo")

    print("DIA-2026-0103: ida e volta no mesmo dia")
    saida = chamar(calcular_diarias, "B", "MT", "2026-10-07", "2026-11-05", "2026-11-05")
    conferir("Quantidade: 0.5 diárias" in saida and "Valor total: R$ 140.00" in saida,
             "sem pernoite: 0,5 diária × R$ 280,00 = R$ 140,00")

    print("DIA-2026-0110: viagem a outra UF com saldo insuficiente na unidade")
    saida = chamar(calcular_diarias, "B", "RO", "2026-10-02", "2026-11-10", "2026-11-14")
    conferir("Valor total: R$ 1800.00" in saida, "4,5 diárias × R$ 400,00 (outra UF) = R$ 1.800,00")
    saida = chamar(consultar_saldo_diarias, "CRH", 1800.0)
    conferir("Critério saldo_orcamentario: NÃO ATENDE." in saida,
             "saldo da CRH (R$ 640,00) menor que R$ 1.800,00")


# ------------------------------------------------------------------ [2] contra o gabarito

def instruir_com_ferramentas(pedido: dict) -> dict:
    """Encadeia as ferramentas na ordem do desenho e monta o resultado comparável ao gabarito.

    Faz, sem modelo, o caminho que o agente deve fazer; o único dado que não vem das
    ferramentas é a urgência, declarada em URGENCIA_DECLARADA.
    """
    servidor = consultar_servidor(pedido["matricula"], pedido["nome"])
    saidas.append(servidor)
    if "cadastro" in nao_atendidos(servidor):
        return {"recomendacao": "diligencia", "quantidade_diarias": None, "valor_total": None,
                "exige_autorizacao_superior": False, "criterios_nao_atendidos": ["cadastro"]}

    calculo = calcular_diarias(re.search(r"Grupo da diária: (\w)", servidor).group(1),
                               pedido["destino_uf"], pedido["data_pedido"],
                               pedido["data_partida"], pedido["data_retorno"] or "")
    saidas.append(calculo)
    if "dados_completos" in nao_atendidos(calculo):
        return {"recomendacao": "diligencia", "quantidade_diarias": None, "valor_total": None,
                "exige_autorizacao_superior": False, "criterios_nao_atendidos": ["dados_completos"]}

    quantidade = numero(r"Quantidade: (\d+\.\d) diárias", calculo)
    valor = numero(r"Valor total: R\$ (\d+\.\d{2})", calculo)
    historico = consultar_historico_diarias(pedido["matricula"], pedido["data_partida"], quantidade)
    saldo = consultar_saldo_diarias(re.search(r"Unidade de lotação: (\w+)", servidor).group(1), valor)
    saidas.extend([historico, saldo])

    criterios = nao_atendidos(calculo, historico, saldo)
    urgente = "antecedencia" in criterios and pedido["numero"] in URGENCIA_DECLARADA
    if urgente:
        criterios.discard("antecedencia")
    return {"recomendacao": "nao_recomendado" if criterios else "apto_para_autorizacao",
            "quantidade_diarias": quantidade, "valor_total": valor,
            "exige_autorizacao_superior": urgente and not criterios,
            "criterios_nao_atendidos": sorted(criterios)}


def complementado(numero: str) -> dict:
    """Aplica ao pedido a correção trazida pelo texto da complementação."""
    pedido = dict(PEDIDOS[numero])
    texto = COMPLEMENTACOES[numero]["texto"]
    if data := re.search(r"\d{4}-\d{2}-\d{2}", texto):
        pedido["data_retorno"] = data.group()
    if matricula := re.search(r"\b\d{6}\b", texto):
        pedido["matricula"] = matricula.group()
    return pedido


def contra_o_gabarito() -> None:
    print("[2] Ferramentas encadeadas, sem modelo, contra o gabarito.json\n")
    casos = [(n, PEDIDOS[n], GABARITO["pedidos"][n]) for n in PEDIDOS]
    casos += [(f"{n} (compl.)", complementado(n), GABARITO["complementacoes"][n])
              for n in COMPLEMENTACOES]
    campos = ("recomendacao", "quantidade_diarias", "valor_total", "exige_autorizacao_superior",
              "criterios_nao_atendidos")
    print(f"  {'caso':22} {'recomendação':24} {'qtd':>4} {'valor':>8}  {'não atendidos':28} resultado")
    certos = 0
    for rotulo, pedido, esperado in casos:
        obtido = instruir_com_ferramentas(pedido)
        divergentes = [c for c in campos if obtido[c] != (sorted(esperado[c])
                       if c == "criterios_nao_atendidos" else esperado[c])]
        certos += not divergentes
        qtd = "-" if obtido["quantidade_diarias"] is None else f"{obtido['quantidade_diarias']:.1f}"
        valor = "-" if obtido["valor_total"] is None else f"{obtido['valor_total']:.2f}"
        print(f"  {rotulo:22} {obtido['recomendacao']:24} {qtd:>4} {valor:>8}  "
              f"{', '.join(obtido['criterios_nao_atendidos']) or '-':28} "
              f"{'ok' if not divergentes else 'DIVERGE em ' + ', '.join(divergentes)}")
        if divergentes:
            falhas.append(f"{rotulo}: {divergentes}")
    print(f"\n  {certos} de {len(casos)} casos iguais ao gabarito\n")


# ------------------------------------------------------------------ execução

if __name__ == "__main__":
    print("Ferramentas, na ordem de consulta, e a primeira linha da docstring de cada uma:")
    for funcao in FERRAMENTAS:
        print(f"  {funcao.__name__:28} {funcao.__doc__.splitlines()[0]}")
    print()

    casos_do_enunciado()
    contra_o_gabarito()

    print("[3] Minimização: o que as ferramentas devolveram ao longo de todo o teste\n")
    conferir(not any(CPF.search(s) for s in saidas), f"nenhuma das {len(saidas)} saídas contém CPF")
    conferir(not any(EMAIL.search(s) for s in saidas), f"nenhuma das {len(saidas)} saídas contém e-mail")

    print(f"Resultado: {'todas as conferências passaram' if not falhas else f'{len(falhas)} falha(s)'}")
    for falha in falhas:
        print(f"  - {falha}")
    sys.exit(1 if falhas else 0)
