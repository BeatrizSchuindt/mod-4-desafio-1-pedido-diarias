"""Página "Sobre o sistema": o que o agente faz, o que não faz e como trata os dados."""
import streamlit as st

import interface as ui
from agente import MODELO, NUM_HISTORY_RUNS, TOOL_CALL_LIMIT
from eliminacao import PRAZO_RETENCAO_DIAS

ui.cabecalho("Sobre o sistema", "Como a instrução automática funciona e quais são os limites.")

c1, c2 = st.columns(2)
with c1:
    with st.container(border=True):
        st.markdown("##### O que o agente faz")
        st.markdown(
            "- Consulta o **cadastro funcional**, calcula **quantidade, valor e antecedência**, "
            "consulta o **histórico** de diárias e prestações e o **saldo** da unidade, nesta ordem.\n"
            "- Aplica a IN SEMA nº 07/2026 (hipotética) e recomenda: **apto para autorização**, "
            "**diligência** ou **não recomendado**.\n"
            "- Redige a **minuta do despacho**, que o servidor edita antes de registrar.")
    with st.container(border=True):
        st.markdown("##### O que o agente não faz")
        st.markdown(
            "- **Não decide.** Quem defere ou indefere é o ordenador de despesa (art. 10).\n"
            "- **Não faz contas.** Todos os números vêm das ferramentas, que são código comum.\n"
            "- **Não confirma fatos da justificativa.** A urgência é avaliada pelo texto, e a "
            "autorização escrita do Secretário Adjunto precisa ser conferida no processo.")
with c2:
    with st.container(border=True):
        st.markdown("##### Proteções")
        st.markdown(
            "- **Filtro de dados pessoais:** CPF e dados bancários são mascarados antes de "
            "chegar ao modelo, ao banco e à tela.\n"
            "- **Barreira no código:** toda matrícula, data e valor da instrução precisa vir do "
            "pedido ou das ferramentas; se não vier, a instrução é recusada e o pedido volta à "
            "análise manual.\n"
            "- **Erro da API:** nunca é exibido como resposta; aparece a mensagem padrão.")
    with st.container(border=True):
        st.markdown("##### Dados guardados")
        st.markdown(
            f"- **Banco do agente:** o histórico de cada pedido (até {NUM_HISTORY_RUNS} "
            f"execuções), por até **{PRAZO_RETENCAO_DIAS} dias** depois do último registro do "
            "conferente. O titular pode pedir a eliminação na página *Eliminação de dados*.\n"
            "- **Registro das conferências:** a decisão do servidor ao lado da sugestão do "
            "agente, sem nome, matrícula ou minuta.")
st.caption(f"Modelo: {MODELO} · teto de {TOOL_CALL_LIMIT} chamadas de ferramenta por execução · "
           "chamadas paralelas desligadas.")
ui.rodape()
