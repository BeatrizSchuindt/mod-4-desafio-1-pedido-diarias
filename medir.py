"""Mede o agente contra o gabarito, em três rodadas, com as chamadas paralelas de ferramentas
desligadas (configuração A, a do sistema) ou ligadas (configuração B).

Cada rodada instrui os 12 pedidos e, logo depois do DIA-2026-0111 e do DIA-2026-0112, envia a
complementação na mesma sessão, como no formulário: 14 execuções por rodada. Cada rodada usa um
banco próprio, criado vazio (bancos/medicao_A1.db, ...), que é apagado no fim: ele guarda dados
pessoais e não serve a mais nada depois da medição. O gabarito.json é lido só aqui; o agente
nunca o vê.

Cada execução cai numa de cinco categorias. A comparação com o gabarito usa cinco campos:
recomendação, quantidade, valor, autorização superior e critérios não atendidos.

  certo               entregue e igual ao gabarito;
  erro silencioso     entregue e diferente do gabarito: chegaria ao conferente como se
                      estivesse certo (o pior desfecho);
  recusa correta      a barreira recusou uma instrução diferente do gabarito: o erro ficou
                      visível e o pedido voltou à análise manual;
  falso positivo      a barreira recusou uma instrução igual ao gabarito nos cinco campos. A
                      barreira também confere argumentos e texto, que o gabarito não cobre; por
                      isso os motivos são impressos, para conferência caso a caso;
  falha de execução   erro da API ou resposta fora do contrato.

Uso (uma configuração por vez; cerca de US$ 0,20 e 8 a 10 minutos cada):
  python medir.py --config A | tee resultados/medicao_A.txt
  python medir.py --config B | tee resultados/medicao_B.txt
  python medir.py --comparar | tee resultados/medicao_comparacao.txt
"""
import argparse
import json
import time
from pathlib import Path
from statistics import median

from agente import TOOL_CALL_LIMIT, construir_agente, instruir
from dados import COMPLEMENTACOES, PEDIDOS

BASE = Path(__file__).parent
PASTA_BANCOS = BASE / "bancos"
PASTA_RESULTADOS = BASE / "resultados"
GABARITO = json.loads((BASE / "exemplos" / "gabarito.json").read_text(encoding="utf-8"))

CONFIGURACOES = {"A": ("paralelas desligadas", False), "B": ("paralelas ligadas", True)}
CATEGORIAS = ("certo", "erro silencioso", "recusa correta", "falso positivo", "falha de execução")
CAMPOS = ("recomendacao", "quantidade", "valor", "autorizacao_superior", "nao_atendidos")
TOLERANCIA = 0.01

# Volume e estimativas do desenho.md (Seção 5), para o confronto com o medido.
VOLUME_MENSAL = {"completo": 333, "diligencia": 67, "complementacao": 67}
ESTIMADO = {"completo": {"passos": 5, "entrada": 11_500, "usd": 0.00333},
            "diligencia": {"passos": 2, "entrada": 4_240, "usd": 0.00174},
            "complementacao": {"passos": 5, "entrada": 15_500, "usd": 0.00413}}
ESTIMADO_PRIMEIRA_CHAMADA = 2_060
ESTIMADO_ACRESCIMO = (90, 150)
ESTIMADO_MES = 1.50
TIPOS = {"completo": "pedido completo", "diligencia": "diligência",
         "complementacao": "complementação"}

# Dependências entre as ferramentas (Aula 06, Seção 4.3): cada uma precisa do resultado das
# anteriores. Pedir juntas duas ferramentas dependentes obriga o modelo a supor um dado.
DEPENDE_DE = {"calcular_diarias": {"consultar_servidor"},
              "consultar_historico_diarias": {"consultar_servidor", "calcular_diarias"},
              "consultar_saldo_diarias": {"consultar_servidor", "calcular_diarias"}}


def lote_fora_de_ordem(lote: list[str]) -> bool:
    """Um lote (ferramentas pedidas na mesma chamada) com uma ferramenta e outra de que ela depende."""
    return any(DEPENDE_DE.get(f, set()) & set(lote) for f in lote)


# A sequência de uma rodada: cada complementação logo depois do seu pedido, na mesma sessão.
ROTEIRO = []
for _numero in PEDIDOS:
    ROTEIRO.append((_numero, None))
    if _numero in COMPLEMENTACOES:
        ROTEIRO.append((_numero, COMPLEMENTACOES[_numero]))


# ------------------------------------------------------------------ formatação

def br(valor: float, casas: int = 0) -> str:
    """Número no formato brasileiro: 15.840 ou 0,00430."""
    texto = f"{valor:,.{casas}f}"
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(parte: int, todo: int) -> str:
    return f"{br(100 * parte / todo, 0)}%" if todo else "-"


# ------------------------------------------------------------------ comparação com o gabarito

def campos_obtidos(instrucao) -> dict:
    return {"recomendacao": instrucao.recomendacao,
            "quantidade": instrucao.quantidade_diarias,
            "valor": instrucao.valor_total,
            "autorizacao_superior": instrucao.exige_autorizacao_superior,
            "nao_atendidos": sorted(v.criterio for v in instrucao.verificacoes
                                    if v.situacao == "nao_atende")}


def campos_esperados(gabarito: dict) -> dict:
    return {"recomendacao": gabarito["recomendacao"],
            "quantidade": gabarito["quantidade_diarias"],
            "valor": gabarito["valor_total"],
            "autorizacao_superior": gabarito["exige_autorizacao_superior"],
            "nao_atendidos": sorted(gabarito["criterios_nao_atendidos"])}


def igual(obtido, esperado) -> bool:
    numeros = all(isinstance(v, (int, float)) and not isinstance(v, bool)
                  for v in (obtido, esperado))
    return abs(obtido - esperado) <= TOLERANCIA if numeros else obtido == esperado


def tipo_da_execucao(numero: str, complementacao) -> str:
    if complementacao:
        return "complementacao"
    return "diligencia" if GABARITO["pedidos"][numero]["recomendacao"] == "diligencia" else "completo"


def avaliar(rodada: str, numero: str, complementacao, resultado) -> dict:
    """Uma linha da medição: categoria, campos comparados, ferramentas e medidas."""
    gabarito = (GABARITO["complementacoes"] if complementacao else GABARITO["pedidos"])[numero]
    esperado = campos_esperados(gabarito)
    instrucao = resultado.instrucao or resultado.instrucao_recusada
    obtido = campos_obtidos(instrucao) if instrucao else None
    certos = {c: igual(obtido[c], esperado[c]) for c in CAMPOS} if obtido else None
    tudo_certo = bool(certos) and all(certos.values())
    if resultado.situacao == "erro":
        categoria = "falha de execução"
    elif resultado.situacao == "entregue":
        categoria = "certo" if tudo_certo else "erro silencioso"
    else:
        categoria = "falso positivo" if tudo_certo else "recusa correta"
    m = resultado.medidas
    return {"rodada": rodada, "pedido": numero,
            "turno": "complementacao" if complementacao else "pedido",
            "tipo": tipo_da_execucao(numero, complementacao),
            "situacao": resultado.situacao, "categoria": categoria,
            "obtido": obtido, "esperado": esperado, "campos_certos": certos,
            "motivos": resultado.motivos,
            "ferramentas": [c.ferramenta for c in resultado.consultas],
            "segundos": m.get("segundos", 0.0),
            "chamadas_ao_modelo": m.get("chamadas_ao_modelo", 0),
            "entrada_por_chamada": m.get("entrada_por_chamada", []),
            "ferramentas_por_chamada": m.get("ferramentas_por_chamada", []),
            "max_ferramentas_por_chamada": max(map(len, m.get("ferramentas_por_chamada", [])),
                                               default=0),
            "paralela_fora_de_ordem": any(map(lote_fora_de_ordem,
                                              m.get("ferramentas_por_chamada", []))),
            "tokens_entrada": m.get("tokens_entrada", 0),
            "tokens_saida": m.get("tokens_saida", 0),
            "custo_usd": m.get("custo_usd", 0.0)}


# ------------------------------------------------------------------ execução

def apagar_banco(banco: Path) -> None:
    for arquivo in banco.parent.glob(banco.name + "*"):      # .db, -wal, -shm, -journal
        arquivo.unlink()


def imprimir_execucao(linha: dict) -> None:
    rotulo = f"{linha['pedido']}{' (compl.)' if linha['turno'] == 'complementacao' else ''}"
    print(f"  {linha['rodada']:3} {rotulo:22} {linha['categoria']:18} "
          f"{len(linha['ferramentas'])} consultas · {linha['chamadas_ao_modelo']} chamadas · "
          f"{br(linha['tokens_entrada']):>6} tokens · US$ {br(linha['custo_usd'], 5)} · "
          f"{br(linha['segundos'], 1)} s"
          + (" · paralelas" if linha["max_ferramentas_por_chamada"] > 1 else "")
          + (" FORA DA ORDEM" if linha["paralela_fora_de_ordem"] else ""))
    if linha["categoria"] != "certo":
        if linha["campos_certos"]:
            for campo, certo in linha["campos_certos"].items():
                if not certo:
                    print(f"        {campo}: obtido {linha['obtido'][campo]} × "
                          f"gabarito {linha['esperado'][campo]}")
        for motivo in linha["motivos"][:3]:
            print(f"        motivo: {motivo}")


def medir(config: str, rodadas: int) -> list[dict]:
    rotulo, paralelas = CONFIGURACOES[config]
    print(f"Configuração {config} ({rotulo}): {rodadas} rodada(s) de {len(ROTEIRO)} execuções\n")
    linhas = []
    for n in range(1, rodadas + 1):
        rodada = f"{config}{n}"
        banco = PASTA_BANCOS / f"medicao_{rodada}.db"
        apagar_banco(banco)                       # sobra de uma medição interrompida
        agente = construir_agente(paralelas=paralelas, memoria="historico", banco=banco)
        print(f"[rodada {rodada}] banco {banco.relative_to(BASE)}, criado vazio")
        for numero, complementacao in ROTEIRO:
            resultado = instruir(PEDIDOS[numero], complementacao, agente=agente)
            linha = avaliar(rodada, numero, complementacao, resultado)
            imprimir_execucao(linha)
            linhas.append(linha)
        apagar_banco(banco)
        certos = sum(l["categoria"] == "certo" for l in linhas if l["rodada"] == rodada)
        print(f"  rodada {rodada}: {certos} de {len(ROTEIRO)} certas; banco apagado\n")
    return linhas


# ------------------------------------------------------------------ resumo

def _estat(valores: list[float]) -> dict:
    if not valores:
        return {"n": 0, "mediana": 0, "maximo": 0, "cauda": 0}
    med, mx = median(valores), max(valores)
    return {"n": len(valores), "mediana": med, "maximo": mx, "cauda": mx / med if med else 0}


def resumir(linhas: list[dict]) -> dict:
    rodadas = sorted({l["rodada"] for l in linhas}, key=lambda r: int(r[1:]))
    por_rodada = {r: {c: sum(l["categoria"] == c for l in linhas if l["rodada"] == r)
                      for c in CATEGORIAS} for r in rodadas}
    com_instrucao = [l for l in linhas if l["campos_certos"]]
    campo_a_campo = {c: sum(l["campos_certos"][c] for l in com_instrucao) for c in CAMPOS}

    urgencia = {}
    for numero in ("DIA-2026-0106", "DIA-2026-0107"):
        execucoes = [l for l in linhas if l["pedido"] == numero]
        urgencia[numero] = {
            "execucoes": len(execucoes),
            "autorizacao_certa": sum(bool(l["campos_certos"])
                                     and l["campos_certos"]["autorizacao_superior"]
                                     for l in execucoes),
            "certas": sum(l["categoria"] == "certo" for l in execucoes)}

    distribuicao = {}
    for tipo in TIPOS:
        do_tipo = [l for l in linhas if l["tipo"] == tipo and l["situacao"] != "erro"]
        distribuicao[tipo] = {
            "chamadas": _estat([l["chamadas_ao_modelo"] for l in do_tipo]),
            "entrada": _estat([l["tokens_entrada"] for l in do_tipo]),
            "saida": _estat([l["tokens_saida"] for l in do_tipo]),
            "usd": _estat([l["custo_usd"] for l in do_tipo]),
            "segundos": _estat([l["segundos"] for l in do_tipo]),
            "primeira_chamada": _estat([l["entrada_por_chamada"][0] for l in do_tipo
                                        if l["entrada_por_chamada"]])}

    # Acréscimo de entrada entre chamadas consecutivas de um pedido completo
    acrescimos = [b - a for l in linhas if l["tipo"] == "completo"
                  for a, b in zip(l["entrada_por_chamada"], l["entrada_por_chamada"][1:])]

    def mensal(chave: str) -> float:
        return sum(VOLUME_MENSAL[t] * distribuicao[t]["usd"][chave] for t in TIPOS)

    return {
        "execucoes": len(linhas), "rodadas": rodadas, "por_rodada": por_rodada,
        "categorias": {c: sum(l["categoria"] == c for l in linhas) for c in CATEGORIAS},
        "certas_por_rodada": [por_rodada[r]["certo"] for r in rodadas],
        "com_instrucao": len(com_instrucao), "campo_a_campo": campo_a_campo,
        "urgencia": urgencia, "distribuicao": distribuicao,
        "acrescimo_por_chamada": _estat(acrescimos),
        "max_consultas_numa_execucao": max((len(l["ferramentas"]) for l in linhas), default=0),
        "max_ferramentas_numa_chamada": max((l["max_ferramentas_por_chamada"] for l in linhas),
                                            default=0),
        "execucoes_com_paralelas": sum(l["max_ferramentas_por_chamada"] > 1 for l in linhas),
        "execucoes_fora_de_ordem": sum(l["paralela_fora_de_ordem"] for l in linhas),
        "execucoes_com_consulta_repetida": sum(len(l["ferramentas"]) != len(set(l["ferramentas"]))
                                              for l in linhas),
        "custo_mensal": {"mediana": mensal("mediana"), "cauda": mensal("maximo")},
        "custo_total": sum(l["custo_usd"] for l in linhas),
        "segundos_total": sum(l["segundos"] for l in linhas)}


def imprimir_resumo(config: str, r: dict) -> None:
    n_rodada = len(ROTEIRO)
    print("=" * 100)
    print(f"Resumo da configuração {config} ({CONFIGURACOES[config][0]}): "
          f"{r['execucoes']} execuções em {len(r['rodadas'])} rodada(s)\n")

    print("[1] Categorias por rodada")
    print(f"  {'rodada':8}" + "".join(f"{c:>19}" for c in CATEGORIAS))
    for rodada, contagem in r["por_rodada"].items():
        print(f"  {rodada:8}" + "".join(f"{contagem[c]:>19}" for c in CATEGORIAS))
    print(f"  {'total':8}" + "".join(f"{r['categorias'][c]:>19}" for c in CATEGORIAS))
    if r["categorias"]["falso positivo"]:
        print("\n  Falso positivo = recusa com os cinco campos iguais ao gabarito. Confira os motivos "
              "acima: se\n  apontarem argumento suposto ou texto sem âncora, a recusa foi devida, "
              "porque o gabarito não\n  cobre argumentos nem texto.")
    certas = r["certas_por_rodada"]
    print(f"\n  Acertos por rodada: {', '.join(map(str, certas))} de {n_rodada} "
          f"(faixa de {min(certas)} a {max(certas)}; {pct(sum(certas), r['execucoes'])} no total)")

    print(f"\n[2] Acerto campo a campo, nas {r['com_instrucao']} execuções que produziram instrução "
          "(entregue ou recusada)")
    for campo, acertos in r["campo_a_campo"].items():
        print(f"  {campo:22} {acertos:>3} de {r['com_instrucao']} ({pct(acertos, r['com_instrucao'])})")

    print("\n[3] Urgência: o único julgamento do modelo")
    u6, u7 = r["urgencia"]["DIA-2026-0106"], r["urgencia"]["DIA-2026-0107"]
    print(f"  DIA-2026-0106 (urgência legítima): autorização superior certa em "
          f"{u6['autorizacao_certa']} de {u6['execucoes']}; instrução certa em {u6['certas']}")
    print(f"  DIA-2026-0107 (ordem embutida): autorização superior certa em "
          f"{u7['autorizacao_certa']} de {u7['execucoes']}; instrução certa em {u7['certas']}")

    print("\n[4] Distribuição por tipo de execução (mediana · máximo · cauda = máximo/mediana)")
    print(f"  {'tipo':16} {'n':>3} {'chamadas':>12} {'entrada (tokens)':>22} {'saída':>14} "
          f"{'US$':>20} {'segundos':>14} {'cauda US$':>10}")
    for tipo, d in r["distribuicao"].items():
        if not d["usd"]["n"]:
            continue
        print(f"  {TIPOS[tipo]:16} {d['usd']['n']:>3} "
              f"{d['chamadas']['mediana']:>5g} · {d['chamadas']['maximo']:<4g} "
              f"{br(d['entrada']['mediana']):>9} · {br(d['entrada']['maximo']):<9} "
              f"{br(d['saida']['mediana']):>5} · {br(d['saida']['maximo']):<6} "
              f"{br(d['usd']['mediana'], 5):>9} · {br(d['usd']['maximo'], 5):<8} "
              f"{br(d['segundos']['mediana'], 1):>5} · {br(d['segundos']['maximo'], 1):<6} "
              f"{br(d['usd']['cauda'], 2):>9}x")

    print("\n[5] Ferramentas")
    print(f"  Maior número de consultas numa execução: {r['max_consultas_numa_execucao']} "
          f"(teto: tool_call_limit={TOOL_CALL_LIMIT})")
    print(f"  Maior número de ferramentas pedidas numa mesma chamada ao modelo: "
          f"{r['max_ferramentas_numa_chamada']}")
    print(f"  Execuções com chamadas paralelas: {r['execucoes_com_paralelas']} de {r['execucoes']}")
    print(f"  Execuções com paralelas fora da ordem de dependência (uma ferramenta pedida junto com "
          f"outra de que depende): {r['execucoes_fora_de_ordem']} de {r['execucoes']}")
    print(f"  Execuções que repetiram uma consulta: {r['execucoes_com_consulta_repetida']} "
          f"de {r['execucoes']}")

    print(f"\n[6] Custo mensal: 400 pedidos ({VOLUME_MENSAL['completo']} completos, "
          f"{VOLUME_MENSAL['diligencia']} diligências, {VOLUME_MENSAL['complementacao']} "
          "complementações)")
    print(f"  pela mediana de cada tipo: US$ {br(r['custo_mensal']['mediana'], 2)}")
    print(f"  pelo máximo de cada tipo (cauda): US$ {br(r['custo_mensal']['cauda'], 2)}")

    print("\n[7] Estimado (desenho.md) × medido (mediana)")
    print(f"  {'tipo':16} {'passos':>13} {'entrada (tokens)':>22} {'US$':>22} {'diferença US$':>14}")
    for tipo, est in ESTIMADO.items():
        d = r["distribuicao"][tipo]
        if not d["usd"]["n"]:
            continue
        dif = (d["usd"]["mediana"] - est["usd"]) / est["usd"] * 100
        print(f"  {TIPOS[tipo]:16} {est['passos']:>5} × {d['chamadas']['mediana']:<5g} "
              f"{br(est['entrada']):>9} × {br(d['entrada']['mediana']):<10} "
              f"{br(est['usd'], 5):>9} × {br(d['usd']['mediana'], 5):<10} {dif:>+12.0f}%")
    primeira = r["distribuicao"]["completo"]["primeira_chamada"]
    acrescimo = r["acrescimo_por_chamada"]
    print(f"  primeira chamada (pedido completo): estimada {br(ESTIMADO_PRIMEIRA_CHAMADA)} × "
          f"medida {br(primeira['mediana'])} tokens")
    print(f"  acréscimo por chamada: estimado {ESTIMADO_ACRESCIMO[0]} a {ESTIMADO_ACRESCIMO[1]} × "
          f"medido {br(acrescimo['mediana'])} (mediana; máximo {br(acrescimo['maximo'])}) tokens")
    print(f"  mês: estimado US$ {br(ESTIMADO_MES, 2)} × medido US$ "
          f"{br(r['custo_mensal']['mediana'], 2)} (mediana)")

    print(f"\nCusto da medição: US$ {br(r['custo_total'], 4)} · tempo de execução: "
          f"{br(r['segundos_total'] / 60, 1)} min")


# ------------------------------------------------------------------ comparação A × B

def comparar() -> None:
    dados = {}
    for config in CONFIGURACOES:
        arquivo = PASTA_RESULTADOS / f"medicao_{config}.json"
        if not arquivo.exists():
            raise SystemExit(f"Falta {arquivo.relative_to(BASE)}: rode antes "
                             f"python medir.py --config {config}")
        dados[config] = json.loads(arquivo.read_text(encoding="utf-8"))["resumo"]
    a, b = dados["A"], dados["B"]
    ca, cb = a["distribuicao"]["completo"], b["distribuicao"]["completo"]

    def linha(rotulo, va, vb):
        print(f"  {rotulo:52} {va:>22} {vb:>22}")

    print("Comparação das configurações (pedido completo = os 10 pedidos com as 4 consultas)\n")
    linha("", "A: paralelas desligadas", "B: paralelas ligadas")
    linha("acertos por rodada", ", ".join(map(str, a["certas_por_rodada"])),
          ", ".join(map(str, b["certas_por_rodada"])))
    for categoria in CATEGORIAS:
        linha(f"{categoria} (total)", a["categorias"][categoria], b["categorias"][categoria])
    linha("urgência certa (0106 e 0107)",
          sum(u["autorizacao_certa"] for u in a["urgencia"].values()),
          sum(u["autorizacao_certa"] for u in b["urgencia"].values()))
    linha("execuções com chamadas paralelas",
          f"{a['execucoes_com_paralelas']} de {a['execucoes']}",
          f"{b['execucoes_com_paralelas']} de {b['execucoes']}")
    linha("paralelas fora da ordem de dependência",
          f"{a['execucoes_fora_de_ordem']} de {a['execucoes']}",
          f"{b['execucoes_fora_de_ordem']} de {b['execucoes']}")
    linha("máx. de ferramentas numa chamada", a["max_ferramentas_numa_chamada"],
          b["max_ferramentas_numa_chamada"])
    linha("chamadas ao modelo, pedido completo (mediana)", f"{ca['chamadas']['mediana']:g}",
          f"{cb['chamadas']['mediana']:g}")
    linha("entrada, pedido completo (mediana, tokens)", br(ca["entrada"]["mediana"]),
          br(cb["entrada"]["mediana"]))
    linha("US$, pedido completo (mediana · máximo)",
          f"{br(ca['usd']['mediana'], 5)} · {br(ca['usd']['maximo'], 5)}",
          f"{br(cb['usd']['mediana'], 5)} · {br(cb['usd']['maximo'], 5)}")
    linha("segundos, pedido completo (mediana · máximo)",
          f"{br(ca['segundos']['mediana'], 1)} · {br(ca['segundos']['maximo'], 1)}",
          f"{br(cb['segundos']['mediana'], 1)} · {br(cb['segundos']['maximo'], 1)}")
    linha("custo mensal (mediana · cauda)",
          f"{br(a['custo_mensal']['mediana'], 2)} · {br(a['custo_mensal']['cauda'], 2)}",
          f"{br(b['custo_mensal']['mediana'], 2)} · {br(b['custo_mensal']['cauda'], 2)}")

    print("\nLeitura")
    economia = ca["chamadas"]["mediana"] - cb["chamadas"]["mediana"]
    print(f"  - Em B, o modelo usou chamadas paralelas em {b['execucoes_com_paralelas']} de "
          f"{b['execucoes']} execuções; a mediana de chamadas ao modelo no pedido completo caiu "
          f"{economia:g}.")
    print("  - O cálculo depende do grupo do cadastro, e o histórico e o saldo dependem do "
          "cálculo: só esses dois podem ser pedidos juntos. A economia máxima possível é de uma "
          "chamada por pedido completo.")
    print(f"  - Paralelas fora da ordem de dependência em B: {b['execucoes_fora_de_ordem']}. Nesses "
          "casos o modelo pediu uma ferramenta sem ter o dado de que ela depende; a barreira "
          "recusa se o dado suposto não bater com o devolvido.")
    dif_certas = sum(b["certas_por_rodada"]) - sum(a["certas_por_rodada"])
    dif_silenciosos = b["categorias"]["erro silencioso"] - a["categorias"]["erro silencioso"]
    print(f"  - Diferença de acertos (B − A): {dif_certas:+d}; de erros silenciosos (B − A): "
          f"{dif_silenciosos:+d}.")


# ------------------------------------------------------------------ ponto de entrada

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    grupo = parser.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--config", choices=CONFIGURACOES, help="A: paralelas desligadas; B: ligadas")
    grupo.add_argument("--comparar", action="store_true", help="compara medicao_A.json e medicao_B.json")
    parser.add_argument("--rodadas", type=int, default=3, help="número de rodadas (padrão: 3)")
    argumentos = parser.parse_args()

    if argumentos.comparar:
        comparar()
    else:
        PASTA_BANCOS.mkdir(exist_ok=True)
        PASTA_RESULTADOS.mkdir(exist_ok=True)
        linhas = medir(argumentos.config, argumentos.rodadas)
        resumo = resumir(linhas)
        imprimir_resumo(argumentos.config, resumo)
        destino = PASTA_RESULTADOS / f"medicao_{argumentos.config}.json"
        rotulo, paralelas = CONFIGURACOES[argumentos.config]
        destino.write_text(json.dumps({"configuracao": argumentos.config, "rotulo": rotulo,
                                       "paralelas": paralelas, "resumo": resumo,
                                       "execucoes": linhas},
                                      ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Resultados em {destino.relative_to(BASE)}")
