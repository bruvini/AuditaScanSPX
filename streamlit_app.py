import streamlit as st
import pandas as pd
import os
from datetime import datetime

# Nossos módulos
from processamento.extrator_excel import carregar_dados_excel, analisar_qualidade_dados
from processamento.extrator_pdf import processar_pdf_laudos
from processamento.comparador import realizar_conciliacao
from processamento.exportador import gerar_excel_colorido

# Configuração da Página
st.set_page_config(page_title="AuditaScan SPX", layout="wide", page_icon="🔍")

# --- ESTILO CSS PERSONALIZADO ---
st.markdown("""
    <style>
    .main { background-color: #f8fafc; }
    .header-container {
        background: linear-gradient(90deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 40px;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 30px;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1);
    }
    .step-card {
        background-color: white;
        padding: 25px;
        border-radius: 15px;
        border: 1px solid #e2e8f0;
        margin-bottom: 20px;
        transition: transform 0.2s;
    }
    .step-number {
        background-color: #3b82f6;
        color: white;
        width: 30px;
        height: 30px;
        border-radius: 50%;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        margin-right: 10px;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

# --- CABEÇALHO ---
st.markdown("""
    <div class="header-container">
        <h1>🔍 AuditaScan SPX</h1>
        <p style="font-size: 1.3em;">Inteligência de Dados para Auditoria Hospitalar</p>
        <p style="opacity: 0.9;">Reduza em até 90% o tempo de conferência manual de laudos e solicitações.</p>
    </div>
    """, unsafe_allow_html=True)

# --- ESTADO DA SESSÃO ---
if 'etapa' not in st.session_state: st.session_state.etapa = 1
if 'df_excel' not in st.session_state: st.session_state.df_excel = None
if 'df_laudos' not in st.session_state: st.session_state.df_laudos = None

# --- FLUXO GAMIFICADO ---

# PASSO 1: EXCEL
with st.container():
    st.markdown('<div class="step-card">', unsafe_allow_html=True)
    st.markdown('<h3><span class="step-number">1</span> Base de Dados (Excel)</h3>', unsafe_allow_html=True)
    
    arquivo_excel = st.file_uploader("Arraste aqui a planilha de procedimentos", type=["xlsx"], key="up_excel")
    
    if arquivo_excel:
        df_temp = carregar_dados_excel(arquivo_excel)
        stats = analisar_qualidade_dados(df_temp)
        st.session_state.df_excel = df_temp
        st.session_state.etapa = max(st.session_state.etapa, 2)
        st.success(f"📈 **Planilha Analisada:** {stats['total_registros']} registros encontrados em {len(stats['exames_por_data'])} datas diferentes.")
    st.markdown('</div>', unsafe_allow_html=True)

# PASSO 2: LAUDOS (DESBLOQUEIA APÓS PASSO 1)
if st.session_state.etapa >= 2:
    with st.container():
        st.markdown('<div class="step-card">', unsafe_allow_html=True)
        st.markdown('<h3><span class="step-number">2</span> Laudos Oficiais (PDF)</h3>', unsafe_allow_html=True)
        
        arquivos_laudos = st.file_uploader("Selecione os arquivos de laudo (múltiplos permitidos)", type=["pdf"], accept_multiple_files=True)
        
        if arquivos_laudos:
            with st.spinner("Processando inteligência dos laudos..."):
                todos_exames = []
                for arq in arquivos_laudos:
                    with open("temp_l.pdf", "wb") as f: f.write(arq.getbuffer())
                    todos_exames.extend(processar_pdf_laudos("temp_l.pdf"))
                
                st.session_state.df_laudos = pd.DataFrame(todos_exames)
                st.session_state.etapa = max(st.session_state.etapa, 3)
                st.success(f"📄 **Leitura Concluída:** {len(st.session_state.df_laudos)} exames identificados nos documentos.")
        st.markdown('</div>', unsafe_allow_html=True)

# PASSO 3: SOLICITAÇÕES
if st.session_state.etapa >= 3:
    with st.container():
        st.markdown('<div class="step-card">', unsafe_allow_html=True)
        st.markdown('<h3><span class="step-number">3</span> Solicitações Escaneadas</h3>', unsafe_allow_html=True)
        st.caption("Fase final: Validação das imagens escaneadas (Disponível em breve)")
        st.file_uploader("Upload de imagens escaneadas", type=["pdf"], disabled=True)
        
        # Botão para liberar a conciliação
        if st.button("Finalizar Preparação e Ir para Auditoria ➡️"):
            st.session_state.etapa = 4
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# --- ETAPA 4: CONCILIAÇÃO ---
if st.session_state.etapa >= 4:
    st.divider()
    st.header("⚖️ Painel de Conciliação")
    
    col_btn, col_info = st.columns([1, 3])
    with col_btn:
        if st.button("🚀 Iniciar Auditoria Automática", use_container_width=True, type="primary"):
            with st.status("Auditando dados...", expanded=False) as s:
                # Realiza a comparação entre as fontes
                df_res = realizar_conciliacao(st.session_state.df_excel, st.session_state.df_laudos)
                st.session_state.df_auditoria = df_res
                s.update(label="Auditoria Finalizada!", state="complete")

    if 'df_auditoria' in st.session_state:
        df_fin = st.session_state.df_auditoria
        
        # --- PREPARAÇÃO PARA EXPORTAÇÃO (EXCEL) ---
        # Criamos uma cópia limpa para o exportador não sujar a visualização da tela
        df_para_exportar = df_fin.copy()

        # Converte colunas de tempo para apenas data (remove 00:00:00)
        for col in ["Data", "D. Nascimento"]:
            if col in df_para_exportar.columns:
                df_para_exportar[col] = pd.to_datetime(df_para_exportar[col]).dt.date

        # Gera o arquivo binário com as cores e larguras ajustadas
        with st.spinner("Gerando arquivo Excel colorido..."):
            excel_colorido = gerar_excel_colorido(df_para_exportar)
        
        # --- INTERFACE DE RESULTADOS ---
        # Filtros e Download
        c1, c2 = st.columns([3, 1])
        with c1:
            opcoes = list(df_fin['Status Auditoria'].unique())
            filtro = st.multiselect("Filtrar visualização por status:", options=opcoes, default=opcoes)
        
        with c2:
            st.download_button(
                label="📥 Baixar Planilha Auditada",
                data=excel_colorido,
                file_name=f"Auditoria_SPX_{datetime.now().strftime('%d-%m-%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )

        # Filtra o que será exibido na tabela da tela
        df_exibir = df_fin[df_fin['Status Auditoria'].isin(filtro)]

        # --- TABELA COM DESIGN PERFECCIONISTA ---
        st.dataframe(
            df_exibir,
            column_config={
                "Status Auditoria": st.column_config.TextColumn("Status", width="small", help="✅ OK | ⚠️ Divergência | ❌ Não Encontrado"),
                "Data": st.column_config.DateColumn("Data Exame", format="DD/MM/YYYY"),
                "D. Nascimento": st.column_config.DateColumn("Nascimento", format="DD/MM/YYYY"),
                "Observação": st.column_config.TextColumn("Observação", width="large"),
                "Paciente": st.column_config.TextColumn("Paciente", width="medium"),
            },
            hide_index=True,
            use_container_width=True
        )