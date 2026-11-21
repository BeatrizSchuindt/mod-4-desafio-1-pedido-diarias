"""Filtro de dados pessoais aplicado ao pedido antes de ele chegar ao modelo e ao banco.

O PIIDetectionGuardrail do Agno vem com padrões norte-americanos (número da previdência dos
EUA, cartão de crédito, e-mail e telefone daquele país). O de telefone casa com qualquer
sequência de dez algarismos e mascararia números de processo, como a Aula 06 (Seção 5.2)
mostrou. Os padrões norte-americanos ficam desligados; o de e-mail, que não depende de país,
continua ligado; e entram dois padrões brasileiros:

- CPF: confere a máscara (000.000.000-00, com ou sem pontuação), e não os dígitos
  verificadores, porque os CPFs do acervo são inválidos de propósito;
- conta e agência bancária: número de 4 a 12 algarismos seguido de hífen e dígito, como
  98765-4 ou 1234-5.

A configuração está certa quando o CPF e os dados bancários do DIA-2026-0104 são mascarados e
nenhuma matrícula, data ou número de pedido muda; o testar_filtro.py confere as duas coisas.
O filtro reconhece formatos, e não significado: um dado pessoal escrito por extenso passa.
"""
from agno.guardrails import PIIDetectionGuardrail
from agno.run.agent import RunInput

PADROES = {
    "CPF": r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b",
    "CONTA_OU_AGENCIA": r"\b\d{4,12}-[\dXx]\b",
}


def filtro_dados_pessoais() -> PIIDetectionGuardrail:
    """Guardrail que troca CPF, dados bancários e e-mail por asteriscos (mask_pii=True)."""
    return PIIDetectionGuardrail(
        mask_pii=True,
        enable_ssn_check=False,
        enable_credit_card_check=False,
        enable_phone_check=False,
        custom_patterns=PADROES,
    )


def mascarar(texto: str) -> str:
    """Aplica o mesmo filtro a um texto qualquer, como o formulário faz antes de exibir o pedido.

    A tela também é um lugar de exposição: o servidor vê a justificativa como o modelo a viu.
    """
    entrada = RunInput(input_content=texto)
    filtro_dados_pessoais().check(entrada)
    return entrada.input_content
