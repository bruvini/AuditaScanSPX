import pandas as pd
from io import BytesIO

def gerar_excel_colorido(df):
    """
    Gera um Excel ordenado por criticidade (Vermelho -> Amarelo -> Verde),
    com coluna de revisão na coluna J e coloração restrita ao intervalo A:J.
    """
    if df is None or df.empty:
        return None

    df_export = df.copy()

    # --- 1. LÓGICA DE ORDENAÇÃO POR PRIORIDADE ---
    # Criamos um peso para ordenar: Vermelho (0), Amarelo (1), Verde (2)
    def definir_prioridade(row):
        s = str(row.get("Solicitação Física", "")).strip().upper()
        l = str(row.get("Laudo Digital", "")).strip().upper()
        
        if s == "SIM" and l == "SIM":
            return 2 # Verde (Fim)
        if s == "NÃO" and l == "NÃO":
            return 0 # Vermelho (Início)
        return 1     # Amarelo (Meio)

    df_export['_prioridade'] = df_export.apply(definir_prioridade, axis=1)
    # Ordena pelo peso e depois por Data do Exame
    df_export = df_export.sort_values(by=['_prioridade', 'Data do Exame'], ascending=[True, True])
    
    # Remove a coluna temporária após ordenar
    df_export = df_export.drop(columns=['_prioridade'])

    # --- 2. ADIÇÃO DA COLUNA J (REVISÃO) ---
    df_export["Observações de Revisão"] = "" # Coluna J

    # Tratamento de Datas para exibição
    if "Data do Exame" in df_export.columns:
        df_export["Data do Exame"] = pd.to_datetime(df_export["Data do Exame"]).dt.date

    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Auditoria')
        workbook  = writer.book
        worksheet = writer.sheets['Auditoria']

        # --- ESTILOS ---
        fmt_data = 'dd/mm/yyyy'
        style_base = {'border': 1, 'align': 'left', 'valign': 'vcenter'}
        
        f_verde    = workbook.add_format({**style_base, 'bg_color': '#C6EFCE', 'font_color': '#006100'})
        f_amarelo  = workbook.add_format({**style_base, 'bg_color': '#FFEB9C', 'font_color': '#9C5700'})
        f_vermelho = workbook.add_format({**style_base, 'bg_color': '#FFC7CE', 'font_color': '#9C0006'})
        
        # Formato específico para a coluna de Data para não perder o dd/mm/yyyy
        f_v_data = workbook.add_format({**style_base, 'bg_color': '#C6EFCE', 'font_color': '#006100', 'num_format': fmt_data})
        f_a_data = workbook.add_format({**style_base, 'bg_color': '#FFEB9C', 'font_color': '#9C5700', 'num_format': fmt_data})
        f_r_data = workbook.add_format({**style_base, 'bg_color': '#FFC7CE', 'font_color': '#9C0006', 'num_format': fmt_data})

        f_header = workbook.add_format({
            'bold': True, 'bg_color': '#4472C4', 'font_color': 'white',
            'border': 1, 'align': 'center', 'valign': 'vcenter'
        })

        # --- IDENTIFICAÇÃO DE COLUNAS ---
        idx_solic = df_export.columns.get_loc("Solicitação Física")
        idx_laudo = df_export.columns.get_loc("Laudo Digital")
        last_col  = df_export.columns.get_loc("Observações de Revisão") # Coluna J (9)

        # --- LÓGICA DE COLORAÇÃO RESTRITA (A:J) ---
        for row_num in range(len(df_export)):
            s = str(df_export.iloc[row_num, idx_solic]).strip().upper()
            l = str(df_export.iloc[row_num, idx_laudo]).strip().upper()
            
            # Seleção do formato da linha e do formato específico da célula de data
            if s == "SIM" and l == "SIM":
                fmt, fmt_dt = f_verde, f_v_data
            elif s == "NÃO" and l == "NÃO":
                fmt, fmt_dt = f_vermelho, f_r_data
            else:
                fmt, fmt_dt = f_amarelo, f_a_data
            
            # Pintamos célula por célula da coluna A até J para não vazar a cor para o resto do Excel
            for col_num in range(last_col + 1):
                val = df_export.iloc[row_num, col_num]
                # Se for a primeira coluna (Data), aplica formato de data
                f_final = fmt_dt if col_num == 0 else fmt
                
                # worksheet.write(linha, coluna, valor, formato)
                # row_num + 1 para pular o cabeçalho
                worksheet.write(row_num + 1, col_num, val, f_final)

        # --- AJUSTE DE LAYOUT ---
        for i, col in enumerate(df_export.columns):
            max_len = max(
                df_export[col].astype(str).map(len).max(),
                len(str(col))
            )
            # A coluna de observações ganha um espaço maior por padrão
            width = 40 if i == last_col else min(max_len + 2, 50)
            
            worksheet.set_column(i, i, width)
            worksheet.write(0, i, col, f_header)

    return output.getvalue()