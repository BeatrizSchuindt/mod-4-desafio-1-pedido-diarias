# Etapa 4 — Memória, custo por turno e eliminação

## Objetivo

Ligar a memória com `SqliteDb`, `add_history_to_context` e teto em `num_history_runs`, tratando
cada pedido como uma sessão (`session_id` = número do pedido; `user_id` = matrícula do
solicitante, informados a cada `run`). Medir o custo da memória com as duas complementações em
três configurações. Implementar a rotina de eliminação e testá-la com as duas servidoras que
passaram por diligência.

## O que foi feito

| Arquivo | Mudança |
|---|---|
| `agente.py` | `construir_agente(memoria=..., banco=...)` com três configurações (`nenhuma`, `historico`, `historico_e_usuario`); `instruir` passa `session_id` e `user_id` a cada `run`; a medição deixou de contar mensagens do histórico (`from_history`) como chamadas |
| `instruir_pedido.py` | Roda sem memória, para que reexecutar o mesmo pedido não some histórico |
| `eliminacao.py` (novo) | Rotina de eliminação em três etapas e funções de inspeção do banco |
| `medir_memoria.py` (novo) | 0111 e 0112 em dois turnos (pedido e complementação) nas configurações A, B, C e D |
| `testar_eliminacao.py` (novo) | Banco com três titulares; elimina Beatriz e Carla e confere tabela por tabela |

**Configuração adotada no sistema:** `memoria="historico"`, com `SqliteDb` em
`banco/instrucoes.db`, `add_history_to_context=True` e `num_history_runs=3` (o turno original e
até duas complementações).

**Regra de derivação do `user_id`:** a matrícula **como protocolada no pedido**, também no turno
da complementação, mesmo quando ela corrige a matrícula. A correção é conteúdo, aplicado pelo
modelo e conferido pela barreira, e não identidade da sessão.

**Validação antes da execução real:** como não havia chave do lado de quem escreveu o código, a
etapa foi validada com um simulador da API (transporte HTTP falso, que responde como um modelo
roteirizado). Ele não vai ao repositório. Revelou dois pontos corrigidos antes da entrega: a
contagem de chamadas incluía as mensagens do histórico, e o comportamento real da configuração D
(abaixo).

## Comandos executados

```bash
python testar_ferramentas.py > /dev/null; echo "ferramentas: $?"   # 0
python testar_filtro.py > /dev/null; echo "filtro: $?"             # 0
python testar_barreira.py > /dev/null; echo "barreira: $?"         # 0
python medir_memoria.py | tee resultados/memoria_custo_por_turno.txt
python testar_eliminacao.py | tee resultados/teste_eliminacao.txt
python eliminacao.py 207418 "Carla Regina Souza" --banco bancos/memoria_C.db
python eliminacao.py 207418 "Carla Regina Souza" --banco bancos/memoria_C.db --apagar-encontradas
```

## Resultado e evidências

### Custo da memória por turno

Saída em [`resultados/memoria_custo_por_turno.txt`](../resultados/memoria_custo_por_turno.txt) e
detalhe em [`resultados/memoria_custo_por_turno.json`](../resultados/memoria_custo_por_turno.json).
Custo da execução: US$ 0,04075.

| Config. | Pedido | Turno 1: 1ª chamada / total | Turno 2: 1ª chamada / total | Chamadas no turno 2 | Aplicada ao pedido certo? | US$ (T1 + T2) |
|---|---|---:|---:|---:|:-:|---:|
| A · sem memória | 0111 | 2.866 / 5.835 | 2.765 / 8.516 | 3 | **não** (recusada) | 0,00435 |
| A · sem memória | 0112 | 2.866 / 5.829 | 2.768 / 5.625 | 2 | **não** (recusada) | 0,00368 |
| B · histórico da sessão | 0111 | 2.866 / 5.835 | 3.628 / 19.592 | 5 | **SIM** | 0,00699 |
| B · histórico da sessão | 0112 | 2.866 / 5.829 | 3.554 / 19.216 | 5 | **SIM** | 0,00673 |
| C · histórico + memórias | 0111 | 2.891 / 7.125 | 3.787 / 21.685 | 5 | **SIM** | 0,00782 |
| C · histórico + memórias | 0112 | 2.891 / 7.103 | 3.662 / 21.043 | 5 | **SIM** | 0,00742 |
| D · B com `user_id` corrigido | 0112 | 2.866 / 5.829 | 2.768 / 5.625 | 2 | **não** (recusada) | 0,00376 |

**Leitura dos números:**

- **O histórico acrescenta cerca de 690 a 760 tokens a cada chamada** do turno da
  complementação: a 1ª chamada passa de 2.866 para 3.554 a 3.628. A estimativa do `desenho.md`
  era de 800 tokens, próxima do medido.
- **As memórias do usuário acrescentam mais 110 a 160 tokens por chamada** (C contra B, no turno
  2) **e cerca de 1.220 a 1.300 tokens de extração por turno**: é a coluna "fora" da saída, a
  entrada total menos a soma das chamadas do agente.
- **No Agno 3.0.9, as chamadas de extração de memória entram nas métricas do turno.** A coluna
  "fora" é maior que zero só em C. A Aula 07 (Seção 3.1) tinha observado o contrário; a diferença
  provavelmente é de versão, e por isso a medição foi feita em vez de suposta.
- **C custa cerca de 10% a 12% mais que B** (US$ 0,00782 contra 0,00699; US$ 0,00742 contra
  0,00673) **e acerta o mesmo** (2 de 2). A diferença é menor que a da Aula 07 porque aqui o
  contexto de base do agente já é grande (cerca de 2.900 tokens), e a extração pesa menos em
  proporção.
- **A sozinha é a mais barata, mas não serve:** a complementação chega sem o pedido.

### A barreira como única defesa (configurações A e D)

Sem o pedido no contexto, o modelo **não pediu os dados que faltavam: tentou instruir assim
mesmo**, e a barreira foi a única coisa entre essa tentativa e o conferente:

| Caso | O que o modelo fez | Motivo da recusa |
|---|---|---|
| A · 0111 | Chamou as ferramentas com matrícula, nome e data do pedido vazios (3 chamadas) | `consultar_servidor consultou a matrícula '', que não consta do pedido nem da complementação`; `calcular_diarias usou data_pedido='', mas o pedido informa '2026-10-09'` |
| A · 0112 | Usou a matrícula da complementação (207418) e um nome inventado, `'*'` | `consultar_servidor usou o nome '*', diferente do nome do pedido` |
| D · 0112 | O mesmo comportamento de A, porque o histórico não foi achado | `consultar_servidor usou o nome '*', diferente do nome do pedido` |

### A armadilha do DIA-2026-0112 (configuração D)

Na configuração D, a complementação do 0112 foi enviada com o `user_id` da matrícula corrigida
(207418), e não com o da matrícula do pedido (207481), com que a sessão tinha sido aberta:

- o Agno buscou o histórico filtrando pelo `user_id` e **não o encontrou**: a 1ª chamada do turno
  2 tem 2.768 tokens, o tamanho de uma conversa nova, contra 3.554 em B;
- o modelo recebeu a complementação sem o pedido e a barreira recusou a instrução;
- no banco, a linha da sessão `DIA-2026-0112` ficou sob o `user_id` 207481, e a execução da
  complementação foi gravada na mesma sessão sob o `user_id` 207418 (verificado no simulador,
  consultando as tabelas `agno_sessions` e `agno_runs`). **Uma mesma sessão passa a ter dados sob
  dois identificadores.**

### O que as memórias do usuário guardaram (configuração C)

| `user_id` | Memória extraída pelo Agno |
|---|---|
| 206689 | "Beatriz Moraes Cunha (matrícula 206689) tem o pedido de diárias DIA-2026-0111 (…) viagem a Colniza-MT, com partida em 17/11/2026 e retorno previsto para 20/11/2026 (…) para operação conjunta de fiscalização com a polícia ambiental." |
| **207481** | "Carla Regina Souza, matrícula correta 207418, tem um pedido de diárias DIA-2026-0112 (…) A complementação (…) corrigiu a matrícula anteriormente informada por erro de digitação." |

**Necessidade (Aula 07, Seção 6.1):** as memórias repetem o que já está no pedido e no histórico
da sessão. Como cada pedido é uma sessão própria, nada do que elas guardam é usado em outra
sessão. Elas criam um lugar a mais com dados pessoais, e **a da Carla fica sob a matrícula de
outro servidor**.

### Rotina de eliminação

Saída em [`resultados/teste_eliminacao.txt`](../resultados/teste_eliminacao.txt): todas as
conferências passaram.

| Conferência | Resultado |
|---|---|
| CPF e conta do DIA-2026-0104 no banco | **Ausentes.** O filtro mascarou antes de gravar, e a memória extraída sobre Heitor não contém o CPF |
| Beatriz (206689), antes | Aparecia em `agno_memories` (1), `agno_sessions` (1) e `agno_runs` (2) |
| Beatriz, etapas 1 e 2 | Sessão DIA-2026-0111 e 1 memória apagadas pelo `user_id` |
| Beatriz, etapa 3 | **Nada restou** |
| Carla (207418), só pelo `user_id` | **Nenhuma sessão e nenhuma memória encontradas.** A conferência tabela por tabela ainda achou os dados dela em `agno_memories` (1) e `agno_runs` (2) |
| Carla, varredura | Achou a sessão DIA-2026-0112 e a memória, ambas sob o `user_id` 207481 |
| Carla, depois da confirmação | **Nada restou**, nem a matrícula 207481 digitada por engano |
| Heitor (testemunha) | Intacto: sessão DIA-2026-0104, 1 execução e 1 memória |

A rotina pela linha de comando, no banco da configuração C, repetiu o comportamento: sem
confirmação, encontra e não apaga; com `--apagar-encontradas`, apaga e confere que nada restou.

## Achados e armadilhas

- **Sem memória, o modelo não para: inventa os argumentos.** Esperava-se que ele pedisse os
  dados; ele preferiu chamar as ferramentas com campos vazios ou com o nome `'*'`. A barreira
  recusou em 3 de 3 casos (A e D). Essa é a evidência de que a verificação no código não é
  redundante.
- **O `user_id` decide se o histórico é encontrado.** O Agno filtra a sessão por `session_id` **e**
  `user_id`. Trocar o `user_id` no meio da sessão não gera erro: produz uma conversa sem
  histórico e grava dados sob dois identificadores.
- **A busca pelo `user_id` da titular não basta.** No 0112, ela não achou nada, e sem a varredura
  os dados da Carla teriam ficado no banco (Aula 07, Seção 6.2, em versão mais grave: não só a
  memória, mas a sessão inteira está sob outro identificador).
- **Risco inverso, apontado para o LEIA-ME:** se o servidor 207481 (Rafael) pedisse a eliminação
  dos próprios dados, a busca pelo `user_id` dele apagaria a sessão da Carla. Por isso a rotina
  lista o que encontra e mostra o `user_id` de cada item, e o formulário deve pedir confirmação.
- **Os nomes com acento são gravados escapados no JSON** (`á`). A varredura procura as duas
  formas.
- **A extração de memórias entra nas métricas nesta versão do Agno**, ao contrário do que a Aula
  07 observou.

## Decisões e justificativa

| Decisão | Justificativa (número medido ou norma) |
|---|---|
| Memória do sistema: **histórico da sessão (B)**, com teto `num_history_runs=3` | Aplicou a complementação ao pedido certo em 2 de 2 casos; C acertou o mesmo, custando de 10% a 12% mais; A errou 2 de 2 |
| **Sem memórias do usuário** (`update_memory_on_run` desligado) | Não melhora o acerto, acrescenta cerca de 1.250 tokens de extração por turno e cria mais uma tabela com dados pessoais, com dados de uma servidora sob a matrícula de outro (princípio da necessidade, LGPD art. 6º, III) |
| `user_id` = matrícula como protocolada, nos dois turnos | É o identificador com que a sessão foi aberta; com outro, o histórico não é achado (configuração D) |
| `session_id` e `user_id` informados no `run`, e não na construção | Um único agente em cache no formulário atende todos os pedidos sem misturá-los |
| Eliminação em três etapas, sempre executadas | O que o agente guarda é probabilístico; a etapa 3 é a única que acha o 0112 |
| Itens achados pela varredura só são apagados com confirmação | Um homônimo apareceria pelo nome; quem confirma vê o `user_id` de cada item |
| A rotina não toca o processo de diárias | O banco do agente é cópia de trabalho; o processo é registro de despesa pública, sujeito à transparência e à guarda das normas de prestação de contas |

## Pendências

- **Prazo de retenção (pergunta 3 do LEIA-ME):** definir por quanto tempo o banco guarda as
  sessões (proposta: até o encaminhamento ao ordenador, mais um prazo curto para a conferência)
  e se haverá expurgo automático. Decidir na Etapa 5, junto com a tela de eliminação.
- **Etapa 5:** o formulário deve enviar a complementação na mesma sessão, com o `user_id` do
  pedido, e ter uma área separada para a eliminação, com a confirmação dos itens achados pela
  varredura.
- **Etapa 6:** cada rodada de medição precisa começar com o banco vazio (ou sem memória), para
  que uma rodada não leve histórico para a seguinte.
- **`relatorio.md`:** levar a tabela de custo por turno e o caso "a barreira como única defesa".
