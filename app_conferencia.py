"""Formulário de conferência da instrução de pedidos de diárias (SEMA-MT, protótipo acadêmico).

Ponto de entrada da aplicação Streamlit. Monta a identidade visual e o menu lateral com as
páginas; cada página fica em paginas/ e importa o que precisa de interface.py.

Execução:
    streamlit run app_conferencia.py
    PROVOCAR_ERRO_API=1 streamlit run app_conferencia.py   # demonstra a mensagem padrão
"""
import streamlit as st

import interface

st.set_page_config(page_title="SEMA-MT · Instrução de diárias", page_icon=":material/forest:",
                   layout="wide", initial_sidebar_state="auto")
interface.aplicar_identidade()

paginas = {
    "Diárias": [
        st.Page("paginas/instruir.py", title="Instruir pedido", icon=":material/assignment:",
                default=True),
        st.Page("paginas/registro.py", title="Registro das conferências",
                icon=":material/fact_check:"),
    ],
    "Proteção de dados": [
        st.Page("paginas/eliminacao_dados.py", title="Eliminação de dados",
                icon=":material/person_remove:"),
    ],
    "Ajuda": [
        st.Page("paginas/sobre.py", title="Sobre o sistema", icon=":material/info:"),
    ],
}
st.navigation(paginas, position="sidebar").run()
