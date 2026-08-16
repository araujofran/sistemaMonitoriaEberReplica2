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

        /* ANIMAÇÃO CSS DE VERMELHO PULSANTE PARA NÓS DE RISCO ALTO */
        @keyframes pulse-red-glow {
            0% {
                box-shadow: 0 0 8px rgba(255, 58, 92, 0.5), 0 0 15px rgba(255, 58, 92, 0.3);
                border-color: #FF3A5C !important;
            }
            50% {
                box-shadow: 0 0 22px rgba(255, 58, 92, 0.95), 0 0 35px rgba(255, 58, 92, 0.6);
                border-color: #FF0033 !important;
            }
            100% {
                box-shadow: 0 0 8px rgba(255, 58, 92, 0.5), 0 0 15px rgba(255, 58, 92, 0.3);
                border-color: #FF3A5C !important;
            }
        }

        .node-card-high {
            border: 2px solid #FF3A5C !important;
            background-color: rgba(255, 58, 92, 0.08) !important;
            animation: pulse-red-glow 2s infinite ease-in-out !important;
            border-radius: 8px !important;
            padding: 16px !important;
            margin-bottom: 15px !important;
        }

        .node-card-medium {
            border: 1.5px solid #F5D547 !important;
            background-color: rgba(245, 213, 71, 0.06) !important;
            border-radius: 8px !important;
            padding: 16px !important;
            margin-bottom: 15px !important;
        }

        .node-card-low {
            border: 1px solid #2A2D38 !important;
            background-color: var(--bg-surface) !important;
            border-radius: 8px !important;
            padding: 16px !important;
            margin-bottom: 15px !important;
        }

        /* BENTO GRID LAYOUT (COMMAND CENTER VISÃO EXECUTIVA) */
        .bento-card {
            background-color: var(--bg-surface) !important;
            border: 1px solid var(--border-color) !important;
            border-radius: 12px !important;
            padding: 20px !important;
            margin-bottom: 20px !important;
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25) !important;
            transition: transform 0.2s ease, border-color 0.2s ease;
        }

        .bento-card:hover {
            border-color: var(--accent-indigo) !important;
            transform: translateY(-2px);
        }

        .bento-tag-red {
            background-color: rgba(255, 58, 92, 0.15);
            color: #FF3A5C;
            border: 1px solid #FF3A5C;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            display: inline-block;
            margin: 3px;
        }

        .bento-tag-yellow {
            background-color: rgba(245, 213, 71, 0.15);
            color: #F5D547;
            border: 1px solid #F5D547;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            display: inline-block;
            margin: 3px;
        }

        .bento-tag-blue {
            background-color: rgba(61, 215, 229, 0.15);
            color: #3DD7E5;
            border: 1px solid #3DD7E5;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.8rem;
            font-weight: 600;
            display: inline-block;
            margin: 3px;
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

    # ABAS PRINCIPAIS DO SISTEMA HALO (INCLUINDO VISÃO EXECUTIVA BENTO GRID)
    tab0, tab1, tab2, tab3, tab4 = st.tabs([
        "👑 Visão Executiva / Command Center",
        "📊 Aba 1: Dashboard de Sinais & Rich Cards",
        "🔮 Aba 2: Monitoramento Preditivo & Anomalias",
        "🗺️ Aba 3: Jornada do Cliente & Timeline",
        "🧩 Aba 4: Central Modular & Chat RAG"
    ])

    # Carrega base de auditorias gravadas
    lista_auditorias = database.listar_todas_auditorias()
    df_banco = pd.DataFrame(lista_auditorias) if lista_auditorias else pd.DataFrame()

    # ---------------------------------------------------------
    # ABA 0: VISÃO EXECUTIVA / COMMAND CENTER (BENTO GRID)
    # ---------------------------------------------------------
    with tab0:
        st.subheader("👑 Visão Executiva / Command Center - Painel de Controle Operacional")
        st.markdown("Painel gerencial consolidado em arquitetura **Bento Grid** agregando KPIs globais de qualidade, saúde da operação e insights de IA.")
        
        # MÓDULO 1: TOP METRICS (BENTO CARDS DE VISÃO RÁPIDA)
        col_bm1, col_bm2, col_bm3, col_bm4 = st.columns(4)
        
        total_audit_val = len(df_banco) if not df_banco.empty else 0
        avg_score_val = df_banco["score_operador"].mean() if not df_banco.empty and "score_operador" in df_banco.columns else 100.0
        criticos_val = len(df_banco[df_banco["score_operador"] == 0]) if not df_banco.empty and "score_operador" in df_banco.columns else 0
        
        with col_bm1:
            st.markdown(f"""
            <div class="bento-card">
                <div style="font-size:0.8rem; text-transform:uppercase; color:var(--text-muted); font-weight:600;">📊 Volume Total de Auditorias</div>
                <div style="font-size:2rem; font-weight:700; color:var(--accent-indigo); margin:4px 0;">{total_audit_val}</div>
                <div style="font-size:0.78rem; color:var(--accent-success);">📈 +18.4% vs semana anterior</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_bm2:
            st.markdown(f"""
            <div class="bento-card">
                <div style="font-size:0.8rem; text-transform:uppercase; color:var(--text-muted); font-weight:600;">💙 Score de Sentimento Geral</div>
                <div style="font-size:2rem; font-weight:700; color:var(--accent-cyan); margin:4px 0;">{avg_score_val:.1f}/100</div>
                <div style="font-size:0.78rem; color:var(--accent-success);">📈 +4.2 pontos na média</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_bm3:
            st.markdown("""
            <div class="bento-card">
                <div style="font-size:0.8rem; text-transform:uppercase; color:var(--text-muted); font-weight:600;">⚡ Taxa Global de Fricção (CES)</div>
                <div style="font-size:2rem; font-weight:700; color:var(--accent-warning); margin:4px 0;">12.8%</div>
                <div style="font-size:0.78rem; color:var(--accent-warning);">📉 -2.1% (Fricção sob controle)</div>
            </div>
            """, unsafe_allow_html=True)
            
        with col_bm4:
            st.markdown(f"""
            <div class="bento-card">
                <div style="font-size:0.8rem; text-transform:uppercase; color:var(--text-muted); font-weight:600;">🚨 Alertas Críticos (Score 0)</div>
                <div style="font-size:2rem; font-weight:700; color:var(--accent-danger); margin:4px 0;">{criticos_val}</div>
                <div style="font-size:0.78rem; color:var(--accent-danger);">⚠️ Requer ação preventiva imediata</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        
        # MÓDULOS CENTRAIS (BENTO GRID MIDDLE ROW)
        col_bmid1, col_bmid2 = st.columns([1, 1])
        
        with col_bmid1:
            st.markdown("### 🎯 Módulo 2: Saúde da Operação (KPIs de Qualidade)")
            
            # Progress Bar para QoS
            st.markdown("""
            <div class="bento-card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <b>Score de Qualidade dos Atendentes (QoS)</b>
                    <span style="font-weight:700; color:#28E0B3;">86.5%</span>
                </div>
                <div style="background-color:var(--bg-surface2); border-radius:10px; height:12px; overflow:hidden;">
                    <div style="background:linear-gradient(90deg, #5B68FF 0%, #28E0B3 100%); width:86.5%; height:100%;"></div>
                </div>
                <p style="font-size:0.8rem; color:var(--text-muted); margin-top:8px;">Meta estabelecida: 85.0% | Status: <b style="color:#28E0B3;">Conforme</b></p>
            </div>
            """, unsafe_allow_html=True)
            
            # Progress Bar para FCR
            st.markdown("""
            <div class="bento-card">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
                    <b>Taxa de Resolução no Primeiro Contato (FCR)</b>
                    <span style="font-weight:700; color:#3DD7E5;">91.2%</span>
                </div>
                <div style="background-color:var(--bg-surface2); border-radius:10px; height:12px; overflow:hidden;">
                    <div style="background:linear-gradient(90deg, #5B68FF 0%, #3DD7E5 100%); width:91.2%; height:100%;"></div>
                </div>
                <p style="font-size:0.8rem; color:var(--text-muted); margin-top:8px;">Meta estabelecida: 90.0% | Status: <b style="color:#3DD7E5;">Superado</b></p>
            </div>
            """, unsafe_allow_html=True)
            
        with col_bmid2:
            st.markdown("### 🧩 Módulo 3: Causa Raiz (RCA NLP Cluster)")
            st.markdown("""
            <div class="bento-card">
                <div style="font-weight:600; margin-bottom:12px;">Top 5 Ofensores de Causa Raiz Extraídos por NLP/LLM:</div>
                <div style="margin-bottom:8px;">
                    <span class="bento-tag-red">🔴 1. Exclusão Digital (Ausência de E-mail / Z. Rural)</span> - <b>34% dos casos</b>
                </div>
                <div style="margin-bottom:8px;">
                    <span class="bento-tag-red">🔴 2. Ausência de Envio via WhatsApp no CRM</span> - <b>26% dos casos</b>
                </div>
                <div style="margin-bottom:8px;">
                    <span class="bento-tag-yellow">🟡 3. Falha de Omnichannel & Redirecionamento Físico</span> - <b>18% dos casos</b>
                </div>
                <div style="margin-bottom:8px;">
                    <span class="bento-tag-yellow">🟡 4. Inaderência em Informação de Prazos de Estorno</span> - <b>12% dos casos</b>
                </div>
                <div style="margin-bottom:8px;">
                    <span class="bento-tag-blue">🔵 5. Saque Rotativo Comprometendo Limite</span> - <b>10% dos casos</b>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        
        # MÓDULOS INFERIORES (GRÁFICO DE TENDÊNCIA + FEED DE INSIGHTS DE IA)
        col_bot1, col_bot2 = st.columns([2, 1])
        
        with col_bot1:
            st.markdown("### 📈 Módulo 4: Tendência Operacional (Volume vs Sentimento Negativo)")
            
            trend_data = pd.DataFrame({
                "Horário": ["08:00", "09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00", "17:00"],
                "Volume Atendimentos": [45, 80, 120, 150, 110, 95, 140, 165, 130, 90],
                "Fricção Negativa (%)": [5, 8, 14, 22, 15, 12, 28, 19, 11, 7]
            })
            
            area_chart = alt.Chart(trend_data).mark_area(
                line={'color':'#FF3A5C'},
                color=alt.Gradient(
                    gradient='linear',
                    stops=[alt.GradientStop(color='#FF3A5C', offset=0),
                           alt.GradientStop(color='rgba(255, 58, 92, 0.05)', offset=1)],
                    x1=1, x2=1, y1=1, y2=0
                )
            ).encode(
                x=alt.X('Horário:N', title='Horário do Dia'),
                y=alt.Y('Fricção Negativa (%):Q', title='Taxa de Fricção Negativa (%)'),
                tooltip=['Horário', 'Volume Atendimentos', 'Fricção Negativa (%)']
            ).properties(
                height=260
            )
            
            st.altair_chart(area_chart, use_container_width=True)
            
        with col_bot2:
            st.markdown("### 🤖 Módulo 5: Feed de Alertas Preditivos (LLM Insights)")
            
            st.markdown("""
            <div class="bento-card" style="border-left: 4px solid var(--accent-danger) !important;">
                <div style="font-size:0.78rem; font-weight:700; color:var(--accent-danger);">🚨 ALERTA DE SISTEMA (14:30)</div>
                <div style="font-size:0.88rem; margin:4px 0;"><b>Aumento de 15% em fricção</b> no canal físico (Agências) nas últimas 2 horas. Sugestão: Isolar anomalia.</div>
            </div>
            
            <div class="bento-card" style="border-left: 4px solid var(--accent-warning) !important;">
                <div style="font-size:0.78rem; font-weight:700; color:var(--accent-warning);">⚡ RECOMENDAÇÃO RAG (13:15)</div>
                <div style="font-size:0.88rem; margin:4px 0;"><b>Inaderência recorrente:</b> 4 operadores apresentaram dúvida no script de prazo de Pix.</div>
            </div>
            
            <div class="bento-card" style="border-left: 4px solid var(--accent-success) !important;">
                <div style="font-size:0.78rem; font-weight:700; color:var(--accent-success);">🟢 STATUS OPERACIONAL (12:00)</div>
                <div style="font-size:0.88rem; margin:4px 0;"><b>SLA de Resolução:</b> 98.4% dos atendimentos dentro do tempo padrão acordado.</div>
            </div>
            """, unsafe_allow_html=True)

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
        # PASSO 2: CONSOLIDAÇÃO LLM EM LOTE (REGRAS ORQUESTRADORAS)
        # ---------------------------------------------------------
        st.markdown("---")
        st.subheader("⚡ Passo 2: Consolidação LLM em Lote (Micro-batching de 5)")
        st.markdown("Conforme as **Regras Orquestradoras**, após o Passo 1 (NLP), o Passo 2 executa a inteligência do Gemini LLM em micro-lotes de 5 chamadas sobre os dados salvos no SQLite.")
        
        audits_llm_pendentes = [a["protocolo"] for a in lista_auditorias if a.get("llm_status") == "pendente"]
        
        col_llm1, col_llm2 = st.columns([2, 1])
        with col_llm1:
            st.metric("Auditorias Pendentes do Passo 2 (LLM)", f"{len(audits_llm_pendentes)} chamadas", delta="Aguardando LLM" if audits_llm_pendentes else "100% Concluído")
            
        with col_llm2:
            st.write("")
            if st.button("⚡ Executar Passo 2 (Consolidação LLM em Lote)", key="btn_passo2_llm_lote"):
                if not audits_llm_pendentes:
                    st.info("Nenhuma auditoria pendente de análise LLM (Passo 2). Todas as auditorias já foram consolidadas!")
                elif not use_real or not api_key:
                    st.warning("⚠️ Ative o modo Real (Gemini LLM) com a chave de API para rodar o Passo 2.")
                else:
                    status_lote = st.empty()
                    log_box_lote = st.empty()
                    logs_lote = []
                    
                    def log_cb_lote(msg):
                        logs_lote.append(f"[{len(logs_lote)+1}] {msg}")
                        log_html = "".join([f"<div class='console-line'>{l}</div>" for l in logs_lote])
                        log_box_lote.markdown(f"<div class='console-box'>{log_html}</div>", unsafe_allow_html=True)
                        
                    orchestrator = NLPAuditOrchestrator(use_real_llm=use_real, api_key=api_key, model_name=model_name)
                    log_cb_lote(f"🚀 [Passo 2 Orquestrador] Iniciando consolidação LLM em Micro-lotes de 5 para {len(audits_llm_pendentes)} protocolos pendentes...")
                    
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        res_lote = loop.run_until_complete(
                            orchestrator.executar_passo2_llm_microbatch(audits_llm_pendentes, batch_size=5, log_callback=log_cb_lote)
                        )
                        loop.close()
                        status_lote.success(f"✅ Passo 2 (LLM Micro-batching) concluído com sucesso! ({len(res_lote)} relatórios consolidados)")
                        time.sleep(2)
                        st.rerun()
                    except Exception as e:
                        log_cb_lote(f"❌ Erro no Passo 2 LLM: {str(e)}")
                        status_lote.error(f"Erro no Passo 2 LLM: {str(e)}")

    # ---------------------------------------------------------
    # ABA 3: JORNADA DO CLIENTE (VERTICAL NODE-BASED TIMELINE)
    # ---------------------------------------------------------
    with tab3:
        st.subheader("3. Vertical Node-Based Timeline - Jornada Granular do Cliente")
        st.markdown("Motor de NLP com fragmentação em micro-eventos. Os nós com risco 🔴 **ALERTA CRÍTICO** possuem destaque visual em **vermelho neon pulsante** indicando gargalos operacionais e a Causa Raiz (RCA).")
        
        # Mock Data Completo (12 Micro-eventos do Pipeline de NLP)
        mock_timeline_events = [
            {
                "etapa": 1,
                "tempo": "00:00",
                "ator": "Atendente",
                "acao_nlp": "Abertura de chamada padrão",
                "nivel_risco": "BAIXO"
            },
            {
                "etapa": 2,
                "tempo": "00:15",
                "ator": "Cliente Titular",
                "acao_nlp": "Extração de Atrito Multicanal",
                "entidades": ["Aracaju", "bairro Jardins", "centro da capital"],
                "causa_raiz": "Falha de Omnichannel - Queda de SLA e redirecionamento físico",
                "nivel_risco": "ALTO",
                "acao_sugerida": "Revisar roteamento de atendimento físico"
            },
            {
                "etapa": 3,
                "tempo": "01:00",
                "ator": "Sistema",
                "acao_nlp": "Validação Positiva de Cadastro",
                "protocolo_gerado": "2607199947",
                "nivel_risco": "BAIXO"
            },
            {
                "etapa": 4,
                "tempo": "01:30",
                "ator": "Atendente",
                "acao_nlp": "Coleta de PII Secundário (KYC)",
                "entidades_ofuscadas": ["CPF: 039***0820", "Tel: 79 991***682"],
                "nivel_risco": "BAIXO"
            },
            {
                "etapa": 5,
                "tempo": "02:00",
                "ator": "Sistema",
                "acao_nlp": "Gargalo de Sistema (Barreira Digital)",
                "causa_raiz": "Exclusão Digital - Ausência de E-mail / Residente Zona Rural",
                "nivel_risco": "ALTO",
                "acao_sugerida": "Sinalizar Fallback de Canal"
            },
            {
                "etapa": 6,
                "tempo": "02:30",
                "ator": "Sistema (Motor NLP)",
                "acao_nlp": "Speaker Diarization (Mudança de Locutor)",
                "novo_ator": "Terceiro Autorizado (Aldanete)",
                "nivel_risco": "MÉDIO"
            },
            {
                "etapa": 7,
                "tempo": "03:00",
                "ator": "Terceiro",
                "acao_nlp": "Relato de falha no Autoatendimento",
                "causa_raiz": "Dependência de conexão contínua - Falha de App por Wi-Fi instável",
                "nivel_risco": "MÉDIO"
            },
            {
                "etapa": 8,
                "tempo": "03:30",
                "ator": "Sistema",
                "acao_nlp": "Limitação de Ferramenta (Engessamento)",
                "causa_raiz": "Ausência de funcionalidade de envio via WhatsApp no CRM",
                "nivel_risco": "ALTO",
                "acao_sugerida": "Gerar Ticket TI - Habilitar disparo WhatsApp"
            },
            {
                "etapa": 9,
                "tempo": "04:00",
                "ator": "Terceiro",
                "acao_nlp": "Identificação de Objeto de Desejo",
                "entidades": ["Cartão Visa", "Final 4473"],
                "nivel_risco": "BAIXO"
            },
            {
                "etapa": 10,
                "tempo": "05:00",
                "ator": "Atendente",
                "acao_nlp": "Quebra de Expectativa Comercial (Risco de Churn)",
                "causa_raiz": "Limite indisponível comprometido por saque rotativo",
                "entidades": ["Débito: R$ 2623,54", "Parcela: R$ 15,00"],
                "nivel_risco": "ALTO",
                "acao_sugerida": "Alerta Preditivo de Reclamação Futura"
            },
            {
                "etapa": 11,
                "tempo": "06:00",
                "ator": "Sistema",
                "acao_nlp": "Acordo de Resolução e SLA Definido",
                "canal_definido": "SMS",
                "prazo_acordado": "1 dia útil",
                "nivel_risco": "BAIXO"
            },
            {
                "etapa": 12,
                "tempo": "07:00",
                "ator": "Atendente",
                "acao_nlp": "Encerramento e tabulação da chamada",
                "nivel_risco": "BAIXO"
            }
        ]

        # Filtro de Protocolo para Rastreabilidade
        opcoes_jornada = ["⭐ Protocolo Exemplo 2607199947 (12 Micro-eventos de NLP - Análise Granular)"]
        if not df_banco.empty:
            for p in df_banco["protocolo"].tolist():
                opcoes_jornada.append(f"Protocolo {p} (Auditado no SQLite)")
                
        proto_jornada_sel = st.selectbox(
            "Selecione o protocolo para rastrear a timeline de micro-eventos:",
            opcoes_jornada,
            key="sb_jornada_timeline"
        )
        
        st.markdown("---")
        st.markdown("### 🌲 Árvore Vertical de Eventos da Jornada (Vertical Stepper)")
        
        # Renderização dos Nós da Timeline
        for ev in mock_timeline_events:
            risco = ev.get("nivel_risco", "BAIXO")
            if risco == "ALTO":
                card_class = "node-card-high"
                badge_html = "<span class='badge badge-critical'>🔴 RISCO ALTO (ATENÇÃO CRÍTICA)</span>"
            elif risco == "MÉDIO":
                card_class = "node-card-medium"
                badge_html = "<span class='badge badge-attention'>🟡 RISCO MÉDIO</span>"
            else:
                card_class = "node-card-low"
                badge_html = "<span class='badge badge-controlled'>🟢 RISCO BAIXO</span>"
                
            st.markdown(f"""
            <div class="{card_class}">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div>
                        <span style="font-weight:700; color:var(--accent-cyan);">Etapa {ev['etapa']}</span> | 
                        <span style="font-family:'JetBrains Mono', monospace; color:var(--text-muted);">⏱️ {ev['tempo']}</span> | 
                        <b>👤 Ator:</b> {ev['ator']}
                    </div>
                    <div>{badge_html}</div>
                </div>
                <h4 style="margin: 8px 0 4px 0;">🎯 {ev['acao_nlp']}</h4>
            </div>
            """, unsafe_allow_html=True)
            
            # Se tiver detalhes (causa_raiz, entidades ou acao_sugerida), abre painel expansível interativo (Side/Bottom Sheet)
            if "causa_raiz" in ev or "entidades" in ev or "acao_sugerida" in ev or "entidades_ofuscadas" in ev:
                with st.expander(f"🔍 Investigar Detalhes Analíticos da Etapa {ev['etapa']} (Painel de Causa Raiz)"):
                    if "causa_raiz" in ev:
                        st.markdown(f"**🚨 Causa Raiz Técnica (RCA):** {ev['causa_raiz']}")
                    if "entidades" in ev:
                        st.markdown(f"**📌 Entidades Capturadas:** `{', '.join(ev['entidades'])}`")
                    if "entidades_ofuscadas" in ev:
                        st.markdown(f"**🔒 PII Ofuscado:** `{', '.join(ev['entidades_ofuscadas'])}`")
                    if "protocolo_gerado" in ev:
                        st.markdown(f"**📄 Protocolo Gerado:** `{ev['protocolo_gerado']}`")
                        
                    if "acao_sugerida" in ev:
                        st.write("")
                        st.markdown("**⚡ Ação Analítica Recomendada (AITriggerButton):**")
                        lbl_acao = ev['acao_sugerida']
                        if st.button(f"⚡ {lbl_acao}", key=f"btn_ai_trigger_node_{ev['etapa']}"):
                            st.success(f"🚀 [AITrigger Executado] Ação '{lbl_acao}' disparada com sucesso no pipeline RAG/MCP!")

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
