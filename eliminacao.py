"""Rotina de eliminação dos dados de um servidor guardados pelo agente (LGPD, art. 18).

O banco do agente guarda o que passou pelas conversas: o pedido (já filtrado), as consultas e
as instruções, nas tabelas de sessões e de execuções, e, quando as memórias do usuário estão
ligadas, os fatos que o Agno extraiu sobre a pessoa (Aula 07, Seção 2). Antes de tudo, a
rotina confere no cadastro funcional que a matrícula e o nome são do mesmo servidor: sem isso,
a matrícula de outra pessoa, digitada com qualquer nome, apagaria os dados dela. A eliminação
tem então três etapas, executadas sempre, porque o que o agente guarda é probabilístico
(Aula 07, Seção 6):

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

Prazo de retenção: a sessão de um pedido fica no banco até 30 dias depois do último registro
do conferente naquele pedido (ver elegiveis_ao_expurgo); expurgar() apaga as vencidas.

Uso:
    python eliminacao.py 206689 "Beatriz Moraes Cunha"
    python eliminacao.py 207418 "Carla Regina Souza" --apagar-encontradas
    python eliminacao.py 207418 "Carla Regina Souza" --banco bancos/eliminacao.db
    python eliminacao.py --expurgar            # apaga as sessões com prazo de retenção vencido
"""
import argparse
import json
import re
import sqlite3
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

from datetime import datetime, timedelta

from agno.db.base import SessionType
from agno.db.sqlite import SqliteDb

from agente import BANCO_PADRAO
from conferencias import BANCO_CONFERENCIAS, ultimo_registro_por_pedido
from dados import SERVIDORES


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


def _nome(texto: str) -> str:
    """Nome para comparação: sem diferença de maiúsculas, acentos ou espaços extras."""
    sem_acento = "".join(c for c in unicodedata.normalize("NFKD", str(texto))
                         if not unicodedata.combining(c))
    return " ".join(sem_acento.split()).casefold()


def conferir_titular(matricula: str, nome: str) -> str:
    """A matrícula e o nome precisam ser do mesmo servidor no cadastro funcional.

    Sem esta conferência, quem digitasse a matrícula de outra pessoa com qualquer nome apagaria
    os dados dela: as etapas 1 e 2 procuram só pela matrícula. Levanta ValueError se não conferir
    e devolve o nome como está no cadastro, que é o usado na varredura: digitado sem acento, o
    nome não acharia o texto gravado com acento.
    """
    servidor = SERVIDORES.get(str(matricula).strip())
    if servidor is None:
        raise ValueError(f"a matrícula {matricula} não consta do cadastro funcional")
    if _nome(servidor["nome"]) != _nome(nome):
        # O nome do cadastro não é revelado: daria para descobrir o nome de qualquer servidor
        # digitando matrículas.
        raise ValueError(f"o nome informado não corresponde ao titular da matrícula {matricula} "
                         "no cadastro funcional. Confira a grafia do nome completo; maiúsculas "
                         "e acentos não fazem diferença")
    return servidor["nome"]


def _achados_por_conteudo(db: SqliteDb, termos: list[str], excluir_sessoes=(),
                          excluir_memorias=()) -> list[dict]:
    """Sessões e memórias que citam o titular, gravadas sob qualquer user_id (a varredura)."""
    achados = []
    for sessao in db.get_sessions(session_type=SessionType.AGENT) or []:
        if sessao.session_id not in excluir_sessoes and _contem(
                json.dumps(sessao.to_dict(), default=str, ensure_ascii=False), termos):
            achados.append({"tipo": "sessão", "id": sessao.session_id, "user_id": sessao.user_id})
    for memoria in db.get_user_memories() or []:
        if memoria.memory_id not in excluir_memorias and _contem(str(memoria.memory), termos):
            achados.append({"tipo": "memória", "id": memoria.memory_id, "user_id": memoria.user_id})
    return achados


@dataclass
class Localizacao:
    """O que o banco do agente guarda sobre o titular, antes de qualquer exclusão."""
    matricula: str
    nome: str
    sessoes: list[dict] = field(default_factory=list)       # pelo user_id
    memorias: list[dict] = field(default_factory=list)      # pelo user_id
    por_conteudo: list[dict] = field(default_factory=list)  # sob outro user_id
    ocorrencias: dict = field(default_factory=dict)         # tabela por tabela

    @property
    def vazio(self) -> bool:
        return not (self.sessoes or self.memorias or self.por_conteudo or self.ocorrencias)


def localizar_titular(matricula: str, nome: str, banco: Path = BANCO_PADRAO) -> Localizacao:
    """Lista, sem apagar nada, o que seria eliminado. Confere o titular no cadastro antes."""
    nome = conferir_titular(matricula, nome)
    local = Localizacao(matricula=matricula, nome=nome)
    if not Path(banco).exists():
        return local
    db = SqliteDb(db_file=str(banco))
    local.sessoes = [{"tipo": "sessão", "id": s.session_id, "user_id": s.user_id,
                      "execucoes": len(s.runs or [])}
                     for s in db.get_sessions(session_type=SessionType.AGENT, user_id=matricula) or []]
    local.memorias = [{"tipo": "memória", "id": m.memory_id, "user_id": m.user_id}
                      for m in db.get_user_memories(user_id=matricula) or []]
    local.por_conteudo = _achados_por_conteudo(
        db, [matricula, nome], {s["id"] for s in local.sessoes}, {m["id"] for m in local.memorias})
    local.ocorrencias = ocorrencias(banco, [matricula, nome])
    return local


def eliminar_titular(matricula: str, nome: str, banco: Path = BANCO_PADRAO,
                     apagar_encontradas: bool = False) -> Relatorio:
    """Elimina do banco do agente os dados do titular e confere o que restou.

    Confere antes, no cadastro funcional, que a matrícula e o nome são do mesmo servidor.
    """
    nome = conferir_titular(matricula, nome)
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
        relatorio.encontradas_na_varredura = _achados_por_conteudo(db, termos)
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


# ------------------------------------------------------------------ prazo de retenção

PRAZO_RETENCAO_DIAS = 30


def elegiveis_ao_expurgo(prazo_dias: int = PRAZO_RETENCAO_DIAS, banco: Path = BANCO_PADRAO,
                         banco_conferencias: Path = BANCO_CONFERENCIAS,
                         agora: datetime | None = None) -> list[dict]:
    """Sessões que já passaram do prazo de retenção.

    Regra: a sessão de um pedido é guardada até 30 dias depois do último registro do conferente
    naquele pedido. Na diligência, o registro feito quando a complementação chega reinicia o
    prazo. Sem nenhum registro (pedido abandonado), conta a última execução do agente.
    """
    if not Path(banco).exists():
        return []
    agora = agora or datetime.now()
    ultimo = ultimo_registro_por_pedido(banco_conferencias)
    elegiveis = []
    for sessao in SqliteDb(db_file=str(banco)).get_sessions(session_type=SessionType.AGENT) or []:
        if sessao.session_id in ultimo:
            referencia, origem = ultimo[sessao.session_id], "último registro do conferente"
        else:
            referencia = datetime.fromtimestamp(sessao.updated_at or sessao.created_at or 0)
            origem = "última execução (sem registro do conferente)"
        if agora - referencia > timedelta(days=prazo_dias):
            elegiveis.append({"session_id": sessao.session_id, "user_id": sessao.user_id,
                              "referencia": referencia.isoformat(timespec="seconds"),
                              "origem": origem})
    return elegiveis


def expurgar(prazo_dias: int = PRAZO_RETENCAO_DIAS, banco: Path = BANCO_PADRAO,
             banco_conferencias: Path = BANCO_CONFERENCIAS,
             agora: datetime | None = None) -> list[dict]:
    """Apaga as sessões vencidas (e as execuções delas) e devolve o que foi apagado."""
    elegiveis = elegiveis_ao_expurgo(prazo_dias, banco, banco_conferencias, agora)
    if elegiveis:
        SqliteDb(db_file=str(banco)).delete_sessions(
            session_ids=[e["session_id"] for e in elegiveis])
    return elegiveis


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
    argumentos.add_argument("matricula", nargs="?")
    argumentos.add_argument("nome", nargs="?")
    argumentos.add_argument("--banco", type=Path, default=BANCO_PADRAO)
    argumentos.add_argument("--apagar-encontradas", action="store_true",
                            help="apaga também as sessões e memórias achadas pelo conteúdo")
    argumentos.add_argument("--expurgar", action="store_true",
                            help=f"apaga as sessões com mais de {PRAZO_RETENCAO_DIAS} dias de retenção")
    opcoes = argumentos.parse_args()
    if opcoes.expurgar:
        apagadas = expurgar(banco=opcoes.banco)
        print(f"Sessões expurgadas por prazo de retenção: {len(apagadas)}")
        for sessao in apagadas:
            print(f"  {sessao['session_id']} (user_id {sessao['user_id']}): {sessao['origem']} em "
                  f"{sessao['referencia']}")
    elif opcoes.matricula and opcoes.nome:
        try:
            mostrar(eliminar_titular(opcoes.matricula, opcoes.nome, opcoes.banco,
                                     opcoes.apagar_encontradas))
        except ValueError as erro:
            argumentos.exit(1, f"Eliminação recusada: {erro}.\n")
    else:
        argumentos.error("informe a matrícula e o nome do titular, ou use --expurgar")
