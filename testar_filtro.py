"""Testa o filtro de dados pessoais sem modelo e sem chave de API.

O filtro é aplicado ao texto exatamente como o agente o recebe (texto_do_pedido e
texto_da_complementacao), por meio do mesmo objeto RunInput que o Agno entrega ao guardrail.
A configuração está certa quando:

[1] o CPF e os dados bancários do DIA-2026-0104 são mascarados;
[2] nenhuma matrícula, data ou número de pedido é mascarado, em nenhum dos 12 pedidos e das 2
    complementações, e nada muda nos textos que não têm dado pessoal;
[3] formatos que o filtro deve cobrir além do acervo (CPF sem pontuação, e-mail) também são
    mascarados.

Uso: python testar_filtro.py | tee resultados/teste_filtro.txt
"""
import sys

from agno.run.agent import RunInput

from agente import texto_da_complementacao, texto_do_pedido
from dados import COMPLEMENTACOES, PEDIDOS
from filtro_dados_pessoais import filtro_dados_pessoais

FILTRO = filtro_dados_pessoais()
falhas: list[str] = []


def filtrar(texto: str) -> str:
    """Aplica o guardrail como o Agno o aplica antes da chamada ao modelo."""
    entrada = RunInput(input_content=texto)
    FILTRO.check(entrada)
    return entrada.input_content


def conferir(condicao: bool, descricao: str) -> None:
    print(f"  [{'ok' if condicao else 'FALHOU'}] {descricao}")
    if not condicao:
        falhas.append(descricao)


print("[1] DIA-2026-0104: CPF e conta bancária colados na justificativa\n")
pedido = PEDIDOS["DIA-2026-0104"]
filtrado = filtrar(texto_do_pedido(pedido))
print(f"  justificativa original : {pedido['justificativa']}")
print(f"  como o modelo a recebe : "
      f"{filtrado[filtrado.find('Representação'):filtrado.rfind(chr(34))]}\n")
conferir("052.318.947-20" not in filtrado, "o CPF 052.318.947-20 foi mascarado")
conferir("98765-4" not in filtrado, "a conta corrente 98765-4 foi mascarada")
conferir("1234-5" not in filtrado, "a agência 1234-5 foi mascarada")

print("\n[2] Matrículas, datas e números de pedido intactos nos 14 textos\n")
textos = [(n, p, texto_do_pedido(p)) for n, p in PEDIDOS.items()]
textos += [(f"{n} (compl.)", PEDIDOS[n], texto_da_complementacao(c))
           for n, c in COMPLEMENTACOES.items()]
for rotulo, pedido, texto in textos:
    filtrado = filtrar(texto)
    preservados = [pedido["numero"], pedido["matricula"], pedido["data_pedido"],
                   pedido["data_partida"], pedido["data_retorno"]]
    if "compl." in rotulo:
        preservados = [pedido["numero"], COMPLEMENTACOES[pedido["numero"]]["data"]]
    intactos = all(valor in filtrado for valor in preservados if valor and valor in texto)
    sem_mudanca = filtrado == texto
    if pedido["numero"] == "DIA-2026-0104" and "compl." not in rotulo:
        conferir(intactos, f"{rotulo}: número, matrícula e datas intactos (só o CPF e a conta mudaram)")
    else:
        conferir(intactos and sem_mudanca, f"{rotulo}: texto sem dado pessoal chegou sem alteração")

print("\n[3] Formatos além do acervo\n")
for exemplo, dado in [("Meu CPF é 05231894720, sem pontuação.", "05231894720"),
                      ("Contato: heitor.lima@sema.exemplo.gov.br", "heitor.lima@sema.exemplo.gov.br"),
                      ("Conta 0012345-6, agência 3412-X.", "0012345-6")]:
    filtrado = filtrar(exemplo)
    print(f"  {exemplo}  →  {filtrado}")
    conferir(dado not in filtrado, f"'{dado}' mascarado")

print(f"\nResultado: {'todas as conferências passaram' if not falhas else f'{len(falhas)} falha(s)'}")
for falha in falhas:
    print(f"  - {falha}")
sys.exit(1 if falhas else 0)
