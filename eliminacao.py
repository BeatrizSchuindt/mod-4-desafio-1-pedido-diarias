"""Rotina de eliminação dos dados de um servidor guardados pelo agente (LGPD, art. 18).

O banco do agente guarda o que passou pelas conversas: o pedido (já filtrado), as consultas e
as instruções, nas tabelas de sessões e de execuções, e, quando as memórias do usuário estão
ligadas, os fatos que o Agno extraiu sobre a pessoa (Aula 07, Seção 2). A eliminação tem três
etapas, executadas sempre, porque o que o agente guarda é probabilístico (Aula 07, Seção 6):

1. apagar as sessões do titular, encontradas pelo user_id (a matrícula); a exclusão leva junto
   as execuções dessas sessões;
2. listar as memórias do titular e apagá-las pelos identificadores (delete_user_memories
   recebe a lista de ids, e não o usuário);
3. conferir o banco tabela por tabela, procurando a matrícula e o nome do titular.

A etapa 3 é obrigatória por causa de pedidos como o DIA-2026-0112: a matrícula digitada era de
outro servidor, a sessão ficou gravada sob o identificador dele, e a busca pelo user_id da
titular não a encontra. A varredura acha a sessão pelo conteúdo; apagá-la exige confirmação
(`apagar_encontradas=True`), porque um homônimo também apareceria pelo nome.

Alcance: só o banco do agente, que é cópia de trabalho. O processo de diárias é registro de
despesa pública, sujeito à transparência e à guarda das normas de prestação de contas, e não é
tocado por esta rotina.

Uso:
    python eliminacao.py 206689 "Beatriz Moraes Cunha"
    python eliminacao.py 207418 "Carla Regina Souza" --apagar-encontradas
    python eliminacao.py 207418 "Carla Regina Souza" --banco bancos/eliminacao.db
"""
import argparse
import json
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from agno.db.base import SessionType
from agno.db.sqlite import SqliteDb

from agente import BANCO_PADRAO


# ------------------------------------------------------------------ inspeção do banco

def _variantes(termo: str) -> set[str]:
    """O termo como texto e como o JSON o grava (acentos viram \\u00e1 com ensure_ascii)."""
    return {termo.casefold(), json.dumps(termo)[1:-1].casefold()}


def _contem(texto: str, termos: list[str]) -> bool:
    """O texto contém algum dos termos? Números (a matrícula) só casam isolados."""
    texto = texto.casefold()
    for termo in termos:
        if termo.isdigit():
            if re.search(rf"(?<!\d){termo}(?!\d)", texto):
                return True
        elif any(variante in texto for variante in _variantes(termo)):
            return True
    return False


def tabelas(banco: Path) -> dict[str, int]:
    """Quantas linhas há em cada tabela do banco."""
    if not Path(banco).exists():
        return {}
    with sqlite3.connect(banco) as conexao:
        nomes = [n for (n,) in conexao.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        return {n: conexao.execute(f'SELECT COUNT(*) FROM "{n}"').fetchone()[0] for n in nomes}


def ocorrencias(banco: Path, termos: list[str]) -> dict[str, int]:
    """Em cada tabela, quantas linhas contêm algum dos termos (a conferência da etapa 3)."""
    if not Path(banco).exists():
        return {}
    encontrado = {}
    with sqlite3.connect(banco) as conexao:
        for (tabela,) in conexao.execute("SELECT name FROM sqlite_master WHERE type='table'"):
            linhas = conexao.execute(f'SELECT * FROM "{tabela}"').fetchall()
            total = sum(1 for linha in linhas if _contem(str(linha), termos))
            if total:
                encontrado[tabela] = total
    return encontrado


def sessoes(banco: Path) -> list[dict]:
    """As sessões gravadas: número do pedido, user_id e quantas execuções guardam."""
    if not Path(banco).exists():
        return []
    db = SqliteDb(db_file=str(banco))
    return [{"session_id": s.session_id, "user_id": s.user_id, "execucoes": len(s.runs or [])}
            for s in (db.get_sessions(session_type=SessionType.AGENT) or [])]


def memorias(banco: Path) -> list[dict]:
    """As memórias do usuário extraídas pelo Agno, de todos os usuários."""
    if not Path(banco).exists():
        return []
    db = SqliteDb(db_file=str(banco))
    return [{"memory_id": m.memory_id, "user_id": m.user_id, "memoria": m.memory}
            for m in (db.get_user_memories() or [])]


# ------------------------------------------------------------------ eliminação

@dataclass
class Relatorio:
    """O que a rotina fez e o que restou, etapa por etapa."""
    matricula: str
    nome: str
    antes: dict = field(default_factory=dict)
    sessoes_apagadas: list[str] = field(default_factory=list)
    memorias_apagadas: int = 0
    restos_apos_user_id: dict = field(default_factory=dict)
    encontradas_na_varredura: list[dict] = field(default_factory=list)
    apagadas_na_varredura: bool = False
    depois: dict = field(default_factory=dict)

    @property
    def nada_restou(self) -> bool:
        return not self.depois


def eliminar_titular(matricula: str, nome: str, banco: Path = BANCO_PADRAO,
                     apagar_encontradas: bool = False) -> Relatorio:
    """Elimina do banco do agente os dados do titular e confere o que restou."""
    relatorio = Relatorio(matricula=matricula, nome=nome)
    termos = [matricula, nome]
    relatorio.antes = ocorrencias(banco, termos)
    if not Path(banco).exists():
        return relatorio
    db = SqliteDb(db_file=str(banco))

    # 1. Sessões do titular pelo user_id; a exclusão leva junto as execuções.
    proprias = db.get_sessions(session_type=SessionType.AGENT, user_id=matricula) or []
    relatorio.sessoes_apagadas = [s.session_id for s in proprias]
    if relatorio.sessoes_apagadas:
        db.delete_sessions(session_ids=relatorio.sessoes_apagadas, user_id=matricula)

    # 2. Memórias do titular: listar para obter os ids e então apagar.
    ids = [m.memory_id for m in (db.get_user_memories(user_id=matricula) or []) if m.memory_id]
    if ids:
        db.delete_user_memories(memory_ids=ids, user_id=matricula)
    relatorio.memorias_apagadas = len(ids)

    # 3. Conferência tabela por tabela, pela matrícula e pelo nome.
    relatorio.restos_apos_user_id = ocorrencias(banco, termos)
    if relatorio.restos_apos_user_id:
        for sessao in db.get_sessions(session_type=SessionType.AGENT) or []:
            if _contem(json.dumps(sessao.to_dict(), default=str, ensure_ascii=False), termos):
                relatorio.encontradas_na_varredura.append(
                    {"tipo": "sessão", "id": sessao.session_id, "user_id": sessao.user_id})
        for memoria in db.get_user_memories() or []:
            if _contem(str(memoria.memory), termos):
                relatorio.encontradas_na_varredura.append(
                    {"tipo": "memória", "id": memoria.memory_id, "user_id": memoria.user_id})
        if apagar_encontradas and relatorio.encontradas_na_varredura:
            sessoes_achadas = [e["id"] for e in relatorio.encontradas_na_varredura
                               if e["tipo"] == "sessão"]
            memorias_achadas = [e["id"] for e in relatorio.encontradas_na_varredura
                                if e["tipo"] == "memória"]
            if sessoes_achadas:
                db.delete_sessions(session_ids=sessoes_achadas)
            if memorias_achadas:
                db.delete_user_memories(memory_ids=memorias_achadas)
            relatorio.apagadas_na_varredura = True

    relatorio.depois = ocorrencias(banco, termos)
    return relatorio


def mostrar(relatorio: Relatorio) -> None:
    print(f"Titular: {relatorio.nome} (matrícula {relatorio.matricula})")
    print(f"  antes, aparece em: {relatorio.antes or 'nenhuma tabela'}")
    print(f"  1. sessões apagadas pelo user_id: {relatorio.sessoes_apagadas or 'nenhuma'}")
    print(f"  2. memórias apagadas pelo user_id: {relatorio.memorias_apagadas}")
    print(f"  3. conferência tabela por tabela: {relatorio.restos_apos_user_id or 'nada restou'}")
    for achado in relatorio.encontradas_na_varredura:
        print(f"     encontrada pelo conteúdo: {achado['tipo']} {achado['id']} "
              f"(user_id {achado['user_id']})")
    if relatorio.encontradas_na_varredura:
        print(f"     {'apagadas após confirmação' if relatorio.apagadas_na_varredura else 'NÃO apagadas: confirme com --apagar-encontradas'}")
    print(f"  depois, aparece em: {relatorio.depois or 'nenhuma tabela — nada restou'}")


if __name__ == "__main__":
    argumentos = argparse.ArgumentParser(description="Elimina do banco do agente os dados de um servidor.")
    argumentos.add_argument("matricula")
    argumentos.add_argument("nome")
    argumentos.add_argument("--banco", type=Path, default=BANCO_PADRAO)
    argumentos.add_argument("--apagar-encontradas", action="store_true",
                            help="apaga também as sessões e memórias achadas pelo conteúdo")
    opcoes = argumentos.parse_args()
    mostrar(eliminar_titular(opcoes.matricula, opcoes.nome, opcoes.banco, opcoes.apagar_encontradas))
