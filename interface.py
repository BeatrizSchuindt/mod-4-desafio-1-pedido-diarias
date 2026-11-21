"""Identidade visual e componentes comuns do formulário de conferência.

A paleta parte da identidade da SEMA-MT (o azul do fundo da marca, #1D3281, e o azul do
texto, #252B77) e das cores da bandeira de Mato Grosso (azul, branco, verde e amarelo), usadas
na faixa sob o cabeçalho. Verde, laranja e vermelho marcam as três recomendações, sempre com
texto escuro sobre fundo claro, para manter o contraste.

Na tela, a marca é tipográfica (SEMA-MT no menu e no cabeçalho); o logo da secretaria
(assets/logo_sema.png) aparece na minuta em PDF. A aplicação é um protótipo acadêmico, com
dados e norma hipotéticos, e o aviso aparece em todas as páginas e no rodapé do PDF.

Avisos: cada evento aparece como toast colorido (verde para sucesso, amarelo para aviso,
vermelho para erro), e o aviso fica também na página quando o servidor precisa dele para agir.
O st.toast do Streamlit não tem cor por tipo, por isso o toast é desenhado aqui, em HTML e CSS:
aparece no canto superior direito e some sozinho, com animação (o de erro fica mais tempo). Os
avisos de uma execução são desenhados no rodapé da página; os disparados antes de um st.rerun
ficam guardados e aparecem na execução seguinte.

As páginas importam daqui o agente em cache e as funções que desenham a instrução. Nenhuma
delas fala com o Agno diretamente: tudo passa por `instruir`.
"""
import html
import logging
import os
from datetime import date
from pathlib import Path

import streamlit as st

from agente import MENSAGEM_PADRAO, construir_agente, instruir

BASE = Path(__file__).parent
registro_tecnico = logging.getLogger("instrucao_diarias")
ICONES_AVISO = {"sucesso": "✔", "aviso": "⚠", "erro": "✖"}

AZUL_SEMA, AZUL_TEXTO, VERDE_MT, AMARELO_MT = "#1D3281", "#252B77", "#0B7A3E", "#F2B705"

ROTULOS_FERRAMENTAS = {
    "consultar_servidor": "Consultando o cadastro funcional",
    "calcular_diarias": "Calculando a quantidade, o valor e a antecedência",
    "consultar_historico_diarias": "Consultando o histórico de diárias e prestações de contas",
    "consultar_saldo_diarias": "Consultando o saldo da unidade",
}
ROTULOS_CRITERIOS = {
    "cadastro": "Cadastro funcional (art. 9º)",
    "dados_completos": "Dados completos (art. 9º)",
    "antecedencia": "Antecedência mínima (art. 5º)",
    "prestacao_contas": "Prestação de contas (art. 7º)",
    "limite_mensal": "Limite mensal de diárias (art. 6º)",
    "saldo_orcamentario": "Saldo da unidade (art. 8º)",
}
SITUACOES = {"atende": "✅ Atende", "nao_atende": "❌ Não atende", "nao_verificado": "➖ Não verificado"}
RECOMENDACOES = {
    "apto_para_autorizacao": ("Apto para autorização", "selo-apto"),
    "diligencia": ("Diligência", "selo-diligencia"),
    "nao_recomendado": ("Não recomendado", "selo-nao"),
}

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@600;700;800&display=swap');
.sema-cabecalho {{
  background: linear-gradient(135deg, {AZUL_SEMA} 0%, {AZUL_TEXTO} 100%);
  color: #FFFFFF; border-radius: 14px; padding: 1.1rem 1.4rem;
  display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between;
  gap: .6rem 1.5rem;
}}
.sema-cabecalho .marca {{ display: flex; flex-direction: column; align-items: flex-start;
                          flex: 0 1 auto; }}
.sema-cabecalho .sigla {{
  font-family: 'Montserrat', 'Segoe UI', sans-serif; font-weight: 800; line-height: 1;
  font-size: clamp(1.7rem, 4vw, 2.4rem); letter-spacing: .03em;
}}
.sema-cabecalho .orgao {{
  font-family: 'Montserrat', 'Segoe UI', sans-serif; font-weight: 600;
  font-size: clamp(.78rem, 1.5vw, .95rem); opacity: .92; margin-top: .25rem;
}}
.sema-cabecalho .pagina {{ text-align: right; flex: 1 1 260px; }}
.sema-cabecalho .pagina .titulo {{
  color: #FFFFFF; font-family: 'Montserrat', 'Segoe UI', sans-serif; font-weight: 700;
  font-size: clamp(1.05rem, 2.2vw, 1.4rem); line-height: 1.2;
}}
.sema-cabecalho .pagina .descricao {{ margin-top: .25rem; font-size: .88rem; opacity: .9; }}
/* Menos espaço acima do cabeçalho */
[data-testid="stMainBlockContainer"] {{ padding-top: 3.2rem; }}
/* Marca da secretaria no topo do menu lateral, acima das páginas */
[data-testid="stSidebarContent"] {{ display: flex; flex-direction: column; }}
[data-testid="stSidebarHeader"] {{ order: 0; }}
[data-testid="stSidebarUserContent"] {{ order: 1; padding-top: 0; padding-bottom: .5rem; }}
[data-testid="stSidebarNav"] {{ order: 2; }}
/* Página ativa marcada com o amarelo da bandeira de Mato Grosso */
[data-testid="stSidebarNavLink"][aria-current="page"] {{ box-shadow: inset 4px 0 0 {AMARELO_MT}; }}
.sema-aviso {{
  display: inline-block; font-size: .74rem; margin-top: .45rem; padding: .12rem .6rem;
  border-radius: 999px; background: rgba(255,255,255,.14); border: 1px solid rgba(255,255,255,.35);
}}
.sema-faixa {{
  height: 7px; border-radius: 4px; margin: .45rem 0 1.1rem 0; border: 1px solid #D5DBEA;
  background: linear-gradient(90deg, {AZUL_SEMA} 0 45%, #FFFFFF 45% 60%, {VERDE_MT} 60% 82%,
                              {AMARELO_MT} 82% 100%);
}}
.selo {{ display: inline-block; padding: .3rem .8rem; border-radius: 999px; font-weight: 700; }}
.selo-apto {{ background: #E7F4EC; color: {VERDE_MT}; border: 1px solid #0B7A3E40; }}
.selo-diligencia {{ background: #FDF1E7; color: #B54708; border: 1px solid #B5470840; }}
.selo-nao {{ background: #FBECEA; color: #B42318; border: 1px solid #B4231840; }}
.sema-rodape {{
  font-size: .78rem; color: #5B6280; border-top: 1px solid #D5DBEA;
  padding-top: .6rem; margin-top: 2.2rem;
}}
.sema-lateral {{ color: #FFFFFF; line-height: 1.25; margin-bottom: 1rem; }}
.sema-lateral .sigla {{ font-family: 'Montserrat', sans-serif; font-weight: 800; font-size: 1.6rem; }}
.sema-lateral .setor {{ font-size: .82rem; opacity: .9; }}
/* Toasts coloridos: verde (sucesso), amarelo (aviso), vermelho (erro) */
.sema-avisos {{
  position: fixed; top: 1rem; right: 1rem; z-index: 1000005; pointer-events: none;
  display: flex; flex-direction: column; gap: .55rem; width: min(390px, calc(100vw - 2rem));
}}
.sema-toast {{
  display: flex; gap: .65rem; align-items: flex-start; padding: .8rem 1rem;
  border-radius: .65rem; border-left: 6px solid; font-size: .93rem; line-height: 1.4;
  box-shadow: 0 8px 24px rgba(20, 30, 70, .20); animation: sema-toast-a 6s ease forwards;
}}
.sema-toast .icone {{ font-weight: 700; font-size: 1.05rem; line-height: 1.3; }}
.sema-toast-sucesso {{ background: #E3F3E9; color: #0A4F28; border-color: {VERDE_MT}; }}
.sema-toast-aviso {{ background: #FFF4CC; color: #5C4300; border-color: {AMARELO_MT}; }}
.sema-toast-erro {{ background: #FBE6E3; color: #7E170F; border-color: #B42318;
                    animation-duration: 9s; }}
.sema-toast.ciclo-a {{ animation-name: sema-toast-a; }}
.sema-toast.ciclo-b {{ animation-name: sema-toast-b; }}
@keyframes sema-toast-a {{
  0% {{ opacity: 0; transform: translateX(16px); }}
  5% {{ opacity: 1; transform: none; }}
  88% {{ opacity: 1; }}
  100% {{ opacity: 0; visibility: hidden; }}
}}
@keyframes sema-toast-b {{
  0% {{ opacity: 0; transform: translateX(16px); }}
  5% {{ opacity: 1; transform: none; }}
  88% {{ opacity: 1; }}
  100% {{ opacity: 0; visibility: hidden; }}
}}
@media (prefers-reduced-motion: reduce) {{ .sema-toast {{ transform: none; }} }}
@media (max-width: 640px) {{
  .sema-cabecalho {{ flex-direction: column; align-items: flex-start; padding: 1rem 1.1rem; }}
  /* Em coluna, a base flexível viraria altura: no celular, cada bloco ocupa só o necessário */
  .sema-cabecalho .marca, .sema-cabecalho .pagina {{ flex: 0 0 auto; }}
  .sema-cabecalho .pagina {{ text-align: left; }}
  [data-testid="stMainBlockContainer"] {{ padding-top: 2.8rem; }}
}}
</style>
"""


# ------------------------------------------------------------------ moldura das páginas

def avisar(mensagem: str, tipo: str = "sucesso") -> None:
    """Toast desta execução: "sucesso" (verde), "aviso" (amarelo) ou "erro" (vermelho)."""
    st.session_state.setdefault("avisos_agora", []).append((mensagem, tipo))


def avisar_depois(mensagem: str, tipo: str = "sucesso") -> None:
    """Toast que sobrevive a um st.rerun: aparece na próxima execução."""
    st.session_state.setdefault("avisos_pendentes", []).append((mensagem, tipo))


def desenhar_avisos() -> None:
    """Desenha, no canto da tela, os toasts desta execução (chamado pelo rodapé)."""
    avisos = st.session_state.pop("avisos_agora", [])
    if avisos:
        # O Streamlit reaproveita o elemento quando o HTML se repete (o mesmo clique de novo) e só
        # atualiza atributos; a animação, já terminada, não recomeçaria e o toast não
        # reapareceria. Alternar entre duas animações idênticas de nomes diferentes (ciclo-a e
        # ciclo-b) obriga o navegador a reiniciá-la a cada desenho.
        n = st.session_state["avisos_desenhados"] = st.session_state.get("avisos_desenhados", 0) + 1
        ciclo = "ciclo-a" if n % 2 else "ciclo-b"
        st.markdown('<div class="sema-avisos">' + "".join(
            f'<div class="sema-toast sema-toast-{tipo} {ciclo}" '
            f'role="{"alert" if tipo == "erro" else "status"}">'
            f'<span class="icone">{ICONES_AVISO[tipo]}</span><span>{html.escape(mensagem)}</span></div>'
            for mensagem, tipo in avisos) + "</div>", unsafe_allow_html=True)


def aplicar_identidade() -> None:
    """Estilos, marca no menu lateral e avisos pendentes; chamado antes de cada página."""
    st.markdown(_CSS, unsafe_allow_html=True)
    st.session_state["avisos_agora"] = st.session_state.pop("avisos_pendentes", [])
    st.sidebar.markdown(
        '<div class="sema-lateral"><div class="sigla">SEMA-MT</div>'
        '<div class="setor">Coordenadoria de Diárias e Passagens</div></div>',
        unsafe_allow_html=True)


def cabecalho(titulo: str, descricao: str) -> None:
    st.markdown(
        f'<div class="sema-cabecalho"><div class="marca"><span class="sigla">SEMA</span>'
        f'<span class="orgao">Secretaria de Estado de Meio Ambiente · Mato Grosso</span>'
        f'<span class="sema-aviso">Protótipo acadêmico · dados e norma hipotéticos</span></div>'
        f'<div class="pagina"><div class="titulo" role="heading" aria-level="1">{titulo}</div>'
        f'<div class="descricao">{descricao}</div></div></div>'
        f'<div class="sema-faixa"></div>', unsafe_allow_html=True)


def rodape() -> None:
    """Rodapé da página; também desenha os toasts da execução, que ficam fixos no canto."""
    desenhar_avisos()
    st.markdown(
        '<div class="sema-rodape">A instrução é preparada por um agente de IA e conferida pelo '
        'servidor; a decisão é do ordenador de despesa (art. 10 da IN SEMA nº 07/2026, '
        'hipotética). Protótipo do curso FIC DEV IA, sem vínculo com sistemas oficiais.</div>',
        unsafe_allow_html=True)


# ------------------------------------------------------------------ agente e execução

@st.cache_resource
def agente_em_cache():
    """Um único agente para todas as interações e todos os usuários.

    É seguro compartilhá-lo porque session_id e user_id vão a cada `run` (memória da Etapa 4),
    e não ficam no objeto. PROVOCAR_ERRO_API=1 monta o modelo com a configuração que a API
    recusa, para demonstrar a mensagem padrão; o servidor não vê essa opção.
    """
    return construir_agente(memoria="historico",
                            provocar_erro_api=os.getenv("PROVOCAR_ERRO_API") == "1")


def executar_com_progresso(pedido: dict, complementacao: dict | None = None):
    """Instrui o pedido mostrando cada consulta no momento em que ela começa."""
    titulo = "Instruindo a complementação" if complementacao else "Instruindo o pedido"
    with st.status(f"{titulo} {pedido['numero']}…", expanded=True) as status:
        resultado = instruir(pedido, complementacao, agente=agente_em_cache(),
                             ao_chamar_ferramenta=lambda nome: st.write(
                                 f"{ROTULOS_FERRAMENTAS.get(nome, nome)}…"))
        segundos = decimal(resultado.medidas.get("segundos", 0), 1)
        if resultado.situacao == "entregue":
            status.update(label=f"Instrução concluída em {segundos} s", state="complete",
                          expanded=False)
            avisar_depois(f"Instrução do pedido {pedido['numero']} concluída.")
            if resultado.instrucao.exige_autorizacao_superior:
                avisar_depois("O pedido exige autorização escrita do Secretário Adjunto.", "aviso")
            if resultado.instrucao.recomendacao == "diligencia":
                avisar_depois("Pedido em diligência: envie a complementação quando chegar.", "aviso")
        else:
            # O motivo técnico vai para o registro do sistema, e nunca para a tela.
            registro_tecnico.warning("%s (%s): %s", pedido["numero"], resultado.situacao,
                                     "; ".join(resultado.motivos))
            status.update(label="Instrução não concluída", state="error", expanded=False)
            avisar_depois(f"Pedido {pedido['numero']} devolvido à análise manual.", "erro")
    return resultado


# ------------------------------------------------------------------ formatação

def reais(valor: float | None) -> str:
    if valor is None:
        return "—"
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def inteiro(valor: int) -> str:
    """Inteiro com ponto de milhar: 15.840."""
    return f"{valor:,}".replace(",", ".")


def decimal(valor: float, casas: int) -> str:
    """Número com vírgula decimal: 12,3."""
    return f"{valor:.{casas}f}".replace(".", ",")


def data_br(texto: str | None) -> str:
    return date.fromisoformat(texto).strftime("%d/%m/%Y") if texto else "não informada"


# ------------------------------------------------------------------ o pedido e a instrução

def cartao_pedido(pedido: dict, justificativa_filtrada: str) -> None:
    """Os dados do pedido como protocolado, com a justificativa já filtrada."""
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        c1.markdown(f"**Solicitante**  \n{pedido['nome']}  \nMatrícula {pedido['matricula']}")
        c2.markdown(f"**Destino**  \n{pedido['destino_municipio']}/{pedido['destino_uf']}  \n"
                    f"{pedido['transporte'].capitalize()}")
        c3.markdown(f"**Período**  \n{data_br(pedido['data_partida'])} a "
                    f"{data_br(pedido['data_retorno'])}  \nProtocolado em "
                    f"{data_br(pedido['data_pedido'])}")
        st.markdown(f"**Justificativa**  \n{justificativa_filtrada}")


def mostrar_resultado(resultado) -> None:
    """Desenha a instrução entregue, campo a campo; em erro ou recusa, só a mensagem padrão."""
    if resultado.situacao == "entregue":
        st.status(f"Instrução concluída em {decimal(resultado.medidas.get('segundos', 0), 1)} s",
                  state="complete", expanded=False)
    else:
        st.status("Instrução não concluída", state="error", expanded=False)
    if resultado.situacao != "entregue":
        st.error(MENSAGEM_PADRAO, icon=":material/report:")
        st.caption("O pedido deve seguir para análise manual. O motivo técnico ficou no registro "
                   "do sistema, para a equipe responsável.")
        return
    i = resultado.instrucao
    rotulo, classe = RECOMENDACOES[i.recomendacao]
    c1, c2, c3 = st.columns([1.4, 1, 1], vertical_alignment="center")
    c1.markdown(f"**Recomendação do agente**  \n<span class='selo {classe}'>{rotulo}</span>",
                unsafe_allow_html=True)
    c2.metric("Quantidade de diárias",
              "—" if i.quantidade_diarias is None else decimal(i.quantidade_diarias, 1))
    c3.metric("Valor total", reais(i.valor_total))
    if i.exige_autorizacao_superior:
        st.warning("**Exige autorização expressa e escrita do Secretário Adjunto** antes do "
                   "encaminhamento (art. 5º, § 2º). Autorização verbal não supre.",
                   icon=":material/gavel:")
    for alerta in i.alertas:
        st.warning(alerta, icon=":material/warning:")
    for pendencia in i.pendencias:
        st.info(pendencia, icon=":material/assignment_late:")

    # st.table quebra o texto em várias linhas: o fundamento aparece inteiro, sem cortes.
    st.markdown("##### Verificações da norma")
    st.table([{"Critério": ROTULOS_CRITERIOS.get(v.criterio, v.criterio),
               "Situação": SITUACOES[v.situacao], "Fundamento": v.detalhe}
              for v in i.verificacoes], hide_index=True)

    st.markdown("##### Consultas realizadas")
    st.table([{"Ordem": n, "Consulta": ROTULOS_FERRAMENTAS.get(c.ferramenta, c.ferramenta),
               "Argumentos": ", ".join(f"{k} = {v}" for k, v in c.argumentos.items())}
              for n, c in enumerate(resultado.consultas, 1)], hide_index=True)
    m = resultado.medidas
    st.caption(f"{m.get('chamadas_ao_modelo', 0)} chamadas ao modelo · "
               f"{inteiro(m.get('tokens_entrada', 0))} tokens de entrada · "
               f"{inteiro(m.get('tokens_saida', 0))} de saída · "
               f"US$ {decimal(m.get('custo_usd', 0), 4)} · {decimal(m.get('segundos', 0), 1)} s")
