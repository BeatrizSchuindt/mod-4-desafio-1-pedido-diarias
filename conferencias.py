"""Registro da conferência humana: o encaminhamento decidido pelo servidor, ao lado do sugerido
pelo agente, com o motivo quando os dois divergem.

É o lugar físico da conferência (Aula 01, Seção 5; Aula 05) e o que permite medir, com o uso,
com que frequência o servidor discorda do agente. Fica em tabela própria do órgão
(banco/conferencias.db), separada do banco do agente, porque é dado do processo, e não memória
do framework (Aula 07, Seção 4).

Minimização: o registro não guarda nome, matrícula nem o texto da minuta, só o número do
pedido. A minuta conferida segue para o processo oficial pelo botão de download do formulário.
O motivo é texto livre, e a tela orienta a não escrever dado pessoal nele.

A data do registro é a do relógio do sistema, e não a data da análise fixa no acervo
(2026-10-09), que vale só para as regras da norma. É ela que conta o prazo de retenção do banco
do agente (eliminacao.expurgar).
"""
import csv
import sqlite3
from datetime import datetime
from pathlib import Path

BANCO_CONFERENCIAS = Path(__file__).parent / "banco" / "conferencias.db"

# Encaminhamentos possíveis. Os três primeiros correspondem às recomendações do agente; o
# último é o destino de toda instrução que não chegou ao conferente (erro ou recusa).
ENCAMINHAMENTOS = {
    "apto_para_autorizacao": "Encaminhar ao ordenador: apto para autorização",
    "nao_recomendado": "Encaminhar ao ordenador: não recomendado",
    "diligencia": "Devolver ao solicitante em diligência",
    "analise_manual": "Devolver à análise manual",
}

_CRIAR = """CREATE TABLE IF NOT EXISTS conferencias (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_pedido TEXT NOT NULL,
    turno TEXT NOT NULL,                 -- pedido ou complementacao
    situacao_instrucao TEXT NOT NULL,    -- entregue, recusada ou erro
    sugestao_agente TEXT NOT NULL,       -- recomendação do agente, ou analise_manual
    encaminhamento TEXT NOT NULL,        -- decidido pelo servidor
    divergiu INTEGER NOT NULL,
    motivo TEXT NOT NULL,
    minuta_editada INTEGER NOT NULL,
    chamadas INTEGER,
    custo_usd REAL,
    segundos REAL,
    registrado_em TEXT NOT NULL
)"""


def _conectar(banco: Path) -> sqlite3.Connection:
    Path(banco).parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(banco)
    conexao.row_factory = sqlite3.Row
    conexao.execute(_CRIAR)
    return conexao


def registrar(numero_pedido: str, turno: str, situacao_instrucao: str,
              recomendacao_agente: str | None, encaminhamento: str, motivo: str = "",
              minuta_editada: bool = False, medidas: dict | None = None,
              banco: Path = BANCO_CONFERENCIAS, agora: datetime | None = None) -> dict:
    """Grava a decisão do servidor. O motivo é obrigatório quando ela diverge da sugestão.

    Quando a instrução não foi entregue (erro ou recusa), a sugestão é "analise_manual".
    """
    if encaminhamento not in ENCAMINHAMENTOS:
        raise ValueError(f"encaminhamento desconhecido: {encaminhamento}")
    sugestao = recomendacao_agente if situacao_instrucao == "entregue" else "analise_manual"
    divergiu = encaminhamento != sugestao
    if divergiu and not motivo.strip():
        raise ValueError("o motivo é obrigatório quando o encaminhamento diverge da sugestão")
    medidas = medidas or {}
    registro = {"numero_pedido": numero_pedido, "turno": turno,
                "situacao_instrucao": situacao_instrucao, "sugestao_agente": sugestao,
                "encaminhamento": encaminhamento, "divergiu": int(divergiu),
                "motivo": motivo.strip(), "minuta_editada": int(minuta_editada),
                "chamadas": medidas.get("chamadas_ao_modelo"),
                "custo_usd": medidas.get("custo_usd"), "segundos": medidas.get("segundos"),
                "registrado_em": (agora or datetime.now()).isoformat(timespec="seconds")}
    with _conectar(banco) as conexao:
        conexao.execute(f"INSERT INTO conferencias ({', '.join(registro)}) "
                        f"VALUES ({', '.join('?' for _ in registro)})", list(registro.values()))
    return registro


def listar(banco: Path = BANCO_CONFERENCIAS) -> list[dict]:
    """Todos os registros, do mais recente para o mais antigo."""
    if not Path(banco).exists():
        return []
    with _conectar(banco) as conexao:
        return [dict(linha) for linha in
                conexao.execute("SELECT * FROM conferencias ORDER BY id DESC")]


def indicadores(banco: Path = BANCO_CONFERENCIAS) -> dict:
    """Quantas conferências, quantas discordâncias e quantas instruções não chegaram à tela."""
    registros = listar(banco)
    total = len(registros)
    divergencias = sum(r["divergiu"] for r in registros)
    sem_instrucao = sum(r["situacao_instrucao"] != "entregue" for r in registros)
    return {"total": total, "divergencias": divergencias,
            "taxa_divergencia": divergencias / total if total else 0.0,
            "sem_instrucao": sem_instrucao,
            "minutas_editadas": sum(r["minuta_editada"] for r in registros)}


def ultimo_registro_por_pedido(banco: Path = BANCO_CONFERENCIAS) -> dict[str, datetime]:
    """A data do último registro de cada pedido, que conta o prazo de retenção."""
    ultimo: dict[str, datetime] = {}
    for registro in listar(banco):
        data = datetime.fromisoformat(registro["registrado_em"])
        if registro["numero_pedido"] not in ultimo or data > ultimo[registro["numero_pedido"]]:
            ultimo[registro["numero_pedido"]] = data
    return ultimo


def exportar_csv(destino: Path, banco: Path = BANCO_CONFERENCIAS) -> Path:
    """Grava os registros em CSV, como evidência para a pasta resultados/."""
    registros = listar(banco)
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "w", newline="", encoding="utf-8") as arquivo:
        if registros:
            escritor = csv.DictWriter(arquivo, fieldnames=list(registros[0]))
            escritor.writeheader()
            escritor.writerows(reversed(registros))
    return destino
