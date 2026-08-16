import streamlit as st
import os
import json
import asyncio
import time
import io
import pandas as pd
import database
from nlp_orchestrator import NLPAuditOrchestrator, render_markdown_report, achatar_dados_auditoria, call_gemini_with_rate_limit_retry
from google import genai
from google.genai import types

# ---------------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA E DESIGN SYSTEM (HALO DARK)
# ---------------------------------------------------------
st.set_page_config(page_title="Daycoval | Auditoria CX Inteligente", layout="wide")

def inject_custom_css():
    st.markdown("""
        <style>
        /* Importando tipografia similar ao Halo System */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

        /* Variáveis de cor da paleta Halo Dark */
        :root {
            --bg-base: #0A0B0F;
            --bg-surface: #14151C;
            --bg-surface2: #1E2029;
            --border-color: #2A2D38;
            --text-primary: #F2F4F8;
            --text-muted: #8B8D98;
            --accent-indigo: #5B68FF;
            --accent-success: #28E0B3;
            --accent-warning: #F5D547;
            --accent-danger: #FF3A5C;
            --accent-cyan: #3DD7E5;
        }

        /* Fundo geral da aplicação */
        .stApp {
            background-color: var(--bg-base);
            color: var(--text-primary);
            font-family: 'Inter', sans-serif;
        }

        /* Estilização dos Containers e Expander */
        div[data-testid="stMetric"], div.css-1r6slb0, div[data-testid="stExpander"] {
            background-color: var(--bg-surface) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 6px !important;
            padding: 18px !important;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2) !important;
        }
        
        /* Expander Header */
        .streamlit-expanderHeader {
            background-color: var(--bg-surface) !important;
            color: var(--text-primary) !important;
            font-family: 'Inter', sans-serif !important;
            font-weight: 500 !important;
        }

        /* Títulos */
        h1, h2, h3, h4, h5, h6 {
            color: var(--text-primary) !important;
            font-family: 'Inter', sans-serif;
            font-weight: 600;
        }

        /* Textos e Labels */
        p, li {
            color: var(--text-primary);
        }
        
        .text-muted {
            color: var(--text-muted) !important;
        }

        /* Garante legibilidade em inputs e áreas de texto */
        div[data-baseweb="input"] input, div[data-baseweb="textarea"] textarea, select {
            color: var(--text-primary) !important;
            background-color: var(--bg-surface2) !important;
            border: 1px solid var(--border-color) !important;
        }
        
        /* Nota da Monitoria Metric Value */
        div[data-testid="stMetricValue"] {
            color: var(--accent-indigo) !important;
            font-family: 'JetBrains Mono', monospace !important;
            font-weight: 700 !important;
            font-size: 2.2rem !important;
        }
        
        /* Delta Value */
        div[data-testid="stMetricDelta"] > div {
            color: var(--accent-cyan) !important;
        }

        /* Estilizando Tabelas */
        table {
            color: var(--text-primary) !important;
            background-color: var(--bg-surface) !important;
            border-collapse: collapse;
            width: 100%;
            margin: 10px 0;
            font-size: 0.9rem;
        }
        
        th {
            background-color: var(--bg-surface2) !important;
            color: var(--accent-cyan) !important;
            font-weight: 600;
            text-align: left;
            padding: 10px;
            border: 1px solid var(--border-color);
        }
        
        td {
            padding: 10px;
            border: 1px solid var(--border-color);
            background-color: var(--bg-surface);
        }
        
        tr:hover td {
            background-color: var(--bg-surface2) !important;
        }
        
        /* Botões */
        div.stButton > button {
            background-color: var(--accent-indigo) !important;
            color: #ffffff !important;
            border: 1px solid var(--accent-indigo) !important;
            border-radius: 4px;
            font-family: 'Inter', sans-serif;
            font-weight: 600;
            padding: 10px 24px;
            transition: all 0.2s ease;
        }
        div.stButton > button:hover {
            background-color: #4A56E2 !important;
            border-color: #4A56E2 !important;
            transform: translateY(-1px);
        }
        
        /* Custom Console para logs do MCP */
        .console-box {
            background-color: #0d0e12;
            border: 1px solid #1c1d24;
            border-radius: 6px;
            padding: 12px;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
            color: #3DD7E5;
            height: 180px;
            overflow-y: auto;
            margin-bottom: 20px;
        }
        
        .console-line {
            margin-bottom: 4px;
        }
        
        /* Alertas Customizados */
        .badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-weight: 600;
            font-size: 0.75rem;
            text-transform: uppercase;
        }
        .badge-controlled { background-color: rgba(40, 224, 179, 0.15); color: var(--accent-success); border: 1px solid var(--accent-success); }
        .badge-attention { background-color: rgba(245, 213, 71, 0.15); color: var(--accent-warning); border: 1px solid var(--accent-warning); }
        .badge-relevant { background-color: rgba(255, 120, 0, 0.15); color: #FF7800; border: 1px solid #FF7800; }
        .badge-critical { background-color: rgba(255, 58, 92, 0.15); color: var(--accent-danger); border: 1px solid var(--accent-danger); }
        
        </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------
# 2. FRONTEND - UTILS E CHAVE GEMINI
# ---------------------------------------------------------
def load_gemini_key():
    caminho = r"C:\Users\fabio\OneDrive\Área de Trabalho\Fran\eber\sistemaPiloto\chaveGemini\gemini_fabio.txt"
    if os.path.exists(caminho):
        try:
            with open(caminho, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except Exception:
            pass
    return None

def renderizar_dashboard_14_blocos(dados, protocolo_id):
    """Renderiza a visualização do painel de 14 blocos na tela."""
    # Tabs de visualização
    tab_relatorio, tab_markdown, tab_json = st.tabs([
        "📊 Relatório Visual (14 Blocos)", 
        "📄 Relatório Markdown Bruto", 
        "💾 JSON de Integração"
    ])
    
    with tab_relatorio:
        # BLOCO 1: CABEÇALHO DO ATENDIMENTO E NOTA
        st.subheader("1. Cabeçalho do Atendimento")
        col_cab1, col_cab2 = st.columns([3, 1])
        
        with col_cab1:
            cab = dados.get("cabecalho", {})
            st.markdown(f"""
            <table>
                <tr>
                    <th>Data</th><th>Protocolo</th><th>Cliente</th><th>CPF</th>
                </tr>
                <tr>
                    <td>{cab.get('data', '-')}</td>
                    <td>{cab.get('protocolo', '-')}</td>
                    <td>{cab.get('cliente', '-')}</td>
                    <td>{cab.get('cpf', '-')}</td>
                </tr>
                <tr>
                    <th>Atendente</th><th>Produto</th><th>Categoria</th><th>Canal</th>
                </tr>
                <tr>
                    <td>{cab.get('atendente', '-')}</td>
                    <td>{cab.get('produto', '-')}</td>
                    <td>{cab.get('categoria', '-')}</td>
                    <td>{cab.get('canal', '-')}</td>
                </tr>
            </table>
            """, unsafe_allow_html=True)
        
        with col_cab2:
            st.metric(
                label="NOTA FINAL DA MONITORIA",
                value=f"{dados.get('score_operador', 100)}/100",
                delta=dados.get('classificacao_operador', 'Supera as expectativas'),
                delta_color="normal"
            )

        # BLOCO 2: CLASSIFICAÇÃO EXECUTIVA
        st.markdown("---")
        st.subheader("2. Classificação Executiva do Caso")
        vg = dados.get("visao_geral", {})
        status = vg.get("status", "🟡 PONTO DE ATENÇÃO")
        
        if "CONTROLADO" in status:
            badge_class = "badge-controlled"
        elif "ATENÇÃO" in status:
            badge_class = "badge-attention"
        elif "RELEVANTE" in status:
            badge_class = "badge-relevant"
        else:
            badge_class = "badge-critical"
            
        st.markdown(f"<span class='badge {badge_class}'>{status}</span>", unsafe_allow_html=True)
        st.write("")
        st.info(vg.get("resumo", ""))

        # BLOCO 3: FEEDBACK DA MONITORIA
        st.subheader("3. Feedback da Monitoria")
        tab_pos, tab_melh, tab_coach = st.tabs(["✅ Pontos Positivos", "⚠️ Pontos de Melhoria", "🎓 Coaching Sugerido"])
        fb = dados.get("feedback", {})
        
        with tab_pos:
            for p in fb.get("positivos", []):
                st.markdown(f"- {p}")
            if not fb.get("positivos"):
                st.caption("Nenhuma ocorrência identificada.")
                
        with tab_melh:
            for m in fb.get("melhorias", []):
                st.markdown(f"- {m}")
            if not fb.get("melhorias"):
                st.caption("Nenhuma ocorrência identificada.")
                
        with tab_coach:
            st.success(fb.get("coaching", "Sem coaching sugerido."))

        # BLOCO 4: NOTA DA MONITORIA
        st.subheader("4. Tabela de Notas por Pilar")
        nm = dados.get("nota_monitoria", {})
        st.markdown(f"""
        <table>
            <tr>
                <th>Pilar</th><th>Peso Máximo</th><th>Nota Obtida</th><th>Status</th>
            </tr>
            <tr>
                <td>Relacionamento e Conduta</td><td>50</td><td>{nm.get('relacionamento', 50)}</td><td>{"Conforme" if nm.get('relacionamento', 50) == 50 else "Oportunidade"}</td>
            </tr>
            <tr>
                <td>Resolutividade</td><td>10</td><td>{nm.get('resolutividade', 10)}</td><td>{"Conforme" if nm.get('resolutividade', 10) == 10 else "Oportunidade"}</td>
            </tr>
            <tr>
                <td>CX</td><td>40</td><td>{nm.get('cx', 40)}</td><td>{"Conforme" if nm.get('cx', 40) == 40 else "Oportunidade"}</td>
            </tr>
            <tr>
                <td>Inaderências</td><td>Zera Atendimento</td><td>{nm.get('inaderencias', 0)}</td><td>{"Nenhuma inaderência" if nm.get('inaderencias', 0) == 0 else "🚨 Crítico"}</td>
            </tr>
            <tr>
                <td>Pontos Extras</td><td>Bônus</td><td>{nm.get('pontos_extras', 0)}</td><td>{"Sem bônus" if nm.get('pontos_extras', 0) == 0 else "⭐ Bônus"}</td>
            </tr>
        </table>
        """, unsafe_allow_html=True)

        # BLOCO 5: DETALHAMENTO DA MONITORIA
        st.subheader("5. Detalhamento da Monitoria")
        dt = dados.get("detalhamento", {})
        
        with st.expander("🤝 Relacionamento e Conduta"):
            st.markdown("<table><tr><th>Código</th><th>Critério</th><th>Peso</th><th>Resultado</th><th>Nota</th><th>Evidência</th></tr>", unsafe_allow_html=True)
            for r in dt.get("relacionamento", []):
                st.markdown(f"<tr><td>{r['codigo']}</td><td>{r['criterio']}</td><td>{r['peso']}</td><td>{r['resultado']}</td><td>{r['nota']}</td><td>{r['evidencia']}</td></tr>", unsafe_allow_html=True)
            st.markdown("</table>", unsafe_allow_html=True)
            
        with st.expander("🎯 Resolutividade"):
            st.markdown("<table><tr><th>Código</th><th>Critério</th><th>Peso</th><th>Resultado</th><th>Nota</th><th>Evidência</th></tr>", unsafe_allow_html=True)
            for r in dt.get("resolutividade", []):
                st.markdown(f"<tr><td>{r['codigo']}</td><td>{r['criterio']}</td><td>{r['peso']}</td><td>{r['resultado']}</td><td>{r['nota']}</td><td>{r['evidencia']}</td></tr>", unsafe_allow_html=True)
            st.markdown("</table>", unsafe_allow_html=True)
            
        with st.expander("💙 CX"):
            st.markdown("<table><tr><th>Código</th><th>Critério</th><th>Peso</th><th>Resultado</th><th>Nota</th><th>Evidência</th></tr>", unsafe_allow_html=True)
            for r in dt.get("cx", []):
                st.markdown(f"<tr><td>{r['codigo']}</td><td>{r['criterio']}</td><td>{r['peso']}</td><td>{r['resultado']}</td><td>{r['nota']}</td><td>{r['evidencia']}</td></tr>", unsafe_allow_html=True)
            st.markdown("</table>", unsafe_allow_html=True)

        # BLOCO 6: INADERÊNCIAS
        st.subheader("6. Inaderências Críticas")
        inad = dados.get("inaderencias", [])
        st.markdown("<table><tr><th>Código</th><th>Critério</th><th>Resultado</th><th>Penalidade</th><th>Evidência</th></tr>", unsafe_allow_html=True)
        for i in inad:
            res_visual = "Conforme" if i["resultado"] == "Não" else ("Inaderência identificada" if i["resultado"] == "Sim" else i["resultado"])
            st.markdown(f"<tr><td>{i['codigo']}</td><td>{i['criterio']}</td><td>{res_visual}</td><td>{i['penalidade']}</td><td>{i['evidencia']}</td></tr>", unsafe_allow_html=True)
        st.markdown("</table>", unsafe_allow_html=True)

        # DIVISÓRIA: INTELIGÊNCIA DE CX
        st.markdown("<h2 style='text-align: center; color: var(--accent-cyan) !important; margin: 40px 0 20px 0;'>──────── INTELIGÊNCIA DE CX E QUALIDADE ────────</h2>", unsafe_allow_html=True)
        int_cx = dados.get("inteligencia_cx", {})
        
        # BLOCO 7: DIAGNÓSTICO DA EXPERIÊNCIA
        st.subheader("7. Diagnóstico da Experiência")
        col_cx1, col_cx2, col_cx3 = st.columns(3)
        with col_cx1:
            st.metric("Score Experiência (CES)", f"{int_cx.get('score_experiencia', 100)}/100")
        with col_cx2:
            st.metric("Esforço do Cliente", int_cx.get("esforco_cliente", "Baixo"))
        with col_cx3:
            st.metric("Fricção da Jornada", int_cx.get("friccao", "Baixa"))
        
        st.markdown("**Interpretação da Experiência:**")
        st.info(int_cx.get("interpretacao", ""))

        # BLOCO 8 & 9: ESFORÇO/FRICÇÃO E RISCOS/IMPACTOS
        col_cxa, col_cxb = st.columns([1, 1])
        
        with col_cxa:
            st.subheader("8. Indicadores CES de Jornada")
            st.markdown(f"""
            <table>
                <tr><th>Indicador</th><th>Resultado</th></tr>
                <tr><td>Mudança de Canal</td><td>Não</td></tr>
                <tr><td>Retrabalho/Reabertura</td><td>Não</td></tr>
                <tr><td>Redução de Esforço</td><td>{'Não' if int_cx.get('esforco_cliente') == 'Alto' else 'Sim'}</td></tr>
            </table>
            """, unsafe_allow_html=True)
            
        with col_cxb:
            st.subheader("9. Riscos e Impactos")
            st.markdown(f"""
            <table>
                <tr><th>Risco</th><th>Probabilidade</th><th>Consequência</th></tr>
                <tr><td>Reclamação</td><td>{int_cx.get('risco_reclamacao', 'Baixo')}</td><td>Abertura no Procon/Bacen</td></tr>
                <tr><td>Cancelamento</td><td>Baixa</td><td>Churn/Perda de Receita</td></tr>
                <tr><td>Contestação</td><td>{"Alta" if "Contestação" in cab.get("categoria", "") else "Baixa"}</td><td>Custos operacionais adicionais</td></tr>
            </table>
            """, unsafe_allow_html=True)

        # BLOCO 10: CAUSA RAIZ E RESPONSABILIDADE
        st.subheader("10. Causa Raiz e Responsabilidade")
        causa = int_cx.get("causa_raiz", {})
        st.markdown(f"""
        * **Motivo Aparente:** {causa.get('motivo', '-')}
        * **Causa Identificada:** {causa.get('causa_identificada', '-')}
        * **Causa Raiz Técnica:** {causa.get('causa_raiz', '-')}
        * **Dono da Jornada:** {causa.get('dono_jornada', '-')}
        * **Responsabilidade:** {causa.get('responsabilidade', '-')}
        * **Justificativa de Responsabilidade:** {causa.get('responsabilidade_motivo', '-')}
        """)
        st.error(f"**Evidência Científica:** {causa.get('evidencia', '-')}")

        # BLOCO 11: INSIGHTS DA INTERAÇÃO
        st.subheader("11. Insights da Interação")
        ins = int_cx.get("insights", {})
        col_in1, col_in2 = st.columns(2)
        with col_in1:
            st.markdown(f"**💡 Insight Operacional:**\n{ins.get('insight_operacional', '-')}")
            st.markdown(f"**💙 Apontamento de CX:**\n{ins.get('apontamentos_cx', '-')}")
        with col_in2:
            st.markdown(f"**🎯 Apontamento de Resolutividade:**\n{ins.get('apontamentos_resolutividade', '-')}")
            st.markdown(f"**👤 Oportunidade do Operador:**\n{ins.get('oportunidades_operador', '-')}")

        # BLOCO 12: FALHAS OPERACIONAIS
        st.subheader("12. Falhas Operacionais Identificadas")
        falhas = int_cx.get("falhas_operacionais", [])
        st.markdown("<table><tr><th>Falha Operacional</th><th>Ocorrências</th><th>Evidência</th></tr>", unsafe_allow_html=True)
        for f in falhas:
            st.markdown(f"<tr><td>{f['falha']}</td><td>{f['ocorrencias']}</td><td>{f['evidencia']}</td></tr>", unsafe_allow_html=True)
        if not falhas:
            st.markdown("<tr><td>Nenhuma falha operacional identificada</td><td>0</td><td>-</td></tr>", unsafe_allow_html=True)
        st.markdown("</table>", unsafe_allow_html=True)

        # BLOCO 13: RECOMENDAÇÕES E PLANO DE AÇÃO
        st.subheader("13. Recomendações e Plano de Ação")
        recom = int_cx.get("recomendacoes", [])
        st.markdown("<table><tr><th>Prioridade</th><th>Ação Sugerida</th><th>Responsável</th><th>Prazo</th><th>Impacto Esperado</th></tr>", unsafe_allow_html=True)
        for r in recom:
            st.markdown(f"<tr><td>{r['prioridade']}</td><td>{r['acao']}</td><td>{r['responsavel']}</td><td>{r['prazo']}</td><td>{r['impacto']}</td></tr>", unsafe_allow_html=True)
        if not recom:
            st.markdown("<tr><td colspan='5'>Sem recomendações pendentes.</td></tr>", unsafe_allow_html=True)
        st.markdown("</table>", unsafe_allow_html=True)

        # BLOCO 14: CONCLUSÃO EXECUTIVA
        st.subheader("14. Conclusão Executiva")
        st.info(int_cx.get("conclusao_executiva", "-"))
        
    with tab_markdown:
        st.subheader("Relatório Completo em Formato Markdown")
        relatorio_md = render_markdown_report(dados)
        st.text_area("Markdown gerado pelas regras do prompt:", relatorio_md, height=450)
        
    with tab_json:
        st.subheader("Payload JSON Estruturado (MCP Output)")
        st.json(dados)
        json_string = json.dumps(dados, ensure_ascii=False, indent=4)
        st.download_button(
            label="Baixar JSON da Auditoria",
            data=json_string,
            file_name=f"auditoria_{protocolo_id}.json",
            mime="application/json"
        )

# ---------------------------------------------------------
# 3. INTERFACE E ABAS PRINCIPAIS
# ---------------------------------------------------------
def main():
    inject_custom_css()

    # Sidebar de Configurações
    st.sidebar.image("https://logodownload.org/wp-content/uploads/2019/09/banco-daycoval-logo-1.png", width=200)
    st.sidebar.title("Configurações do Piloto")
    st.sidebar.markdown("---")
    
    default_key = load_gemini_key()
    default_mode_index = 1 if default_key else 0
    
    mode = st.sidebar.radio(
        "Modo de Operação NLP:",
        ["Simulado (Sem Chave API)", "Real (Gemini LLM)"],
        index=default_mode_index,
        help="O modo simulado roda as regras lógicas locais. O modo real conecta ao Gemini."
    )
    
    use_real = (mode == "Real (Gemini LLM)")
    api_key = None
    model_name = "gemini-2.5-flash"
    
    if use_real:
        if default_key:
            st.sidebar.info("🔑 Chave API carregada do arquivo local (`gemini_fabio.txt`).")
            api_key = st.sidebar.text_input(
                "Gemini API Key:",
                value=default_key,
                type="password"
            )
        else:
            api_key = st.sidebar.text_input("Gemini API Key:", type="password")
            
        model_name = st.sidebar.selectbox("Modelo Gemini:", ["gemini-2.5-flash", "gemini-2.5-pro"])
        
        if not api_key:
            st.sidebar.warning("⚠️ Forneça uma chave de API para rodar no modo Real.")
            
    st.sidebar.markdown("---")
    st.sidebar.caption("📁 Database local: `sistema_piloto.db`")
    st.sidebar.caption("📁 Pasta Ingestão: `/transcricoes`")
    st.sidebar.caption("📁 Pasta Auditoria: `/auditorias`")

    # Título Principal
    st.title("Halo. | Auditoria de CX e Qualidade")
    st.markdown("Plataforma de Auditoria de Transcrições do Banco Daycoval operando via **MCP**.")

    tab_ingestao, tab_painel, tab_chat = st.tabs([
        "📂 Ingestão & Processamento (Passo 1)",
        "📊 Painel de Auditorias (Passo 2)",
        "💬 Chat Conversacional com a Base"
    ])

    # ---------------------------------------------------------
    # ABA 1: INGESTÃO E PROCESSAMENTO
    # ---------------------------------------------------------
    with tab_ingestao:
        st.subheader("Ingestão de Arquivos e Planilhas")
        uploaded_file = st.file_uploader(
            "Carregue arquivos de transcrição (.txt) ou planilhas (.csv, .xls, .xlsx) para iniciar o Passo 1 (NLP)", 
            type=["txt", "csv", "xls", "xlsx"]
        )

        if uploaded_file is not None:
            filename = uploaded_file.name
            
            # Se for TXT (Fluxo Original)
            if filename.endswith(".txt"):
                st.info(f"Arquivo de texto `{filename}` carregado.")
                
                # Salva o arquivo na pasta de transcrições
                trans_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transcricoes")
                os.makedirs(trans_dir, exist_ok=True)
                caminho_salvar = os.path.join(trans_dir, filename)
                
                with open(caminho_salvar, "wb") as f:
                    f.write(uploaded_file.getbuffer())
                
                protocolo_id = filename.replace("protocolo_", "").replace(".txt", "")
                
                # Visualiza prévia
                with st.expander("📝 Visualizar Transcrição"):
                    st.code(uploaded_file.getvalue().decode("utf-8", errors="ignore"), language="text")
                
                if st.button("Executar Passo 1 (NLP Local)"):
                    log_box = st.empty()
                    logs = []
                    def log_cb(msg):
                        logs.append(f"[{len(logs)+1}] {msg}")
                        log_html = "".join([f"<div class='console-line'>{l}</div>" for l in logs])
                        log_box.markdown(f"<div class='console-box'>{log_html}</div>", unsafe_allow_html=True)
                    
                    try:
                        orchestrator = NLPAuditOrchestrator(use_real_llm=use_real, api_key=api_key, model_name=model_name)
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        dados_nlp = loop.run_until_complete(
                            orchestrator.executar_passo1_nlp(protocolo_id, uploaded_file.getvalue().decode("utf-8", errors="ignore"), log_cb)
                        )
                        loop.close()
                        st.success(f"✅ Passo 1 (NLP) concluído para o protocolo {protocolo_id}! Salvo no Banco de Dados.")
                    except Exception as e:
                        st.error(f"Erro no processamento: {str(e)}")

            # Se for Planilha
            else:
                st.info(f"Planilha `{filename}` carregada.")
                
                # Lê DataFrame
                try:
                    if filename.endswith(".csv"):
                        df = pd.read_csv(uploaded_file)
                    else:
                        df = pd.read_excel(uploaded_file)
                        
                    st.write(f"Linhas carregadas: **{len(df)}**")
                    st.dataframe(df.head(5))
                    
                    # Coluna de Transcrição
                    transcricao_col = next((c for c in df.columns if "transcricao" in c.lower()), None)
                    if not transcricao_col:
                        transcricao_col = st.selectbox("Selecione a coluna que contém as transcrições:", df.columns)
                    else:
                        st.success(f"Coluna de transcrição identificada automaticamente: `{transcricao_col}`")
                        
                    # Botão para Processar Lote
                    if st.button("Processar Lote de Transcrições (Passo 1 - NLP)"):
                        progress_bar = st.progress(0)
                        status_text = st.empty()
                        
                        orchestrator = NLPAuditOrchestrator(use_real_llm=use_real, api_key=api_key, model_name=model_name)
                        
                        flat_results = []
                        total_rows = len(df)
                        
                        for idx, row in df.iterrows():
                            texto_trans = str(row.get(transcricao_col, "")).strip()
                            # Tenta achar protocolo
                            proto_val = str(row.get("PROTOCOLO", row.get("protocolo", f"LOTE_{int(time.time())}_{idx}"))).strip()
                            
                            status_text.write(f"⏳ Processando {idx+1}/{total_rows}: Protocolo {proto_val}...")
                            progress_bar.progress((idx + 1) / total_rows)
                            
                            if not texto_trans or texto_trans == "nan":
                                flat_results.append({})
                                continue
                                
                            try:
                                # Roda o NLP de forma síncrona
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                dados_nlp = loop.run_until_complete(
                                    orchestrator.executar_passo1_nlp(proto_val, texto_transcricao=texto_trans)
                                )
                                loop.close()
                                
                                # Roda também o LLM de forma sequencial se estiver no modo real ativo
                                if use_real and api_key:
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    dados_consolidado = loop.run_until_complete(
                                        orchestrator.executar_passo2_llm(proto_val)
                                    )
                                    loop.close()
                                    flat_data = achatar_dados_auditoria(dados_consolidado)
                                    time.sleep(3) # Pausa estratégica para respeitar limite de 15 RPM
                                else:
                                    flat_data = achatar_dados_auditoria(dados_nlp)
                                    
                                flat_results.append(flat_data)
                            except Exception as e:
                                flat_results.append({"ERRO_AUDITORIA": str(e)})
                                
                        status_text.success("✅ Processamento em lote finalizado!")
                        
                        # Concatena e Enriquece
                        df_res = pd.DataFrame(flat_results)
                        df_enriquecido = pd.concat([df, df_res], axis=1)
                        
                        st.subheader("📊 Métricas Consolidadas do Lote")
                        col_m1, col_m2, col_m3 = st.columns(3)
                        with col_m1:
                            st.metric("Total de Transcrições", len(df_enriquecido))
                        with col_m2:
                            avg_score = df_enriquecido["SCORE_OPERADOR"].mean() if "SCORE_OPERADOR" in df_enriquecido.columns else 100.0
                            st.metric("Score Médio do Operador", f"{avg_score:.2f}/100")
                        with col_m3:
                            top_causa = df_enriquecido["CAUSA_RAIZ_TECNICA"].mode().iloc[0] if "CAUSA_RAIZ_TECNICA" in df_enriquecido.columns and not df_enriquecido["CAUSA_RAIZ_TECNICA"].empty else "-"
                            st.metric("Top Causa Raiz Técnica", top_causa)
                            
                        # Download da planilha
                        output = io.BytesIO()
                        with pd.ExcelWriter(output, engine='openpyxl') as writer:
                            df_enriquecido.to_excel(writer, index=False, sheet_name='Auditorias CX')
                        processed_data = output.getvalue()
                        
                        st.download_button(
                            label="📥 Baixar Planilha Enriquecida (Excel)",
                            data=processed_data,
                            file_name=f"auditorias_cx_enriquecida_{int(time.time())}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                except Exception as e:
                    st.error(f"Erro ao carregar a planilha: {str(e)}")

    # ---------------------------------------------------------
    # ABA 2: PAINEL DE AUDITORIAS (VISUAL E HISTÓRICO)
    # ---------------------------------------------------------
    with tab_painel:
        st.subheader("Auditorias Gravadas no Banco SQLite")
        
        # Carrega lista do banco
        lista_auditorias = database.listar_todas_auditorias()
        
        if lista_auditorias:
            df_banco = pd.DataFrame(lista_auditorias)
            
            # Formata colunas para exibição na tabela
            st.dataframe(
                df_banco[["protocolo", "atendente", "cliente", "score_operador", "status_caso", "nlp_status", "llm_status", "created_at"]],
                use_container_width=True
            )
            
            # Ações de lote na base
            col_lote1, col_lote2 = st.columns([1, 1])
            with col_lote1:
                if st.button("🔄 Rodar Auditoria Gemini (LLM) em Lote"):
                    pendentes = [a["protocolo"] for a in lista_auditorias if a["llm_status"] == "pendente"]
                    if not pendentes:
                        st.info("Nenhuma auditoria pendente de análise LLM.")
                    elif not use_real or not api_key:
                        st.warning("⚠️ Ative o modo Real (Gemini LLM) com chave válida para processar o lote.")
                    else:
                        progress_lote = st.progress(0)
                        status_lote = st.empty()
                        log_box_lote = st.empty()
                        logs_lote = []
                        
                        def log_cb_lote(msg):
                            logs_lote.append(f"[{len(logs_lote)+1}] {msg}")
                            log_html = "".join([f"<div class='console-line'>{l}</div>" for l in logs_lote])
                            log_box_lote.markdown(f"<div class='console-box'>{log_html}</div>", unsafe_allow_html=True)
                            
                        orchestrator = NLPAuditOrchestrator(use_real_llm=use_real, api_key=api_key, model_name=model_name)
                        sucessos = 0
                        erros = 0
                        
                        log_cb_lote(f"🚀 Iniciando auditoria LLM em Micro-lotes (agrupamento de 5) para {len(pendentes)} protocolos pendentes...")
                        
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            res_lote = loop.run_until_complete(
                                orchestrator.executar_passo2_llm_microbatch(pendentes, batch_size=5, log_callback=log_cb_lote)
                            )
                            loop.close()
                            status_lote.success(f"✅ Processamento LLM em micro-lotes concluído com sucesso! ({len(res_lote)} relatórios gerados)")
                        except Exception as e:
                            log_cb_lote(f"❌ Erro no lote: {str(e)}")
                            status_lote.error(f"Erro no lote: {str(e)}")
                            
                        log_cb_lote(f"🎉 Finalizada auditoria em lote com Micro-batching & Key Pool!")
                        time.sleep(2)
                        st.rerun()
            
            with col_lote2:
                if st.button("🚨 Limpar Banco de Dados (Reset)"):
                    database.limpar_banco()
                    st.success("Banco de dados resetado com sucesso!")
                    st.rerun()

            # Seleção de um protocolo para ver o Dashboard
            st.markdown("---")
            st.subheader("Visualizar Detalhamento da Auditoria")
            
            proto_selecionado = st.selectbox(
                "Selecione o protocolo para abrir o relatório de 14 blocos:",
                df_banco["protocolo"].tolist()
            )
            
            if proto_selecionado:
                reg = database.obter_registro_auditoria(proto_selecionado)
                
                # Se LLM pendente, oferece botão para rodar
                if reg.get("llm_status") == "pendente":
                    st.warning(f"O protocolo {proto_selecionado} foi analisado apenas por NLP heurístico (Passo 1).")
                    
                    if st.button("🚀 Executar Auditoria Gemini (Passo 2)"):
                        if not use_real or not api_key:
                            st.error("⚠️ Para rodar a auditoria do Gemini, ative o modo Real (Gemini LLM) e insira a chave de API.")
                        else:
                            log_box = st.empty()
                            logs = []
                            def log_cb(msg):
                                logs.append(f"[{len(logs)+1}] {msg}")
                                log_html = "".join([f"<div class='console-line'>{l}</div>" for l in logs])
                                log_box.markdown(f"<div class='console-box'>{log_html}</div>", unsafe_allow_html=True)
                            
                            try:
                                orchestrator = NLPAuditOrchestrator(use_real_llm=use_real, api_key=api_key, model_name=model_name)
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                dados_llm = loop.run_until_complete(orchestrator.executar_passo2_llm(proto_selecionado, log_cb))
                                loop.close()
                                st.success("✅ Auditoria do Gemini executada e consolidada no banco!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro na auditoria LLM: {str(e)}")
                                
                # Carrega o JSON correto (dá preferência para llm_json se disponível, se não usa nlp_json)
                dados_exibir_str = reg.get("llm_json") if reg.get("llm_json") else reg.get("nlp_json")
                if dados_exibir_str:
                    try:
                        dados_exibir = json.loads(dados_exibir_str)
                        st.markdown(f"### Exibindo Relatório do Protocolo {proto_selecionado} ({'Consolidado por LLM' if reg.get('llm_status') == 'concluido' else 'NLP Heurístico'})")
                        renderizar_dashboard_14_blocos(dados_exibir, proto_selecionado)
                    except Exception as e:
                        st.error(f"Erro ao carregar os dados salvos: {str(e)}")
        else:
            st.info("Nenhuma auditoria encontrada no banco SQLite. Processe uma transcrição ou planilha na aba anterior.")

    # ---------------------------------------------------------
    # ABA 3: CHAT CONVERSACIONAL COM A BASE
    # ---------------------------------------------------------
    with tab_chat:
        st.subheader("Chat Conversacional sobre a Base de Auditorias")
        st.markdown("Faça perguntas sobre os atendimentos auditados (ex: Notas médias, piores causas, resumos operacionais).")
        
        # Inicializa o histórico de mensagens
        if "chat_messages" not in st.session_state:
            st.session_state["chat_messages"] = []
            
        # Mostra as mensagens anteriores
        for msg in st.session_state["chat_messages"]:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
                
        # Recebe entrada
        user_input = st.chat_input("Pergunte algo sobre a base de auditoria...")
        
        if user_input:
            # Exibe mensagem do usuário
            with st.chat_message("user"):
                st.markdown(user_input)
            st.session_state["chat_messages"].append({"role": "user", "content": user_input})
            
            # Processa a resposta
            with st.chat_message("assistant"):
                with st.spinner("Analisando base de auditorias e gerando resposta..."):
                    # Carrega resumo das auditorias do banco
                    try:
                        audit_db = database.listar_todas_auditorias()
                        resumo_list = []
                        for a in audit_db:
                            resumo_list.append(
                                f"Protocolo: {a['protocolo']} | Atendente: {a['atendente']} | Cliente: {a['cliente']} | "
                                f"Score Operador: {a['score_operador']} | Status Caso: {a['status_caso']} | "
                                f"NLP Status: {a['nlp_status']} | LLM Status: {a['llm_status']}"
                            )
                        dados_resumo_tabela = "\n".join(resumo_list) if resumo_list else "Nenhuma auditoria registrada no banco."
                    except Exception as e:
                        dados_resumo_tabela = f"Erro ao acessar banco SQLite: {str(e)}"
                        
                    if use_real and api_key:
                        try:
                            prompt_system = f"""
                            Você é um assistente analítico de monitoria de CX do Banco Daycoval.
                            Seu objetivo é responder a perguntas do usuário com base nas auditorias registradas no banco de dados do sistema.
                            
                            Aqui está a lista consolidada das auditorias gravadas no banco de dados (resumo das principais colunas):
                            {dados_resumo_tabela}
                            
                            Instruções:
                            - Responda de forma clara, objetiva, profissional e em português.
                            - Se a pergunta for sobre um protocolo específico (ex: 12345), você pode detalhar as notas, inaderências e causa raiz se esses dados estiverem presentes.
                            - Se a pergunta pedir estatísticas (ex: média de notas, atendentes com problemas), faça as contas aproximadas com base na lista fornecida.
                            - Responda apenas sobre os dados presentes no banco de dados. Caso não tenha informações, informe gentilmente.
                            """
                            
                            # Chamada usando a interface nativa de Chat do SDK do Gemini (client.chats.create)
                            client = genai.Client(api_key=api_key)
                            
                            try:
                                chat = client.chats.create(
                                    model=model_name,
                                    config=types.GenerateContentConfig(
                                        system_instruction=prompt_system,
                                        temperature=0.3
                                    )
                                )
                                response = chat.send_message(user_input)
                                resposta_final = response.text
                            except Exception as chat_err:
                                err_str = str(chat_err)
                                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                                    # Fallback de modelo para gemini-flash-latest
                                    chat_fallback = client.chats.create(
                                        model="gemini-flash-latest",
                                        config=types.GenerateContentConfig(
                                            system_instruction=prompt_system,
                                            temperature=0.3
                                        )
                                    )
                                    response = chat_fallback.send_message(user_input)
                                    resposta_final = response.text
                                else:
                                    raise chat_err
                        except Exception as e:
                            err_msg = str(e)
                            if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "Quota exceeded" in err_msg:
                                resposta_final = "⚠️ **Limite de Cota do Gemini Atingido (HTTP 429)**\n\nA cota de requisições da chave do Gemini foi excedida temporariamente. O sistema aplicou a troca de modelo fallback, mas a cota gratuita do projeto foi atingida.\n\n*Dica: Você pode consultar as notas e estatísticas navegando diretamente na aba **Painel de Auditorias**.*"
                            else:
                                resposta_final = f"❌ Erro ao chamar o Gemini: {err_msg}"
                    else:
                        resposta_final = "⚠️ O chat conversacional inteligente requer o modo Real (Gemini LLM) ativo com a chave de API configurada."
                        
                    st.markdown(resposta_final)
                    st.session_state["chat_messages"].append({"role": "assistant", "content": resposta_final})

if __name__ == "__main__":
    main()
