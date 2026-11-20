# Etapa 2 — Ferramentas sobre os dados do órgão

## Objetivo

Escrever as ferramentas como funções Python comuns, cada uma substituindo uma consulta que o
servidor faz à mão, com docstring que funcione como especificação (quando usar, o que devolve e
formato dos argumentos), aplicando a minimização e deixando todas as contas no código. Testá-las
sem agente e sem chave, com os casos do enunciado, e guardar a saída como evidência.

## O que foi feito

1. **`dados.py`**: porta única de leitura do acervo de `exemplos/dados/`. Descarta CPF e e-mail
   do cadastro na própria leitura e não lê o `gabarito.json`.
2. **`ferramentas.py`**: as regras da norma em funções auxiliares e as quatro ferramentas, na
   ordem das dependências entre os dados:

   | Ferramenta | Argumentos | Critérios que devolve |
   |---|---|---|
   | `consultar_servidor` | `matricula`, `nome` | `cadastro` |
   | `calcular_diarias` | `grupo`, `destino_uf`, `data_pedido`, `data_partida`, `data_retorno` | `dados_completos`, `antecedencia` |
   | `consultar_historico_diarias` | `matricula`, `data_partida`, `quantidade_pedida` | `prestacao_contas`, `limite_mensal` |
   | `consultar_saldo_diarias` | `unidade`, `valor` | `saldo_orcamentario` |

3. **`testar_ferramentas.py`**: teste sem modelo e sem chave, em três partes:
   - [1] os casos pedidos no enunciado;
   - [2] as ferramentas encadeadas contra o gabarito;
   - [3] a minimização.

   O script termina com código de saída 1 se alguma conferência falhar.

## Comandos executados

```bash
python testar_ferramentas.py | tee resultados/teste_ferramentas.txt; echo "código de saída: ${PIPESTATUS[0]}"

# experimento: introduzir de propósito a armadilha da data de hoje e desfazê-la
sed -i 's/        if prazo < DATA_DA_ANALISE:/        if prazo < date.today():/' ferramentas.py
python testar_ferramentas.py | grep -E "FALHOU|DIVERGE|casos iguais|Resultado"; echo "código de saída: ${PIPESTATUS[0]}"
sed -i 's/        if prazo < date.today():/        if prazo < DATA_DA_ANALISE:/' ferramentas.py
python testar_ferramentas.py | tail -1; echo "código de saída: ${PIPESTATUS[0]}"
```

## Resultado e evidências

Saída completa em [`resultados/teste_ferramentas.txt`](../resultados/teste_ferramentas.txt).

**[1] Casos do enunciado: todos `[ok]`**

| Caso | Chamada | Resultado |
|---|---|---|
| DIA-2026-0112 | `consultar_servidor('207481', 'Carla Regina Souza')` | A matrícula pertence a outro servidor; critério `cadastro` NÃO ATENDE; o nome do titular real não é revelado |
| DIA-2026-0112 (compl.) | `consultar_servidor('207418', 'Carla Regina Souza')` | Critério `cadastro` ATENDE; grupo C, unidade CUC |
| DIA-2026-0108 | `consultar_historico_diarias('203648', '2026-11-03', 3.5)` | Retorno em 18/09 + 5 dias úteis = 25/09, antes de 09/10: prestação VENCIDA |
| DIA-2026-0102 (contraste) | `consultar_historico_diarias('205882', '2026-11-09', 3.5)` | Retorno em 06/10 + 5 dias úteis = 13/10, depois de 09/10: pendente, mas no prazo |
| DIA-2026-0103 | `calcular_diarias('B', 'MT', '2026-10-07', '2026-11-05', '2026-11-05')` | 0,5 diária, R$ 140,00 |
| DIA-2026-0110 | `calcular_diarias('B', 'RO', …)` + `consultar_saldo_diarias('CRH', 1800.0)` | R$ 1.800,00 contra o saldo de R$ 640,00: critério `saldo_orcamentario` NÃO ATENDE |

**[2] Contra o gabarito: 14 de 14 casos iguais**

Comparados 5 campos: recomendação, quantidade, valor, `exige_autorizacao_superior` e critérios
não atendidos. Os 12 pedidos e as 2 complementações reproduziram o gabarito, com as ferramentas
encadeadas sem modelo.

**[3] Minimização**

Nenhuma das 58 saídas de ferramenta produzidas no teste contém CPF ou e-mail.

**Experimento: o teste detecta a armadilha da data de hoje**

Com `date.today()` (2026-11-19) no lugar da data da análise, a prestação do DIA-2026-0102 passou
a constar como vencida:

```
[FALHOU] retorno em 2026-10-06 + 5 dias úteis = 2026-10-13, depois de 2026-10-09: no prazo
DIA-2026-0102   nao_recomendado   3.5   770.00   prestacao_contas   DIVERGE em recomendacao, criterios_nao_atendidos
13 de 14 casos iguais ao gabarito
Resultado: 2 falha(s)
código de saída: 1
```

Depois de desfeita a alteração: `todas as conferências passaram`, código de saída 0.

**Esquema que o modelo recebe** (gerado pelo Agno 3.0.9 a partir das anotações de tipo):

| Ferramenta | Argumentos (todos obrigatórios) |
|---|---|
| `consultar_servidor` | `matricula: string`, `nome: string` |
| `calcular_diarias` | `grupo`, `destino_uf`, `data_pedido`, `data_partida`, `data_retorno`: `string` |
| `consultar_historico_diarias` | `matricula: string`, `data_partida: string`, `quantidade_pedida: number` |
| `consultar_saldo_diarias` | `unidade: string`, `valor: number` |

## Achados e armadilhas

- **Data da análise × data de hoje.** O experimento mostrou que basta trocar uma comparação para
  o DIA-2026-0102 virar "não recomendado". O erro seria silencioso: o caso continuaria com
  quantidade e valor corretos.
- **A matrícula trocada expõe dado de terceiro.** No DIA-2026-0112, a matrícula 207481 é do
  Rafael Lima Antunes. Uma consulta ingênua ao cadastro devolveria ao modelo, e depois ao banco,
  os dados de alguém que não fez pedido nenhum.
- **"Pendente" não é "vencida".** O DIA-2026-0102 tem prestação pendente, mas ainda no prazo. A
  comparação é estrita (`prazo < data da análise`), como no gerador do gabarito.
- **O limite mensal soma todas as diárias do mês**, em qualquer situação (entregue, pendente ou
  viagem futura). No DIA-2026-0109, as duas viagens futuras de novembro (4,5 + 3,5) mais as 3,5
  pedidas dão 11,5.
- **A urgência é o único dado que as ferramentas não decidem.** No teste ela foi declarada
  (`URGENCIA_DECLARADA`), como faz o `gerar_dados.py`. No sistema, ela é julgamento do modelo.

## Decisões e justificativa

| Decisão | Justificativa |
|---|---|
| Vereditos no formato `Critério <nome>: ATENDE.` / `NÃO ATENDE.`, com os nomes do `Literal` do contrato `Verificacao` | O modelo transcreve, não calcula. O código consegue conferir o que o modelo transcreveu, o que é a base da barreira |
| CPF e e-mail descartados na leitura (`dados.py`), e não apenas omitidos na resposta | O dado que não é carregado não vaza, nem por erro de programação |
| `consultar_servidor` não revela o nome do titular de outra matrícula | Minimização: é dado pessoal de terceiro, desnecessário à instrução |
| `consultar_historico_diarias` recebe a `quantidade_pedida` | O confronto com o limite mensal sai pronto, sem conta feita pelo modelo |
| `calcular_diarias` recebe o grupo, e não a matrícula | Mantém a dependência cadastro → cálculo do `desenho.md`, que fundamenta a decisão sobre as chamadas paralelas e permite à barreira conferir o grupo usado |
| Texto do art. 5º, §§ 1º e 2º, anexado quando a antecedência não é atendida | A urgência é o único julgamento do modelo, que precisa da regra à vista no ponto de uso |
| Valores com ponto decimal (`R$ 980.00`) | Igual ao exemplo do enunciado; o modelo transcreve `980.0` no campo `float` do contrato sem converter vírgula |
| Nome comparado sem diferenciar maiúsculas e espaços, mas com acentos | Postura conservadora: na dúvida, o nome não confere e o pedido vai para diligência |
| Erros de argumento devolvidos como mensagem, e não como exceção | A ferramenta relata o erro ao modelo em vez de quebrar a execução (Aula 03) |
| `gabarito.json` lido só pelo teste | O agente importa as ferramentas, que importam o `dados.py`; o gabarito fica fora do alcance dele |

## Pendências

- O `desenho.md` não precisou de ajuste: os cinco compromissos assumidos para as ferramentas
  foram cumpridos (nomes e ordem, limite pronto no histórico, cadastro sem CPF e e-mail,
  feriados declarados, data da análise fixa).
- Etapa 3: a barreira deve reutilizar as regras de `ferramentas.py` para conferir os
  argumentos e os números da instrução contra o pedido e os retornos das ferramentas.
