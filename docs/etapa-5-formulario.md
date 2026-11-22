# Etapa 5 — Formulário de conferência

## Objetivo

Entregar o agente ao servidor numa aplicação Streamlit, no padrão de formulário da Aula 06:

- a tela mostra a recomendação, as verificações com o fundamento, os alertas, as pendências e as
  consultas com os argumentos;
- a minuta do despacho fica em campo editável;
- o servidor registra o encaminhamento que decidiu ao lado do que o agente sugeriu, com o motivo
  quando divergirem;
- na diligência, a complementação é enviada na mesma sessão do pedido;
- numa área separada, a tela aciona a rotina de eliminação e mostra o que restou no banco;
- se a execução falhar ou a barreira recusar a instrução, a tela exibe só a mensagem padrão e
  devolve o pedido à análise manual.

## O que foi feito

| Arquivo | Papel |
|---|---|
| `app_conferencia.py` | Ponto de entrada: tema, menu lateral com as páginas (`st.navigation`) |
| `paginas/instruir.py` | Instrução com progresso, conferência do servidor, minuta em PDF e complementação |
| `paginas/registro.py` | Indicadores (taxa de discordância) e tabela das conferências, com exportação para CSV |
| `paginas/eliminacao_dados.py` | Eliminação em três passos (identificar, ver, confirmar), inventário do banco e expurgo |
| `paginas/sobre.py` | O que o agente faz e não faz, proteções e dados guardados |
| `interface.py` | Identidade visual, toasts coloridos, agente em cache e funções que desenham a instrução |
| `conferencias.py` | Registro da conferência em `banco/conferencias.db`, sem dado pessoal |
| `minuta_pdf.py` | Minuta do despacho em PDF, com logo, marca d'água e aviso de protótipo |
| `testar_conferencias.py`, `testar_minuta_pdf.py` | Testes sem chave do registro, do expurgo e do PDF |
| `.streamlit/config.toml` | Tema SEMA-MT, estatísticas de uso desligadas, menu de desenvolvedor oculto |
| `agente.py` | `instruir(..., ao_chamar_ferramenta=...)`: progresso em modo de eventos |
| `eliminacao.py` | Conferência do titular no cadastro, localização sem apagar, expurgo por prazo |
| `filtro_dados_pessoais.py` | `mascarar()`, para a tela exibir a justificativa já filtrada |
| `assets/logo_sema.png` | Logo usado apenas na minuta em PDF |

**Identidade visual.** O azul da marca SEMA (`#1D3281`) e o azul do texto (`#252B77`) foram
extraídos da imagem da secretaria. A faixa sob o cabeçalho e a página ativa do menu usam as cores
da bandeira de Mato Grosso. Verde, amarelo e vermelho marcam sucesso, aviso e erro. A tela é
responsiva: no celular, o menu começa recolhido e o conteúdo se empilha. Todas as páginas e o PDF
avisam que é um protótipo acadêmico, com dados e norma hipotéticos.

**Como executar:**

```bash
streamlit run app_conferencia.py
PROVOCAR_ERRO_API=1 streamlit run app_conferencia.py   # demonstra a mensagem padrão
```

## Validação antes da execução real

Sem a chave do lado de quem escreveu o código, a etapa foi validada em três frentes, que não
vão ao repositório:

1. **Simulador da API.** Um transporte HTTP falso faz o papel do modelo, com suporte a
   streaming e ao erro 400 real da API.
2. **`AppTest` do Streamlit.** Um roteiro de 10 passos, com cerca de 40 conferências, executa as
   quatro páginas e clica nos botões sem navegador.
3. **Capturas num navegador headless** (Chromium), em 1366 px e 390 px de largura, e a
   renderização do PDF em imagem.

Essa validação encontrou e corrigiu, antes de chegar à execução real:

- o menu lateral abria por cima do conteúdo no celular;
- o cabeçalho ficava com um vazio no celular;
- o título do cabeçalho quebrava de linha no computador;
- no modo de eventos, o erro da API não entregava objeto de resposta.

## Comandos executados

```bash
pip install -r requirements.txt                       # fpdf2
python testar_conferencias.py | tee resultados/teste_conferencias.txt
python testar_minuta_pdf.py | tee resultados/teste_minuta_pdf.txt
python testar_eliminacao.py | tee resultados/teste_eliminacao.txt
streamlit run app_conferencia.py                      # roteiro manual, abaixo
PROVOCAR_ERRO_API=1 streamlit run app_conferencia.py
```

## Resultado e evidências

### Testes sem chave e de eliminação

- [`resultados/teste_conferencias.txt`](../resultados/teste_conferencias.txt): todas as
  conferências passaram. O registro exige motivo na divergência, a taxa de discordância é de 1/3
  no cenário de teste, o registro não tem colunas de nome, matrícula ou minuta, e o expurgo apaga
  só as sessões vencidas.
- [`resultados/teste_minuta_pdf.txt`](../resultados/teste_minuta_pdf.txt): o PDF é gerado com a
  fonte do sistema e também com a Helvetica de reserva; o exemplo está em
  [`resultados/minuta_exemplo.pdf`](../resultados/minuta_exemplo.pdf).
- [`resultados/teste_eliminacao.txt`](../resultados/teste_eliminacao.txt): todas as conferências
  passaram, inclusive a nova seção **[4]**. A matrícula da Beatriz (206689) com o nome da Carla é
  recusada, e os dados da Beatriz continuam no banco.
- Os testes anteriores (ferramentas, filtro e barreira) continuaram com código de saída 0.

### Roteiro manual com o modelo real (21/11/2026)

| Caso | O que se viu |
|---|---|
| 0101 | Progresso das 4 consultas, uma a uma; apto, 3,5 diárias, R$ 980,00 (15.840 tokens de entrada, US$ 0,0043, 10,6 s). Minuta editada e conferência registrada concordando com o agente |
| 0105 | Divergência sem motivo recusada (toast vermelho e erro na página); com o motivo, registrada como discordância |
| 0104 | Justificativa exibida com `CPF **************` e `conta corrente *******` |
| 0106 | Aviso de autorização escrita do Secretário Adjunto, na tela e em destaque laranja no PDF (2 páginas) |
| 0111 e 0112 | Diligência registrada e complementação enviada na mesma sessão; no 0112, apto, R$ 770,00 (19.261 tokens de entrada, US$ 0,0050, 11,4 s) |
| Eliminação da Carla (207418) | Nada encontrado pela matrícula; a varredura achou a sessão DIA-2026-0112 sob o identificador 207481; depois da confirmação, nada restou |
| Eliminação do Diego (204775) | Sessão DIA-2026-0106 apagada pela matrícula; conferido tabela por tabela, nada restou |
| Erro de API | "Instrução não concluída", só a mensagem padrão; sugestão do agente "Devolver à análise manual"; registro sem PDF |

**Registro das conferências** ([`resultados/conferencias.csv`](../resultados/conferencias.csv),
exportado durante o roteiro): 5 conferências, **1 discordância (20%)** no 0105 e 1 minuta
editada (0101).

## Achados e armadilhas

Defeitos encontrados pela aluna ao testar a interface, todos corrigidos e cobertos por teste:

1. **A eliminação apagava pela matrícula sem conferir o nome.** A matrícula 206689 (Beatriz) com o
   nome "Carla Regina Souza" apagou a sessão da Beatriz: bastaria digitar a matrícula de outra
   pessoa para apagar os dados dela. Agora `conferir_titular` exige que matrícula e nome sejam do
   mesmo servidor no cadastro funcional, antes de localizar ou apagar qualquer coisa, na tela e
   na linha de comando.
2. **A tela de eliminação apagava no primeiro clique.** Ela foi redesenhada em três passos:
   identificar (nada é apagado), ver o que existe (pela matrícula e sob outro identificador) e
   confirmar.
3. **"Diogo" × "Diego".** A recusa estava correta, mas não orientava. A mensagem agora pede para
   conferir a grafia, **sem revelar** o nome do cadastro (o que permitiria descobrir o nome de
   qualquer servidor pela matrícula). A comparação passou a ignorar maiúsculas, acentos e espaços
   extras. Depois de aceito, o titular é buscado pelo nome **oficial** do cadastro, para que
   "Patricia", digitado sem acento, ache "Patrícia" no banco.
4. **O toast não reaparecia ao repetir a mesma ação.** O Streamlit reaproveita o elemento quando
   o HTML se repete, e a animação, já terminada, não recomeçava: no segundo e no terceiro clique,
   o toast ficava invisível. A correção alterna entre duas animações idênticas de nomes
   diferentes, o que força o navegador a reiniciá-la (medido no navegador: visível nos 3 cliques).

Outros achados:

- **O `st.toast` do Streamlit não tem cor por tipo** nem permite estilizar por tipo. O toast passou
  a ser desenhado em HTML e CSS (verde, amarelo e vermelho).
- **Toasts longos ganham um "view more"** em inglês. Os toasts ficaram curtos, e o detalhe
  continua no aviso da página.
- **O `st.dataframe` cortava os fundamentos e os argumentos.** O `st.table` quebra a linha e
  mostra o texto inteiro.
- **A seta "↑ 20%" sugeria aumento** da taxa de discordância. Foi desligada (`delta_arrow="off"`).
- **No modo de eventos, o erro da API chega como `RunErrorEvent`, sem objeto de resposta.** Ele é
  convertido numa resposta com status de erro, e o motivo técnico fica igual ao do modo comum.
- **O registro técnico do erro** ("execução terminou com status ERROR") vai para o terminal do
  servidor, nunca para a tela.

## Decisões e justificativa

| Decisão | Justificativa |
|---|---|
| Encaminhamento começa em branco, sem a sugestão do agente | Pré-selecionar a sugestão induz a aprovar sem ler; o padrão nunca deve ser o desfecho que aprova (Aula 05) |
| Motivo obrigatório quando o servidor diverge | É o que torna a discordância mensurável e auditável |
| Registro da conferência em tabela própria, sem nome, matrícula ou minuta | Dado do processo fica em tabela do órgão (Aula 07, Seção 4); minimização (LGPD, art. 6º, III) |
| Página recarrega depois do registro e mostra a decisão e o PDF | O registro é o estado final da conferência; o formulário não pode ser reenviado por engano |
| PDF gerado no momento do registro, com a minuta como o servidor a deixou | O documento leva a decisão do servidor, e não a sugestão do agente |
| Marca d'água "MINUTA" e aviso de protótipo no PDF; logo só no PDF | O documento tem o logo oficial, mas não pode passar por documento oficial |
| Justificativa exibida já mascarada | A tela também é um lugar de exposição |
| Retenção: 30 dias depois do último registro do conferente (ou da última execução, sem registro) | O banco do agente é cópia de trabalho; o processo oficial é quem guarda o registro. A complementação reinicia o prazo |
| Registro das conferências não é expurgado | Não tem dado pessoal e é a base da medida de discordância |
| Eliminação só depois de conferir o titular no cadastro e com confirmação explícita | Impede apagar dados de terceiros e homônimos achados pela varredura |
| Toasts próprios, curtos, e o detalhe na página | Cor por tipo e mensagem legível sem o "view more" |
| Agente único em `@st.cache_resource` | Seguro porque `session_id` e `user_id` vão a cada `run` (Etapa 4) |
| Erro provocado por variável de ambiente (`PROVOCAR_ERRO_API=1`) | Demonstra a mensagem padrão sem expor a opção ao conferente |

## Pendências

Nenhuma. Situação final de cada item que estava pendente:

- **Capturas de tela:** feitas, em `resultados/telas/`, com um índice
  ([`telas.md`](../resultados/telas/telas.md)) que liga cada captura ao que o enunciado pede. As
  14 capturas são do roteiro real de 21/11, recortadas para mostrar só o formulário. O progresso
  durante a execução não tem captura, porque todas foram tiradas depois que a instrução
  terminou; o índice explica onde vê-lo.
- **`resultados/conferencias.csv`:** mantido com os 5 registros do roteiro, que são os citados no
  `relatorio.md` (5 conferências, 1 discordância). O banco local tem mais 2 registros, feitos
  depois da exportação. Eles não foram exportados, para o CSV continuar igual ao relatório.
- **Logo:** `assets/logo_sema.png` está no repositório.
- **Banco próprio na medição:** feito na Etapa 6 (`bancos/medicao_*.db`, apagado ao fim de cada
  rodada).
- **Conferência humana no relatório:** feita (Seção 9 do `relatorio.md`).
