import pandas as pd
from io import BytesIO

def gerar_excel_colorido(df):
    """
    Gera um Excel com linhas coloridas, datas formatadas e colunas auto-ajustadas.
    """
    # Criamos uma cópia para não afetar o DataFrame original da sessão
    df_export = df.copy()
    
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_export.to_excel(writer, index=False, sheet_name='Auditoria')
        
        workbook  = writer.book
        worksheet = writer.sheets['Auditoria']

        # 1. DEFINIÇÃO DE FORMATOS
        # Formatos de cor com a data embutida
        fmt_data = 'dd/mm/yyyy'
        
        # OK - Verde Claro
        f_ok = workbook.add_format({'bg_color': '#C6EFCE', 'font_color': '#006100', 'num_format': fmt_data, 'border': 1})
        # Divergência - Amarelo Claro
        f_div = workbook.add_format({'bg_color': '#FFEB9C', 'font_color': '#9C5700', 'num_format': fmt_data, 'border': 1})
        # Erro - Vermelho Claro
        f_err = workbook.add_format({'bg_color': '#FFC7CE', 'font_color': '#9C0006', 'num_format': fmt_data, 'border': 1})
        
        # Formato apenas para o cabeçalho (Negrito e cinza claro)
        f_header = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1})

        # 2. APLICANDO CORES E FORMATO DE DATA NAS LINHAS
        idx_status = df_export.columns.get_loc("Status Auditoria")

        for row_num in range(len(df_export)):
            status = str(df_export.iloc[row_num, idx_status])
            
            # Escolhe o formato baseado no status
            if '✅' in status:
                fmt_atual = f_ok
            elif '⚠️' in status:
                fmt_atual = f_div
            else:
                fmt_atual = f_err
                
            # Aplica o formato na linha inteira (da coluna A até a última)
            # O ExcelWriter começa a contar do 1 para dados (0 é o header)
            worksheet.set_row(row_num + 1, None, fmt_atual)

        # 3. AUTO-AJUSTE DE LARGURA DAS COLUNAS
        # Iteramos por cada coluna para achar o tamanho máximo do conteúdo
        for i, col in enumerate(df_export.columns):
            # Comprimento do nome da coluna
            column_len = len(str(col))
            # Comprimento do maior item na coluna (máximo de 50 para não ficar gigante)
            max_val_len = df_export[col].astype(str).map(len).max()
            
            width = max(column_len, max_val_len) + 2 # +2 de margem
            if width > 60: width = 60 # Limite para a coluna Observação não esticar infinito
            
            worksheet.set_column(i, i, width)
            
        # Reaplica o formato de cabeçalho
        for col_num, value in enumerate(df_export.columns.values):
            worksheet.write(0, col_num, value, f_header)

    return output.getvalue()