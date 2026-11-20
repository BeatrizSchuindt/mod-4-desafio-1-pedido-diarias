"""Estimativa de confiabilidade e custo do agente, feita antes de qualquer código de agente.

Reproduz a aritmética da Aula 01, Seção 6, com os parâmetros deste desafio:
confiabilidade composta pelo número de passos e custo estimado por pedido e por mês.
Usa só a biblioteca padrão e não chama modelo algum.

Uso: python estimativa_desenho.py | tee resultados/estimativa_desenho.txt
"""

# ---------------------------------------------------------------- parâmetros
# Cada valor é uma hipótese do desenho; a medição contra o gabarito traz o valor real.
ENTRADA_1A_CHAMADA = 2060        # instrução + esquemas das ferramentas + esquema da saída + pedido
ACRESCIMOS = (90, 120, 150)      # tokens que cada chamada seguinte acrescenta (faixa do enunciado)
SAIDA_POR_FERRAMENTA = 40        # pedido de ferramenta com os argumentos
SAIDA_FINAL = 700                # objeto Instrucao: verificações, pendências, alertas e minuta
HISTORICO_COMPLEMENTACAO = 800   # turno anterior reenviado pela memória (a medir no teste de memória)
USD_ENTRADA, USD_SAIDA = 0.20, 1.20   # gpt-5.6-luna, US$ por milhão de tokens (Aula 06)
TOOL_CALL_LIMIT = 8

VOLUME_MENSAL = 400              # pedidos novos por mês ("centenas", segundo o enunciado)
FRACAO_DILIGENCIA = 2 / 12       # proporção do acervo; cada diligência volta com complementação
CASOS_DO_GABARITO = 14           # 12 pedidos + 2 complementações

# Uma chamada ao modelo = um passo. Pedido completo: 4 ferramentas em sequência + resposta final.
PASSOS = {"pedido completo": 5, "diligência": 2, "complementação": 5}


def confiabilidade(por_passo: float, passos: int) -> float:
    return por_passo ** passos


def tokens(passos: int, acrescimo: int, historico: int = 0) -> tuple[int, int]:
    """Entrada acumulada das chamadas e saída total de uma execução."""
    entrada = sum(ENTRADA_1A_CHAMADA + historico + k * acrescimo for k in range(passos))
    saida = (passos - 1) * SAIDA_POR_FERRAMENTA + SAIDA_FINAL
    return entrada, saida


def custo(entrada: int, saida: int) -> float:
    return entrada / 1e6 * USD_ENTRADA + saida / 1e6 * USD_SAIDA


print("1. Confiabilidade composta (Aula 01, Tabela 1)\n")
print(f"{'passos':>6} {'99% por passo':>14} {'95% por passo':>14}")
for n in (1, 2, 3, 4, 5, 8, 9, 10):
    print(f"{n:>6} {confiabilidade(0.99, n):>14.1%} {confiabilidade(0.95, n):>14.1%}")

print("\nCasos certos esperados nos 14 do gabarito, por tipo de execução:")
for p in (0.99, 0.95):
    esperado = (10 * confiabilidade(p, 5) + 2 * confiabilidade(p, 2) + 2 * confiabilidade(p, 5))
    print(f"  a {p:.0%} por passo: {esperado:.1f} de {CASOS_DO_GABARITO}")

print("\n2. Custo por execução (acréscimo central de 120 tokens; faixa 90 a 150)\n")
print(f"{'execução':18} {'passos':>6} {'entrada':>9} {'saída':>6} {'US$':>9} {'faixa US$':>19}")
custos = {}
for nome, passos in PASSOS.items():
    hist = HISTORICO_COMPLEMENTACAO if nome == "complementação" else 0
    faixa = [custo(*tokens(passos, a, hist)) for a in ACRESCIMOS]
    entrada, saida = tokens(passos, 120, hist)
    custos[nome] = custo(entrada, saida)
    print(f"{nome:18} {passos:>6} {entrada:>9,} {saida:>6} {custos[nome]:>9.5f} "
          f"{faixa[0]:>9.5f}–{faixa[-1]:.5f}")

teto_passos = TOOL_CALL_LIMIT + 1
entrada, saida = tokens(teto_passos, 150)
print(f"{'teto (limite 8)':18} {teto_passos:>6} {entrada:>9,} {saida:>6} {custo(entrada, saida):>9.5f}"
      "   pior caso: 8 ferramentas em sequência + resposta")

print("\n3. Custo mensal\n")
completos = VOLUME_MENSAL * (1 - FRACAO_DILIGENCIA)
diligencias = VOLUME_MENSAL * FRACAO_DILIGENCIA
mensal = (completos * custos["pedido completo"] + diligencias * custos["diligência"]
          + diligencias * custos["complementação"])
print(f"  {VOLUME_MENSAL} pedidos/mês: {completos:.0f} completos, {diligencias:.0f} em diligência "
      f"(+ {diligencias:.0f} complementações)")
print(f"  execuções no mês: {completos + 2 * diligencias:.0f} · custo estimado: US$ {mensal:.2f}")
print(f"  custo médio por pedido protocolado: US$ {mensal / VOLUME_MENSAL:.5f}")
