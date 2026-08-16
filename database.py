import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sistema_piloto.db")

def get_connection():
    """Retorna uma conexão com o banco de dados SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Inicializa as tabelas do banco de dados se não existirem."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS auditorias_cx (
        protocolo TEXT PRIMARY KEY,
        texto_transcricao TEXT,
        nlp_status TEXT DEFAULT 'pendente',
        nlp_json TEXT,
        llm_status TEXT DEFAULT 'pendente',
        llm_json TEXT,
        atendente TEXT,
        cliente TEXT,
        score_operador REAL,
        status_caso TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

def salvar_transcricao_nlp(protocolo: str, texto: str, nlp_json_str: str) -> None:
    """Insere ou atualiza o registro da transcrição com o resultado da análise NLP local."""
    init_db()
    
    # Extrai metadados básicos do JSON
    atendente = "-"
    cliente = "-"
    score_operador = 100.0
    status_caso = "🟢 CASO CONTROLADO"
    
    try:
        dados = json.loads(nlp_json_str)
        cab = dados.get("cabecalho", {})
        atendente = cab.get("atendente", atendente)
        cliente = cab.get("cliente", cliente)
        score_operador = dados.get("score_operador", score_operador)
        status_caso = dados.get("visao_geral", {}).get("status", status_caso)
    except Exception:
        pass
        
    conn = get_connection()
    cursor = conn.cursor()
    
    # Verifica se já existe
    cursor.execute("SELECT 1 FROM auditorias_cx WHERE protocolo = ?", (protocolo,))
    exists = cursor.fetchone()
    
    if exists:
        cursor.execute("""
        UPDATE auditorias_cx
        SET texto_transcricao = ?,
            nlp_status = 'concluido',
            nlp_json = ?,
            atendente = ?,
            cliente = ?,
            score_operador = ?,
            status_caso = ?
        WHERE protocolo = ?
        """, (texto, nlp_json_str, atendente, cliente, score_operador, status_caso, protocolo))
    else:
        cursor.execute("""
        INSERT INTO auditorias_cx (protocolo, texto_transcricao, nlp_status, nlp_json, atendente, cliente, score_operador, status_caso)
        VALUES (?, ?, 'concluido', ?, ?, ?, ?, ?)
        """, (protocolo, texto, nlp_json_str, atendente, cliente, score_operador, status_caso))
        
    conn.commit()
    conn.close()

def salvar_auditoria_llm(protocolo: str, llm_json_str: str) -> None:
    """Atualiza a auditoria com o resultado consolidado da LLM (Gemini)."""
    init_db()
    
    # Extrai metadados atualizados pela LLM
    atendente = None
    cliente = None
    score_operador = None
    status_caso = None
    
    try:
        dados = json.loads(llm_json_str)
        cab = dados.get("cabecalho", {})
        atendente = cab.get("atendente")
        cliente = cab.get("cliente")
        score_operador = dados.get("score_operador")
        status_caso = dados.get("visao_geral", {}).get("status")
    except Exception:
        pass

    conn = get_connection()
    cursor = conn.cursor()
    
    # Atualiza
    updates = ["llm_status = 'concluido'", "llm_json = ?"]
    params = [llm_json_str]
    
    if atendente:
        updates.append("atendente = ?")
        params.append(atendente)
    if cliente:
        updates.append("cliente = ?")
        params.append(cliente)
    if score_operador is not None:
        updates.append("score_operador = ?")
        params.append(score_operador)
    if status_caso:
        updates.append("status_caso = ?")
        params.append(status_caso)
        
    params.append(protocolo)
    query = f"UPDATE auditorias_cx SET {', '.join(updates)} WHERE protocolo = ?"
    
    cursor.execute(query, tuple(params))
    conn.commit()
    conn.close()

def obter_registro_auditoria(protocolo: str) -> dict:
    """Retorna um registro completo a partir do número do protocolo."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM auditorias_cx WHERE protocolo = ?", (protocolo,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None

def listar_todas_auditorias() -> list:
    """Retorna a lista resumida de todas as auditorias para listagem no painel."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT protocolo, atendente, cliente, score_operador, status_caso, nlp_status, llm_status, created_at 
    FROM auditorias_cx 
    ORDER BY created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(r) for r in rows]

def limpar_banco() -> None:
    """Limpa todos os registros do banco de dados (útil para resets/testes)."""
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM auditorias_cx")
    conn.commit()
    conn.close()

# Inicializa o banco de dados na importação
init_db()
