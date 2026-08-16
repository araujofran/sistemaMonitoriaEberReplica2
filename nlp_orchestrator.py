import os
import json
import time
import re
import asyncio
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Optional
from mcp_client import LocalMCPClient

PROMPT_RULES_PATH = r"C:\Users\fabio\OneDrive\Área de Trabalho\Fran\eber\nlt\1-promptAnaliseAtendimentos.txt"

# ---------------------------------------------------------
# ESQUEMAS PYDANTIC PARA GARANTIR RETORNO DE JSON ESTRUTURADO
# ---------------------------------------------------------

class Cabecalho(BaseModel):
    data: str = Field(description="Data do atendimento formatada (ex: DD/MM/AAAA)")
    protocolo: str = Field(description="Identificador do protocolo")
    cliente: str = Field(description="Nome do cliente (usar 'Não identificado' se ausente)")
    cpf: str = Field(description="CPF mascarado (ex: 123.XXX.XXX-XX)")
    atendente: str = Field(description="Nome do atendente")
    produto: str = Field(description="Produto principal (ex: Cartão de Crédito)")
    categoria: str = Field(description="Categoria ou motivo principal do contato")
    canal: str = Field(description="Canal de atendimento (ex: Telefone, Chat)")

class VisaoGeral(BaseModel):
    status: str = Field(description="Status do caso (ex: '🟢 CASO CONTROLADO', '🟡 PONTO DE ATENÇÃO', '🟠 CASO RELEVANTE', '🔴 ALERTA CRÍTICO')")
    resumo: str = Field(description="Resumo executivo do caso contendo contexto, desenvolvimento, solução e desfecho")

class Feedback(BaseModel):
    positivos: List[str] = Field(description="Lista de pontos positivos identificados")
    melhorias: List[str] = Field(description="Lista de pontos de melhoria identificados")
    coaching: str = Field(description="Coaching sugerido para o operador")

class NotaMonitoria(BaseModel):
    relacionamento: float = Field(description="Nota obtida no pilar Relacionamento e Conduta (máximo 50)")
    resolutividade: float = Field(description="Nota obtida no pilar Resolutividade (máximo 10)")
    cx: float = Field(description="Nota obtida no pilar CX (máximo 40)")
    inaderencias: float = Field(description="Penalidade total das inaderências (ex: -100 ou 0)")
    pontos_extras: float = Field(description="Bônus total por pontos extras (ex: 1 ou 0)")

class ItemDetalhamento(BaseModel):
    codigo: str = Field(description="Código técnico do critério (ex: at_rel_cord1)")
    criterio: str = Field(description="Nome oficial do critério")
    peso: float = Field(description="Peso do critério")
    resultado: str = Field(description="Resultado obtido (ex: 'Sim', 'Não', 'Não Aplicável')")
    nota: float = Field(description="Nota obtida no critério")
    evidencia: str = Field(description="Evidência encontrada na transcrição (justificativa técnica)")

class Detalhamento(BaseModel):
    relacionamento: List[ItemDetalhamento] = Field(description="Itens do pilar Relacionamento e Conduta")
    resolutividade: List[ItemDetalhamento] = Field(description="Itens do pilar Resolutividade")
    cx: List[ItemDetalhamento] = Field(description="Itens do pilar CX")

class ItemInaderencia(BaseModel):
    codigo: str = Field(description="Código técnico da inaderência (ex: at_inad_compr1)")
    criterio: str = Field(description="Nome oficial da inaderência")
    resultado: str = Field(description="Resultado (ex: 'Sim', 'Não', 'Não Aplicável')")
    penalidade: float = Field(description="Penalidade aplicada (ex: -100 ou 0)")
    evidencia: str = Field(description="Evidência da inaderência ou conformidade")

class ItemPontoExtra(BaseModel):
    codigo: str = Field(description="Código do ponto extra (ex: inv_extra1)")
    criterio: str = Field(description="Nome oficial do ponto extra")
    resultado: str = Field(description="Resultado (ex: 'Sim', 'Não')")
    bonus: float = Field(description="Bônus aplicado (ex: 1 ou 0)")
    evidencia: str = Field(description="Evidência do bônus ou justificativa")

class CausaRaiz(BaseModel):
    motivo: str = Field(description="Motivo aparente")
    causa_identificada: str = Field(description="Causa identificada")
    causa_raiz: str = Field(description="Causa raiz técnica")
    dono_jornada: str = Field(description="Dono da jornada (ex: Canais Digitais, Operações, Tecnologia)")
    responsabilidade: str = Field(description="Responsabilidade (valores permitidos: Processo, Pessoa, Plataforma, Política, Não identificado, Não aplicado)")
    responsabilidade_motivo: str = Field(description="Justificativa da responsabilidade")
    evidencia: str = Field(description="Evidência na transcrição")

class Insights(BaseModel):
    insight_operacional: str = Field(description="Insight operacional gerado")
    apontamentos_cx: str = Field(description="Apontamentos de CX")
    apontamentos_resolutividade: str = Field(description="Apontamentos de resolutividade")
    oportunidades_operador: str = Field(description="Oportunidades do operador")

class FalhaOperacional(BaseModel):
    falha: str = Field(description="Descrição da falha operacional identificada")
    ocorrencias: int = Field(description="Número de ocorrências")
    evidencia: str = Field(description="Evidência na transcrição")

class Recomendacao(BaseModel):
    prioridade: str = Field(description="Prioridade (ex: Alta, Média, Baixa)")
    acao: str = Field(description="Ação sugerida")
    responsavel: str = Field(description="Área/pessoa responsável")
    prazo: str = Field(description="Prazo sugerido")
    impacto: str = Field(description="Impacto esperado")

class InteligenciaCX(BaseModel):
    score_experiencia: float = Field(description="Score Experiência (CES) calculado de acordo com as regras")
    esforco_cliente: str = Field(description="Esforço do cliente (ex: Baixo, Médio, Alto)")
    risco_reclamacao: str = Field(description="Risco/probabilidade de reclamação (ex: Baixo, Médio, Alto)")
    interpretacao: str = Field(description="Interpretação detalhada da experiência do cliente")
    friccao: str = Field(description="Nível de fricção (ex: Baixa, Média, Alta)")
    causa_raiz: CausaRaiz = Field(description="Estrutura de análise de causa raiz")
    insights: Insights = Field(description="Estrutura de insights gerados")
    falhas_operacionais: List[FalhaOperacional] = Field(description="Lista de falhas operacionais identificadas")
    recomendacoes: List[Recomendacao] = Field(description="Lista de recomendações e plano de ação")
    conclusao_executiva: str = Field(description="Conclusão executiva final")

class AuditoriaCXReport(BaseModel):
    cabecalho: Cabecalho
    score_operador: float = Field(description="Score final do operador calculado conforme as regras do motor de decisão (0 a 100)")
    classificacao_operador: str = Field(description="Classificação final do operador baseada na faixa de score")
    visao_geral: VisaoGeral
    feedback: Feedback
    nota_monitoria: NotaMonitoria
    detalhamento: Detalhamento
    inaderencias: List[ItemInaderencia]
    pontos_extras: List[ItemPontoExtra]
    inteligencia_cx: InteligenciaCX
    atendimento_resolutivo: str = Field(description="Se o atendimento foi resolutivo (valores: Sim, Não)")
    humor_cliente: str = Field(description="Humor do cliente (valores: Negativo, Neutro, Positivo)")
    humor_atendente: str = Field(description="Humor do atendente (valores: Negativo, Neutro, Positivo)")
    probabilidade_recontato: str = Field(description="Probabilidade de recontato (valores: Baixa, Média, Alta)")

# ---------------------------------------------------------
# CLASSE ORQUESTRADORA PRINCIPAL
# ---------------------------------------------------------

class NLPAuditOrchestrator:
    """
    Orquestrador que gerencia as chamadas NLP e interage com o Servidor MCP.
    Realiza a auditoria em duas etapas: Passo 1 (NLP local) e Passo 2 (Gemini LLM estruturado).
    """
    def __init__(self, use_real_llm=False, api_key=None, model_name="gemini-2.5-flash"):
        self.use_real_llm = use_real_llm
        self.api_key = api_key
        self.model_name = model_name
        self.prompt_rules = self._load_prompt_rules()

    def _load_prompt_rules(self) -> str:
        """Carrega o arquivo de prompt com as regras de auditoria."""
        if os.path.exists(PROMPT_RULES_PATH):
            try:
                with open(PROMPT_RULES_PATH, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                return f"Erro ao ler regras do prompt: {str(e)}"
        return "Instruções de monitoria não localizadas no caminho especificado."

    async def executar_auditoria(self, protocolo: str, texto_transcricao: str = None, log_callback=None) -> dict:
        """
        Fluxo unificado que executa o Passo 1 (NLP local) e em seguida o Passo 2 (LLM se configurado).
        """
        # Passo 1: NLP
        dados_nlp = await self.executar_passo1_nlp(protocolo, texto_transcricao, log_callback)
        
        # Passo 2: LLM (se ativo)
        if self.use_real_llm and self.api_key:
            try:
                dados_llm = await self.executar_passo2_llm(protocolo, log_callback)
                return dados_llm
            except Exception as e:
                if log_callback: log_callback(f"⚠️ Falha no Passo 2 (LLM): {str(e)}. Retornando resultados da etapa NLP local.")
                return dados_nlp
        else:
            if log_callback: log_callback("ℹ️ Modo Gemini LLM inativo ou chave ausente. Retornando análise NLP local.")
            return dados_nlp

    async def executar_passo1_nlp(self, protocolo: str, texto_transcricao: str = None, log_callback=None) -> dict:
        """
        Passo 1: Executa a análise local NLP (regras heurísticas) e salva no SQLite via MCP.
        """
        if log_callback: log_callback(f"🏁 [NLP] Iniciando Passo 1 (Regras Locais) para protocolo {protocolo}...")
        
        async with LocalMCPClient() as mcp:
            if texto_transcricao is None:
                if log_callback: log_callback(f"📂 [MCP Tool] Buscando transcrição para o protocolo {protocolo}...")
                texto_transcricao = await mcp.call_tool("buscar_transcricao", {"protocolo": protocolo})
            
            # Análise NLP
            dados_nlp = self.analisar_nlp_local(protocolo, texto_transcricao)
            nlp_json_str = json.dumps(dados_nlp, ensure_ascii=False)
            
            # Salva no banco SQLite via MCP
            if log_callback: log_callback(f"💾 [MCP Tool] Gravando análise NLP no banco...")
            retorno = await mcp.call_tool("salvar_nlp_db", {
                "protocolo": protocolo,
                "texto_transcricao": texto_transcricao,
                "nlp_json": nlp_json_str
            })
            if log_callback: log_callback(f"✔️ {retorno}")
            
            return dados_nlp

    async def executar_passo2_llm(self, protocolo: str, log_callback=None) -> dict:
        """
        Passo 2: Recupera o NLP do SQLite, chama o Gemini para auditar a transcrição e consolida.
        """
        if log_callback: log_callback(f"🧠 [LLM] Iniciando Passo 2 (Auditoria Avançada) para protocolo {protocolo}...")
        
        texto_transcricao = None
        nlp_json_str = None
        
        # Tenta obter via MCP Tool primeiro; se falhar o transporte, faz fallback direto para database.py
        try:
            async with LocalMCPClient() as mcp:
                if log_callback: log_callback(f"📂 [MCP Tool] Obtendo transcrição e NLP do banco...")
                registro_str = await mcp.call_tool("obter_registro_db", {"protocolo": protocolo})
                if registro_str and registro_str != "None":
                    registro = json.loads(registro_str)
                    if isinstance(registro, dict):
                        texto_transcricao = registro.get("texto_transcricao")
                        nlp_json_str = registro.get("nlp_json")
        except Exception as mcp_err:
            if log_callback: log_callback(f"ℹ️ [MCP] Notificação de transporte: {mcp_err}. Usando conexão direta SQLite...")
            
        if not texto_transcricao:
            import database
            registro = database.obter_registro_auditoria(protocolo)
            if registro:
                texto_transcricao = registro.get("texto_transcricao")
                nlp_json_str = registro.get("nlp_json")
                
        if not texto_transcricao:
            # Tenta buscar arquivo em transcricoes/
            trans_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transcricoes")
            possible_files = [
                os.path.join(trans_dir, f"protocolo_{protocolo}.txt"),
                os.path.join(trans_dir, f"{protocolo}.txt")
            ]
            for pf in possible_files:
                if os.path.exists(pf):
                    with open(pf, "r", encoding="utf-8", errors="ignore") as f:
                        texto_transcricao = f.read()
                    break
                    
        if not texto_transcricao:
            raise RuntimeError(f"Registro do protocolo {protocolo} não encontrado no banco ou sem transcrição.")
            
        if not nlp_json_str:
            dados_nlp_temp = self.analisar_nlp_local(protocolo, texto_transcricao)
            nlp_json_str = json.dumps(dados_nlp_temp, ensure_ascii=False)
            
        if log_callback: log_callback("🌐 Conectando à API do Google Gemini...")
        client = genai.Client(api_key=self.api_key)
        
        prompt_input = f"""
        Você deve realizar a auditoria da transcrição de atendimento abaixo, refinando a análise NLP preliminar gerada pelo sistema heurístico local.
        
        --- TRANSCRIÇÃO ---
        {texto_transcricao}
        --- FIM TRANSCRIÇÃO ---
        
        --- ANÁLISE NLP PRELIMINAR (PASSO 1) ---
        {nlp_json_str}
        --- FIM ANÁLISE NLP PRELIMINAR ---
        
        Realize todas as análises de acordo com as instruções de monitoria do sistema (system_instruction).
        Sua resposta final deve ser estritamente no formato JSON fornecido, preenchendo todos os critérios.
        """
        
        if log_callback: log_callback("🧠 Enviando dados estruturados para o Gemini...")
        
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()
            
        response = await loop.run_in_executor(
            None,
            lambda: client.models.generate_content(
                model=self.model_name,
                contents=prompt_input,
                config=types.GenerateContentConfig(
                    system_instruction=self.prompt_rules,
                    response_mime_type="application/json",
                    response_schema=AuditoriaCXReport,
                    temperature=0.1
                )
            )
        )
        
        llm_json_str = response.text
        if log_callback: log_callback("📥 Auditoria consolidada recebida. Decodificando...")
        
        dados_consolidado = json.loads(llm_json_str)
        
        # Tenta salvar via MCP, se falhar salva via database.py diretamente
        try:
            async with LocalMCPClient() as mcp:
                if log_callback: log_callback(f"💾 [MCP Tool] Gravando auditoria consolidada no banco...")
                await mcp.call_tool("salvar_llm_db", {
                    "protocolo": protocolo,
                    "llm_json": llm_json_str
                })
                await mcp.call_tool("salvar_auditoria", {
                    "protocolo": protocolo,
                    "dados_auditoria": llm_json_str
                })
        except Exception:
            if log_callback: log_callback(f"💾 Gravando auditoria via conexão direta SQLite...")
            import database
            database.salvar_auditoria_llm(protocolo, llm_json_str)
            
        if log_callback: log_callback(f"✅ Auditoria do protocolo {protocolo} gravada com sucesso!")
        dados_consolidado["_raw_llm_markdown"] = ""
        return dados_consolidado

    def analisar_nlp_local(self, protocolo: str, texto: str) -> dict:
        """Executa a análise NLP heurística local (Passo 1) sobre a transcrição."""
        atendente = "Não identificado"
        cliente = "Não identificado"
        cpf = "***.XXX.XXX-**"
        produto = "Não identificado"
        
        match_atendente = re.search(r"Atendente \((.*?)\):", texto)
        if match_atendente: atendente = match_atendente.group(1)
        
        match_cliente = re.search(r"Cliente \((.*?)\):", texto)
        if match_cliente: cliente = match_cliente.group(1)
        
        if "cartão" in texto.lower() or "limite" in texto.lower():
            produto = "Cartão de Crédito"
        elif "empréstimo" in texto.lower() or "consignado" in texto.lower():
            produto = "Empréstimo Consignado"
        elif "conta" in texto.lower():
            produto = "Conta Corrente"
            
        match_cpf = re.search(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b", texto)
        if match_cpf:
            cpf_raw = match_cpf.group(0)
            cpf = f"{cpf_raw[:3]}.XXX.XXX-{cpf_raw[-2:]}"
        else:
            match_cpf_digits = re.search(r"\b\d{11}\b", texto)
            if match_cpf_digits:
                cpf_raw = match_cpf_digits.group(0)
                cpf = f"{cpf_raw[:3]}.XXX.XXX-{cpf_raw[-2:]}"
                
        # Detecção de Atrito de Prazo e Desligamento
        tem_atrito_prazo = "prazo" in texto.lower() or "quantos dias" in texto.lower() or "quando" in texto.lower() or "limite" in texto.lower()
        tem_desligamento = "agradecemos o seu contato" in texto.lower() or "tenha uma excelente" in texto.lower()
        
        relacionamento_nota = 45.0 if tem_atrito_prazo else 50.0
        resolutividade_nota = 7.5 if tem_atrito_prazo else 10.0
        cx_nota = 33.0 if tem_atrito_prazo else 40.0
        
        score_operador = relacionamento_nota + resolutividade_nota + cx_nota
        
        inaderencias_penalidade = 0.0
        inad_list = []
        if tem_atrito_prazo:
            inad_list.append({
                "codigo": "at_inad_compr3",
                "criterio": "Falta de informação sobre prazo",
                "resultado": "Sim",
                "penalidade": -100.0,
                "evidencia": "Operador não informou prazos de estorno de forma clara."
            })
            inaderencias_penalidade -= 100.0
            
        if tem_desligamento and tem_atrito_prazo:
            inad_list.append({
                "codigo": "at_inad_compr5",
                "criterio": "Desligamento inadequado",
                "resultado": "Sim",
                "penalidade": -100.0,
                "evidencia": "Operador realizou o encerramento antes de tirar as dúvidas sobre prazos."
            })
            inaderencias_penalidade -= 100.0
            
        # Adiciona inaderências padrão como Não se não detectadas
        for cod, crit in [
            ("at_inad_compr1", "Direcionamento para pesquisa"),
            ("at_inad_compr2", "Omissão do protocolo"),
            ("at_inad_compr4", "Alteração de prazo"),
            ("at_inad_compr6", "Uso de linguagem inadequada"),
            ("at_inad_compr7", "Causar prejuízo")
        ]:
            if not any(i["codigo"] == cod for i in inad_list):
                inad_list.append({
                    "codigo": cod,
                    "criterio": crit,
                    "resultado": "Não",
                    "penalidade": 0.0,
                    "evidencia": "Nenhuma inaderência detectada."
                })
                
        pontos_extras = [{
            "codigo": "inv_extra1",
            "criterio": "Elogio espontâneo do cliente",
            "resultado": "Não",
            "bonus": 0.0,
            "evidencia": "Sem bônus aplicado."
        }]
        
        if inaderencias_penalidade < 0:
            score_operador = 0.0
            
        classificacao_operador = "Pode Melhorar Muito" if score_operador < 50 else ("Atende as expectativas" if score_operador < 85 else "Supera as expectativas")
        
        score_experiencia = 70.0 if tem_atrito_prazo else 95.0
        status_caso = "🟡 PONTO DE ATENÇÃO" if tem_atrito_prazo else "🟢 CASO CONTROLADO"
        esforco_cliente = "Médio" if tem_atrito_prazo else "Baixo"
        risco_reclamacao = "Médio" if tem_atrito_prazo else "Baixo"
        friccao = "Média" if tem_atrito_prazo else "Baixa"
        
        dados = {
            "cabecalho": {
                "data": "16/08/2026",
                "protocolo": protocolo,
                "cliente": cliente,
                "cpf": cpf,
                "atendente": atendente,
                "produto": produto,
                "categoria": "Contestação de Lançamento" if tem_atrito_prazo else "Dúvidas Gerais",
                "canal": "Chat"
            },
            "score_operador": score_operador,
            "classificacao_operador": classificacao_operador,
            "visao_geral": {
                "status": status_caso,
                "resumo": "Análise Heurística NLP local: Atrito de prazo identificado na transcrição." if tem_atrito_prazo else "Análise Heurística NLP local: Atendimento fluído e cordial."
            },
            "feedback": {
                "positivos": [
                    "Cordialidade mantida durante o diálogo (at_rel_cord1)",
                    "Uso correto das regras do português (at_rel_ling2)"
                ],
                "melhorias": [
                    "Fornecer prazos e alinhamento corretos com o cliente"
                ] if tem_atrito_prazo else [],
                "coaching": "Trabalhar no treinamento do operador a especificação de prazos nos encerramentos." if tem_atrito_prazo else "Manter excelência no atendimento."
            },
            "nota_monitoria": {
                "relacionamento": relacionamento_nota,
                "resolutividade": resolutividade_nota,
                "cx": cx_nota,
                "inaderencias": inaderencias_penalidade,
                "pontos_extras": 0.0
            },
            "detalhamento": {
                "relacionamento": [
                    {"codigo": "at_rel_cord1", "criterio": "Cortesia e tratamento respeitoso", "peso": 5.0, "resultado": "Sim", "nota": 5.0, "evidencia": "Tratou com respeito."},
                    {"codigo": "at_rel_ling2", "criterio": "Ausência de vícios de linguagem", "peso": 5.0, "resultado": "Sim", "nota": 5.0, "evidencia": "Linguagem adequada."},
                    {"codigo": "at_rel_cond4", "criterio": "Empatia e escuta ativa", "peso": 10.0, "resultado": "Sim", "nota": 10.0, "evidencia": "Escuta ativa demonstrada."}
                ],
                "resolutividade": [
                    {"codigo": "at_resol_solic1", "criterio": "Esclarecimento de dúvidas", "peso": 5.0, "resultado": "Sim", "nota": 5.0, "evidencia": "Confirmou duplicidade."},
                    {"codigo": "at_resol_solic2", "criterio": "Resolução do problema", "peso": 5.0, "resultado": "Parcial" if tem_atrito_prazo else "Sim", "nota": 2.5 if tem_atrito_prazo else 5.0, "evidencia": "Problema registrado."}
                ],
                "cx": [
                    {"codigo": "at_cx_intro1", "criterio": "Saudação institucional", "peso": 5.0, "resultado": "Sim", "nota": 5.0, "evidencia": "Saudação adequada."},
                    {"codigo": "at_cx_intro2", "criterio": "Confirmação de dados", "peso": 5.0, "resultado": "Sim", "nota": 5.0, "evidencia": "Dados validados."},
                    {"codigo": "at_cx_compr3", "criterio": "Alinhamento e entendimento", "peso": 10.0, "resultado": "Sim", "nota": 10.0, "evidencia": "Entendimento ok."},
                    {"codigo": "at_cx_classif2", "criterio": "Orientação de próximos passos e prazos", "peso": 10.0, "resultado": "Não" if tem_atrito_prazo else "Sim", "nota": 0.0 if tem_atrito_prazo else 10.0, "evidencia": "Sem prazos claros." if tem_atrito_prazo else "Orientação de prazos ok."}
                ]
            },
            "inaderencias": inad_list,
            "pontos_extras": pontos_extras,
            "inteligencia_cx": {
                "score_experiencia": score_experiencia,
                "esforco_cliente": esforco_cliente,
                "risco_reclamacao": risco_reclamacao,
                "interpretacao": "Análise de jornada local heurística efetuada.",
                "friccao": friccao,
                "causa_raiz": {
                    "motivo": "Contestação de Lançamento" if tem_atrito_prazo else "Dúvidas Gerais",
                    "causa_identificada": "Fricção na confirmação de estorno" if tem_atrito_prazo else "Consulta geral",
                    "causa_raiz": "Divergência sistêmica no app" if tem_atrito_prazo else "Sem falhas",
                    "dono_jornada": "Tecnologia" if tem_atrito_prazo else "Operações",
                    "responsabilidade": "Processo" if tem_atrito_prazo else "Não identificado",
                    "responsabilidade_motivo": "Processo de atualização do saldo",
                    "evidencia": "Cliente reportou lançamentos duplicados."
                },
                "insights": {
                    "insight_operacional": "Ajustar roteiro de prazos.",
                    "apontamentos_cx": "Esclarecer data limite.",
                    "apontamentos_resolutividade": "Acompanhar liquidação.",
                    "oportunidades_operador": "Reciclar conduta de prazos."
                },
                "falhas_operacionais": [
                    {"falha": "Omissão de prazos regulatórios/internos", "ocorrencias": 1 if tem_atrito_prazo else 0, "evidencia": "Omissão de prazo constatada."}
                ],
                "recomendacoes": [
                    {"prioridade": "Média", "acao": "Treinar equipe em prazos de estorno", "responsavel": "Treinamento", "prazo": "30 dias", "impacto": "Menor recontato"}
                ],
                "conclusao_executiva": "Auditoria inicial NLP finalizada."
            },
            "atendimento_resolutivo": "Não" if tem_atrito_prazo else "Sim",
            "humor_cliente": "Negativo" if tem_atrito_prazo else "Neutro",
            "humor_atendente": "Positivo",
            "probabilidade_recontato": "Alta" if tem_atrito_prazo else "Baixa"
        }
        return dados

# ---------------------------------------------------------
# FUNÇÃO UTILITÁRIA DE ACHATAMENTO DE DADOS (FLATTEN)
# ---------------------------------------------------------

def achatar_dados_auditoria(dados: dict) -> dict:
    """Converte o JSON hierárquico da auditoria em um dicionário plano (flat) para exportação em planilhas."""
    cab = dados.get("cabecalho", {})
    vg = dados.get("visao_geral", {})
    fb = dados.get("feedback", {})
    nm = dados.get("nota_monitoria", {})
    int_cx = dados.get("inteligencia_cx", {})
    causa = int_cx.get("causa_raiz", {})
    ins = int_cx.get("insights", {})
    
    # Extrai códigos de inaderências identificadas (onde resultado == 'Sim')
    inaderencias_ativas = [i["codigo"] for i in dados.get("inaderencias", []) if i.get("resultado") == "Sim"]
    inad_str = ", ".join(inaderencias_ativas) if inaderencias_ativas else "Nenhuma"
    
    # Extrai bônus ativos
    bonus_ativos = [b["codigo"] for b in dados.get("pontos_extras", []) if b.get("resultado") == "Sim"]
    bonus_str = ", ".join(bonus_ativos) if bonus_ativos else "Nenhum"

    flat = {
        "PROTOCOLO": cab.get("protocolo", ""),
        "DATA_AUDITORIA": cab.get("data", ""),
        "CLIENTE": cab.get("cliente", ""),
        "CPF": cab.get("cpf", ""),
        "ATENDENTE": cab.get("atendente", ""),
        "PRODUTO": cab.get("produto", ""),
        "CATEGORIA": cab.get("categoria", ""),
        "CANAL": cab.get("canal", ""),
        "STATUS_CASO": vg.get("status", ""),
        "RESUMO_EXECUTIVO": vg.get("resumo", ""),
        "SCORE_OPERADOR": dados.get("score_operador", 100.0),
        "CLASSIFICACAO_OPERADOR": dados.get("classificacao_operador", ""),
        "NOTA_RELACIONAMENTO": nm.get("relacionamento", 50.0),
        "NOTA_RESOLUTIVIDADE": nm.get("resolutividade", 10.0),
        "NOTA_CX": nm.get("cx", 40.0),
        "PENALIDADE_INADERENCIAS": nm.get("inaderencias", 0.0),
        "BONUS_PONTOS_EXTRAS": nm.get("pontos_extras", 0.0),
        "INADERENCIAS_CRITICAS": inad_str,
        "PONTOS_EXTRAS_APLICADOS": bonus_str,
        "COACHING_SUGERIDO": fb.get("coaching", ""),
        "SCORE_EXPERIENCIA_CES": int_cx.get("score_experiencia", 100.0),
        "ESFORCO_CLIENTE": int_cx.get("esforco_cliente", ""),
        "RISCO_RECLAMACAO": int_cx.get("risco_reclamacao", ""),
        "FRICCÃO_JORNADA": int_cx.get("friccao", ""),
        "CAUSA_RAIZ_MOTIVO": causa.get("motivo", ""),
        "CAUSA_RAIZ_IDENTIFICADA": causa.get("causa_identificada", ""),
        "CAUSA_RAIZ_TECNICA": causa.get("causa_raiz", ""),
        "CAUSA_RAIZ_DONO_JORNADA": causa.get("dono_jornada", ""),
        "CAUSA_RAIZ_RESPONSABILIDADE": causa.get("responsabilidade", ""),
        "CAUSA_RAIZ_JUSTIFICATIVA": causa.get("responsabilidade_motivo", ""),
        "CAUSA_RAIZ_EVIDENCIA": causa.get("evidencia", ""),
        "INSIGHT_OPERACIONAL": ins.get("insight_operacional", ""),
        "INSIGHT_CX": ins.get("apontamentos_cx", ""),
        "INSIGHT_RESOLUTIVIDADE": ins.get("apontamentos_resolutividade", ""),
        "OPORTUNIDADES_OPERADOR": ins.get("oportunidades_operador", ""),
        "ATENDIMENTO_RESOLUTIVO": dados.get("atendimento_resolutivo", ""),
        "HUMOR_CLIENTE": dados.get("humor_cliente", ""),
        "HUMOR_ATENDENTE": dados.get("humor_atendente", ""),
        "PROBABILIDADE_RECONTATO": dados.get("probabilidade_recontato", ""),
        "CONCLUSAO_EXECUTIVA": int_cx.get("conclusao_executiva", "")
    }
    return flat

# ---------------------------------------------------------
# RENDERIZADOR DE RELATÓRIO MARKDOWN (14 BLOCOS)
# ---------------------------------------------------------

def render_markdown_report(dados: dict) -> str:
    """
    Recebe o dicionário de auditoria e constrói o relatório visual 
    respeitando estritamente a ordem e formatação dos 14 blocos obrigatórios.
    """
    cab = dados.get("cabecalho", {})
    vg = dados.get("visao_geral", {})
    fb = dados.get("feedback", {})
    nm = dados.get("nota_monitoria", {})
    dt = dados.get("detalhamento", {})
    int_cx = dados.get("inteligencia_cx", {})
    causa = int_cx.get("causa_raiz", {})
    ins = int_cx.get("insights", {})
    falhas = int_cx.get("falhas_operacionais", [])
    recom = int_cx.get("recomendacoes", [])
    
    md = []
    
    # 1. CABEÇALHO DO ATENDIMENTO
    md.append("# MONITORIA DE QUALIDADE\n")
    md.append(f"| Data | Protocolo | Cliente | CPF | Atendente | Produto | Categoria | Canal |")
    md.append(f"|---|---|---|---|---|---|---|---|")
    md.append(f"| {cab.get('data', '-')} | {cab.get('protocolo', '-')} | {cab.get('cliente', '-')} | {cab.get('cpf', '-')} | {cab.get('atendente', '-')} | {cab.get('produto', '-')} | {cab.get('categoria', '-')} | {cab.get('canal', '-')} |\n")
    
    # 2. VISÃO GERAL DA MONITORIA (ou CLASSIFICAÇÃO EXECUTIVA)
    md.append("## 2. Classificação Executiva do Caso")
    md.append(f"**Status:** {vg.get('status', '🟡 PONTO DE ATENÇÃO')}\n")
    md.append(f"{vg.get('resumo', '')}\n")
    
    # 3. FEEDBACK DA MONITORIA
    md.append("## 3. Feedback da Monitoria")
    md.append("### ✅ Pontos Positivos")
    for p in fb.get("positivos", []):
        md.append(f"- {p}")
    if not fb.get("positivos"):
        md.append("- Nenhuma ocorrência identificada.")
        
    md.append("\n### ⚠️ Pontos de Melhoria")
    for m in fb.get("melhorias", []):
        md.append(f"- {m}")
    if not fb.get("melhorias"):
        md.append("- Nenhuma ocorrência identificada.")
        
    md.append("\n### 🎓 Coaching Sugerido")
    md.append(f"> {fb.get('coaching', 'Nenhuma recomendação de coaching cadastrada.')}\n")
    
    # 4. NOTA DA MONITORIA
    md.append("## 4. Nota da Monitoria")
    md.append("| Pilar | Peso máximo | Nota obtida | Status |")
    md.append("|---|---:|---:|---|")
    md.append(f"| Relacionamento e Conduta | 50 | {nm.get('relacionamento', 50)} | {'Conforme' if nm.get('relacionamento', 50) == 50 else 'Oportunidade'} |")
    md.append(f"| Resolutividade | 10 | {nm.get('resolutividade', 10)} | {'Conforme' if nm.get('resolutividade', 10) == 10 else 'Oportunidade'} |")
    md.append(f"| CX | 40 | {nm.get('cx', 40)} | {'Conforme' if nm.get('cx', 40) == 40 else 'Oportunidade'} |")
    md.append(f"| Inaderências | Zera atendimento | {nm.get('inaderencias', 0)} | {'Nenhuma inaderência' if nm.get('inaderencias', 0) == 0 else '🚨 Crítico'} |")
    md.append(f"| Pontos Extras | Bônus | {nm.get('pontos_extras', 0)} | {'Sem bônus' if nm.get('pontos_extras', 0) == 0 else '⭐ Bônus'} |")
    md.append(f"\n**NOTA FINAL: {dados.get('score_operador', 100)} / 100**")
    md.append(f"**Classificação do Operador: {dados.get('classificacao_operador', 'Supera as expectativas')}**\n")
    
    # 5. DETALHAMENTO DA MONITORIA
    md.append("## 5. Detalhamento da Monitoria")
    md.append("### 🤝 Relacionamento e Conduta")
    md.append("| Código | Critério | Peso | Resultado | Nota | Evidência |")
    md.append("|---|---|---:|---|---:|---|")
    for r in dt.get("relacionamento", []):
        md.append(f"| {r['codigo']} | {r['criterio']} | {r['peso']} | {r['resultado']} | {r['nota']} | {r['evidencia']} |")
        
    md.append("\n### 🎯 Resolutividade")
    md.append("| Código | Critério | Peso | Resultado | Nota | Evidência |")
    md.append("|---|---|---:|---|---:|---|")
    for r in dt.get("resolutividade", []):
        md.append(f"| {r['codigo']} | {r['criterio']} | {r['peso']} | {r['resultado']} | {r['nota']} | {r['evidencia']} |")
        
    md.append("\n### 💙 CX")
    md.append("| Código | Critério | Peso | Resultado | Nota | Evidência |")
    md.append("|---|---|---:|---|---:|---|")
    for r in dt.get("cx", []):
        md.append(f"| {r['codigo']} | {r['criterio']} | {r['peso']} | {r['resultado']} | {r['nota']} | {r['evidencia']} |")
    md.append("")
 
    # 6. INADERÊNCIAS
    md.append("## 6. Inaderências Críticas")
    res_inad = "✅ Nenhuma inaderência identificada" if nm.get('inaderencias', 0) == 0 else "🚨 Inaderência crítica identificada"
    md.append(f"**Resultado Geral:** {res_inad}\n")
    md.append("| Código | Critério | Resultado | Penalidade | Evidência |")
    md.append("|---|---|---|---:|---|")
    for i in dados.get("inaderencias", []):
        res_visual = "Conforme" if i["resultado"] == "Não" else ("Inaderência identificada" if i["resultado"] == "Sim" else i["resultado"])
        md.append(f"| {i['codigo']} | {i['criterio']} | {res_visual} | {i['penalidade']} | {i['evidencia']} |")
    md.append("")
    
    # DIVISÓRIA
    md.append("<h2 style='text-align: center; color: var(--accent-cyan) !important;'>──────── INTELIGÊNCIA DE CX E QUALIDADE ────────</h2>\n")
    
    # 7. DIAGNÓSTICO DA EXPERIÊNCIA
    md.append("## 7. Diagnóstico da Experiência")
    md.append("| Indicador | Resultado | Evidência ou Interpretação |")
    md.append("|---|---|---|")
    md.append(f"| Score Experiência | {int_cx.get('score_experiencia', 100)}/100 | {int_cx.get('interpretacao', '')} |")
    md.append(f"| Resolutividade | {dados.get('atendimento_resolutivo', 'Sim' if nm.get('resolutividade', 10) > 5 else 'Não')} | {causa.get('evidencia', '')} |")
    md.append(f"| Motivo do Contato | {causa.get('motivo', '')} | {vg.get('resumo', '')} |")
    md.append(f"| Humor do Cliente | {dados.get('humor_cliente', 'Neutro')} | {causa.get('evidencia', '')} |")
    md.append(f"| Humor do Atendente | {dados.get('humor_atendente', 'Positivo')} | {dt.get('relacionamento', [{}])[0].get('evidencia', '') if dt.get('relacionamento') else ''} |")
    md.append(f"| Esforço do Cliente | {int_cx.get('esforco_cliente', 'Baixo')} | {int_cx.get('interpretacao', '')} |")
    md.append(f"| Probabilidade Recontato | {dados.get('probabilidade_recontato', 'Baixa')} | {fb.get('coaching', '')} |")
    md.append(f"| Responsabilidade | {causa.get('responsabilidade', 'Não identificado')} | {causa.get('responsabilidade_motivo', '')} |\n")
    
    md.append("### Interpretação da Experiência")
    md.append(f"{int_cx.get('interpretacao', 'Atendimento adequado sem quebras de processo.')}\n")
 
    # 8. ESFORÇO E FRICÇÃO DA JORNADA
    md.append("## 8. Esforço e Fricção da Jornada")
    md.append("### CES — Customer Effort")
    md.append("| Código | Indicador | Resultado | Evidência |")
    md.append("|---|---|---|---|")
    md.append(f"| ces1_canal | Mudança de canal | Não | O cliente abriu o chamado via Chat direto. |")
    md.append(f"| ces2_retrabalho | Retrabalho | Não | Cliente não reportou reaberturas. |")
    md.append(f"| ces3_reduziu | Redução do esforço | Sim | Operador realizou a consulta imediatamente. |")
    
    md.append("\n### Fricção da Jornada")
    md.append(f"**Classificação de Fricção:** {int_cx.get('friccao', 'Baixa')} Fricção")
    md.append(f"- **Justificativa:** {int_cx.get('interpretacao', '')}\n")
    
    # 9. RISCOS E IMPACTOS
    md.append("## 9. Riscos e Impactos")
    md.append("| Risco | Resultado | Evidência | Possível consequência |")
    md.append("|---|---|---|---|")
    md.append(f"| Reclamação | {int_cx.get('risco_reclamacao', 'Baixo')} | Nenhuma menção a BACEN ou Ouvidoria. | Abertura de protocolo externo. |")
    md.append(f"| Cancelamento | Baixo | Cliente focado em resolver a duplicidade do lançamento. | Perda do cliente. |")
    md.append(f"| Contestação | Alto | Cliente solicita formalmente estorno. | Disputa de chargeback. |")
    md.append(f"| Ouvidoria | Baixo | Sem menção de reclamação na ouvidoria. | Custos internos de retrabalho. |")
    md.append(f"| Regulatório | Baixo | Sem risco regulatório identificado. | Risco BACEN. |\n")
    
    # 10. CAUSA RAIZ E RESPONSABILIDADE
    md.append("## 10. Causa Raiz e Responsabilidade")
    md.append("### Motivo aparente")
    md.append(f"- {causa.get('motivo', '')}")
    md.append("\n### Causa identificada")
    md.append(f"- {causa.get('causa_identificada', '')}")
    md.append("\n### Causa raiz")
    md.append(f"- {causa.get('causa_raiz', '')}")
    md.append("\n### Dono da Jornada")
    md.append(f"- {causa.get('dono_jornada', '')}")
    md.append("\n### Responsabilidade")
    md.append(f"- **{causa.get('responsabilidade', '')}** ({causa.get('responsabilidade_motivo', '')})")
    md.append("\n### Evidência")
    md.append(f"- {causa.get('evidencia', '')}\n")
    
    # 11. INSIGHTS DA INTERAÇÃO
    md.append("## 11. Insights da Interação")
    md.append(f"### 💡 Insight Operacional\n{ins.get('insight_operacional', '')}\n")
    md.append(f"### 💙 Apontamento de CX\n{ins.get('apontamentos_cx', '')}\n")
    md.append(f"### 🎯 Apontamento de Resolutividade\n{ins.get('apontamentos_resolutividade', '')}\n")
    md.append(f"### 👤 Oportunidade do Operador\n{ins.get('oportunidades_operador', '')}\n")
    
    # 12. FALHAS OPERACIONAIS IDENTIFICADAS
    md.append("## 12. Falhas Operacionais Identificadas")
    md.append("| Falha operacional | Ocorrências | Evidência |")
    md.append("|---|---:|---|")
    for f in falhas:
        md.append(f"| {f['falha']} | {f['ocorrencias']} | {f['evidencia']} |")
    if not falhas:
        md.append("| Nenhuma falha identificada | 0 | - |")
    md.append("")
    
    # 13. RECOMENDAÇÕES E PLANO DE AÇÃO
    md.append("## 13. Recomendações e Plano de Ação")
    md.append("| Prioridade | Ação | Responsável sugerido | Prazo sugerido | Impacto esperado |")
    md.append("|---|---|---|---|---|")
    for r in recom:
        md.append(f"| {r['prioridade']} | {r['acao']} | {r['responsavel']} | {r['prazo']} | {r['impacto']} |")
    if not recom:
        md.append("| Baixa | Monitorar recontatos do cliente | Supervisor | Curto prazo | Estabilidade |")
    md.append("")
    
    # 14. CONCLUSÃO EXECUTIVA
    md.append("## 14. Conclusão Executiva")
    md.append(f"{int_cx.get('conclusao_executiva', '')}")
    
    return "\n".join(md)
