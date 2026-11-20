"""Barreira no código: confere a instrução antes que ela chegue ao conferente.

A instrução de sistema é um pedido ao modelo, e não uma garantia; a barreira pertence ao
código (Aula 01, Seção 8; Aula 03, Seção 6.3). Esta verificação é código comum, sem modelo,
executada sobre o que a aplicação tem em mãos: o pedido, a complementação, as chamadas de
ferramenta registradas na execução (resposta.tools) e a instrução devolvida.

A barreira não julga a urgência, que é o único julgamento do modelo. Ela confere que todo dado
da instrução veio do pedido ou das ferramentas, em quatro grupos:

1. argumentos ancorados no pedido: toda matrícula consultada e toda data usada constam do
   pedido ou da complementação (exigência do enunciado), assim como o nome e a UF;
2. argumentos ancorados nas ferramentas: o grupo e a unidade vêm do cadastro, e a quantidade e
   o valor vêm do cálculo (ancoragem numérica, Aula 04);
3. instrução ancorada: número, matrícula, quantidade, valor, verificações e valores em reais
   citados no texto coincidem com o que as ferramentas devolveram, e a recomendação é a que os
   vereditos das ferramentas impõem;
4. completude e sigilo: recomendação de mérito só com as quatro consultas feitas, e nenhum CPF
   ou dado bancário no texto da instrução.

`verificar` devolve a lista de motivos de recusa; lista vazia significa instrução aprovada.
"""
import re
from dataclasses import dataclass

from contrato import CRITERIOS, Instrucao
from ferramentas import AUSENTE
from filtro_dados_pessoais import PADROES


@dataclass
class Chamada:
    """Uma chamada de ferramenta registrada na execução (um item de resposta.tools)."""
    ferramenta: str
    argumentos: dict
    resultado: str


VEREDITO = re.compile(r"Critério (\w+): (ATENDE|NÃO ATENDE)\.")
DATA_ISO = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
MATRICULA = re.compile(r"\b\d{6}\b")
REAIS = re.compile(r"R\$\s?(\d[\d.,]*\d|\d)")
MILHAR_SEM_CENTAVOS = re.compile(r"^\d{1,3}(\.\d{3})+$")
DADO_PESSOAL = [re.compile(padrao) for padrao in PADROES.values()]
TOLERANCIA = 0.01
CONSULTAS_DE_MERITO = ("cadastro", "antecedencia", "prestacao_contas", "limite_mensal",
                       "saldo_orcamentario")


# ------------------------------------------------------------------ utilidades

def _texto(valor) -> str:
    """Texto limpo; valores que significam "ausente" ("null", "a definir"…) viram ""."""
    texto = "" if valor is None else str(valor).strip()
    return "" if texto.lower() in AUSENTE else texto


def _nome(texto) -> str:
    return " ".join(str(texto).split()).casefold()


def _numero(valor) -> float | None:
    try:
        return float(valor)
    except (TypeError, ValueError):
        return None


def _reais(bruto: str) -> float | None:
    """Converte valores como '1.800,00', '1800.00', '1.800' ou '980' em número."""
    texto = bruto.strip()
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    elif MILHAR_SEM_CENTAVOS.match(texto):
        texto = texto.replace(".", "")
    return _numero(texto)


def _extrair(padrao: str, texto: str) -> str | None:
    achado = re.search(padrao, texto)
    return achado.group(1) if achado else None


def _ultima(chamadas: list[Chamada], ferramenta: str, contendo: str) -> Chamada | None:
    """A última chamada da ferramenta cujo resultado contém o trecho indicado."""
    for chamada in reversed(chamadas):
        if chamada.ferramenta == ferramenta and contendo in chamada.resultado:
            return chamada
    return None


def pedido_efetivo(pedido: dict, complementacao: dict | None) -> dict:
    """O pedido com as correções da complementação aplicadas.

    A complementação chega como texto livre. Uma data no texto completa a data de retorno
    ausente; seis algarismos no texto corrigem a matrícula.
    """
    efetivo = dict(pedido)
    if complementacao:
        texto = complementacao["texto"]
        datas = DATA_ISO.findall(texto)
        if datas and not _texto(pedido.get("data_retorno")):
            efetivo["data_retorno"] = datas[0]
        matriculas = MATRICULA.findall(texto)
        if matriculas:
            efetivo["matricula"] = matriculas[0]
    return efetivo


# ------------------------------------------------------------------ as quatro conferências

def _argumentos_no_pedido(pedido: dict, efetivo: dict, chamadas: list[Chamada]) -> list[str]:
    motivos = []
    matriculas = {pedido["matricula"], efetivo["matricula"]}
    datas = {"data_pedido": _texto(efetivo["data_pedido"]),
             "data_partida": _texto(efetivo["data_partida"]),
             "data_retorno": _texto(efetivo.get("data_retorno"))}
    for chamada in chamadas:
        argumentos = chamada.argumentos
        if "matricula" in argumentos and _texto(argumentos["matricula"]) not in matriculas:
            motivos.append(f"{chamada.ferramenta} consultou a matrícula "
                           f"{argumentos['matricula']}, que não consta do pedido nem da "
                           "complementação")
        if "nome" in argumentos and _nome(argumentos["nome"]) != _nome(pedido["nome"]):
            motivos.append(f"{chamada.ferramenta} usou o nome '{argumentos['nome']}', diferente "
                           "do nome do pedido")
        for campo, esperada in datas.items():
            if campo in argumentos and _texto(argumentos[campo]) != esperada:
                motivos.append(f"{chamada.ferramenta} usou {campo}='{argumentos[campo]}', mas o "
                               f"pedido e a complementação informam '{esperada or 'nenhuma'}'")
        if ("destino_uf" in argumentos
                and _texto(argumentos["destino_uf"]).upper() != pedido["destino_uf"].upper()):
            motivos.append(f"{chamada.ferramenta} usou a UF {argumentos['destino_uf']}, mas o "
                           f"pedido informa {pedido['destino_uf']}")
    return motivos


def _argumentos_nas_ferramentas(chamadas: list[Chamada], cadastro: Chamada | None,
                                calculo: Chamada | None) -> list[str]:
    motivos = []
    grupo = _extrair(r"Grupo da diária: (\w)", cadastro.resultado) if cadastro else None
    unidade = _extrair(r"Unidade de lotação: (\w+)", cadastro.resultado) if cadastro else None
    quantidade = _numero(_extrair(r"Quantidade: (\d+\.\d) diárias", calculo.resultado)) if calculo else None
    valor = _numero(_extrair(r"Valor total: R\$ (\d+\.\d{2})", calculo.resultado)) if calculo else None

    for chamada in chamadas:
        argumentos = chamada.argumentos
        if chamada.ferramenta == "calcular_diarias":
            if grupo is None:
                motivos.append("calcular_diarias foi chamada sem um cadastro conferido")
            elif _texto(argumentos.get("grupo")).upper() != grupo:
                motivos.append(f"calcular_diarias usou o grupo {argumentos.get('grupo')}, mas o "
                               f"cadastro informa o grupo {grupo}")
        elif chamada.ferramenta == "consultar_historico_diarias":
            pedida = _numero(argumentos.get("quantidade_pedida"))
            if quantidade is None or pedida is None or abs(pedida - quantidade) > TOLERANCIA:
                motivos.append(f"consultar_historico_diarias usou a quantidade "
                               f"{argumentos.get('quantidade_pedida')}, que não é a devolvida "
                               "por calcular_diarias")
        elif chamada.ferramenta == "consultar_saldo_diarias":
            if unidade is None or _texto(argumentos.get("unidade")).upper() != unidade:
                motivos.append(f"consultar_saldo_diarias usou a unidade "
                               f"{argumentos.get('unidade')}, que não é a do cadastro")
            pedido_em_reais = _numero(argumentos.get("valor"))
            if valor is None or pedido_em_reais is None or abs(pedido_em_reais - valor) > TOLERANCIA:
                motivos.append(f"consultar_saldo_diarias usou o valor {argumentos.get('valor')}, "
                               "que não é o devolvido por calcular_diarias")
    return motivos


def _instrucao_ancorada(pedido: dict, efetivo: dict, chamadas: list[Chamada],
                        cadastro: Chamada | None, calculo: Chamada | None,
                        instrucao: Instrucao) -> list[str]:
    motivos = []

    # Identificação
    if instrucao.numero_pedido.strip() != pedido["numero"]:
        motivos.append(f"a instrução se refere ao pedido {instrucao.numero_pedido}, e não a "
                       f"{pedido['numero']}")
    matricula = _texto(cadastro.argumentos.get("matricula")) if cadastro else None
    if matricula and instrucao.matricula.strip() != matricula:
        motivos.append(f"a instrução traz a matrícula {instrucao.matricula}, mas o cadastro "
                       f"conferido é o da matrícula {matricula}")
    elif not matricula and instrucao.matricula.strip() not in {pedido["matricula"], efetivo["matricula"]}:
        motivos.append(f"a matrícula {instrucao.matricula} não consta do pedido nem da "
                       "complementação")

    # Vereditos devolvidos pelas ferramentas (o último de cada critério prevalece)
    vereditos: dict[str, bool] = {}
    for chamada in chamadas:
        for criterio, situacao in VEREDITO.findall(chamada.resultado):
            vereditos[criterio] = situacao == "ATENDE"
    completo = bool(_texto(efetivo.get("data_retorno")))
    urgencia = instrucao.exige_autorizacao_superior

    # Verificações: uma por critério, cada uma igual ao veredito da ferramenta
    por_criterio = {}
    for verificacao in instrucao.verificacoes:
        if verificacao.criterio in por_criterio:
            motivos.append(f"o critério {verificacao.criterio} aparece mais de uma vez")
        por_criterio[verificacao.criterio] = verificacao
    for criterio in CRITERIOS:
        if criterio not in por_criterio:
            motivos.append(f"falta a verificação do critério {criterio}")
    for criterio, verificacao in por_criterio.items():
        if criterio in vereditos:
            esperada = "atende" if vereditos[criterio] else "nao_atende"
            excecao_por_urgencia = (criterio == "antecedencia" and esperada == "nao_atende"
                                    and verificacao.situacao == "atende" and urgencia)
            if verificacao.situacao != esperada and not excecao_por_urgencia:
                motivos.append(f"a verificação {criterio} diz {verificacao.situacao}, mas a "
                               f"ferramenta devolveu {esperada}")
        elif criterio == "dados_completos" and verificacao.situacao != "nao_verificado":
            esperada = "atende" if completo else "nao_atende"
            if verificacao.situacao != esperada:
                motivos.append(f"a verificação dados_completos diz {verificacao.situacao}, mas o "
                               f"pedido {'traz' if completo else 'não traz'} a data de retorno")
        elif criterio != "dados_completos" and verificacao.situacao != "nao_verificado":
            motivos.append(f"a verificação {criterio} diz {verificacao.situacao} sem que a "
                           "ferramenta que decide o critério tenha sido consultada")

    # Recomendação imposta pelos vereditos
    nao_atendidos = {criterio for criterio, atende in vereditos.items() if not atende}
    if not completo:
        nao_atendidos.add("dados_completos")
    if urgencia and "antecedencia" not in nao_atendidos:
        motivos.append("exige_autorizacao_superior é verdadeiro, mas a ferramenta não apontou "
                       "antecedência insuficiente")
    impedimentos = nao_atendidos - ({"antecedencia"} if urgencia else set())
    if {"cadastro", "dados_completos"} & impedimentos:
        esperada = "diligencia"
    elif impedimentos:
        esperada = "nao_recomendado"
    else:
        esperada = "apto_para_autorizacao"
    if instrucao.recomendacao != esperada:
        motivos.append(f"a recomendação é {instrucao.recomendacao}, mas os vereditos das "
                       f"ferramentas impõem {esperada}")
    if urgencia and esperada != "apto_para_autorizacao":
        motivos.append("a autorização superior só se aplica a pedido apto para autorização")

    # Quantidade e valor
    if instrucao.recomendacao == "diligencia":
        if instrucao.quantidade_diarias is not None or instrucao.valor_total is not None:
            motivos.append("na diligência, quantidade e valor devem ser nulos (art. 9º)")
        if not any(por_criterio.get(c) and por_criterio[c].situacao == "nao_atende"
                   for c in ("cadastro", "dados_completos")):
            motivos.append("a diligência não marca como nao_atende o critério que a motiva")
    else:
        for criterio in CONSULTAS_DE_MERITO:
            if criterio not in vereditos:
                motivos.append(f"recomendação de mérito sem a consulta que decide {criterio}")
        quantidade = _numero(_extrair(r"Quantidade: (\d+\.\d) diárias", calculo.resultado)) if calculo else None
        valor = _numero(_extrair(r"Valor total: R\$ (\d+\.\d{2})", calculo.resultado)) if calculo else None
        for rotulo, dito, devolvido in (("quantidade_diarias", instrucao.quantidade_diarias, quantidade),
                                         ("valor_total", instrucao.valor_total, valor)):
            if devolvido is None or dito is None or abs(dito - devolvido) > TOLERANCIA:
                motivos.append(f"{rotulo} = {dito}, mas calcular_diarias devolveu {devolvido}")

    # Valores em reais citados no texto
    autorizados = {v for c in chamadas for bruto in REAIS.findall(c.resultado)
                   if (v := _reais(bruto)) is not None}
    for texto in _textos(instrucao):
        for bruto in REAIS.findall(texto):
            citado = _reais(bruto)
            if citado is None or all(abs(citado - a) > TOLERANCIA for a in autorizados):
                motivos.append(f"o texto da instrução cita R$ {bruto}, valor que nenhuma "
                               "ferramenta devolveu")
    return motivos


def _textos(instrucao: Instrucao) -> list[str]:
    return [instrucao.minuta_despacho, *instrucao.pendencias, *instrucao.alertas,
            *(v.detalhe for v in instrucao.verificacoes)]


def _sigilo(instrucao: Instrucao) -> list[str]:
    if any(padrao.search(texto) for texto in _textos(instrucao) for padrao in DADO_PESSOAL):
        return ["o texto da instrução contém um número com formato de CPF ou de dado bancário"]
    return []


# ------------------------------------------------------------------ ponto de entrada

def verificar(pedido: dict, complementacao: dict | None, chamadas: list[Chamada],
              instrucao: Instrucao) -> list[str]:
    """Confere a instrução contra o pedido e as ferramentas; devolve os motivos de recusa."""
    efetivo = pedido_efetivo(pedido, complementacao)
    cadastro = _ultima(chamadas, "consultar_servidor", "Critério cadastro: ATENDE.")
    calculo = _ultima(chamadas, "calcular_diarias", "Quantidade:")
    return [*_argumentos_no_pedido(pedido, efetivo, chamadas),
            *_argumentos_nas_ferramentas(chamadas, cadastro, calculo),
            *_instrucao_ancorada(pedido, efetivo, chamadas, cadastro, calculo, instrucao),
            *_sigilo(instrucao)]
