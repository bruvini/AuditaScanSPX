import streamlit as st
import pandas as pd
import os
import sys
import time
from datetime import datetime, timedelta

# Garante que o diretório atual está no path para as importações
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# --- CONFIGURAÇÃO DA PÁGINA ---
# DEVE SER A PRIMEIRA CHAMADA DO STREAMLIT
st.set_page_config(
    page_title="AuditaScan SPX",
    layout="wide",
    page_icon="🏥",
    initial_sidebar_state="expanded"
)

# --- IMPORTAÇÃO DOS SEUS MÓDULOS ---
try:
    from processamento.extrator_excel import carregar_dados_excel
    from processamento.extrator_pdf import processar_pdf_laudos
    from processamento.comparador import realizar_conciliacao
    from processamento.exportador import gerar_excel_colorido
    from processamento.extrator_scaneado import extrair_dados_solicitacao
except ImportError as e:
    st.error(f"❌ Erro crítico de importação: {e}. Verifique se a pasta 'processamento' existe.")
    st.stop()

# --- ESTILO CSS (Design System) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Roboto', sans-serif; }
    .stApp { background-color: #f8fafc; }
    
    /* Header Principal */
    .main-header {
        background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
        padding: 2.5rem;
        border-radius: 12px;
        color: white;
        margin-bottom: 2rem;
        text-align: center;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
    }
    .main-header h1 { 
        color: white; 
        margin-bottom: 0.5rem; 
        font-weight: 700; 
        letter-spacing: -0.5px;
    }
    .main-header p {
        font-size: 1.1rem;
        opacity: 0.9;
        font-weight: 300;
    }
    
    /* Box de ROI (Tempo Economizado) */
    .roi-box {
        background-color: #dcfce7;
        border: 1px solid #86efac;
        color: #166534;
        padding: 1.5rem;
        border-radius: 10px;
        text-align: center;
        margin-top: 20px;
        margin-bottom: 20px;
        font-size: 1.2rem;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .roi-time {
        font-weight: 700;
        font-size: 1.5rem;
        color: #14532d;
    }
    
    /* Ajuste para Métricas (Cards) */
    div[data-testid="stMetric"] {
        background-color: white;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        border: 1px solid #e2e8f0;
    }

    /* Footer Fixo */
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: white;
        color: #64748b;
        text-align: center;
        padding: 10px;
        font-size: 0.8rem;
        border-top: 1px solid #e2e8f0;
        z-index: 100;
    }
    
    /* Ajuste para centralizar logo na sidebar */
    [data-testid="stSidebar"] img {
        display: block;
        margin-left: auto;
        margin-right: auto;
        margin-bottom: 20px;
        border-radius: 10px;
    }
    
    /* Inputs alinhados */
    .stFileUploader {
        padding-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --- INICIALIZAÇÃO DE ESTADO ---
if 'etapa' not in st.session_state: st.session_state.etapa = 1
if 'df_excel' not in st.session_state: st.session_state.df_excel = None
if 'df_laudos' not in st.session_state: st.session_state.df_laudos = None
if 'df_scans' not in st.session_state: st.session_state.df_scans = None
if 'df_auditoria' not in st.session_state: st.session_state.df_auditoria = None
if 'tempo_economizado' not in st.session_state: st.session_state.tempo_economizado = None

# --- SIDEBAR (NAVEGAÇÃO E HELP) ---
with st.sidebar:
    st.image("https://d2q79iu7y748jz.cloudfront.net/s/_squarelogo/256x256/1eb674070b34e074b60c70b24e82bd01", width=180)
    
    st.title("AuditaScan SPX")
    st.caption("v2.4 | Hospital Mun. São José")
    st.markdown("---")
    
    st.markdown("### 🧭 Guia de Uso")
    st.info("""
    **Siga o fluxo para auditar:**
    
    1. **Planilha**: Carregue o relatório de produção (.xlsx).
    2. **Laudos**: Importe os PDFs oficiais dos exames.
    3. **Scans**: Suba as digitalizações das guias físicas.
    4. **Auditoria**: O sistema cruza os dados automaticamente.
    """)

    st.markdown("---")
    if st.button("🔄 Nova Auditoria", type="secondary", use_container_width=True):
        import gc
        st.session_state.clear()
        gc.collect()
        st.rerun()

# --- HEADER E KPIS ---
def render_header():
    st.markdown("""
    <div class="main-header">
        <h1>🔍 AuditaScan SPX</h1>
        <p>Excelência e Precisão na Auditoria de Diagnósticos por Imagem</p>
    </div>
    """, unsafe_allow_html=True)

def render_metrics():
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("1. Base Excel", "OK" if st.session_state.df_excel is not None else "Pendente",
                  delta="Carregado" if st.session_state.df_excel is not None else None)
    with col2:
        val = f"{len(st.session_state.df_laudos)} exames" if st.session_state.df_laudos is not None else "Pendente"
        st.metric("2. Laudos PDF", "OK" if st.session_state.df_laudos is not None else "Aguardando",
                  delta=val if st.session_state.df_laudos is not None else None)
    with col3:
        val_scan = f"{len(st.session_state.df_scans)} guias" if st.session_state.df_scans is not None else "Pendente"
        st.metric("3. PDF Solicitações", "OK" if st.session_state.df_scans is not None else "Aguardando",
                  delta=val_scan if st.session_state.df_scans is not None else None)
    with col4:
        status = "Pronto" if st.session_state.etapa >= 4 else "Em Preparação"
        st.metric("Status", status, delta_color="inverse" if status == "Pronto" else "off")

render_header()
render_metrics()
st.markdown("---")

# --- ÁREA DE INPUTS (TRÊS COLUNAS LADO A LADO) ---
with st.container():
    col_excel, col_laudos, col_scans = st.columns(3, gap="medium")

    # ---------------------------------------------------------
    # COLUNA 1: DADOS DA PLANILHA
    # ---------------------------------------------------------
    with col_excel:
        st.markdown("### 📂 1. Dados da Planilha")
        
        if st.session_state.df_excel is not None:
            # Card de Sucesso com contagem
            st.success(f"✅ **{len(st.session_state.df_excel)} linhas** carregadas.")
            if st.checkbox("Trocar arquivo Excel?", key="chk_excel"):
                st.session_state.df_excel = None
                st.rerun()
        else:
            arquivo_excel = st.file_uploader("Upload Planilha (.xlsx)", type=["xlsx"], key="up_excel")
            if arquivo_excel:
                try:
                    with st.spinner("Lendo planilha..."):
                        df_temp = carregar_dados_excel(arquivo_excel)
                        if 'Data' not in df_temp.columns or 'Paciente' not in df_temp.columns:
                            st.error("Colunas obrigatórias ausentes: 'Data' e 'Paciente'.")
                        else:
                            st.session_state.df_excel = df_temp
                            st.session_state.etapa = max(st.session_state.etapa, 2)
                            st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")

    # ---------------------------------------------------------
    # COLUNA 2: LAUDOS MÉDICOS
    # ---------------------------------------------------------
    with col_laudos:
        st.markdown("### 📄 2. Laudos Médicos")
        
        if st.session_state.etapa < 2:
            st.info("🔒 Aguardando Planilha...")
        elif st.session_state.df_laudos is not None:
            # Card de Sucesso com contagem
            st.success(f"✅ **{len(st.session_state.df_laudos)} exames** extraídos.")
            if st.checkbox("Trocar Laudos?", key="chk_laudos"):
                import gc
                del st.session_state.df_laudos
                st.session_state.df_laudos = None
                gc.collect()
                st.rerun()
        else:
            arquivos_laudos = st.file_uploader("Upload Laudos (.pdf)", type=["pdf"], accept_multiple_files=True)
            if arquivos_laudos:
                with st.status("Processando Laudos...", expanded=True):
                    import tempfile
                    import gc
                    chunks_laudos = []
                    for arq in arquivos_laudos:
                        st.write(f"Lendo: {arq.name}")
                        with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as tmp:
                            tmp.write(arq.getbuffer())
                            tmp.flush()
                            try:
                                exames_arquivo = []
                                for exame in processar_pdf_laudos(tmp.name):
                                    exames_arquivo.append(exame)
                                if exames_arquivo:
                                    chunks_laudos.append(pd.DataFrame(exames_arquivo))
                                del exames_arquivo
                            except Exception as e:
                                st.error(f"Erro: {e}")
                        # Liberta memória do ficheiro logo após processá-lo
                        gc.collect()
                    
                    if chunks_laudos:
                        st.session_state.df_laudos = pd.concat(chunks_laudos, ignore_index=True)
                        st.session_state.etapa = max(st.session_state.etapa, 3)
                        del chunks_laudos
                        gc.collect()
                        st.rerun()
                    else:
                        st.warning("Nenhum dado encontrado.")

    # ---------------------------------------------------------
    # COLUNA 3: PDF DAS SOLICITAÇÕES
    # ---------------------------------------------------------
    with col_scans:
        st.markdown("### 📷 3. PDF das Solicitações")
        
        if st.session_state.etapa < 3:
            st.info("🔒 Aguardando Laudos...")
        elif st.session_state.df_scans is not None:
            # Card de Sucesso com contagem
            st.success(f"✅ **{len(st.session_state.df_scans)} guias** lidas.")
            
            with st.expander("Ver dados extraídos"):
                st.dataframe(st.session_state.df_scans, use_container_width=True)
                
            if st.checkbox("Trocar Scans?", key="chk_scans"):
                import gc
                del st.session_state.df_scans
                st.session_state.df_scans = None
                gc.collect()
                st.rerun()
        else:
            uploaded_scans = st.file_uploader("Upload Scans (.pdf)", type=["pdf"], accept_multiple_files=True, key="up_scans")
            if uploaded_scans:
                with st.status("Lendo (OCR)...", expanded=True):
                    import tempfile
                    import gc
                    chunks_scans = []
                    for arq in uploaded_scans:
                        st.write(f"Processando: {arq.name}")
                        with tempfile.NamedTemporaryFile(delete=True, suffix=".pdf") as tmp:
                            tmp.write(arq.getbuffer())
                            tmp.flush()
                            try:
                                scans_arquivo = extrair_dados_solicitacao(tmp.name)
                                if scans_arquivo:
                                    chunks_scans.append(pd.DataFrame(scans_arquivo))
                                del scans_arquivo
                            except Exception as e:
                                st.error(f"Erro: {e}")
                        # Liberta memória do ficheiro logo após processá-lo
                        gc.collect()
                    
                    if chunks_scans:
                        st.session_state.df_scans = pd.concat(chunks_scans, ignore_index=True)
                        st.session_state.etapa = 4
                        del chunks_scans
                        gc.collect()
                        st.rerun()
                    else:
                        st.warning("Nenhuma guia identificada.")

# --- ÁREA DE AUDITORIA ---
if st.session_state.etapa >= 4:
    st.markdown("---")
    st.subheader("⚙️ Execução da Auditoria")
    
    col_filtros, col_acao = st.columns([3, 1])
    
    with col_filtros:
        if st.session_state.df_excel is not None and 'Data' in st.session_state.df_excel.columns:
            datas_unicas = sorted(st.session_state.df_excel['Data'].dropna().unique())
            datas_selecionadas = st.multiselect(
                "Filtrar período para análise:",
                options=datas_unicas,
                format_func=lambda x: x.strftime('%d/%m/%Y'),
                default=datas_unicas
            )
        else:
            datas_selecionadas = []

    with col_acao:
        st.write("")
        st.write("")
        btn_auditar = st.button("🚀 AUDITAR AGORA", type="primary", use_container_width=True)
    
    if btn_auditar:
        if not datas_selecionadas:
            st.warning("Selecione pelo menos uma data.")
        else:
            with st.spinner("Cruzando informações..."):
                df_filtrado = st.session_state.df_excel[
                    st.session_state.df_excel['Data'].isin(datas_selecionadas)
                ].copy()
                
                inicio = time.time()
                resultado = realizar_conciliacao(
                    df_filtrado, 
                    st.session_state.df_laudos, 
                    st.session_state.df_scans
                )
                fim = time.time()
                
                tempo_real = fim - inicio
                linhas = len(df_filtrado)
                economia_seg = max(0, (linhas * 15) - tempo_real)
                str_economia = str(timedelta(seconds=int(economia_seg)))
                
                st.session_state.df_auditoria = resultado
                st.session_state.tempo_economizado = str_economia
                st.toast("Auditoria finalizada com sucesso!", icon="🎉")

    # RESULTADOS
    if st.session_state.df_auditoria is not None and not st.session_state.df_auditoria.empty:
        
        if st.session_state.tempo_economizado:
            st.markdown(f"""
            <div class="roi-box">
                ⏱️ <b>Eficiência Operacional:</b> Você economizou cerca de 
                <span class="roi-time">{st.session_state.tempo_economizado}</span> 
                de trabalho manual nesta auditoria.
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("### 📊 Relatório de Divergências")
        
        tab1, tab2 = st.tabs(["🔍 Visão Interativa", "📥 Exportar Excel"])
        
        with tab1:
            df_visual = st.session_state.df_auditoria.copy()
            st.dataframe(
                df_visual,
                column_config={
                    "Data do Exame": st.column_config.DateColumn("Data do Exame", format="DD/MM/YYYY"),
                    "Solicitação Física": st.column_config.TextColumn("Solicitação Física", width="small"),
                    "Laudo Digital": st.column_config.TextColumn("Laudo Digital", width="small"),
                    "Detalhe Scan": st.column_config.TextColumn("Detalhe Scan", width="medium"),
                    "Detalhe Laudo": st.column_config.TextColumn("Detalhe Laudo", width="medium")
                },
                use_container_width=True,
                hide_index=True
            )
            
        with tab2:
            st.success("Relatório pronto. As linhas coloridas (Verde/Vermelho) estarão no arquivo baixado.")
            excel_data = gerar_excel_colorido(st.session_state.df_auditoria)
            st.download_button(
                label="📥 Baixar Excel Colorido (.xlsx)",
                data=excel_data,
                file_name=f"Auditoria_SPX_{datetime.now().strftime('%d-%m-%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

# --- FOOTER ---
st.markdown(f"""
<div class="footer">
    <p>© {datetime.now().year} Hospital Municipal São José. Todos os direitos reservados. | Desenvolvido para Coordenação NIR pelo Enf. Bruno Vinícius.</p>
</div>
""", unsafe_allow_html=True)