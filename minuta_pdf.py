"""Minuta do despacho em PDF, no modelo visual da SEMA-MT (protótipo acadêmico).

Gerada no momento em que o servidor registra a conferência: leva o texto da minuta como ele
ficou depois da edição, a decisão do servidor ao lado da recomendação do agente e as
verificações da norma. A marca d'água "MINUTA" e o rodapé deixam claro que é um rascunho de
protótipo, com dados e norma hipotéticos e sem valor oficial; a decisão é do ordenador.

Fonte: o PDF procura uma fonte com acentos instalada no sistema (Noto Sans, DejaVu Sans,
Liberation Sans ou Arial, em Linux, Windows e macOS). Sem nenhuma delas, usa a Helvetica com a
codificação windows-1252, que cobre os acentos, o travessão, as aspas curvas, "º" e "§".
"""
from datetime import date, datetime
from pathlib import Path

from fpdf import FPDF
from fpdf.enums import XPos, YPos

BASE = Path(__file__).parent
LOGO = BASE / "assets" / "logo_sema.png"

AZUL, AZUL_TEXTO, TEXTO = (29, 50, 129), (37, 43, 119), (27, 31, 59)
CINZA, FUNDO, BORDA = (91, 98, 128), (238, 241, 248), (213, 219, 234)
VERDE, AMARELO, LARANJA, VERMELHO = (11, 122, 62), (242, 183, 5), (181, 71, 8), (180, 35, 24)

# (regular, negrito), em ordem de preferência
FONTES = [
    (BASE / "assets" / "fontes" / "Regular.ttf", BASE / "assets" / "fontes" / "Negrito.ttf"),
    ("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf", "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"),
    ("/run/host/fonts/truetype/noto/NotoSans-Regular.ttf", "/run/host/fonts/truetype/noto/NotoSans-Bold.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/dejavu/DejaVuSans.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
    ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
     "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    ("C:/Windows/Fonts/arial.ttf", "C:/Windows/Fonts/arialbd.ttf"),
    ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
]

RECOMENDACOES = {"apto_para_autorizacao": "Apto para autorização", "diligencia": "Diligência",
                 "nao_recomendado": "Não recomendado"}
CRITERIOS = {"cadastro": "Cadastro funcional (art. 9º)", "dados_completos": "Dados completos (art. 9º)",
             "antecedencia": "Antecedência mínima (art. 5º)",
             "prestacao_contas": "Prestação de contas (art. 7º)",
             "limite_mensal": "Limite mensal de diárias (art. 6º)",
             "saldo_orcamentario": "Saldo da unidade (art. 8º)"}
SITUACOES = {"atende": ("Atende", VERDE), "nao_atende": ("Não atende", VERMELHO),
             "nao_verificado": ("Não verificado", CINZA)}


def _reais(valor) -> str:
    if valor is None:
        return "—"
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _data(texto) -> str:
    return date.fromisoformat(texto).strftime("%d/%m/%Y") if texto else "não informada"


class _Minuta(FPDF):
    def __init__(self, numero: str, registrado_em: datetime):
        super().__init__(format="A4")
        self.numero, self.registrado_em = numero, registrado_em
        self.set_margins(18, 16, 18)
        self.set_auto_page_break(True, margin=28)
        self.fonte = self._carregar_fonte()
        self.set_title(f"Minuta de despacho - {numero}")
        self.set_author("Protótipo acadêmico - instrução de diárias")

    def _carregar_fonte(self) -> str:
        for regular, negrito in FONTES:
            if Path(regular).exists() and Path(negrito).exists():
                self.add_font("Texto", "", str(regular))
                self.add_font("Texto", "B", str(negrito))
                return "Texto"
        self.core_fonts_encoding = "windows-1252"
        return "Helvetica"

    def t(self, texto) -> str:
        """Texto seguro para a fonte em uso (a Helvetica só conhece o windows-1252)."""
        texto = str(texto)
        if self.fonte == "Helvetica":
            return texto.encode("cp1252", "replace").decode("cp1252")
        return texto

    def fonte_(self, tamanho: float, negrito: bool = False, cor=TEXTO) -> None:
        self.set_font(self.fonte, "B" if negrito else "", tamanho)
        self.set_text_color(*cor)

    def faixa(self, y: float, altura: float = 1.6) -> None:
        """As cores da bandeira de Mato Grosso: azul, branco, verde e amarelo."""
        largura = self.w - self.l_margin - self.r_margin
        partes = [(AZUL, .45), ((255, 255, 255), .15), (VERDE, .22), (AMARELO, .18)]
        x = self.l_margin
        for cor, fracao in partes:
            self.set_fill_color(*cor)
            self.rect(x, y, largura * fracao, altura, style="F")
            x += largura * fracao
        self.set_draw_color(*BORDA)
        self.rect(self.l_margin, y, largura, altura, style="D")

    def header(self) -> None:
        # Marca d'água atrás do conteúdo
        with self.local_context(fill_opacity=0.06):
            self.fonte_(96, True, AZUL)
            with self.rotation(32, x=self.w / 2, y=self.h / 2):
                self.text(self.w / 2 - 58, self.h / 2 + 14, "MINUTA")
        if LOGO.exists():
            self.image(str(LOGO), x=self.l_margin, y=11, w=21, h=21)
        x = self.l_margin + 25
        self.set_xy(x, 12.5)
        self.fonte_(10.5, True, AZUL)
        self.cell(0, 5.5, self.t("SECRETARIA DE ESTADO DE MEIO AMBIENTE · SEMA-MT"))
        self.set_xy(x, 18.5)
        self.fonte_(8.6, cor=CINZA)
        self.cell(0, 4.5, self.t("Coordenadoria de Diárias e Passagens"))
        self.set_xy(x, 23.2)
        self.cell(0, 4.5, self.t("Instrução de pedido de diárias · IN SEMA nº 07/2026 (hipotética)"))
        self.set_xy(self.w - self.r_margin - 60, 12.5)
        self.fonte_(10.5, True, AZUL_TEXTO)
        self.cell(60, 5.5, self.t(f"Pedido {self.numero}"), align="R")
        self.set_xy(self.w - self.r_margin - 60, 18.5)
        self.fonte_(8.6, cor=CINZA)
        self.cell(60, 4.5, self.t(f"Conferido em {self.registrado_em:%d/%m/%Y às %H:%M}"), align="R")
        self.faixa(35)
        self.set_y(42)

    def footer(self) -> None:
        self.faixa(self.h - 22, altura=0.9)
        self.set_y(self.h - 19.5)
        self.fonte_(7.2, cor=CINZA)
        self.multi_cell(150, 3.6, self.t(
            "Minuta preparada com apoio de agente de IA e conferida pelo servidor. A decisão "
            "cabe ao ordenador de despesa (art. 10). Protótipo acadêmico do curso FIC DEV IA: "
            "dados e norma hipotéticos, sem valor oficial."))
        self.set_xy(self.w - self.r_margin - 22, self.h - 19.5)
        self.cell(22, 3.6, self.t(f"Página {self.page_no()} de {{nb}}"), align="R")

    # ------------------------------------------------------------- blocos do documento

    def titulo(self, texto: str, subtitulo: str = "") -> None:
        self.fonte_(16, True, AZUL)
        self.cell(0, 9, self.t(texto), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if subtitulo:
            self.fonte_(9, cor=CINZA)
            self.cell(0, 5, self.t(subtitulo), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(3)

    def secao(self, texto: str) -> None:
        self.ln(2)
        self.fonte_(11, True, AZUL_TEXTO)
        self.cell(0, 7, self.t(texto), new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def quadro_de_dados(self, pares: list[tuple[str, str]]) -> None:
        largura = self.w - self.l_margin - self.r_margin
        linhas = (len(pares) + 1) // 2
        altura_linha, y0 = 11.5, self.get_y()
        self.set_fill_color(*FUNDO)
        self.set_draw_color(*BORDA)
        self.rect(self.l_margin, y0, largura, linhas * altura_linha + 4, style="DF",
                  round_corners=True, corner_radius=2.5)
        for n, (rotulo, valor) in enumerate(pares):
            coluna, linha = n % 2, n // 2
            x = self.l_margin + 5 + coluna * (largura / 2)
            y = y0 + 3 + linha * altura_linha
            self.set_xy(x, y)
            self.fonte_(7.3, True, CINZA)
            self.cell(largura / 2 - 8, 4, self.t(rotulo.upper()))
            self.set_xy(x, y + 4.2)
            # Reduz a fonte até o valor caber na coluna, em vez de passar da borda do quadro.
            tamanho = 10
            self.fonte_(tamanho, True)
            while self.get_string_width(self.t(valor)) > largura / 2 - 10 and tamanho > 7:
                tamanho -= 0.5
                self.fonte_(tamanho, True)
            self.cell(largura / 2 - 8, 5.5, self.t(valor))
        self.set_y(y0 + linhas * altura_linha + 8)

    def destaque(self, texto: str, cor) -> None:
        largura = self.w - self.l_margin - self.r_margin
        y0 = self.get_y()
        self.set_fill_color(253, 241, 231) if cor == LARANJA else self.set_fill_color(*FUNDO)
        self.set_draw_color(*cor)
        self.set_line_width(0.6)
        self.line(self.l_margin, y0, self.l_margin, y0 + 10)
        self.set_line_width(0.2)
        self.set_xy(self.l_margin + 3, y0 + 1)
        self.fonte_(9.2, True, cor)
        self.multi_cell(largura - 4, 4.6, self.t(texto), align="L", new_x=XPos.LMARGIN,
                        new_y=YPos.NEXT)
        self.ln(3)

    def tabela_verificacoes(self, verificacoes) -> None:
        largura = self.w - self.l_margin - self.r_margin
        colunas = (largura * 0.66, largura * 0.34)
        self.set_fill_color(*AZUL)
        self.fonte_(8.6, True, (255, 255, 255))
        self.cell(colunas[0], 6.5, self.t("  Critério"), fill=True)
        self.cell(colunas[1], 6.5, self.t("  Situação"), fill=True, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        for n, v in enumerate(verificacoes):
            self.set_fill_color(*(FUNDO if n % 2 else (255, 255, 255)))
            self.fonte_(8.8)
            self.cell(colunas[0], 6.2, self.t("  " + CRITERIOS.get(v.criterio, v.criterio)), fill=True)
            rotulo, cor = SITUACOES[v.situacao]
            self.fonte_(8.8, True, cor)
            self.cell(colunas[1], 6.2, self.t("  " + rotulo), fill=True,
                      new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*BORDA)


def gerar_minuta_pdf(pedido: dict, instrucao, minuta: str, encaminhamento: str,
                     registrado_em: datetime, motivo: str = "") -> bytes:
    """Monta o PDF da minuta conferida e devolve os bytes, prontos para o download.

    `pedido` é o pedido efetivo (com a complementação aplicada); `instrucao` é a Instrucao
    entregue; `minuta` é o texto como o servidor o deixou; `encaminhamento` é o rótulo da
    decisão do servidor.
    """
    pdf = _Minuta(instrucao.numero_pedido, registrado_em)
    pdf.add_page()
    pdf.titulo("Minuta de despacho", "Ao Ordenador de Despesa, para decisão")
    quantidade = ("—" if instrucao.quantidade_diarias is None
                  else f"{instrucao.quantidade_diarias:.1f}".replace(".", ","))
    pdf.quadro_de_dados([
        ("Servidor(a)", pedido["nome"]), ("Matrícula", instrucao.matricula),
        ("Destino", f"{pedido['destino_municipio']}/{pedido['destino_uf']}"),
        ("Período", f"{_data(pedido['data_partida'])} a {_data(pedido.get('data_retorno'))}"),
        ("Quantidade de diárias", quantidade), ("Valor total", _reais(instrucao.valor_total)),
        ("Recomendação do agente", RECOMENDACOES.get(instrucao.recomendacao, instrucao.recomendacao)),
        ("Decisão do servidor", encaminhamento),
    ])
    if instrucao.exige_autorizacao_superior:
        pdf.destaque("Exige autorização expressa e escrita do Secretário Adjunto antes do "
                     "encaminhamento (art. 5º, § 2º). Autorização verbal não supre.", LARANJA)
    pdf.secao("Texto do despacho")
    pdf.fonte_(10.3)
    pdf.multi_cell(0, 5.6, pdf.t(minuta.strip()), align="L", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    if motivo.strip():
        pdf.ln(2)
        pdf.destaque(f"Observação do servidor ao divergir da recomendação: {motivo.strip()}", AZUL)
    pdf.secao("Verificações da norma")
    pdf.tabela_verificacoes(instrucao.verificacoes)
    pdf.ln(12)
    pdf.fonte_(9.5, cor=CINZA)
    pdf.cell(0, 6, pdf.t("Conferido por: ______________________________________     "
                         "Data: ____/____/________"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
    return bytes(pdf.output())
