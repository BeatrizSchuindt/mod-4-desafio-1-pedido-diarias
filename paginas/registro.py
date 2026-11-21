"""Página "Registro das conferências": o que o servidor decidiu ao lado do que o agente sugeriu.

É daqui que sai a medida, com o uso, de quantas vezes o servidor discorda do agente. O registro
não guarda nome, matrícula nem minuta; só o número do pedido.
"""
from pathlib import Path

import streamlit as st

import interface as ui
from conferencias import ENCAMINHAMENTOS, exportar_csv, indicadores, listar

ui.cabecalho("Registro das conferências",
             "A decisão do servidor ao lado da sugestão do agente.")

numeros = indicadores()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Conferências registradas", numeros["total"], border=True)
c2.metric("Discordâncias do servidor", numeros["divergencias"],
          delta=f"{numeros['taxa_divergencia']:.0%} das conferências", delta_color="off",
          delta_arrow="off", border=True)
c3.metric("Devolvidas à análise manual", numeros["sem_instrucao"],
          help="Execuções com erro ou instruções recusadas pela barreira.", border=True)
c4.metric("Minutas editadas", numeros["minutas_editadas"], border=True)

registros = listar()
if not registros:
    st.info("Nenhuma conferência registrada ainda.", icon=":material/inbox:")
else:
    st.dataframe([{"Registrado em": r["registrado_em"].replace("T", " "),
                   "Pedido": r["numero_pedido"], "Turno": r["turno"],
                   "Instrução": r["situacao_instrucao"],
                   "Sugestão do agente": ENCAMINHAMENTOS[r["sugestao_agente"]],
                   "Decisão do servidor": ENCAMINHAMENTOS[r["encaminhamento"]],
                   "Divergiu": "sim" if r["divergiu"] else "não", "Motivo": r["motivo"],
                   "Minuta editada": "sim" if r["minuta_editada"] else "não"}
                  for r in registros], hide_index=True, width="stretch")
    destino = Path(ui.BASE) / "resultados" / "conferencias.csv"
    if st.button("Salvar em resultados/conferencias.csv", icon=":material/save:"):
        exportar_csv(destino)
        ui.avisar(f"Registro salvo em {destino.relative_to(ui.BASE)}.")
        st.success(f"Registro salvo em {destino.relative_to(ui.BASE)}.", icon=":material/task_alt:")

ui.rodape()
