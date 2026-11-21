"""Testa a geração da minuta em PDF, sem modelo e sem chave de API.

Monta uma instrução de exemplo (o DIA-2026-0106, urgente, com autorização superior) com os
caracteres que mais dão problema em PDF (travessão, aspas curvas, "º", "§", acentos) e confere:

[1] o PDF é gerado com a fonte do sistema e grava resultados/minuta_exemplo.pdf;
[2] o PDF também é gerado sem nenhuma fonte instalada (Helvetica de reserva), sem erro;
[3] o logo da SEMA é encontrado em assets/logo_sema.png.

Uso: python testar_minuta_pdf.py | tee resultados/teste_minuta_pdf.txt
"""
import sys
from datetime import datetime
from pathlib import Path

import minuta_pdf
from contrato import CRITERIOS, Instrucao, Verificacao
from dados import PEDIDOS

falhas: list[str] = []


def conferir(condicao: bool, descricao: str) -> None:
    print(f"  [{'ok' if condicao else 'FALHOU'}] {descricao}")
    if not condicao:
        falhas.append(descricao)


instrucao = Instrucao(
    numero_pedido="DIA-2026-0106", matricula="204775", quantidade_diarias=4.5, valor_total=1260.0,
    verificacoes=[Verificacao(criterio=c, situacao="atende", detalhe="conforme a ferramenta")
                  for c in CRITERIOS],
    recomendacao="apto_para_autorizacao", exige_autorizacao_superior=True, pendencias=[],
    alertas=["O pedido depende de autorização escrita do Secretário Adjunto."],
    minuta_despacho=(
        "Ao Ordenador de Despesa,\n\nTrata-se do pedido de diárias nº DIA-2026-0106, formulado "
        "por Diego Almeida Pires — Fiscal Ambiental —, para deslocamento a Poconé/MT, no período "
        "de 10/10/2026 a 14/10/2026, para “combate a incêndio florestal em curso”.\n\n"
        "Foram calculadas 4,5 diárias, no valor total de R$ 1.260,00. Embora a antecedência seja "
        "de 1 dia, a situação é emergencial (art. 5º, § 1º), e a concessão depende de "
        "autorização expressa e escrita do Secretário Adjunto (art. 5º, § 2º).\n\n"
        "Submete-se o pedido à decisão do ordenador de despesa."))
agora = datetime.now()
destino = Path(__file__).parent / "resultados" / "minuta_exemplo.pdf"

print("[1] Com a fonte do sistema")
pdf = minuta_pdf.gerar_minuta_pdf(PEDIDOS["DIA-2026-0106"], instrucao, instrucao.minuta_despacho,
                                  "Encaminhar ao ordenador: apto para autorização", agora)
destino.parent.mkdir(exist_ok=True)
destino.write_bytes(pdf)
conferir(pdf.startswith(b"%PDF"), f"PDF gerado ({len(pdf):,} bytes) e gravado em resultados/{destino.name}")

print("[2] Sem nenhuma fonte instalada (Helvetica de reserva)")
fontes_originais = minuta_pdf.FONTES
minuta_pdf.FONTES = []
try:
    reserva = minuta_pdf.gerar_minuta_pdf(PEDIDOS["DIA-2026-0106"], instrucao,
                                          instrucao.minuta_despacho, "Encaminhar ao ordenador",
                                          agora, motivo="Conferir a autorização no processo.")
    conferir(reserva.startswith(b"%PDF"), f"PDF gerado com a Helvetica ({len(reserva):,} bytes)")
except Exception as erro:
    conferir(False, f"falhou sem fonte instalada: {type(erro).__name__}: {erro}")
finally:
    minuta_pdf.FONTES = fontes_originais

print("[3] Logo")
conferir(minuta_pdf.LOGO.exists(), f"logo encontrado em {minuta_pdf.LOGO.relative_to(Path(__file__).parent)}")

print(f"\nResultado: {'todas as conferências passaram' if not falhas else f'{len(falhas)} falha(s)'}")
for falha in falhas:
    print(f"  - {falha}")
sys.exit(1 if falhas else 0)
