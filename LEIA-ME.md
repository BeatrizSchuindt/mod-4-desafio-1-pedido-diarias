# LEIA-ME: Instrução de Pedidos de Diárias (SEMA-MT)

Agente feito com Agno 3.0.9 e o modelo `gpt-5.6-luna` que **prepara a instrução** de um pedido
de diárias para conferência: faz as consultas que a norma exige, calcula quantidade e valor,
recomenda um encaminhamento e redige a minuta do despacho. **O agente não decide.** Quem decide é
o ordenador de despesa, depois da conferência de um servidor.

> Protótipo acadêmico (FIC DEV IA, Módulo 4, Desafio 01). A norma (IN SEMA nº 07/2026), os
> servidores e os pedidos são hipotéticos.

Outros documentos: o [`desenho.md`](desenho.md) traz o processo, o PEAS e as contas feitas antes
do código; o [`relatorio.md`](relatorio.md) traz os números medidos e as falhas; a pasta
[`docs/`](docs/README.md) traz o diário de cada etapa.

## 1. Como o sistema funciona

```
pedido protocolado
   │
   ▼
filtro de dados pessoais ── CPF, conta, agência e e-mail viram asteriscos
   │
   ▼
agente (Agno) ── 4 ferramentas, uma por vez:
   │             cadastro → cálculo → histórico → saldo
   ▼
conferência no código ── 1) a execução terminou bem?
   │                     2) a resposta segue o contrato Instrucao?
   │                     3) a barreira aprova? (todo dado veio do pedido ou das ferramentas)
   │
   ├── não ──▶ mensagem padrão; o pedido volta à análise manual
   ▼
formulário de conferência ── o servidor confere, edita a minuta e registra o que decidiu
   │
   ▼
ordenador de despesa ── defere ou indefere
```

**A recomendação tem três valores:**
- **apto para autorização:** todos os critérios foram atendidos;
- **não recomendado:** há um impedimento, como antecedência curta, prestação de contas vencida,
  limite mensal passado ou falta de saldo;
- **diligência:** o pedido está incompleto ou não bate com o cadastro.

Na diligência, o servidor envia a complementação **na mesma sessão** do pedido, e o agente
recupera o caso pelo histórico.

## 2. Como executar

### 2.1 O que é preciso

- Python 3.13 (testado na 3.13.16).
- Uma chave da OpenAI, só para os comandos marcados com 💲 nas tabelas abaixo.

### 2.2 Instalação

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # abra o .env num editor e cole a chave depois de OPENAI_API_KEY=
```

A chave fica só no `.env`, que está no `.gitignore`. O código lê a chave com `load_dotenv`, e ela
nunca aparece no código, no relatório nem na tela.

Os dados do órgão já estão em `exemplos/dados/`. Eles foram gerados por `exemplos/gerar_dados.py`
e não precisam ser gerados de novo.

### 2.3 Testes sem chave (não usam o modelo)

| Comando | O que confere |
|---|---|
| `python testar_ferramentas.py` | As 4 ferramentas nos 12 pedidos e nas 2 complementações, contra o gabarito |
| `python testar_filtro.py` | O filtro mascara CPF, conta e e-mail, e não mexe em matrícula, data e número do pedido |
| `python testar_barreira.py` | A barreira aprova as 14 instruções corretas e recusa as 17 adulteradas |
| `python testar_conferencias.py` | O registro da conferência e o expurgo por prazo |
| `python testar_minuta_pdf.py` | A minuta em PDF |
| `python estimativa_desenho.py` | As contas de passos, confiabilidade e custo do `desenho.md` |

Cada um termina com "Resultado: todas as conferências passaram". Para guardar a saída, acrescente
`| tee resultados/<nome>.txt`, como nos arquivos de [`resultados/`](resultados/).

### 2.4 O formulário de conferência (💲 cerca de US$ 0,004 por pedido)

```bash
streamlit run app_conferencia.py
```

O formulário tem quatro páginas:

| Página | O que faz |
|---|---|
| **Instruir pedido** | Escolha o pedido e clique em instruir. A tela mostra cada consulta enquanto ela acontece. Depois mostra a recomendação, as verificações com o fundamento, os alertas, as pendências, as consultas com os argumentos e a minuta editável. O servidor escolhe o encaminhamento (com motivo obrigatório quando discorda do agente) e registra; a minuta sai em PDF. Na diligência, aparece o campo da complementação |
| **Registro das conferências** | A taxa de discordância entre o servidor e o agente e a tabela das conferências, que pode ser exportada em CSV |
| **Eliminação de dados** | Eliminação dos dados de um servidor em três passos e expurgo das sessões vencidas (Seção 5.3) |
| **Sobre o sistema** | O que o agente faz e não faz, as proteções e os dados guardados |

Para ver a mensagem padrão de erro, que é o que o servidor vê quando a execução falha:

```bash
PROVOCAR_ERRO_API=1 streamlit run app_conferencia.py
```

### 2.5 O agente pela linha de comando (💲)

```bash
python instruir_pedido.py DIA-2026-0101            # um pedido
python instruir_pedido.py --todos                  # os 12 pedidos (cerca de US$ 0,05)
python instruir_pedido.py DIA-2026-0101 --provocar-erro-api
```

O comando mostra o que o conferente receberia, o motivo técnico de uma recusa (que nunca vai à
tela do formulário), as consultas, o consumo e, na última linha, o que o gabarito esperava.

### 2.6 Medições (💲)

| Comando | O que mede | Custo e tempo |
|---|---|---|
| `python medir.py --config A` | 3 rodadas contra o gabarito, com as paralelas desligadas | US$ 0,17 · 7 min |
| `python medir.py --config B` | O mesmo, com as paralelas ligadas | US$ 0,17 · 7 min |
| `python medir.py --comparar` | Compara A e B (não chama a API) | grátis |
| `python provocar_falhas.py` | 6 falhas provocadas, 3 vezes cada (`--falha N` repete uma só) | US$ 0,06 · 3 min |
| `python medir_memoria.py` | Custo por turno de três configurações de memória | US$ 0,04 |
| `python testar_eliminacao.py` | Eliminação de duas servidoras, conferida tabela por tabela | US$ 0,03 |

Os bancos usados nas medições ficam em `bancos/` e são apagados ou recriados a cada execução.
Os bancos do formulário ficam em `banco/`. Nenhum dos dois vai ao Git (`*.db` no `.gitignore`).

### 2.7 Eliminação e expurgo pela linha de comando

```bash
python eliminacao.py 206689 "Beatriz Moraes Cunha"                        # mostra o que há e apaga pela matrícula
python eliminacao.py 207418 "Carla Regina Souza" --apagar-encontradas     # apaga também o que a varredura achou
python eliminacao.py --expurgar                                           # apaga as sessões com mais de 30 dias
```

## 3. Mapa dos arquivos

| Arquivo | Papel |
|---|---|
| `dados.py` | Lê os dados do órgão uma vez. Descarta CPF e e-mail do cadastro já na leitura |
| `ferramentas.py` | As 4 ferramentas. Todas as contas ficam aqui, e não no modelo |
| `contrato.py` | O contrato da resposta (`Instrucao` e `Verificacao`, em Pydantic) |
| `filtro_dados_pessoais.py` | O filtro que mascara CPF, conta, agência e e-mail antes do modelo |
| `barreira.py` | A conferência, no código, de que todo dado da instrução veio do pedido ou das ferramentas |
| `agente.py` | Monta o agente e oferece `instruir()`, que o formulário e as medições usam |
| `eliminacao.py` | Eliminação dos dados de um servidor e expurgo por prazo |
| `conferencias.py`, `minuta_pdf.py` | Registro da conferência e minuta em PDF |
| `app_conferencia.py`, `paginas/`, `interface.py`, `.streamlit/` | O formulário Streamlit |
| `medir.py`, `provocar_falhas.py`, `medir_memoria.py`, `instruir_pedido.py`, `estimativa_desenho.py` | Medições e acompanhamento |
| `testar_*.py` | Testes |
| `resultados/` | As saídas de todos os testes e medições |

## 4. Decisões técnicas e justificativas

### O agente

| Decisão | Justificativa |
|---|---|
| `gpt-5.6-luna` com `reasoning_effort="none"` | Na família GPT-5.6, a API recusa ferramentas com o raciocínio ligado (erro 400, provocado e medido na Etapa 3) |
| **Todas as contas nas ferramentas.** O modelo só copia os vereditos ("Critério X: ATENDE.") | Cada conta feita pelo modelo seria mais um passo que pode errar. Assim, a barreira consegue conferir o que o modelo copiou |
| Resposta em objeto validado (`output_schema=Instrucao`), só com os campos que alguém lê | O formulário, a barreira e a medição leem campos, e não texto solto |
| Ordem fixa das consultas: cadastro → cálculo → histórico → saldo | O cálculo precisa do grupo do cadastro, e o histórico e o saldo precisam do cálculo |
| Chamadas paralelas desligadas e `tool_call_limit=8` | Seção 5.1 |
| `telemetry=False` | Nada sobre os pedidos sai para fora além da chamada ao modelo |
| O gabarito nunca é lido pelo agente | Um agente que vê a resposta esperada não está sendo medido |

### Proteções

| Decisão | Justificativa |
|---|---|
| Filtro de dados pessoais antes do modelo, sem os padrões dos EUA, com padrões de CPF e de conta/agência | O pedido 0104 traz CPF e conta na justificativa. Os padrões que vêm no Agno são dos EUA, e o de telefone casa com qualquer sequência de dez algarismos, como um número de processo (Aula 06). O de e-mail, que não depende de país, continua ligado |
| Status da execução conferido **antes** do conteúdo | Um erro da API chega como texto no conteúdo e pareceria uma resposta |
| Barreira no código, sem modelo | A instrução de sistema é um pedido ao modelo, e não uma garantia (Seção 5.2) |
| Recusa → só a mensagem padrão na tela | "Nada do conteúdo recusado aparece ao servidor." A instrução recusada fica guardada só para a medição |
| `consultar_servidor` não devolve o nome do titular de outra matrícula | É dado de terceiro, que a instrução não precisa |

### O formulário

| Decisão | Justificativa |
|---|---|
| O encaminhamento começa em branco, e não com a sugestão do agente | Deixar a sugestão marcada leva a aprovar sem ler |
| Motivo obrigatório quando o servidor discorda | Torna a discordância medível e auditável |
| O PDF sai com a decisão do servidor e a minuta como ele a deixou | O documento leva a decisão de quem confere, e não a sugestão do agente |
| Um único agente guardado em cache | Seguro porque o `session_id` e o `user_id` vão a cada execução |

## 5. Respostas às perguntas do enunciado

O enunciado anuncia quatro perguntas, mas lista três. Respondemos às três listadas (ver
[`docs/duvidas-enunciado.md`](docs/duvidas-enunciado.md)).

### 5.1 Que configuração de chamadas paralelas, teto de chamadas e memória você escolheu, e com base em que número?

**Chamadas paralelas: desligadas** (`parallel_tool_calls=False`).
- Com elas ligadas, o modelo **não usou nenhuma chamada paralela em 42 execuções**. O custo do
  pedido completo ficou igual (US$ 0,00430 contra 0,00432), assim como o tempo (10,6 s nas duas),
  e o acerto também (42 de 42 nas duas).
- Mesmo que o modelo as usasse, o ganho máximo seria de **1 chamada em 5**: só o histórico e o
  saldo podem ser pedidos juntos.
- Desligadas, a ordem das consultas é garantida pela API. Ligadas, ela depende só de o modelo
  obedecer à instrução.

**Teto de chamadas: `tool_call_limit=8`.**
- O máximo usado foi de **4 consultas em 84 execuções**, sem nenhuma repetida.
- Com o teto em 2, a instrução ficou incompleta nas **3 de 3** tentativas (falha 6).
- O teto de 8 dá o dobro do que foi usado, para o modelo poder repetir uma consulta que falhou, e
  limita o pior caso a **US$ 0,0076** por execução (1,8 vez a mediana de US$ 0,0043).

**Memória: histórico da sessão, com no máximo 3 execuções anteriores, sem memórias do usuário.**
- Cada pedido é uma sessão: o `session_id` é o número do pedido, e o `user_id` é a matrícula como
  foi protocolada, também na complementação.
- Com o histórico, a complementação foi aplicada ao pedido certo em **2 de 2** casos. Sem
  memória, em **0 de 2**.
- As memórias do usuário acertaram o mesmo (2 de 2), mas custaram **10% a 12% a mais** e
  guardaram dados pessoais num lugar a mais. No 0112, a memória ficou sob a matrícula de outro
  servidor.
- O histórico custa cerca de **700 tokens a mais por chamada** na complementação. A
  complementação inteira custa US$ 0,00500.

### 5.2 Como o sistema impede que uma instrução fundamentada em dado inventado chegue ao conferente?

Com cinco camadas, todas no código e nenhuma dependente de o modelo obedecer:

1. **O que não precisa ir ao modelo não vai.** CPF e e-mail do cadastro são descartados na
   leitura dos dados. O filtro mascara CPF, conta e agência do texto do pedido. A ferramenta de
   cadastro não devolve o nome de outra pessoa.
2. **Os números vêm das ferramentas.** Quantidade, valor, antecedência, prazos, limite mensal e
   saldo são calculados no código. O modelo só copia o resultado.
3. **A execução e o formato são conferidos.** Se a execução não terminou bem, ou se a resposta
   não segue o contrato `Instrucao`, a instrução é descartada.
4. **A barreira confere cada dado** (`barreira.py`), comparando a instrução com o pedido e com o
   que as ferramentas devolveram naquela execução:
   - **argumentos das consultas:** a matrícula, o nome, as datas e a UF usados nas consultas
     estão no pedido ou na complementação; o grupo e a unidade vieram do cadastro; a quantidade e
     o valor passados ao histórico e ao saldo vieram do cálculo;
   - **a instrução:** o número do pedido, a matrícula, a quantidade e o valor são os devolvidos;
     cada verificação é igual ao veredito da ferramenta; a recomendação é a que os vereditos
     impõem; todo valor em reais citado no texto foi devolvido por alguma ferramenta;
   - **completude:** uma recomendação de mérito só vale depois das quatro consultas;
   - **sigilo:** nenhum número com formato de CPF ou de conta aparece no texto;
   - **resultado adulterado:** se o resultado de uma ferramenta trouxer um veredito que ela não
     decide, ou dois vereditos diferentes para o mesmo critério, nada nele é confiável, e a
     instrução é recusada.
5. **Se qualquer conferência falhar**, a tela mostra só a mensagem padrão ("Não foi possível
   concluir a instrução automática deste pedido. Ele foi devolvido à análise manual."), e nada do
   conteúdo recusado aparece.

**O que foi medido:**
- Nos testes sem modelo, a barreira aprovou as **14 de 14** instruções corretas e recusou as
  **17 de 17** adulteradas: matrícula, data e grupo inventados, valor trocado, ordem escondida no
  pedido obedecida, CPF na minuta, veredito falso numa ferramenta e outros.
- Nas falhas provocadas, o modelo **inventou um nome** ("Rafael Augusto Mendes", que não existe
  no cadastro) e consultou com nome "*" e com matrícula vazia. A barreira recusou todas as vezes:
  **18 de 18 falhas contidas, nenhuma instrução errada entregue**.
- Contra o gabarito: **84 de 84 certas e nenhum erro silencioso.**

**Limite:** a barreira não julga a urgência, que é o único julgamento de texto do modelo. Se ele
errar, a instrução chega marcada como "exige autorização superior", com o alerta, e o conferente
confere. É um dos motivos de a conferência humana ser obrigatória
([`relatorio.md`](relatorio.md), Seção 9).

### 5.3 Que dados do servidor o agente guarda, por quanto tempo, e como o titular os elimina?

**O que é guardado, e onde:**

| Onde | O que guarda | Dado pessoal? |
|---|---|---|
| `banco/instrucoes.db` (banco do agente) | Por pedido: o texto do pedido já filtrado (nome, matrícula, destino, datas e justificativa), as consultas e os resultados (cargo, grupo, unidade, histórico de diárias e de prestações de contas, saldo) e a instrução com a minuta. A sessão é o número do pedido e fica sob a matrícula protocolada. O banco guarda todas as execuções do pedido, e só as 3 últimas voltam ao modelo | **Sim** |
| `banco/conferencias.db` (registro das conferências) | Número do pedido, sugestão do agente, decisão do servidor, se divergiu e o motivo, se a minuta foi editada, consumo e data | Não tem nome, matrícula nem minuta |

**O que não é guardado:**
- o CPF e o e-mail do cadastro, descartados na leitura;
- o CPF e os dados bancários colados na justificativa, mascarados antes do modelo e do banco (o
  teste de eliminação conferiu que não estão no banco);
- as memórias do usuário, que estão desligadas;
- o PDF da minuta, gerado na hora para baixar.

**Por quanto tempo:** a sessão de um pedido fica no banco do agente até **30 dias depois do
último registro do conferente** naquele pedido.
- Na diligência, o registro da complementação recomeça a contagem.
- Sem nenhum registro (pedido abandonado), conta a última execução do agente.
- Motivo do prazo: o banco do agente é só uma cópia de trabalho. O registro oficial é o processo
  de diárias, e 30 dias cobrem a ida e a volta de uma diligência.
- As sessões vencidas são apagadas pelo botão da página **Eliminação de dados** ou por
  `python eliminacao.py --expurgar`, que pode ser agendado (por exemplo, uma vez por dia). O
  expurgo **não é automático**: alguém precisa clicar ou agendar o comando.
- O registro das conferências não é expurgado: não tem dado pessoal e é a base da medida de
  discordância.

**Como o titular elimina os dados:** o servidor pede à Coordenadoria, e quem opera o sistema usa
a página **Eliminação de dados** (ou `eliminacao.py`), em três passos:

1. **Identificar.** Informa a matrícula e o nome completo. O sistema confere no cadastro
   funcional se os dois são da mesma pessoa. Sem isso, digitar a matrícula de outra pessoa com
   qualquer nome apagaria os dados dela. Neste passo, nada é apagado.
2. **Ver o que existe.** O sistema mostra:
   - as sessões e as memórias encontradas pela matrícula;
   - o que uma **varredura tabela por tabela**, pela matrícula e pelo nome, achou sob outro
     identificador.

   A varredura é necessária por causa de casos como o do 0112: a matrícula digitada era de outro
   servidor, e a sessão ficou gravada sob o identificador dele.
3. **Confirmar.** O sistema apaga as sessões (que levam junto as execuções) e as memórias pelos
   identificadores, e confere de novo, tabela por tabela, que **nada restou**.

O que a varredura acha sob outro identificador só é apagado com confirmação, porque um homônimo
também apareceria pelo nome. No teste ([`teste_eliminacao.txt`](resultados/teste_eliminacao.txt)):
- os dados da Beatriz foram apagados pela matrícula;
- os da Carla foram achados pela varredura, sob a matrícula 207481, e apagados;
- os do Heitor, que serviu de testemunha, ficaram intactos;
- nada das duas restou no banco.

**O que a eliminação não alcança:** o processo de diárias. Ele é registro de despesa pública,
sujeito à transparência e às regras de prestação de contas. A LGPD permite guardar dados para
cumprir obrigação legal (art. 16, I). A rotina atende o direito de eliminação (art. 18) no banco
do agente, que é onde o sistema guarda dados.

## 6. Limites conhecidos

- **A norma, os servidores e os pedidos são hipotéticos**, e a data da análise é fixa
  (09/10/2026).
- **A barreira não julga a urgência.** O erro de julgamento chega sinalizado ao conferente.
- **O agente não vê** se a autorização escrita do Secretário Adjunto existe, não sabe de outros
  pedidos sobre o mesmo saldo, não conta feriados e não confirma se a justificativa é verdadeira.
- **O expurgo de 30 dias depende de alguém** clicar no botão ou agendar o comando.
- **O filtro reconhece formatos, e não significado.** Um CPF escrito por extenso, por exemplo,
  passa sem ser mascarado.
- **O motivo da discordância é texto livre do conferente.** Ele não deve escrever nome, CPF ou
  dados bancários nesse campo.
- **84 acertos em 84 não provam que o agente nunca erra:** são só 14 casos diferentes
  ([`relatorio.md`](relatorio.md), Seção 3).
