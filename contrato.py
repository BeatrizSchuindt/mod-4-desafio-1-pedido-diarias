"""O contrato da instrução: o objeto que o agente devolve e que a barreira, o formulário e a
medição leem sem interpretar texto.

São os campos mínimos do enunciado, sem acréscimos: cada um existe porque alguém o lê. As
descrições (`Field(description=...)`) seguem para o modelo junto com o esquema da saída e
dizem de onde vem cada valor.
"""
from typing import Literal, Optional, get_args

from pydantic import BaseModel, Field

Criterio = Literal["cadastro", "dados_completos", "antecedencia", "prestacao_contas",
                   "limite_mensal", "saldo_orcamentario"]
CRITERIOS: tuple[str, ...] = get_args(Criterio)

Recomendacao = Literal["apto_para_autorizacao", "diligencia", "nao_recomendado"]


class Verificacao(BaseModel):
    criterio: Criterio = Field(description="Critério da norma verificado")
    situacao: Literal["atende", "nao_atende", "nao_verificado"] = Field(
        description="Situação como veio da ferramenta; nao_verificado quando a ferramenta que "
                    "decide o critério não foi consultada, como na diligência")
    detalhe: str = Field(description="O dado que fundamenta a situação, como veio da ferramenta")


class Instrucao(BaseModel):
    numero_pedido: str = Field(description="Número do pedido, como DIA-2026-0101")
    matricula: str = Field(description="Matrícula cujo cadastro foi consultado")
    quantidade_diarias: Optional[float] = Field(
        description="Quantidade devolvida por calcular_diarias; nulo na diligência")
    valor_total: Optional[float] = Field(
        description="Valor total em reais devolvido por calcular_diarias; nulo na diligência")
    verificacoes: list[Verificacao] = Field(
        description="Exatamente uma verificação para cada um dos seis critérios")
    recomendacao: Recomendacao = Field(
        description="apto_para_autorizacao se todos os critérios forem atendidos; diligencia se "
                    "o pedido estiver incompleto ou divergir do cadastro; nao_recomendado se "
                    "houver impedimento")
    exige_autorizacao_superior: bool = Field(
        description="Verdadeiro só quando a antecedência é insuficiente e a justificativa "
                    "descreve urgência legítima (art. 5º, §§ 1º e 2º)")
    pendencias: list[str] = Field(
        description="O que o solicitante precisa corrigir ou complementar; vazio se nada")
    alertas: list[str] = Field(
        description="O que o conferente precisa ver: ordens embutidas no pedido, dados "
                    "mascarados, autorização superior exigida")
    minuta_despacho: str = Field(
        description="Minuta do despacho ao ordenador de despesa, que recomenda sem decidir")
