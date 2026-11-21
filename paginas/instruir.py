"""Página "Instruir pedido": instrução, conferência do servidor e complementação.

Fluxo: o servidor escolhe o pedido → o agente instrui, com o progresso visível → a tela mostra
a recomendação, as verificações com o fundamento, os alertas, as pendências e as consultas →
o servidor edita a minuta e registra o encaminhamento que decidiu → a página se atualiza e passa
a mostrar a decisão registrada e a minuta em PDF → na diligência, o servidor envia a
complementação na mesma sessão. Em erro ou recusa da barreira, só a mensagem padrão.
"""
from datetime import datetime

import streamlit as st

import interface as ui
from barreira import pedido_efetivo
from conferencias import ENCAMINHAMENTOS, registrar
from dados import COMPLEMENTACOES, PEDIDOS
from filtro_dados_pessoais import mascarar
from minuta_pdf import gerar_minuta_pdf

ui.cabecalho("Instruir pedido de diárias",
             "O agente prepara a instrução, o servidor confere e o ordenador decide.")

numero = st.selectbox(
    "Pedido protocolado", list(PEDIDOS),
    format_func=lambda n: f"{n} · {PEDIDOS[n]['nome']} · "
                          f"{PEDIDOS[n]['destino_municipio']}/{PEDIDOS[n]['destino_uf']}")
pedido = PEDIDOS[numero]
ui.cartao_pedido(pedido, mascarar(pedido["justificativa"]))

with st.form("form_instruir"):
    st.caption("Instruir de novo um pedido abre uma sessão nova e descarta a anterior.")
    instruir_agora = st.form_submit_button("Instruir pedido", type="primary",
                                           icon=":material/play_arrow:")
if instruir_agora:
    ui.agente_em_cache().delete_session(session_id=numero)
    st.session_state["atual"] = {"numero": numero, "turno": "pedido", "registrado": False,
                                 "complementacao": None,
                                 "resultado": ui.executar_com_progresso(pedido)}
    st.rerun()

atual = st.session_state.get("atual")
if atual and atual["numero"] == numero:
    resultado = atual["resultado"]
    entregue = resultado.situacao == "entregue"
    if atual["turno"] == "complementacao":
        st.info("Instrução refeita depois da complementação, na mesma sessão do pedido.",
                icon=":material/update:")
    ui.mostrar_resultado(resultado)

    # ---------------------------------------------------------------- conferência
    st.markdown("#### Conferência do servidor")
    if atual["registrado"]:
        # Estado final: a decisão está gravada; o formulário dá lugar ao resumo e ao PDF.
        registro = atual["registro"]
        quando = datetime.fromisoformat(registro["registrado_em"])
        texto = (f"**Conferência registrada** em {quando:%d/%m/%Y} às {quando:%H:%M}. "
                 f"Decisão do servidor: **{ENCAMINHAMENTOS[registro['encaminhamento']]}**.")
        if registro["divergiu"]:
            texto += f"  \nDivergiu da sugestão do agente. Motivo: {registro['motivo']}"
        st.success(texto, icon=":material/task_alt:")
        if atual.get("pdf"):
            st.download_button("Baixar a minuta em PDF", atual["pdf"],
                               file_name=f"{numero}-minuta-conferida.pdf",
                               mime="application/pdf", type="primary",
                               icon=":material/picture_as_pdf:")
            with st.expander("Texto da minuta conferida"):
                st.text_area("Minuta conferida", atual["minuta_final"], height=240,
                             disabled=True, label_visibility="collapsed")
    else:
        sugestao = resultado.instrucao.recomendacao if entregue else "analise_manual"
        st.caption(f"Sugestão do agente: **{ENCAMINHAMENTOS[sugestao]}**. O encaminhamento "
                   "começa em branco para que a decisão seja sempre do servidor.")
        with st.form(f"form_registro_{numero}_{atual['turno']}"):
            minuta_original = resultado.instrucao.minuta_despacho if entregue else ""
            minuta = (st.text_area("Minuta do despacho (edite antes de registrar)",
                                   value=minuta_original, height=300) if entregue else "")
            encaminhamento = st.selectbox("Encaminhamento decidido pelo servidor",
                                          list(ENCAMINHAMENTOS), index=None,
                                          format_func=ENCAMINHAMENTOS.get,
                                          placeholder="Escolha o encaminhamento")
            motivo = st.text_area("Motivo, obrigatório quando o encaminhamento difere da "
                                  "sugestão (não escreva dados pessoais)", height=90)
            registrar_agora = st.form_submit_button("Registrar conferência", type="primary",
                                                    icon=":material/how_to_reg:")
        if registrar_agora:
            if encaminhamento is None:
                ui.avisar("Escolha o encaminhamento antes de registrar.", "erro")
                st.error("Escolha o encaminhamento antes de registrar.", icon=":material/error:")
            else:
                try:
                    registro = registrar(numero, atual["turno"], resultado.situacao,
                                         resultado.instrucao.recomendacao if entregue else None,
                                         encaminhamento, motivo,
                                         minuta_editada=minuta.strip() != minuta_original.strip(),
                                         medidas=resultado.medidas)
                except ValueError as erro:
                    ui.avisar("Conferência não registrada. Veja o motivo na página.", "erro")
                    st.error(f"Não registrado: {erro}.", icon=":material/error:")
                else:
                    pdf = None
                    if entregue:
                        pdf = gerar_minuta_pdf(
                            pedido_efetivo(pedido, atual.get("complementacao")),
                            resultado.instrucao, minuta, ENCAMINHAMENTOS[encaminhamento],
                            datetime.fromisoformat(registro["registrado_em"]), motivo)
                    atual.update(registrado=True, registro=registro, minuta_final=minuta, pdf=pdf)
                    ui.avisar_depois(f"Conferência registrada: {ENCAMINHAMENTOS[encaminhamento]}.")
                    st.rerun()

    # ---------------------------------------------------------------- complementação
    if entregue and resultado.instrucao.recomendacao == "diligencia" and atual["turno"] == "pedido":
        st.markdown("#### Complementação do pedido em diligência")
        st.caption("A resposta do solicitante é enviada na mesma sessão do pedido: o agente "
                   "recupera o caso pelo histórico e refaz a instrução desde a primeira consulta.")
        recebida = COMPLEMENTACOES.get(numero, {})
        with st.form(f"form_complementacao_{numero}"):
            texto = st.text_area("Resposta do solicitante", value=recebida.get("texto", ""),
                                 height=100)
            enviar = st.form_submit_button("Enviar complementação na mesma sessão",
                                           type="primary", icon=":material/send:")
        if enviar and not texto.strip():
            ui.avisar("Escreva a resposta do solicitante antes de enviar.", "erro")
        elif enviar:
            complementacao = {"numero": numero, "data": recebida.get("data", ""),
                              "texto": texto.strip()}
            st.session_state["atual"] = {
                "numero": numero, "turno": "complementacao", "registrado": False,
                "complementacao": complementacao,
                "resultado": ui.executar_com_progresso(pedido, complementacao)}
            st.rerun()

ui.rodape()
