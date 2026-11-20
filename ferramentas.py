"""As quatro ferramentas do agente que instrui pedidos de diárias.

Cada função substitui uma consulta que o servidor da Coordenadoria faz hoje à mão: o cadastro
funcional, o cálculo das diárias, o histórico de diárias e prestações de contas e o saldo da
dotação da unidade. Duas regras de projeto valem para todas:

- Minimização: devolvem ao modelo só o que a instrução usa. CPF e e-mail nem chegam a ser
  carregados (ver dados.py), e a consulta ao cadastro não revela o nome de outro servidor.
- As contas ficam no código: antecedência, quantidade, valor, prazo da prestação, soma do mês
  e comparação com o saldo saem prontos, com o veredito de cada critério da norma escrito como
  "Critério <nome>: ATENDE." ou "Critério <nome>: NÃO ATENDE.", para que o modelo apenas o
  transcreva.

Nenhuma função importa framework. A docstring é a única parte que o modelo lê, e por isso cada
uma diz quando usar a ferramenta, o que ela devolve e o formato dos argumentos.
"""
from datetime import date, timedelta

from dados import (ANTECEDENCIA_MINIMA, DATA_DA_ANALISE, HISTORICO, LIMITE_MENSAL,
                   PRAZO_PRESTACAO, SERVIDORES, UNIDADES, VALORES)

CLASSES = {"interior_mt": "interior de MT", "outra_uf": "outra UF",
           "distrito_federal": "Distrito Federal"}
AUSENTE = {"", "null", "none", "nulo", "nenhuma", "a definir", "-"}
URGENCIA = ("Exceção apenas em caso de urgência (art. 5º, § 1º): situação emergencial que não "
            "podia ser prevista, como combate a incêndio, desastre ambiental, infração ambiental "
            "em curso ou determinação judicial com prazo. O pedido urgente depende de "
            "autorização expressa e escrita do Secretário Adjunto (§ 2º); a autorização verbal "
            "não supre esta exigência.")


# ------------------------------------------------------------------ regras da norma

def classe_destino(uf: str) -> str:
    """Classe do destino no Anexo I: interior de MT, Distrito Federal ou outra UF."""
    uf = uf.strip().upper()
    if uf == "MT":
        return "interior_mt"
    if uf == "DF":
        return "distrito_federal"
    return "outra_uf"


def quantidade_diarias(partida: date, retorno: date) -> float:
    """Art. 4º: uma diária por pernoite e meia no dia do retorno; sem pernoite, meia diária."""
    pernoites = (retorno - partida).days
    return 0.5 if pernoites == 0 else pernoites + 0.5


def somar_dias_uteis(inicio: date, dias: int) -> date:
    """Soma dias úteis (segunda a sexta-feira), sem considerar feriados."""
    atual = inicio
    while dias:
        atual += timedelta(days=1)
        if atual.weekday() < 5:
            dias -= 1
    return atual


def _data(texto) -> date | None:
    try:
        return date.fromisoformat(str(texto).strip())
    except ValueError:
        return None


def _normalizar(nome: str) -> str:
    return " ".join(nome.split()).casefold()


def _veredito(criterio: str, atende: bool) -> str:
    return f"Critério {criterio}: {'ATENDE' if atende else 'NÃO ATENDE'}."


# ------------------------------------------------------------------ ferramentas

def consultar_servidor(matricula: str, nome: str) -> str:
    """Consulta o cadastro funcional e confere se o nome do pedido é o do titular da matrícula.

    Use primeiro, antes de qualquer outra ferramenta, com a matrícula e o nome exatamente como
    constam do pedido, ou da complementação, se ela corrigir a matrícula. `matricula` tem seis
    algarismos, como "204317"; `nome` é o nome completo, como "Ana Paula Figueiredo". Devolve o
    cargo, o grupo da diária (A, B ou C, exigido por calcular_diarias), a sigla da unidade de
    lotação (exigida por consultar_saldo_diarias) e o veredito do critério cadastro. Se a
    matrícula não existir ou pertencer a outro servidor, o critério cadastro não é atendido e o
    pedido vai para diligência, sem cálculo (art. 9º).
    """
    mat = matricula.strip()
    servidor = SERVIDORES.get(mat)
    if servidor is None:
        return (f"Matrícula {mat} não localizada no cadastro funcional. "
                f"{_veredito('cadastro', False)} Pedido em diligência, sem análise de mérito "
                "(art. 9º).")
    if _normalizar(nome) != _normalizar(servidor["nome"]):
        # O nome do titular da matrícula não é devolvido: é dado de um terceiro.
        return (f"A matrícula {mat} pertence a outro servidor: o nome informado no pedido "
                f"({nome.strip()}) não confere com o cadastro funcional. "
                f"{_veredito('cadastro', False)} Pedido em diligência, sem análise de mérito "
                "(art. 9º).")
    sigla = servidor["unidade"]
    return (f"Servidor localizado: matrícula {mat}, nome confere com o cadastro. "
            f"Cargo: {servidor['cargo']}. Grupo da diária: {servidor['grupo_diaria']}. "
            f"Unidade de lotação: {sigla} ({UNIDADES[sigla]['nome']}). "
            f"Sede: {servidor['municipio_sede']}. {_veredito('cadastro', True)}")


def calcular_diarias(grupo: str, destino_uf: str, data_pedido: str, data_partida: str,
                     data_retorno: str) -> str:
    """Calcula a quantidade e o valor das diárias e a antecedência do pedido.

    Use depois de consultar_servidor, com o grupo da diária que ela devolveu. `grupo` é "A",
    "B" ou "C"; `destino_uf` é a sigla da UF de destino, como "MT", "DF" ou "RO"; as três
    datas vêm do pedido no formato AAAA-MM-DD, como "2026-11-09". Se o pedido não informar a
    data de retorno, passe data_retorno="" e a ferramenta indicará a diligência. Devolve a
    quantidade de diárias (art. 4º), o valor unitário e o valor total em reais (Anexo I), a
    antecedência em dias corridos entre o pedido e a partida e os vereditos dos critérios
    dados_completos e antecedencia (art. 5º).
    """
    g = grupo.strip().upper()
    if g not in VALORES:
        return (f"Grupo '{grupo}' inválido. Use o grupo devolvido por consultar_servidor: "
                f"{', '.join(VALORES)}.")
    pedido_em, partida = _data(data_pedido), _data(data_partida)
    if pedido_em is None or partida is None:
        return ("Data do pedido ou da partida inválida. Use o formato AAAA-MM-DD, como as "
                "datas aparecem no pedido.")
    if str(data_retorno).strip().lower() in AUSENTE:
        return ("Data de retorno não informada no pedido: cálculo não realizado. "
                f"{_veredito('dados_completos', False)} Pedido em diligência, sem análise de "
                "mérito (art. 9º).")
    retorno = _data(data_retorno)
    if retorno is None:
        return f"Data de retorno inválida: '{data_retorno}'. Use o formato AAAA-MM-DD."
    if retorno < partida:
        return "A data de retorno é anterior à data de partida. Confira as datas do pedido."

    quantidade = quantidade_diarias(partida, retorno)
    classe = classe_destino(destino_uf)
    unitario = VALORES[g][classe]
    total = round(quantidade * unitario, 2)
    pernoites = (retorno - partida).days
    composicao = ("sem pernoite: meia diária" if pernoites == 0
                  else f"{pernoites} pernoite(s) + meia diária no dia do retorno")
    antecedencia = (partida - pedido_em).days

    texto = (f"Quantidade: {quantidade:.1f} diárias ({composicao}, art. 4º). "
             f"Valor unitário: R$ {unitario:.2f} (grupo {g}, {CLASSES[classe]}, Anexo I). "
             f"Valor total: R$ {total:.2f}. {_veredito('dados_completos', True)} "
             f"Antecedência: {antecedencia} dias corridos entre o pedido ({pedido_em}) e a "
             f"partida ({partida}); mínimo de {ANTECEDENCIA_MINIMA} dias (art. 5º). ")
    if antecedencia >= ANTECEDENCIA_MINIMA:
        return texto + _veredito("antecedencia", True)
    return texto + _veredito("antecedencia", False) + " " + URGENCIA


def consultar_historico_diarias(matricula: str, data_partida: str,
                                quantidade_pedida: float) -> str:
    """Consulta as prestações de contas pendentes e as diárias já concedidas no mês da partida.

    Use depois de calcular_diarias, com a quantidade de diárias que ela devolveu. `matricula`
    tem seis algarismos, como "203648"; `data_partida` vem do pedido no formato AAAA-MM-DD;
    `quantidade_pedida` é a quantidade calculada, com ponto decimal, como 3.5. Devolve, na data
    da análise, cada prestação de contas pendente com o seu prazo (vencida ou ainda no prazo),
    a soma das diárias do mês da partida com as pedidas e os vereditos dos critérios
    prestacao_contas (art. 7º) e limite_mensal (art. 6º).
    """
    mat = matricula.strip()
    if mat not in SERVIDORES:
        return f"Matrícula {mat} não localizada no cadastro funcional."
    partida = _data(data_partida)
    if partida is None:
        return f"Data de partida inválida: '{data_partida}'. Use o formato AAAA-MM-DD."
    pedidas = float(quantidade_pedida)
    registros = [h for h in HISTORICO if h["matricula"] == mat]

    partes = [f"Histórico da matrícula {mat} na data da análise ({DATA_DA_ANALISE})."]
    pendentes = [h for h in registros if h["prestacao_contas"] == "pendente"]
    vencidas = 0
    for h in pendentes:
        prazo = somar_dias_uteis(date.fromisoformat(h["data_retorno"]), PRAZO_PRESTACAO)
        if prazo < DATA_DA_ANALISE:
            vencidas += 1
            situacao = f"o prazo venceu em {prazo}: VENCIDA"
        else:
            situacao = f"ainda no prazo, que vai até {prazo}"
        partes.append(f"Prestação de contas do pedido {h['pedido']} (retorno em "
                      f"{h['data_retorno']}): pendente, {situacao}.")
    if not pendentes:
        partes.append("Nenhuma prestação de contas pendente.")
    partes.append(f"Prazo de {PRAZO_PRESTACAO} dias úteis após o retorno, sem considerar "
                  f"feriados (art. 7º). {_veredito('prestacao_contas', vencidas == 0)}")

    mes = partida.isoformat()[:7]
    do_mes = [h for h in registros if h["data_partida"][:7] == mes]
    concedidas = sum(h["quantidade"] for h in do_mes)
    total = concedidas + pedidas
    detalhe = "; ".join(f"{h['pedido']}: {h['quantidade']:.1f}" for h in do_mes) or "nenhuma"
    partes.append(f"Diárias no mês da partida ({mes}): {concedidas:.1f} já concedidas "
                  f"({detalhe}) + {pedidas:.1f} pedidas = {total:.1f}; limite de "
                  f"{LIMITE_MENSAL:.0f} por mês (art. 6º). "
                  f"{_veredito('limite_mensal', total <= LIMITE_MENSAL)}")
    return " ".join(partes)


def consultar_saldo_diarias(unidade: str, valor: float) -> str:
    """Consulta o saldo da dotação de diárias de uma unidade e o compara com o valor pedido.

    Use depois de calcular o valor total das diárias. `unidade` é a sigla da unidade de
    lotação devolvida pelo cadastro, como CFF ou GAB; `valor` é o total em reais, com ponto
    decimal, como 980.0. Devolve o saldo disponível, a indicação de saldo suficiente ou
    insuficiente para o pedido e o veredito do critério saldo_orcamentario (art. 8º).
    """
    sigla = unidade.strip().upper()
    if sigla not in UNIDADES:
        return f"Unidade '{unidade}' não localizada. Siglas válidas: {', '.join(UNIDADES)}."
    saldo = UNIDADES[sigla]["saldo_diarias"]
    suficiente = saldo >= float(valor)
    situacao = "suficiente" if suficiente else "INSUFICIENTE"
    return (f"Saldo da unidade {sigla}: R$ {saldo:.2f}. Saldo {situacao} para "
            f"R$ {float(valor):.2f} (art. 8º). {_veredito('saldo_orcamentario', suficiente)}")


# Ordem em que o agente deve consultá-las, que é a ordem das dependências entre os dados.
FERRAMENTAS = [consultar_servidor, calcular_diarias, consultar_historico_diarias,
               consultar_saldo_diarias]
