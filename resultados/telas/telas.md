# Capturas do formulário de conferência

Capturas do formulário (`streamlit run app_conferencia.py`) em uso, com a API real. Cada imagem
mostra um item que o enunciado pede na Etapa 5 ou um item dos critérios de avaliação
("progresso visível, despacho editável, decisão do conferente registrada e mensagem padrão no
erro").

| Captura | O que mostra | O que o enunciado pede |
|---|---|---|
| [01](01-progresso-da-instrucao.png) | O quadro de progresso durante a execução, com cada consulta aparecendo no momento em que começa | Progresso visível |
| [02](02-pedido-com-cpf-mascarado.png) | O DIA-2026-0104 com o CPF e a conta trocados por asteriscos já na tela | Filtro de dados pessoais |
| [03](03-recomendacao-e-alertas.png) | O DIA-2026-0106: recomendação, quantidade, valor e os alertas de autorização escrita do Secretário Adjunto | Recomendação e alertas |
| [04](04-verificacoes-e-consultas.png) | As seis verificações com o fundamento de cada uma e as quatro consultas com os argumentos | Verificações com o fundamento e consultas com os argumentos |
| [05](05-minuta-editavel.png) | A minuta do despacho sendo editada pelo servidor | Despacho editável |
| [06](06-divergencia-sem-motivo-recusada.png) | O servidor escolheu outro encaminhamento sem escrever o motivo, e o registro foi recusado | Motivo quando a decisão diverge da sugestão |
| [07](07-conferencia-registrada.png) | A conferência registrada, com a decisão do servidor, a divergência e o motivo | Decisão do conferente registrada |
| [08](08-minuta-em-pdf.png) | A minuta em PDF, com o texto editado, a sugestão do agente e a decisão do servidor | Despacho editável (o PDF sai com o texto como ficou depois da edição) |
| [09](09-diligencia-com-pendencia.png) | O DIA-2026-0112 em diligência: a pendência para o solicitante e os critérios "não verificado" | Pendências |
| [10](10-campo-da-complementacao.png) | O campo da complementação do DIA-2026-0111, enviada na mesma sessão do pedido | Complementação na mesma sessão |
| [11](11-complementacao-aplicada.png) | O DIA-2026-0112 depois da complementação: matrícula corrigida e pedido apto | Complementação aplicada ao pedido certo |
| [12](12-erro-mensagem-padrao.png) | Um erro de API provocado (`PROVOCAR_ERRO_API=1`): só a mensagem padrão aparece | Mensagem padrão no erro |
| [13](13-registro-das-conferencias.png) | A página de registro: 5 conferências, 1 discordância e a exportação para CSV | Medir com que frequência o servidor discorda |
| [14](14-eliminacao-titular-nao-conferido.png) | A eliminação recusada: a matrícula é de um servidor e o nome é de outro | Eliminação (proteção contra apagar dados de outra pessoa) |
| [15](15-eliminacao-nada-restou.png) | A eliminação feita: "nada restou", conferido tabela por tabela, e o que há no banco | Eliminação e o que restou no banco |

## De quando são

- As capturas 02 a 15 são do roteiro de teste de 21/11/2026, feito entre 17h16 e 18h24 com a
  API real. Foram recortadas para mostrar só o formulário, sem a barra do sistema e a do
  navegador.
- A captura 01 é de 22/11/2026.

Entre o roteiro e a versão final do formulário, só mudaram detalhes visuais:

- nas capturas 06, 07 e 14, os avisos do canto superior direito ainda não tinham cor (depois:
  verde para sucesso, amarelo para aviso e vermelho para erro);
- nas capturas 10 e 11, o botão de download ainda baixava a minuta em texto; o PDF da captura 08
  veio logo depois;
- na captura 13, o indicador de discordância tinha uma seta "↑", retirada depois porque parecia
  indicar aumento;
- na captura 14, a mensagem de recusa ganhou depois uma dica sobre a grafia do nome.

As duas capturas da primeira versão da página de eliminação ficaram de fora. Essa versão tinha
um defeito, corrigido antes da entrega: a matrícula de uma servidora digitada com o nome de outra
apagava os dados da primeira. A versão final confere no cadastro se a matrícula e o nome são da
mesma pessoa (captura 14).
