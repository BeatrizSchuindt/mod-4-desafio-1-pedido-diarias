# Etapa 1 — Desenho do processo e quadro PEAS

## Objetivo

Descrever o processo e especificar o agente antes de qualquer código: o processo atual e o
processo com o agente, o quadro PEAS, a contagem de passos com a confiabilidade composta a 95% e
a 99%, a estimativa de custo por passos com o volume mensal adotado e o quadrante de autonomia.
Entregável: [`desenho.md`](../desenho.md), na raiz.

## O que foi feito

1. Criado o `estimativa_desenho.py`, que reproduz a aritmética da Aula 01 (Seção 6) com os
   parâmetros do desafio, sem chamar modelo algum. A saída foi gravada em
   [`resultados/estimativa_desenho.txt`](../resultados/estimativa_desenho.txt).
2. Escrito o `desenho.md` com sete seções: processo atual, processo com o agente, PEAS, passos e
   confiabilidade, custo e volume, quadrante de autonomia e informação que o agente não terá.

## Comandos executados

```bash
python estimativa_desenho.py | tee resultados/estimativa_desenho.txt
```

## Resultado e evidências

**Parâmetros adotados e origem de cada um:**

| Parâmetro | Valor | Origem |
|---|---|---|
| Entrada da 1ª chamada | 2.060 tokens | Execução de referência citada no enunciado |
| Acréscimo por passo seguinte | 90 a 150 tokens (central: 120) | Execução de referência citada no enunciado |
| Saída por pedido de ferramenta | 40 tokens | Estimativa própria |
| Saída da resposta final (`Instrucao`) | 700 tokens | Estimativa própria |
| Histórico reenviado na complementação | 800 tokens | Estimativa própria |
| Preço do `gpt-5.6-luna` | US$ 0,20 / 1,20 por milhão (entrada / saída) | Aula 06, §4.2 |
| Passos do pedido completo | 5 | 4 ferramentas uma por vez + resposta final |
| Passos da diligência | 2 | Cadastro + resposta final (art. 9º) |
| `tool_call_limit` | 8 | Figura 1 do enunciado |
| Volume mensal | 400 pedidos | Adotado ("centenas", segundo o enunciado) |
| Fração em diligência | 2 de 12 | Proporção do acervo |

**Números principais:**

| Medida | 99% por passo | 95% por passo |
|---|---:|---:|
| Confiabilidade com 5 passos | 95,1% | 77,4% |
| Confiabilidade com 4 passos (paralelas ligadas) | 96,1% | 81,5% |
| Casos certos esperados nos 14 do gabarito | 13,4 | 11,1 |

| Execução | Entrada | Saída | US$ |
|---|---:|---:|---:|
| Pedido completo (5 passos) | 11.500 | 860 | 0,00333 |
| Diligência (2 passos) | 4.240 | 740 | 0,00174 |
| Complementação (5 passos) | 15.500 | 860 | 0,00413 |
| Teto (9 passos) | 23.940 | 1.020 | 0,00601 |
| **Mês (400 pedidos, 467 execuções)** | | | **1,50** |

## Achados e armadilhas

- **Os 11,1 casos certos esperados a 95% por passo coincidem com o exemplo do enunciado**
  ("um agente que acerta onze casos e recusa três…"). A própria aritmética mostra que a barreira e
  a conferência humana são necessárias.
- **Tensão no quadrante.** Pela grade pura da Aula 01, "reversível + detectado tarde" cai em "age,
  com auditoria por amostra", mas o enunciado conclui que o agente "não age sozinho". Resolvido no
  `desenho.md` tratando a reversão como apenas formal (ressarcimento de valor já gasto) e
  apoiando-se no art. 10 da IN → "apenas aconselha".
- **O gerador do gabarito aplica as regras numa ordem fixa.** Completude e cadastro vêm primeiro;
  se um dos dois falha, a análise para (diligência) e quantidade e valor ficam nulos. O agente
  precisa seguir a mesma lógica.
- **A urgência é o único julgamento de texto** do processo (DIA-2026-0106 × DIA-2026-0107). Todo o
  resto é conta e deve sair pronto das ferramentas.
- **Saldo disputado.** O DIA-2026-0101 e o DIA-2026-0102 são da mesma unidade (CFF) e da mesma
  viagem, mas a norma e o gabarito comparam o saldo com cada pedido isoladamente.
- **O custo não é o risco do processo.** US$ 1,50 por mês para 400 pedidos; o risco está na
  confiabilidade composta.

## Decisões e justificativa

| Decisão | Justificativa |
|---|---|
| Chamadas paralelas desligadas na estimativa (5 passos) | O cálculo depende do grupo (cadastro), o limite depende da quantidade e o saldo depende do valor. A medição compara com as paralelas ligadas (4 passos) |
| Diligência com 2 passos | Art. 9º: pedido incompleto ou divergente do cadastro volta sem análise de mérito |
| Volume de 400 pedidos por mês | Ponto intermediário de "centenas"; o custo escala de forma linear |
| Quadrante "apenas aconselha" | Detecção tardia, reversão só formal, art. 10 da IN |
| Conferência humana de todos os pedidos, e não por amostra | Confiabilidade estimada de 77,4% a 95% por passo; o registro de divergências no formulário permitirá rever com o uso |
| Estimativas não serão corrigidas depois da medição | O confronto entre previsto e medido é critério de avaliação e vai para o `relatorio.md` |
| Script nomeado por assunto (`estimativa_desenho.py`) | Arquivos do projeto com nomes que o avaliador entende de relance; a numeração por etapas fica só neste diário |

## Pendências

**Compromissos que o desenho assume para a Etapa 2 (ferramentas).** Se algum mudar, ajustar o
`desenho.md` antes de qualquer medição:

1. Nomes e ordem: `consultar_servidor` → `calcular_diarias` → `consultar_historico_diarias` →
   `consultar_saldo_diarias`.
2. A comparação com o limite mensal sai pronta do histórico, que recebe a quantidade calculada.
3. `consultar_servidor` informa se o nome confere e não devolve CPF nem e-mail.
4. A ferramenta de prestação declara que conta dias úteis sem feriados.
5. Todas as contas usam a data da análise 2026-10-09, e não a data de hoje.

**A confrontar com o medido (`relatorio.md`):**

- a entrada real da 1ª chamada e o acréscimo por passo (quando o agente rodar);
- a saída real por pedido de ferramenta e da resposta final;
- o histórico real reenviado na complementação (teste de memória);
- o número real de passos com as paralelas ligadas e desligadas;
- o ponto de conferência humana, justificado pelas recusas da barreira e pelos erros medidos.
