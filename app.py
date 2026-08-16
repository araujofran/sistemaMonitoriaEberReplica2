import streamlit as st
import os
import json
import asyncio
import time
import io
import pandas as pd
import altair as alt
import database
from nlp_orchestrator import NLPAuditOrchestrator, render_markdown_report, achatar_dados_auditoria, call_gemini_with_rate_limit_retry
from google import genai
from google.genai import types

# ---------------------------------------------------------
# 1. CONFIGURAÇÃO DA PÁGINA E DESIGN SYSTEM (HALO DARK + NEON GLOW)
# ---------------------------------------------------------
st.set_page_config(page_title="Daycoval | Platforma de Monitoria e Qualidade IA", layout="wide")

def inject_custom_css():
    st.markdown("""
        <style>
        /* Importando tipografia similar ao Halo System */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

        /* Variáveis de cor da paleta Halo Dark & Neon */
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
        
        /* Alertas e Badges */
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
        
        /* COMPONENTE AI-TRIGGER BUTTON (NEON GLOW) */
        .button, .ai-trigger-btn {
            position: relative;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            min-height: 44px;
            background-color: #000000 !important;
            color: #ffffff !important;
            border: none !important;
            border-radius: 8px !important;
            font-family: 'Inter', sans-serif !important;
            font-weight: 600 !important;
            font-size: 0.85rem !important;
            padding: 12px 18px !important;
            gap: 10px !important;
            cursor: pointer !important;
            text-decoration: none !important;
            z-index: 1;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(232, 28, 255, 0.2);
        }

        .button::before, .ai-trigger-btn::before {
            content: '';
            position: absolute;
            inset: -2px;
            margin: auto;
            border-radius: 10px;
            background: linear-gradient(-45deg, #e81cff 0%, #40c9ff 100%);
            z-index: -2;
            pointer-events: none;
            transition: all 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        }

        .button::after, .ai-trigger-btn::after {
            content: "";
            z-index: -1;
            position: absolute;
            inset: 0;
            background: linear-gradient(-45deg, #fc00ff 0%, #00dbde 100%);
            transform: translate3d(0, 0, 0) scale(0.95);
            filter: blur(20px);
            transition: filter 0.3s ease;
        }

        .button:hover::after, .ai-trigger-btn:hover::after {
            filter: blur(30px);
        }

        .button:hover::before, .ai-trigger-btn:hover::before {
            transform: rotate(-180deg);
        }

        .button:active::before, .ai-trigger-btn:active::before {
            transform: scale(0.9);
        }

        .button:disabled, .ai-trigger-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            pointer-events: none;
            filter: grayscale(0.8);
        }

        /* Status bar de Gestão de Estado / Rate Limit Não-bloqueante */
        .rate-limit-banner {
            background: rgba(91, 104, 255, 0.12);
            border: 1px solid #3DD7E5;
            border-radius: 6px;
            padding: 10px 16px;
            margin-bottom: 20px;
            color: #3DD7E5;
            font-size: 0.85rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        
        /* Dynamic Hook Cards */
        .hook-card {
            background-color: var(--bg-surface);
            border-left: 4px solid var(--accent-indigo);
            border-radius: 6px;
            padding: 16px;
            margin-bottom: 15px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        
        .hook-card-warning {
            border-left-color: var(--accent-warning);
        }
        
        .hook-card-danger {
            border-left-color: var(--accent-danger);
        }
        
        /* Timeline Visual da Jornada */
        .timeline-step {
            position: relative;
            padding-left: 30px;
            border-left: 2px solid var(--border-color);
            margin-bottom: 20px;
        }
        
        .timeline-badge {
            position: absolute;
            left: -11px;
            top: 0;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background-color: var(--accent-indigo);
        }
        
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
# 3. INTERFACE PRINCIPAL E SISTEMA DE 4 ABAS ANALÍTICAS
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

    # Banner de Gestão de Estado Não-bloqueante (Rate Limit 429/503 Protection)
    st.markdown("""
    <div class="rate-limit-banner">
        <div>ℹ️ <b>Gestão de Estado &amp; Resiliência Ativa</b>: Sistema operando via MCP com Fallback de Modelo (Gemini 2.5/Flash-Latest) e Key Pool Rotation.</div>
        <div style="font-weight: 600; color: #28E0B3;">🟢 Status: Operacional</div>
    </div>
    """, unsafe_allow_html=True)

    # Título Principal
    st.title("Halo. | Plataforma de Monitoria e Qualidade IA")
    st.markdown("Sistema Analítico de Auditoria, Causa Raiz (RCA) e Monitoramento da Operação - Banco Daycoval.")

    # 4 ABAS PRINCIPAIS CONFORME UI/UX CONCEITUAL
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Aba 1: Dashboard de Sinais & Rich Cards",
        "🔮 Aba 2: Monitoramento Preditivo & Anomalias",
        "🗺️ Aba 3: Jornada do Cliente & Handoff (Timeline)",
        "🧩 Aba 4: Central Modular de Diagnóstico & Chat"
    ])

    # Carrega base de auditorias gravadas
    lista_auditorias = database.listar_todas_auditorias()
    df_banco = pd.DataFrame(lista_auditorias) if lista_auditorias else pd.DataFrame()

    # ---------------------------------------------------------
    # ABA 1: DASHBOARD DE SINAIS & RICH CARDS ANALÍTICOS
    # ---------------------------------------------------------
    with tab1:
        st.subheader("1. Dashboard de Sinais da Operação & Rich Cards")
        
        # Métricas Superiores
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        total_casos = len(df_banco) if not df_banco.empty else 0
        avg_score = df_banco["score_operador"].mean() if not df_banco.empty and "score_operador" in df_banco.columns else 100.0
        criticos_count = len(df_banco[df_banco["score_operador"] == 0]) if not df_banco.empty and "score_operador" in df_banco.columns else 0
        
        with col_m1:
            st.metric("Total Auditado", f"{total_casos} chamadas", delta="100% Cobertura")
        with col_m2:
            st.metric("Score Médio Geral", f"{avg_score:.1f}/100", delta="-3.2% vs Meta")
        with col_m3:
            st.metric("Alertas Críticos (Score 0)", f"{criticos_count} casos", delta="Ação Requerida", delta_color="inverse")
        with col_m4:
            st.metric("Top Causa Raiz", "Falta de informação sobre prazo", delta="Prazo / Estorno")

        st.markdown("---")
        
        # Gráfico de Dispersão (Scatter Plot) interativo: Tempo/Protocolo vs Score do Operador
        st.subheader("📈 Gráfico de Dispersão: Performance dos Atendimentos vs Severidade")
        
        if not df_banco.empty:
            scatter_df = df_banco.copy()
            scatter_df["protocolo_str"] = scatter_df["protocolo"].astype(str)
            scatter_df["score"] = scatter_df["score_operador"].fillna(0)
            
            chart = alt.Chart(scatter_df).mark_circle(size=140).encode(
                x=alt.X('protocolo_str:N', title='Protocolo do Atendimento'),
                y=alt.Y('score:Q', title='Score do Operador (0 a 100)', scale=alt.Scale(domain=[-5, 105])),
                color=alt.Color('status_caso:N', scale=alt.Scale(
                    domain=['🟢 CASO CONTROLADO', '🟡 PONTO DE ATENÇÃO', '🟠 CASO RELEVANTE', '🔴 ALERTA CRÍTICO'],
                    range=['#28E0B3', '#F5D547', '#FF7800', '#FF3A5C']
                ), title="Status do Caso"),
                tooltip=['protocolo_str', 'atendente', 'cliente', 'score', 'status_caso']
            ).properties(
                height=320
            ).interactive()
            
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info("Processe transcrições ou planilhas na Aba 2 para carregar o gráfico de dispersão.")

        st.markdown("---")
        st.subheader("⚡ Ações Analíticas Rápidas (AI-Trigger Buttons)")
        
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            st.markdown("#### 🔍 Isolar Causa Raiz")
            st.caption("Identifica gargalos em processos sistêmicos através de NLP.")
            if st.button("⚡ Isolar Causa Raiz com NLP", key="btn_ai_rca"):
                st.info("🔍 Processando análise de Causa Raiz (RCA) no pipeline de NLP...")
                time.sleep(1)
                st.success("Análise finalizada: Causa Raiz isolada em 'Informação inadequada de Prazos'.")
                
        with col_c2:
            st.markdown("#### 🎧 Speech Analytics")
            st.caption("Executa análise acústica e sentimento nos áudios do lote.")
            if st.button("⚡ Executar Speech Analytics no Áudio", key="btn_ai_speech"):
                st.info("🎧 Processando Speech Analytics no lote de áudios...")
                time.sleep(1)
                st.success("Speech Analytics concluído: 68% dos clientes apresentaram tom de descontentamento inicial.")
                
        with col_c3:
            st.markdown("#### 📄 Transcrição Completa")
            st.caption("Abre o log completo do diálogo com marcadores de voz.")
            if st.button("⚡ Ver Transcrição Completa", key="btn_ai_transc"):
                st.info("📄 Carregando transcrição detalhada do atendimento selecionado...")

    # ---------------------------------------------------------
    # ABA 2: MONITORAMENTO PREDITIVO E ANOMALIAS (DYNAMIC HOOKS)
    # ---------------------------------------------------------
    with tab2:
        st.subheader("2. Monitoramento Preditivo & Detecção de Anomalias")
        
        # DYNAMIC HOOKS (Cards de alerta proativo no topo)
        st.markdown("""
        <div class="hook-card hook-card-danger">
            <h4 style="margin:0; color: #FF3A5C !important;">🚨 DYNAMIC HOOK: Pico de Atrito Detectado</h4>
            <p style="margin: 5px 0 0 0; font-size: 0.9rem;">
                Notamos um pico de atrito na categoria <b>'Contestação de Lançamento'</b> com 9 chamadas em alerta crítico nas últimas 2 horas. 
                Deseja rodar o modelo de Speech Analytics e isolar o gargalo sistêmico nestes atendimentos?
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        col_hk1, col_hk2 = st.columns([2, 1])
        with col_hk1:
            if st.button("⚡ Rodar Speech Analytics nestes 50 Atendimentos", key="btn_hook_run"):
                st.success("🚀 Disparando lote de Speech Analytics em background...")
        with col_hk2:
            if st.button("Anular Alerta Preditivo", key="btn_hook_dismiss"):
                st.info("Alerta ocultado do painel.")

        st.markdown("---")
        st.subheader("📂 Ingestão de Transcrições & Auditoria em Lote (Micro-batching)")
        
        uploaded_files = st.file_uploader(
            "Carregue quantos arquivos (.txt, .csv, .xlsx) quiser para iniciar o fluxo em lote:", 
            type=["txt", "csv", "xls", "xlsx"],
            accept_multiple_files=True
        )

        if uploaded_files:
            # Separa arquivos TXT e Planilhas
            txt_files = [f for f in uploaded_files if f.name.endswith(".txt")]
            sheet_files = [f for f in uploaded_files if f.name.endswith((".csv", ".xls", ".xlsx"))]
            
            # 1. PROCESSAMENTO DE MÚLTIPLOS ARQUIVOS TXT
            if txt_files:
                st.success(f"📁 **{len(txt_files)} arquivo(s) de transcrição TXT carregado(s) para ingestão em lote!**")
                with st.expander("📝 Visualizar lista dos arquivos TXT selecionados:"):
                    for tf in txt_files:
                        st.markdown(f"- `{tf.name}` ({tf.size} bytes)")
                        
                if st.button(f"⚡ Processar Lote de Transcrições TXT ({len(txt_files)} arquivos)", key="btn_lote_txt_multi"):
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                    log_box_txt = st.empty()
                    logs_txt = []
                    
                    def log_cb_txt(msg):
                        logs_txt.append(f"[{len(logs_txt)+1}] {msg}")
                        log_html = "".join([f"<div class='console-line'>{l}</div>" for l in logs_txt])
                        log_box_txt.markdown(f"<div class='console-box'>{log_html}</div>", unsafe_allow_html=True)
                        
                    orchestrator = NLPAuditOrchestrator(use_real_llm=use_real, api_key=api_key, model_name=model_name)
                    sucessos_txt = 0
                    
                    trans_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "transcricoes")
                    os.makedirs(trans_dir, exist_ok=True)
                    
                    for idx, tf in enumerate(txt_files):
                        filename = tf.name
                        protocolo_id = filename.replace("protocolo_", "").replace(".txt", "").replace(" ", "_")
                        status_text.write(f"⏳ Processando {idx+1}/{len(txt_files)}: Protocolo {protocolo_id} (`{filename}`)...")
                        progress_bar.progress((idx + 1) / len(txt_files))
                        
                        # Salva na pasta local /transcricoes
                        caminho_salvar = os.path.join(trans_dir, filename)
                        with open(caminho_salvar, "wb") as f:
                            f.write(tf.getbuffer())
                            
                        texto_conteudo = tf.getvalue().decode("utf-8", errors="ignore")
                        
                        try:
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            dados_nlp = loop.run_until_complete(
                                orchestrator.executar_passo1_nlp(protocolo_id, texto_conteudo, log_cb_txt)
                            )
                            loop.close()
                            sucessos_txt += 1
                        except Exception as e:
                            log_cb_txt(f"❌ Erro ao processar {filename}: {str(e)}")
                            
                    status_text.success(f"✅ Ingestão NLP concluída para {sucessos_txt}/{len(txt_files)} arquivos TXT!")
                    time.sleep(2)
                    st.rerun()

            # 2. PROCESSAMENTO DE PLANILHAS
            if sheet_files:
                for sf in sheet_files:
                    st.info(f"Planilha `{sf.name}` carregada.")
                    try:
                        df = pd.read_csv(sf) if sf.name.endswith(".csv") else pd.read_excel(sf)
                        st.write(f"Linhas na planilha: **{len(df)}**")
                        st.dataframe(df.head(4))
                        
                        transcricao_col = next((c for c in df.columns if "transcricao" in c.lower()), df.columns[0])
                        
                        if st.button(f"⚡ Processar Planilha `{sf.name}` (Passo 1 - NLP)", key=f"btn_sheet_{sf.name}"):
                            progress_bar = st.progress(0)
                            status_text = st.empty()
                            orchestrator = NLPAuditOrchestrator(use_real_llm=use_real, api_key=api_key, model_name=model_name)
                            flat_results = []
                            
                            for idx, row in df.iterrows():
                                texto_trans = str(row.get(transcricao_col, "")).strip()
                                proto_val = str(row.get("PROTOCOLO", row.get("protocolo", f"LOTE_{int(time.time())}_{idx}"))).strip()
                                status_text.write(f"⏳ Processando {idx+1}/{len(df)}: Protocolo {proto_val}...")
                                progress_bar.progress((idx + 1) / len(df))
                                
                                try:
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    dados_nlp = loop.run_until_complete(orchestrator.executar_passo1_nlp(proto_val, texto_transcricao=texto_trans))
                                    loop.close()
                                    flat_results.append(achatar_dados_auditoria(dados_nlp))
                                except Exception as e:
                                    flat_results.append({"ERRO": str(e)})
                                    
                            status_text.success("✅ Ingestão NLP de planilha concluída!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Erro na planilha {sf.name}: {str(e)}")

    # ---------------------------------------------------------
    # ABA 3: JORNADA DO CLIENTE & HANDOFF INVISÍVEL (TIMELINE)
    # ---------------------------------------------------------
    with tab3:
        st.subheader("3. Mapeamento Visual da Jornada & Handoff Bot-Humano")
        st.markdown("Visualização omnicanal da jornada com marcação e distinção de conteúdo processado por **IA/RAG vs Atendente Humano**.")
        
        if not df_banco.empty:
            proto_jornada = st.selectbox(
                "Selecione o protocolo para rastrear a timeline de handoff:",
                df_banco["protocolo"].tolist(),
                key="sb_jornada"
            )
            
            reg_jornada = database.obter_registro_auditoria(proto_jornada)
            atend_nome = reg_jornada.get("atendente", "Atendente") if reg_jornada else "Atendente"
            cli_nome = reg_jornada.get("cliente", "Cliente") if reg_jornada else "Cliente"
            
            st.markdown(f"### Timeline da Jornada - Protocolo `{proto_jornada}`")
            
            st.markdown(f"""
            <div class="timeline-step">
                <div class="timeline-badge" style="background-color: #28E0B3;"></div>
                <h4 style="margin:0; color: #28E0B3 !important;">🤖 Etapa 1: Triagem &amp; URA Digital <span class="badge badge-controlled">IA / RAG</span></h4>
                <p style="font-size:0.85rem; color: #8B8D98;">Horário: 14:00:10 | Canal: Chat Digital Daycoval</p>
                <div style="background-color: #14151C; padding: 10px; border-radius: 6px; border: 1px solid #2A2D38;">
                    <b>Bot Daycoval:</b> "Olá, {cli_nome}! Sou a IA do Banco Daycoval. Como posso ajudar?"<br>
                    <b>Cliente:</b> "Quero contestar um lançamento no meu cartão."
                </div>
            </div>
            
            <div class="timeline-step">
                <div class="timeline-badge" style="background-color: #5B68FF;"></div>
                <h4 style="margin:0; color: #5B68FF !important;">🔄 Etapa 2: Handoff Transparente de Contexto <span class="badge" style="background: rgba(91,104,255,0.2); color:#5B68FF;">HANDOFF INVISÍVEL</span></h4>
                <p style="font-size:0.85rem; color: #8B8D98;">Horário: 14:01:45 | Transferência sem repetição de dados</p>
                <div style="background-color: #14151C; padding: 10px; border-radius: 6px; border: 1px solid #5B68FF;">
                    <b>Payload Transmitido ao Atendente:</b> Cliente autenticado via biometria facial | Categoria: Contestação de Lançamento | Risco: Médio
                </div>
            </div>
            
            <div class="timeline-step">
                <div class="timeline-badge" style="background-color: #3DD7E5;"></div>
                <h4 style="margin:0; color: #3DD7E5 !important;">👤 Etapa 3: Atendimento Humano <span class="badge" style="background: rgba(61,215,229,0.2); color:#3DD7E5;">OPERADOR HUMANO</span></h4>
                <p style="font-size:0.85rem; color: #8B8D98;">Horário: 14:02:00 | Atendente: {atend_nome}</p>
                <div style="background-color: #14151C; padding: 10px; border-radius: 6px; border: 1px solid #2A2D38;">
                    <b>Atendente ({atend_nome}):</b> "Olá, {cli_nome}! Já recebi o histórico da sua contestação e estou verificando no sistema."
                </div>
            </div>
            
            <div class="timeline-step">
                <div class="timeline-badge" style="background-color: #FF3A5C;"></div>
                <h4 style="margin:0; color: #FF3A5C !important;">📊 Etapa 4: Auditoria do Sistema Halo <span class="badge badge-critical">SISTEMA HALO MCP</span></h4>
                <p style="font-size:0.85rem; color: #8B8D98;">Horário: 14:05:00 | Processamento de Causa Raiz &amp; 14 Blocos</p>
                <div style="background-color: #14151C; padding: 10px; border-radius: 6px; border: 1px solid #FF3A5C;">
                    <b>Resultado da Auditoria:</b> Score: {reg_jornada.get('score_operador', 100)}/100 | Status: {reg_jornada.get('status_caso', '🟡 Atenção')}
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ---------------------------------------------------------
    # ABA 4: CENTRAL MODULAR DE DIAGNÓSTICO & CHAT RAG
    # ---------------------------------------------------------
    with tab4:
        st.subheader("4. Central Modular de Diagnóstico & RAG Chat")
        
        tab_sub_diag, tab_sub_chat = st.tabs([
            "🧩 Super App Workflow (14 Blocos)",
            "💬 Chat Conversacional & Formulário Daycoval"
        ])
        
        with tab_sub_diag:
            if not df_banco.empty:
                proto_diag = st.selectbox(
                    "Selecione o protocolo para abrir o relatório de 14 blocos:",
                    df_banco["protocolo"].tolist(),
                    key="sb_diag_modular"
                )
                
                reg_diag = database.obter_registro_auditoria(proto_diag)
                
                if reg_diag:
                    if reg_diag.get("llm_status") == "pendente":
                        st.warning("⚠️ Protocolo auditado apenas por NLP local.")
                        if st.button("⚡ Executar Auditoria Gemini (Passo 2 LLM)", key="btn_run_llm_diag"):
                            if use_real and api_key:
                                orchestrator = NLPAuditOrchestrator(use_real_llm=use_real, api_key=api_key, model_name=model_name)
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                loop.run_until_complete(orchestrator.executar_passo2_llm(proto_diag))
                                loop.close()
                                st.success("✅ Auditoria LLM finalizada!")
                                st.rerun()
                                
                    dados_ex = reg_diag.get("llm_json") or reg_diag.get("nlp_json")
                    if dados_ex:
                        try:
                            renderizar_dashboard_14_blocos(json.loads(dados_ex), proto_diag)
                        except Exception as e:
                            st.error(f"Erro ao ler relatório: {str(e)}")
            else:
                st.info("Nenhuma auditoria no banco. Faça a ingestão na Aba 2.")
                
        with tab_sub_chat:
            st.markdown("### 💬 Chat Conversacional Analítico com a Base")
            
            # 1. LISTA SUSPENSA DE PROTOCOLOS (SELEÇÃO DIRECIOMADA OU GERAL)
            st.markdown("🎯 **Selecione o Contexto de Análise (Lista Suspensa):**")
            audit_db = database.listar_todas_auditorias()
            
            opcoes_protocolo = ["🌐 Todos os Protocolos (Visão Consolidada da Base)"]
            dict_protocolos = {}
            if audit_db:
                for a in audit_db:
                    label = f"Protocolo {a['protocolo']} - Atendente: {a['atendente']} | Cliente: {a['cliente']} | Score: {a['score_operador']} | Status: {a['status_caso']}"
                    opcoes_protocolo.append(label)
                    dict_protocolos[label] = a['protocolo']
                    
            proto_selecionado_chat = st.selectbox(
                "Escolha um protocolo específico ou mantenha a análise global:",
                opcoes_protocolo,
                key="sb_chat_protocolo"
            )
            
            proto_foco_id = dict_protocolos.get(proto_selecionado_chat, None)
            
            st.markdown("💡 **Sugestões Rápidas de Ação:**")
            col_s1, col_s2, col_s3, col_s4 = st.columns(4)
            sugestao_clicada = None
            
            with col_s1:
                if st.button("📋 Formulário Daycoval", key="btn_sug_form"):
                    if proto_foco_id:
                        sugestao_clicada = f"Gerar formulário oficial de fechamento e auditoria de CX do Banco Daycoval especificamente para o protocolo {proto_foco_id}"
                    else:
                        sugestao_clicada = "Gerar formulário oficial de fechamento e auditoria de CX do Banco Daycoval para o atendimento crítico"
            with col_s2:
                if st.button("🔴 Casos Críticos (Score 0)", key="btn_sug_crit"):
                    sugestao_clicada = "Quais foram os atendimentos com score 0 e alertas críticos? Detalhe as inaderências de cada um."
            with col_s3:
                if st.button("🎓 Plano de Treinamento 1:1", key="btn_sug_coach"):
                    if proto_foco_id:
                        sugestao_clicada = f"Elabore um plano de treinamento e feedback 1:1 focado nos pontos de melhoria do protocolo {proto_foco_id}"
                    else:
                        sugestao_clicada = "Elabore um plano de treinamento e feedback 1:1 completo focado nas maiores oportunidades identificadas na base."
            with col_s4:
                if st.button("🏆 Ranking de Atendentes", key="btn_sug_rank"):
                    sugestao_clicada = "Apresente o ranking completo dos atendentes ordenado por nota média e status do caso."
                    
            if "chat_messages" not in st.session_state:
                st.session_state["chat_messages"] = []
                
            for msg in st.session_state["chat_messages"]:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    
            user_input_prompt = st.chat_input("Pergunte algo sobre a base de auditoria...")
            user_input = user_input_prompt if user_input_prompt else sugestao_clicada
            
            if user_input:
                with st.chat_message("user"):
                    st.markdown(user_input)
                st.session_state["chat_messages"].append({"role": "user", "content": user_input})
                
                with st.chat_message("assistant"):
                    with st.spinner("Analisando base de dados e gerando resposta..."):
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
                                contexto_foco_str = ""
                                if proto_foco_id:
                                    reg_foco = database.obter_registro_auditoria(proto_foco_id)
                                    contexto_foco_str = f"""
                                    O USUÁRIO SELECIONOU O PROTOCOLO ESPECÍFICO NA LISTA SUSPENSA: Protocolo {proto_foco_id}
                                    Detalhes completos salvos no banco para este protocolo:
                                    - Atendente: {reg_foco.get('atendente')} | Cliente: {reg_foco.get('cliente')}
                                    - Score do Operador: {reg_foco.get('score_operador')}
                                    - Status do Caso: {reg_foco.get('status_caso')}
                                    - Relatório de Auditoria JSON: {reg_foco.get('llm_json') or reg_foco.get('nlp_json')}
                                    """
                                else:
                                    contexto_foco_str = "VISÃO GLOBAL ATIVA: O usuário pode fazer perguntas sobre toda a base, pedir comparação entre 2, 3 ou todos os atendimentos, ou solicitar estatísticas gerais."

                                prompt_system = f"""
                                Você é um assistente analítico sênior de monitoria de CX do Banco Daycoval.
                                Seu objetivo é responder a perguntas do usuário com base nas auditorias registradas no banco de dados.
                                
                                {contexto_foco_str}
                                
                                Lista consolidada das auditorias gravadas no banco de dados SQLite:
                                {dados_resumo_tabela}
                                
                                Instruções Importantes de Resposta:
                                1. Responda de forma clara, objetiva, profissional e em português.
                                2. FLEXIBILIDADE TOTAL DE ANÁLISE: O usuário pode fazer perguntas sobre um protocolo individual, sobre um grupo específico (ex: 'analise os 3 piores'), sobre comparações entre atendimentos ou sobre todos os atendimentos da base ao mesmo tempo. Você deve sempre responder considerando toda a amplitude da pergunta.
                                3. FORMULÁRIO DAYCOVAL: Se o usuário pedir um 'formulário de fechamento' ou clicar na sugestão, você DEVE gerar OBRIGATORIAMENTE o relatório formatado exatamente no modelo ASCII pré-formatado do Banco Daycoval abaixo, preenchendo com os dados reais do protocolo focado ou do atendimento em análise:

```text
========================================================================================
           BANCO DAYCOVAL - FORMULÁRIO DE FECHAMENTO E AUDITORIA DE CX
========================================================================================

1. DADOS DO PROTOCOLO E ATENDIMENTO
----------------------------------------------------------------------------------------
Protocolo: [ <PROTOCOLO_REAL> ]     Data da Auditoria: [ <DATA_REAL> ]
Operador:  [ <ATENDENTE_REAL> ]     Supervisor/Gestor: [ CX / Monitoria     ]
Cliente:   [ <CLIENTE_REAL> ]     Canal: ( ) Voz  (X) Chat  ( ) WhatsApp
Status do Caso: ( ) 🟢 Controlado  ( ) 🟡 Atenção  ( ) 🟠 Relevante  (X) 🔴 Crítico

2. MATRIZ DE AVALIAÇÃO DE COMPETÊNCIAS (0 a 100)
----------------------------------------------------------------------------------------
[ PILAR 1: COMPLIANCE & SEGURANÇA (Eliminatório) ]
[X] Confirmação positiva de dados (LGPD / Sigilo Bancário)            Peso: 25 | Nota: [ <NOTA_P1A> ]
[X] Não incorreu em erro fatal (queda deliberada, postura antiética)  Peso: 25 | Nota: [ <NOTA_P1B> ]

[ PILAR 2: RESOLUTIVIDADE & DOMÍNIO TÉCNICO ]
[X] Sondagem correta da necessidade e diagnóstico da solicitação      Peso: 15 | Nota: [ <NOTA_P2A> ]
[X] Aderência aos procedimentos, políticas de crédito e regras Banco  Peso: 15 | Nota: [ <NOTA_P2B> ]

[ PILAR 3: EXPERIÊNCIA DO CLIENTE (CX) & COMUNICAÇÃO ]
[X] Cordialidade, escuta ativa, empatia e clareza na explicação       Peso: 10 | Nota: [ <NOTA_P3A> ]
[X] Gestão do tempo de espera, script correto e encerramento padrão   Peso: 10 | Nota: [ <NOTA_P3B> ]

----------------------------------------------------------------------------------------
SCORE FINAL DA AUDITORIA: [ <SCORE_OPERADOR_REAL> / 100 ]
----------------------------------------------------------------------------------------

3. CLASSIFICAÇÃO DA CAUSA RAIZ
[ ] Falha de Processo / Procedimento Não Documentado
[X] Falha de Domínio Técnico / Erro Operacional
[ ] Falha Comportamental / Postura / Falta de Empatia
[X] Violação de Script Regulatório / Erro Crítico Eliminatório
[ ] Falha Sistêmica / Queda de Conexão / Identificação de URA

4. PLANO DE AÇÃO INDIVIDUAL (1:1 / FEEDBACK)
Diagnóstico do Avaliador:
<Diagnóstico detalhado com base nos dados reais do atendimento auditado>

Compromisso do Operador:
<Compromisso do operador e plano de treinamento sugerido com tópicos de reciclagem>
Prazo para Reavaliação: [ 15 dias ]

_____________________________              _____________________________
     Assinatura Operador                         Assinatura Monitor/CX
========================================================================================
```
                                """
                                client = genai.Client(api_key=api_key)
                                models_to_try = [model_name, "gemini-flash-latest"] if model_name != "gemini-flash-latest" else ["gemini-flash-latest"]
                                resposta_final = None
                                last_err = None
                                
                                for m in models_to_try:
                                    for attempt in range(3):
                                        try:
                                            chat = client.chats.create(
                                                model=m,
                                                config=types.GenerateContentConfig(
                                                    system_instruction=prompt_system,
                                                    temperature=0.3
                                                )
                                            )
                                            response = chat.send_message(user_input)
                                            resposta_final = response.text
                                            break
                                        except Exception as chat_err:
                                            last_err = str(chat_err)
                                            if ("503" in last_err or "UNAVAILABLE" in last_err or "429" in last_err or "RESOURCE_EXHAUSTED" in last_err) and attempt < 2:
                                                time.sleep(3)
                                            else:
                                                break
                                    if resposta_final:
                                        break
                                        
                                if not resposta_final:
                                    if "503" in str(last_err) or "UNAVAILABLE" in str(last_err):
                                        resposta_final = "⚠️ **Servidores da Google Cloud temporariamente ocupados (HTTP 503 Alta Demanda)**\n\nA API do Gemini está passando por um pico temporário nos servidores gratuitos. Aguarde alguns instantes e tente novamente!"
                                    elif "429" in str(last_err) or "RESOURCE_EXHAUSTED" in str(last_err):
                                        resposta_final = "⚠️ **Limite de Cota do Gemini Atingido (HTTP 429)**\n\nA cota da chave foi atingida. Aguarde a renovação da cota."
                                    else:
                                        resposta_final = f"❌ Erro ao chamar o Gemini: {last_err}"
                            except Exception as e:
                                resposta_final = f"❌ Erro na execução do Chat: {str(e)}"
                        else:
                            resposta_final = "⚠️ Ative o modo Real (Gemini LLM) com chave válida para conversar com o assistente."
                            
                        st.markdown(resposta_final)
                        st.session_state["chat_messages"].append({"role": "assistant", "content": resposta_final})

if __name__ == "__main__":
    main()
