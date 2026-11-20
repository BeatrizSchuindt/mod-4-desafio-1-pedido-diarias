# Desenho do processo — Instrução de pedidos de diárias

Este documento descreve o processo e especifica o agente **antes de qualquer código**. Os números
de confiabilidade e de custo são estimativas, calculadas por `estimativa_desenho.py` (saída em
[`resultados/estimativa_desenho.txt`](resultados/estimativa_desenho.txt)), e serão confrontados com
os valores medidos no `relatorio.md`. As estimativas aqui registradas não são corrigidas depois
da medição: a diferença entre o previsto e o medido é parte do resultado.

As regras citadas são as da Instrução Normativa SEMA nº 07/2026, hipotética
([`exemplos/dados/normas.md`](exemplos/dados/normas.md)).

## 1. O processo hoje, executado pelo servidor

A Coordenadoria de Diárias e Passagens recebe centenas de pedidos por mês. Cada um é instruído
por um servidor, que executa os passos abaixo nesta ordem:

1. Recebe o pedido protocolado, com matrícula, nome, destino, datas de partida e de retorno,
   meio de transporte e justificativa.
2. Confere se o pedido está completo, em especial se a data de retorno foi informada (art. 9º).
3. Consulta o cadastro funcional: confirma se a matrícula existe e se o nome informado é o do
   titular. Do cadastro obtém o cargo, o grupo da diária e a unidade de lotação.
4. Se o passo 2 ou o passo 3 falha, devolve o pedido ao solicitante em diligência, sem análise
   de mérito (art. 9º). O processo para aqui até a complementação chegar.
5. Conta a antecedência, em dias corridos, entre a data do pedido e a data da partida (art. 5º).
   Se for menor que dez dias, avalia se a justificativa descreve urgência legítima (§ 1º) e, nesse
   caso, registra que o pedido depende de autorização escrita do Secretário Adjunto (§ 2º).
6. Consulta o histórico de diárias do servidor: verifica se há prestação de contas pendente com o
   prazo de cinco dias úteis após o retorno já vencido (art. 7º) e soma as diárias já concedidas
   no mês da partida (art. 6º).
7. Calcula a quantidade de diárias (art. 4º: uma por pernoite mais meia no retorno, ou meia
   diária sem pernoite) e o valor, pelo grupo do cargo e pela classe do destino (art. 3º e Anexo I).
8. Compara a soma das diárias do mês com o limite de dez (art. 6º) e o valor com o saldo da
   dotação da unidade (art. 8º).
9. Redige a instrução, com a recomendação, e a minuta do despacho.
10. Encaminha o processo ao ordenador de despesa, que defere ou indefere (art. 10).
11. Quando um pedido devolvido em diligência retorna com a complementação, reconstitui o caso
    desde o começo e repete os passos 2 a 10.

**Onde o processo erra hoje.** Os erros raramente aparecem no dia em que são cometidos: uma
diária concedida a quem tem prestação de contas vencida, ou um pedido urgente aceito sem a
autorização escrita, costuma ser descoberto meses depois, na auditoria. A diligência acrescenta
retrabalho, porque o caso é reconstituído do zero quando a complementação chega.

## 2. O processo com o agente

O agente substitui as consultas e as contas feitas à mão e entrega a instrução pronta para
conferência. A decisão continua com o ordenador. A coluna "quem executa" separa o que o modelo
de linguagem decide do que o código garante:

| # | Passo | Quem executa |
|---|---|---|
| 1 | Recebe o pedido como texto e mascara CPF e dados bancários antes de enviá-lo ao modelo | Aplicação (filtro de dados pessoais) |
| 2 | Pede a consulta ao cadastro; recebe cargo, grupo, unidade e se o nome confere | Modelo (chamada 1) → `consultar_servidor` |
| 3 | Pede o cálculo; recebe quantidade, valor e antecedência | Modelo (chamada 2) → `calcular_diarias` |
| 4 | Pede a consulta ao histórico; recebe a situação das prestações e o confronto com o limite mensal | Modelo (chamada 3) → `consultar_historico_diarias` |
| 5 | Pede a consulta ao saldo; recebe o saldo da unidade e se ele é suficiente | Modelo (chamada 4) → `consultar_saldo_diarias` |
| 6 | Julga a urgência, quando a antecedência é insuficiente, e redige a instrução no formato `Instrucao` | Modelo (chamada 5) |
| 7 | Confere o status da execução, se toda matrícula e toda data usadas constam do pedido ou da complementação, e se os números da instrução são os devolvidos pelas ferramentas | Código (barreira) |
| 8 | Exibe a instrução; o servidor confere, edita a minuta e registra o encaminhamento | Servidor (formulário) |
| 9 | Defere ou indefere | Ordenador de despesa |
| 10 | Na diligência, a complementação é enviada na mesma sessão do pedido e o agente recupera o caso pelo histórico | Aplicação e memória |

Três decisões de desenho decorrem dessa divisão:

- **As contas ficam nas ferramentas.** Antecedência, quantidade, valor, prazo da prestação,
  soma do mês e comparação com o saldo saem prontos do código. O modelo transcreve os resultados
  e não calcula.
- **O único julgamento de texto do modelo é a urgência.** Os pedidos DIA-2026-0106 (incêndio
  florestal em curso) e DIA-2026-0107 (autorização verbal e ordem dirigida ao "sistema de análise")
  têm antecedência insuficiente, e só a leitura da justificativa os distingue.
- **A ordem das consultas segue as dependências.** O cálculo depende do grupo, que vem do
  cadastro; o confronto com o limite mensal depende da quantidade calculada; o saldo depende do
  valor. Na diligência (dado ausente ou divergente do cadastro), a instrução é emitida logo após a
  consulta ao cadastro, sem cálculo (art. 9º).

Se a execução falhar, ou se a barreira recusar a instrução, nada do conteúdo chega ao servidor:
o formulário exibe uma mensagem padrão e o pedido volta à análise manual.

## 3. Quadro PEAS

| Elemento | Pergunta | Este agente |
|---|---|---|
| **Medida de desempenho** (*Performance*) | Como se avalia o sucesso? | Concordância com o `gabarito.json` nos 12 pedidos e nas 2 complementações, critério a critério (detalhado abaixo); nenhuma instrução errada entregue ao conferente sem recusa; custo, tokens e tempo por pedido |
| **Ambiente** (*Environment*) | Onde o agente opera? | Cadastro funcional (`servidores.csv`), histórico de diárias e prestações (`historico_diarias.csv`), tabela de valores e regras (`tabela_diarias.json`), saldo das unidades (`unidades.json`), a IN (`normas.md`, levada à instrução de sistema), o pedido, a complementação e o banco SQLite da sessão. Data da análise fixa: 2026-10-09 |
| **Atuadores** (*Actuators*) | Como ele age? | Chamadas às quatro ferramentas, todas de consulta e nenhuma de escrita, e a entrega do objeto `Instrucao` ao formulário. **Não** são atuadores do agente: deferir, indeferir, pagar ou comunicar o servidor (art. 10) |
| **Sensores** (*Sensors*) | Como ele percebe? | O texto do pedido depois do filtro de dados pessoais, o texto da complementação, os retornos das ferramentas e o histórico da sessão |

**O ambiente é parcialmente observável.** O agente só conhece do órgão o que as ferramentas
devolvem, e as ferramentas devolvem apenas o necessário à instrução: o CPF e o e-mail do
cadastro não chegam ao modelo.

**Medida de desempenho, verificável contra o gabarito.** Um caso conta como certo quando os
quatro itens abaixo coincidem com o `gabarito.json`:

1. `recomendacao` igual;
2. `quantidade_diarias` e `valor_total` iguais, com tolerância de 0,01 (ambos nulos na diligência);
3. `exige_autorizacao_superior` igual;
4. o conjunto de critérios com situação `nao_atende` igual a `criterios_nao_atendidos`.

Além do acerto por caso, a medição registra:

- **erro visível**: instrução recusada pela barreira ou execução com erro, que chega ao servidor
  como mensagem padrão e volta à análise manual;
- **erro silencioso**: instrução errada que passa pela barreira e chega ao conferente. A meta é
  zero, porque é o erro que o processo hoje só descobre na auditoria;
- tokens de entrada e de saída, chamadas ao modelo, tempo e custo por pedido;
- ausência do CPF do DIA-2026-0104 na entrada do modelo e no banco.

## 4. Passos e confiabilidade composta

**Passo** é cada chamada ao modelo. Com as chamadas paralelas desligadas, o modelo pede uma
ferramenta por vez, e a contagem fica assim:

| Execução | Chamadas ao modelo | Composição |
|---|---:|---|
| Pedido completo | 5 | 4 ferramentas + resposta final |
| Diligência | 2 | Consulta ao cadastro + resposta final |
| Complementação | 5 | 4 ferramentas + resposta final, com o histórico da sessão |

Aplicando a tabela de confiabilidade composta da Aula 01 (as probabilidades de acerto de cada
passo se multiplicam):

| Passos | 99% por passo | 95% por passo |
|---:|---:|---:|
| 1 | 99,0% | 95,0% |
| 2 | 98,0% | 90,2% |
| 3 | 97,0% | 85,7% |
| 4 | 96,1% | 81,5% |
| **5** | **95,1%** | **77,4%** |
| 8 | 92,3% | 66,3% |
| 9 | 91,4% | 63,0% |
| 10 | 90,4% | 59,9% |

Nos 14 casos do gabarito (10 pedidos completos e 2 complementações, com 5 passos, e 2 diligências,
com 2 passos), o número esperado de casos certos é:

| Por passo | Casos certos esperados |
|---|---:|
| 99% | 13,4 de 14 |
| 95% | 11,1 de 14 |

**Leitura.**

- A 95% por passo, um pedido completo é instruído corretamente em cerca de três de cada quatro
  execuções, e espera-se errar cerca de três dos quatorze casos. É a situação do próprio
  enunciado: um agente que acerta onze e recusa três com a mensagem padrão vale mais do que um
  que acerta treze e entrega um errado. A estimativa mostra que a barreira no código e a
  conferência humana são necessárias, e não opcionais.
- Encurtar a cadeia é a intervenção mais eficaz sobre a confiabilidade (Aula 01, Seção 6). Por
  isso as contas não são passos do modelo: cada conta feita pelo modelo seria mais uma chance de
  erro na multiplicação acima.
- Com as chamadas paralelas ligadas, o cadastro e o histórico poderiam ser pedidos na mesma
  chamada, e o pedido completo cairia para 4 passos (96,1% e 81,5%). O ganho tem um risco: o
  modelo pode pedir uma ferramenta antes de ter o dado de que ela depende, como o grupo que vem
  do cadastro. A medição compara as duas configurações.
- A tabela supõe passos independentes, uma simplificação da Aula 01. O valor medido pode
  divergir, e essa diferença será registrada no `relatorio.md`.

## 5. Custo por passos e volume mensal

**Entrada da primeira chamada.** A primeira chamada leva ao modelo a instrução de sistema (as
regras da IN, a ordem das consultas e a proibição de calcular com dados supostos), os esquemas
das quatro ferramentas (nome, docstring e argumentos), o esquema da saída (`Instrucao` e
`Verificacao`) e o pedido. Na execução de referência citada no enunciado, essa entrada foi de
cerca de **2.060 tokens**.

**Acréscimo por passo.** Cada chamada seguinte reenvia tudo o que veio antes e acrescenta o
pedido de ferramenta e o resultado devolvido: de **90 a 150 tokens** por passo, na referência.

**Conta.** A entrada acumulada de uma execução com *n* chamadas é:

> entrada = *n* × 2.060 + acréscimo × (0 + 1 + … + (*n* − 1))

Para a saída, estimam-se 40 tokens por pedido de ferramenta e 700 tokens para o objeto
`Instrucao` (verificações, pendências, alertas e minuta). Na complementação, o histórico da
sessão acrescenta cerca de 800 tokens a cada chamada. Preços do `gpt-5.6-luna`: US$ 0,20 por
milhão de tokens de entrada e US$ 1,20 por milhão de saída.

| Execução | Passos | Entrada (tokens) | Saída (tokens) | US$ (acréscimo de 120) | Faixa US$ (acréscimo de 90 a 150) |
|---|---:|---:|---:|---:|---|
| Pedido completo | 5 | 11.500 | 860 | 0,00333 | 0,00327 a 0,00339 |
| Diligência | 2 | 4.240 | 740 | 0,00174 | 0,00173 a 0,00174 |
| Complementação | 5 | 15.500 | 860 | 0,00413 | 0,00407 a 0,00419 |
| Teto (`tool_call_limit=8`) | 9 | 23.940 | 1.020 | 0,00601 | pior caso: 8 ferramentas em sequência + resposta |

**Volume mensal adotado: 400 pedidos.** O enunciado fala em "centenas de pedidos" por mês, e 400
é um ponto intermediário dessa ordem de grandeza. Aplicando a proporção do acervo (2 de 12
pedidos em diligência, cada um voltando com uma complementação):

| Item | Valor |
|---|---:|
| Pedidos completos | 333 |
| Pedidos em diligência | 67 |
| Complementações | 67 |
| Execuções do agente no mês | 467 |
| **Custo mensal estimado** | **US$ 1,50** |
| Custo médio por pedido protocolado | US$ 0,00375 |

**Leitura.**

- **O teto fixa o custo da cauda.** O pior caso, limitado pelo `tool_call_limit=8`, custa cerca
  de 1,8 vez um pedido completo (US$ 0,00601 contra US$ 0,00333). Sem teto, um pedido que fizesse
  o agente insistir não teria limite de custo (Aula 03, custo da cauda).
- **O custo não é o problema do processo.** Mesmo multiplicado por dez, o gasto mensal seria
  pequeno diante do valor das diárias instruídas. O risco está na confiabilidade da Seção 4.
- **A estimativa será confrontada com o medido** no `relatorio.md`. Na referência do enunciado,
  a estimativa para cinco passos ficou a menos de 3% do valor medido.

## 6. Quadrante de autonomia

A Aula 01 (Seção 5) posiciona o processo, e não o agente, em dois eixos: a reversibilidade do
erro e o tempo até que ele seja detectado.

|  | Erro detectado logo | Erro detectado tarde |
|---|---|---|
| **Reversível** | Agente age dentro de limites | Agente age, com auditoria por amostra |
| **Irreversível** | Agente age mediante aprovação | **Agente apenas aconselha** ← este processo |

**Detecção: tarde.** Um erro de instrução, como uma diária concedida a quem tem prestação
vencida, costuma ser percebido apenas na auditoria, meses depois do pagamento.

**Reversibilidade: apenas formal.** Em tese, a diária paga indevidamente pode ser devolvida, o
que colocaria o processo no quadrante "age, com auditoria por amostra". Na prática, a reversão
exige processo de ressarcimento, notificação do servidor e devolução de um valor que já foi gasto
na viagem. A auditoria por amostra encontraria o erro justamente no momento em que ele já se
tornou caro de desfazer, que é o problema descrito no enunciado. Por isso o processo é tratado
como **irreversível e detectado tarde**.

**A própria norma reserva a decisão.** O art. 10 da IN estabelece que a instrução não substitui a
autorização do ordenador de despesa.

**Consequência para o desenho.** O agente **apenas aconselha**: prepara a instrução e a minuta e
recomenda um de três encaminhamentos (apto para autorização, diligência ou não recomendado), sem
decidir. A conferência humana é uma etapa obrigatória do fluxo, no formulário: o servidor confere
cada instrução, edita a minuta e registra o encaminhamento que decidiu ao lado do que o agente
sugeriu. Com a confiabilidade estimada na Seção 4, a conferência é de todos os pedidos, e não por
amostra. O registro das divergências entre servidor e agente permitirá medir, com o uso, se esse
ponto de conferência pode ser revisto.

## 7. Informação que o agente não terá

Um agente só julga bem o que lhe foi entregue (Aula 01, Seção 9). As informações abaixo não estão
nas fontes que as ferramentas alcançam, e o desenho as trata explicitamente:

| Informação ausente | Exemplo no acervo | Como o desenho trata |
|---|---|---|
| Se a autorização escrita do Secretário Adjunto existe no processo | DIA-2026-0106 | O agente não presume a autorização: marca `exige_autorizacao_superior` e registra o alerta para o conferente |
| Outros pedidos em andamento sobre o mesmo saldo | DIA-2026-0101 e DIA-2026-0102, da mesma unidade (CFF) e da mesma viagem | O saldo é comparado com cada pedido isoladamente, como na norma; o conferente vê o saldo informado pela ferramenta |
| Feriados no período da prestação de contas | Prazos de prestação do histórico | A ferramenta conta dias úteis sem feriados e declara esse limite no resultado |
| A veracidade dos fatos da justificativa | A urgência do DIA-2026-0106 e a "autorização verbal" do DIA-2026-0107 | O agente classifica pelo texto, segundo o art. 5º, e deixa a confirmação dos fatos ao conferente e ao ordenador |
