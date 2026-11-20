"""Instrui um ou mais pedidos com o agente e mostra o que o conferente receberia.

Serve para acompanhar o agente caso a caso durante a construção. Para cada pedido, mostra:
o que o servidor veria (a instrução ou a mensagem padrão), o motivo técnico quando a instrução
é recusada (que nunca vai à tela do conferente), as consultas com os argumentos, o consumo e,
na última linha, o que o gabarito esperava, para conferência de quem desenvolve.

O gabarito é lido aqui, pela ferramenta de desenvolvimento, e nunca pelo agente.

Uso:
    python instruir_pedido.py DIA-2026-0101
    python instruir_pedido.py DIA-2026-0101 DIA-2026-0103 DIA-2026-0108
    python instruir_pedido.py --todos
    python instruir_pedido.py DIA-2026-0101 --paralelas          # chamadas paralelas ligadas
    python instruir_pedido.py DIA-2026-0101 --provocar-erro-api  # erro da API, de propósito
"""
import argparse
import json
from pathlib import Path

from agente import MENSAGEM_PADRAO, construir_agente, instruir
from dados import PEDIDOS

GABARITO = json.loads((Path(__file__).parent / "exemplos" / "gabarito.json")
                      .read_text(encoding="utf-8"))["pedidos"]


def mostrar(resultado) -> None:
    print("=" * 96)
    print(f"{resultado.numero_pedido} · situação: {resultado.situacao.upper()}")
    print("-" * 96)
    if resultado.situacao == "entregue":
        i = resultado.instrucao
        qtd = "-" if i.quantidade_diarias is None else f"{i.quantidade_diarias:.1f}"
        valor = "-" if i.valor_total is None else f"R$ {i.valor_total:.2f}"
        print(f"recomendação: {i.recomendacao} · quantidade: {qtd} · valor: {valor} · "
              f"autorização superior: {'SIM' if i.exige_autorizacao_superior else 'não'}")
        for v in i.verificacoes:
            print(f"  {v.criterio:20} {v.situacao:15} {v.detalhe[:58]}")
        for rotulo, itens in (("pendências", i.pendencias), ("alertas", i.alertas)):
            for item in itens:
                print(f"  {rotulo}: {item}")
        print(f"minuta: {i.minuta_despacho}")
    else:
        print(f"o conferente vê: {MENSAGEM_PADRAO}")
        print("motivo técnico (registrado, não exibido ao conferente):")
        for motivo in resultado.motivos:
            print(f"  - {motivo}")
    print("consultas:")
    for c in resultado.consultas:
        print(f"  {c.ferramenta}({', '.join(f'{k}={v!r}' for k, v in c.argumentos.items())})")
    m = resultado.medidas
    if "tokens_entrada" in m:
        print(f"consumo: {m['chamadas_ao_modelo']} chamadas ao modelo · entrada por chamada "
              f"{m['entrada_por_chamada']} · total {m['tokens_entrada']} entrada / "
              f"{m['tokens_saida']} saída · US$ {m['custo_usd']:.5f} · {m['segundos']} s")
    if "Para o depósito" in resultado.texto_enviado:
        print(f"texto recebido pelo modelo (trecho): "
              f"{resultado.texto_enviado[resultado.texto_enviado.find('Para o depósito'):][:110]}")
    g = GABARITO.get(resultado.numero_pedido)
    if g:
        print(f"gabarito: {g['recomendacao']} · quantidade {g['quantidade_diarias']} · valor "
              f"{g['valor_total']} · autorização superior {g['exige_autorizacao_superior']} · "
              f"não atendidos {g['criterios_nao_atendidos']}")


if __name__ == "__main__":
    argumentos = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    argumentos.add_argument("pedidos", nargs="*", help="números dos pedidos, como DIA-2026-0101")
    argumentos.add_argument("--todos", action="store_true", help="instrui os 12 pedidos")
    argumentos.add_argument("--paralelas", action="store_true", help="liga as chamadas paralelas")
    argumentos.add_argument("--provocar-erro-api", action="store_true",
                            help="monta o modelo sem reasoning_effort, que a API recusa")
    opcoes = argumentos.parse_args()

    numeros = list(PEDIDOS) if opcoes.todos else opcoes.pedidos
    desconhecidos = [n for n in numeros if n not in PEDIDOS]
    if not numeros or desconhecidos:
        argumentos.error(f"informe pedidos válidos; desconhecidos: {desconhecidos or 'nenhum informado'}")

    agente = construir_agente(paralelas=opcoes.paralelas, provocar_erro_api=opcoes.provocar_erro_api)
    custo = 0.0
    for numero in numeros:
        resultado = instruir(PEDIDOS[numero], agente=agente)
        mostrar(resultado)
        custo += resultado.medidas.get("custo_usd", 0.0)
    print("=" * 96)
    print(f"{len(numeros)} pedido(s) · custo total US$ {custo:.5f}")
