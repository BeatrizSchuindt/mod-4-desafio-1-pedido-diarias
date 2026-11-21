"""Página "Eliminação de dados": a rotina de eliminação do titular e o prazo de retenção.

Área separada da instrução, como pede o enunciado, em três passos explícitos:
1. identificar o titular: a matrícula e o nome são conferidos no cadastro funcional e precisam
   ser do mesmo servidor (sem isso, a matrícula de outra pessoa apagaria os dados dela);
2. ver o que o banco do agente guarda sobre ele, sem apagar nada: o que está sob o
   identificador e o que só a conferência tabela por tabela encontra (caso do DIA-2026-0112);
3. confirmar e eliminar; a tela mostra o que restou, conferido tabela por tabela.
"""
import re

import streamlit as st

import interface as ui
from agente import BANCO_PADRAO
from eliminacao import (PRAZO_RETENCAO_DIAS, elegiveis_ao_expurgo, eliminar_titular, expurgar,
                        localizar_titular, sessoes, tabelas)


def ocorrencias_legiveis(ocorrencias: dict) -> str:
    return ", ".join(f"{tabela} ({n})" for tabela, n in ocorrencias.items()) or "nenhuma"


ui.cabecalho("Eliminação de dados do servidor",
             "Direito do titular à eliminação (LGPD, art. 18) e prazo de retenção.")
st.info("A rotina alcança **somente o banco do agente**, que é cópia de trabalho. O processo de "
        "diárias é registro de despesa pública, sujeito à transparência e à guarda das normas "
        "de prestação de contas, e não é alterado aqui.", icon=":material/policy:")

# ---------------------------------------------------------------- 1. identificar
st.markdown("#### 1. Identificar o titular")
st.caption("Informe a matrícula e o nome de quem pediu a eliminação. Os dois são conferidos no "
           "cadastro funcional e precisam ser do mesmo servidor. Nada é apagado neste passo.")
with st.form("form_localizar"):
    c1, c2 = st.columns([1, 2])
    matricula = c1.text_input("Matrícula", max_chars=6, placeholder="000000")
    nome = c2.text_input("Nome completo", placeholder="Como consta do cadastro funcional")
    localizar = st.form_submit_button("Localizar dados do titular", type="primary",
                                      icon=":material/person_search:")
if localizar:
    st.session_state.pop("localizacao", None)
    st.session_state.pop("eliminacao", None)
    if not re.fullmatch(r"\d{6}", matricula.strip()) or not nome.strip():
        ui.avisar("Matrícula ou nome incompletos.", "erro")
        st.error("Informe a matrícula com seis algarismos e o nome completo.",
                 icon=":material/error:")
    else:
        try:
            achado = localizar_titular(matricula.strip(), nome.strip())
            st.session_state["localizacao"] = achado
            if achado.vazio:
                ui.avisar("Nenhum dado deste titular no banco do agente.", "aviso")
            elif achado.por_conteudo:
                ui.avisar("Há dados do titular sob outro identificador. Confira antes de eliminar.",
                          "aviso")
            else:
                ui.avisar("Titular conferido no cadastro. Confira os dados antes de eliminar.")
        except ValueError as erro:
            ui.avisar("Titular não conferido. Veja o motivo na página.", "erro")
            st.error(f"**Titular não conferido:** {erro}. Nenhum dado foi localizado nem apagado.",
                     icon=":material/gpp_bad:")

# ---------------------------------------------------------------- 2. o que existe
local = st.session_state.get("localizacao")
if local:
    st.markdown("#### 2. O que o banco do agente guarda sobre o titular")
    st.caption(f"Titular conferido no cadastro: **{local.nome}** (matrícula {local.matricula}). "
               "Nada foi apagado ainda.")
    if local.vazio:
        st.success("O banco do agente não guarda nenhum dado deste titular.",
                   icon=":material/verified_user:")
    else:
        itens = ([{"Encontrado": "pela matrícula (identificador)", "Tipo": s["tipo"],
                   "Pedido ou memória": s["id"], "Gravado sob": s["user_id"]}
                  for s in local.sessoes + local.memorias]
                 + [{"Encontrado": "pelo conteúdo, sob outro identificador", "Tipo": e["tipo"],
                     "Pedido ou memória": e["id"], "Gravado sob": e["user_id"]}
                    for e in local.por_conteudo])
        st.table(itens, hide_index=True)
        if local.por_conteudo:
            st.warning("Há dados do titular **gravados sob outro identificador**. Isso acontece "
                       "quando o pedido foi protocolado com a matrícula de outra pessoa (como no "
                       "DIA-2026-0112) e só a conferência tabela por tabela os encontra. Confira "
                       "antes de confirmar: um homônimo também apareceria pelo nome.",
                       icon=":material/search:")

        # ------------------------------------------------------------ 3. confirmar
        st.markdown("#### 3. Confirmar a eliminação")
        confirmado = st.checkbox("Confirmo que o titular pediu a eliminação e que os itens "
                                 "acima são dele")
        if st.button("Eliminar os dados listados", type="primary", disabled=not confirmado,
                     icon=":material/delete_forever:"):
            relatorio = eliminar_titular(local.matricula, local.nome, apagar_encontradas=True)
            st.session_state["eliminacao"] = relatorio
            st.session_state.pop("localizacao", None)
            if relatorio.nada_restou:
                ui.avisar_depois(f"Dados de {relatorio.nome} eliminados: nada restou no banco.")
            else:
                ui.avisar_depois("Eliminação incompleta: ainda há ocorrências do titular.", "erro")
            st.rerun()

# ---------------------------------------------------------------- resultado
relatorio = st.session_state.get("eliminacao")
if relatorio:
    st.markdown("#### Resultado da eliminação")
    if relatorio.nada_restou:
        st.success(f"Conferido tabela por tabela: **nada restou** de {relatorio.nome} "
                   f"(matrícula {relatorio.matricula}) no banco do agente.",
                   icon=":material/verified_user:")
    else:
        st.error(f"Ainda há ocorrências do titular: {ocorrencias_legiveis(relatorio.depois)}.",
                 icon=":material/error:")
    st.table([
        {"Etapa": "Antes da eliminação, o titular aparecia em",
         "Resultado": ocorrencias_legiveis(relatorio.antes)},
        {"Etapa": "1. Sessões apagadas pela matrícula",
         "Resultado": ", ".join(relatorio.sessoes_apagadas) or "nenhuma"},
        {"Etapa": "2. Memórias apagadas pela matrícula", "Resultado": str(relatorio.memorias_apagadas)},
        {"Etapa": "3. Apagados pela conferência tabela por tabela",
         "Resultado": ", ".join(f"{e['tipo']} {e['id']} (gravado sob {e['user_id']})"
                                for e in relatorio.encontradas_na_varredura) or "nenhum"},
        {"Etapa": "Depois da eliminação, o titular aparece em",
         "Resultado": ocorrencias_legiveis(relatorio.depois)},
    ], hide_index=True)

# ---------------------------------------------------------------- o que há no banco
st.markdown("#### O que há no banco do agente")
contagem = tabelas(BANCO_PADRAO)
if not contagem:
    st.caption("O banco do agente ainda não foi criado: nenhum pedido foi instruído.")
else:
    c1, c2 = st.columns([1, 2])
    c1.table([{"Tabela": t, "Registros": n} for t, n in contagem.items()], hide_index=True)
    lista = sessoes(BANCO_PADRAO)
    c2.table([{"Pedido (sessão)": s["session_id"], "Gravado sob (user_id)": s["user_id"],
               "Execuções": s["execucoes"]} for s in lista] or [{"Pedido (sessão)": "nenhum"}],
             hide_index=True)

# ---------------------------------------------------------------- prazo de retenção
st.markdown("#### Prazo de retenção")
st.caption(f"A sessão de um pedido fica no banco até {PRAZO_RETENCAO_DIAS} dias depois do último "
           "registro do conferente naquele pedido (ou da última execução, se não houver "
           "registro). O registro das conferências não tem dado pessoal e não é expurgado.")
vencidas = elegiveis_ao_expurgo()
if not vencidas:
    st.success("Nenhuma sessão com prazo de retenção vencido.", icon=":material/schedule:")
else:
    st.table([{"Pedido": v["session_id"], "Desde": v["referencia"].replace("T", " "),
               "Contado a partir de": v["origem"]} for v in vencidas], hide_index=True)
    if st.button(f"Expurgar {len(vencidas)} sessão(ões) vencida(s)", type="primary",
                 icon=":material/auto_delete:"):
        apagadas = expurgar()
        ui.avisar_depois(f"{len(apagadas)} sessão(ões) expurgada(s) por prazo de retenção.")
        st.rerun()

ui.rodape()
