import pandas as pd
from io import BytesIO

def gerar_excel_colorido(df):
    """
    Gera um Excel com linhas coloridas baseadas na conciliação,
    datas formatadas e colunas auto-ajustadas.
    Compatível com a nova estrutura de colunas (DN, Médico, etc).
    """
    if df is None or df.empty:
        return None

    df_export = df.copy()
    
    # 1. Tratamento de Datas para o Excel não mostrar horas (00:00:00)
    # A coluna 'DN' já vem como string do comparador, então focamos na 'Data do Exame'
    if "Data do Exame" in df_export.columns:
        df_export["Data do Exame"] = pd.to_datetime(df_export["Data do Exame"]).dt.date

    output = BytesIO()
    
    # Engine 'xlsxwriter' é necessária para formatação condicional avançada
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Auditoria')
        workbook  = writer.book
        worksheet = writer.sheets['Auditoria']

        # --- DEFINIÇÃO DE ESTILOS ---
        fmt_data = 'dd/mm/yyyy'
        
        # Estilos de linha (Fundo + Borda + Formato de Data)
        style_base = {'border': 1, 'num_format': fmt_data}
        
        f_verde    = workbook.add_format({**style_base, 'bg_color': '#C6EFCE', 'font_color': '#006100'}) # Verde Excel
        f_amarelo  = workbook.add_format({**style_base, 'bg_color': '#FFEB9C', 'font_color': '#9C5700'}) # Amarelo Excel
        f_vermelho = workbook.add_format({**style_base, 'bg_color': '#FFC7CE', 'font_color': '#9C0006'}) # Vermelho Excel
        
        # Estilo do Cabeçalho
        f_header = workbook.add_format({
            'bold': True, 
            'bg_color': '#4472C4', # Azul corporativo
            'font_color': 'white',
            'border': 1,
            'align': 'center',
            'valign': 'vcenter'
        })

        # --- LÓGICA DE COLORAÇÃO ---
        # Identifica a posição das colunas críticas pelos NOVOS NOMES
        try:
            idx_solic = df_export.columns.get_loc("Solicitação Física")
            idx_laudo = df_export.columns.get_loc("Laudo Digital")
        except KeyError:
            # Segurança: Se as colunas não existirem, não aplica cor mas gera o excel
            idx_solic = -1
            idx_laudo = -1

        # Itera sobre as linhas para aplicar a cor
        for row_num in range(len(df_export)):
            fmt = f_amarelo # Padrão: Divergência Parcial
            
            if idx_solic != -1 and idx_laudo != -1:
                # Pega o valor da célula (convertendo para string maiúscula para garantir)
                s = str(df_export.iloc[row_num, idx_solic]).strip().upper()
                l = str(df_export.iloc[row_num, idx_laudo]).strip().upper()
                
                if s == "SIM" and l == "SIM":
                    fmt = f_verde
                elif s == "NÃO" and l == "NÃO":
                    fmt = f_vermelho
                # Qualquer outra combinação (SIM/NÃO ou NÃO/SIM) fica Amarelo
            
            # Aplica o formato na linha inteira (+1 pois o header é a linha 0)
            worksheet.set_row(row_num + 1, None, fmt)

        # --- AJUSTE FINO DO LAYOUT ---
        # Formata o cabeçalho e ajusta largura das colunas
        for i, col in enumerate(df_export.columns):
            # Calcula largura baseada no tamanho do texto da coluna ou do header
            max_len = max(
                df_export[col].astype(str).map(len).max(),
                len(str(col))
            )
            # Adiciona um respiro (+2) e trava num máximo de 50 para não ficar gigante
            width = min(max_len + 2, 50)
            
            worksheet.set_column(i, i, width)
            worksheet.write(0, i, col, f_header)

    return output.getvalue()