import os
import json
import sys
from mcp.server.fastmcp import FastMCP
import database

# Inicializa o servidor MCP
mcp = FastMCP("CX-Audit-Server")

@mcp.tool()
def buscar_transcricao(protocolo: str) -> str:
    """
    Busca o conteúdo em texto (.txt) da transcrição do atendimento a partir do número do protocolo.
    
    Args:
        protocolo: O número ou identificador do protocolo (Ex: 12345).
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    transcricoes_dir = os.path.join(base_dir, "transcricoes")
    
    # Criar pasta caso não exista
    os.makedirs(transcricoes_dir, exist_ok=True)
    
    # Possíveis padrões de nome do arquivo
    nomes_possiveis = [
        f"protocolo_{protocolo}.txt",
        f"{protocolo}.txt",
        f"protocolo_{protocolo}",
        f"{protocolo}"
    ]
    
    for nome in nomes_possiveis:
        caminho = os.path.join(transcricoes_dir, nome)
        if os.path.exists(caminho) and os.path.isfile(caminho):
            try:
                with open(caminho, 'r', encoding='utf-8') as f:
                    return f.read()
            except UnicodeDecodeError:
                # Fallback para latin-1 se utf-8 falhar
                with open(caminho, 'r', encoding='latin-1') as f:
                    return f.read()
                
    raise FileNotFoundError(f"Transcrição para o protocolo '{protocolo}' não foi localizada na pasta '{transcricoes_dir}'.")

@mcp.tool()
def salvar_auditoria(protocolo: str, dados_auditoria: str) -> str:
    """
    Salva o JSON estruturado gerado pela auditoria no disco (pasta auditorias/).
    
    Args:
        protocolo: O número do protocolo do atendimento correspondente.
        dados_auditoria: Os dados JSON em formato string contendo o relatório estruturado da monitoria.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    auditorias_dir = os.path.join(base_dir, "auditorias")
    os.makedirs(auditorias_dir, exist_ok=True)
    
    caminho = os.path.join(auditorias_dir, f"protocolo_{protocolo}_auditoria.json")
    
    try:
        if isinstance(dados_auditoria, str):
            json_data = json.loads(dados_auditoria)
        else:
            json_data = dados_auditoria
    except Exception as e:
        return f"Erro: O conteúdo fornecido não é um JSON válido. Detalhes: {str(e)}"
        
    with open(caminho, 'w', encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)
        
    return f"Sucesso: Auditoria do protocolo {protocolo} salva em '{caminho}'."

@mcp.tool()
def salvar_nlp_db(protocolo: str, texto_transcricao: str, nlp_json: str) -> str:
    """
    Salva a transcrição e os resultados do primeiro processamento NLP local no banco SQLite.
    """
    try:
        database.salvar_transcricao_nlp(protocolo, texto_transcricao, nlp_json)
        return f"Sucesso: NLP do protocolo {protocolo} salvo no banco."
    except Exception as e:
        return f"Erro ao salvar NLP no banco: {str(e)}"

@mcp.tool()
def salvar_llm_db(protocolo: str, llm_json: str) -> str:
    """
    Salva os resultados consolidados do segundo processamento LLM no banco SQLite.
    """
    try:
        database.salvar_auditoria_llm(protocolo, llm_json)
        return f"Sucesso: LLM do protocolo {protocolo} salvo no banco."
    except Exception as e:
        return f"Erro ao salvar LLM no banco: {str(e)}"

@mcp.tool()
def obter_registro_db(protocolo: str) -> str:
    """
    Busca o registro completo de uma auditoria no banco SQLite e retorna em formato JSON string.
    """
    try:
        registro = database.obter_registro_auditoria(protocolo)
        if registro:
            return json.dumps(registro, ensure_ascii=False)
        return json.dumps({}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)}, ensure_ascii=False)

@mcp.tool()
def listar_todas_db() -> str:
    """
    Lista resumos de todas as auditorias salvas no banco SQLite em formato JSON string.
    """
    try:
        lista = database.listar_todas_auditorias()
        return json.dumps(lista, ensure_ascii=False)
    except Exception as e:
        return json.dumps([], ensure_ascii=False)

if __name__ == "__main__":
    # Inicia o servidor MCP em modo stdio (padrão de transporte da especificação)
    mcp.run()
