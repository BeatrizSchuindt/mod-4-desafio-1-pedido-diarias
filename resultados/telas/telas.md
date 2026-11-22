# Capturas do formulário de conferência

Capturas do formulário (`streamlit run app_conferencia.py`) em uso, com a API real. Cada imagem
mostra um item que o enunciado pede na Etapa 5 ou um item dos critérios de avaliação
("progresso visível, despacho editável, decisão do conferente registrada e mensagem padrão no
erro").

| Captura | O que mostra | O que o enunciado pede |
|---|---|---|
| [01](01-pedido-com-cpf-mascarado.png) | O DIA-2026-0104 com o CPF e a conta trocados por asteriscos já na tela | Filtro de dados pessoais |
| [02](02-recomendacao-e-alertas.png) | O DIA-2026-0106: recomendação, quantidade, valor e os alertas de autorização escrita do Secretário Adjunto | Recomendação e alertas |
| [03](03-verificacoes-e-consultas.png) | As seis verificações com o fundamento de cada uma e as quatro consultas com os argumentos | Verificações com o fundamento e consultas com os argumentos |
| [04](04-minuta-editavel.png) | A minuta do despacho sendo editada pelo servidor | Despacho editável |
| [05](05-divergencia-sem-motivo-recusada.png) | O servidor escolheu outro encaminhamento sem escrever o motivo, e o registro foi recusado | Motivo quando a decisão diverge da sugestão |
| [06](06-conferencia-registrada.png) | A conferência registrada, com a decisão do servidor, a divergência e o motivo | Decisão do conferente registrada |
| [07](07-minuta-em-pdf.png) | A minuta em PDF, com o texto editado, a sugestão do agente e a decisão do servidor | Despacho editável (o PDF sai com o texto como ficou depois da edição) |
| [08](08-diligencia-com-pendencia.png) | O DIA-2026-0112 em diligência: a pendência para o solicitante e os critérios "não verificado" | Pendências |
| [09](09-campo-da-complementacao.png) | O campo da complementação do DIA-2026-0111, enviada na mesma sessão do pedido | Complementação na mesma sessão |
| [10](10-complementacao-aplicada.png) | O DIA-2026-0112 depois da complementação: matrícula corrigida e pedido apto | Complementação aplicada ao pedido certo |
| [11](11-erro-mensagem-padrao.png) | Um erro de API provocado (`PROVOCAR_ERRO_API=1`): só a mensagem padrão aparece | Mensagem padrão no erro |
| [12](12-registro-das-conferencias.png) | A página de registro: 5 conferências, 1 discordância e a exportação para CSV | Medir com que frequência o servidor discorda |
| [13](13-eliminacao-titular-nao-conferido.png) | A eliminação recusada: a matrícula é de um servidor e o nome é de outro | Eliminação (proteção contra apagar dados de outra pessoa) |
| [14](14-eliminacao-nada-restou.png) | A eliminação feita: "nada restou", conferido tabela por tabela, e o que há no banco | Eliminação e o que restou no banco |

**O progresso visível não tem captura.** Ele só aparece durante os cerca de 10 segundos da
execução, e as capturas foram tiradas depois que cada instrução terminou (nelas, o quadro de
progresso já aparece fechado, como "Instrução concluída em X s"). Para vê-lo, basta instruir um
pedido no formulário: o quadro "Instruindo o pedido…" abre e mostra cada consulta no momento em
que ela começa. O código está em `executar_com_progresso`, no `interface.py`.

## De quando são

As 14 capturas são do roteiro de teste de 21/11/2026, feito entre 17h16 e 18h24 com a API real.
Foram recortadas para mostrar só o formulário, sem a barra do sistema e a do navegador.

Entre o roteiro e a versão final do formulário, só mudaram detalhes visuais:

- nas capturas 05, 06 e 13, os avisos do canto superior direito ainda não tinham cor (depois:
  verde para sucesso, amarelo para aviso e vermelho para erro);
- nas capturas 09 e 10, o botão de download ainda baixava a minuta em texto; o PDF da captura 07
  veio logo depois;
- na captura 12, o indicador de discordância tinha uma seta "↑", retirada depois porque parecia
  indicar aumento;
- na captura 13, a mensagem de recusa ganhou depois uma dica sobre a grafia do nome.

As duas capturas da primeira versão da página de eliminação ficaram de fora. Essa versão tinha
um defeito, corrigido antes da entrega: a matrícula de uma servidora digitada com o nome de outra
apagava os dados da primeira. A versão final confere no cadastro se a matrícula e o nome são da
mesma pessoa (captura 13).
