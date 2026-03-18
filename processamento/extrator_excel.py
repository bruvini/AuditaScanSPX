import pandas as pd

def carregar_dados_excel(caminho_arquivo):
    # Lemos o arquivo Excel
    df = pd.read_excel(caminho_arquivo)
    
    # Limpamos os nomes das colunas (removemos espaços extras que podem causar KeyError)
    df.columns = df.columns.astype(str).str.strip()

    # Padronizamos os nomes das colunas para facilitar o acesso
    # Removendo espaços em branco extras nos nomes dos pacientes
    if 'Paciente' in df.columns:
        df['Paciente'] = df['Paciente'].str.strip().str.upper()
    
    # Convertendo colunas de data para o formato datetime do Python
    # O formato M/dd/yyyy é especificado para evitar erros de interpretação
    if 'Data' in df.columns:
        df['Data'] = pd.to_datetime(df['Data'], format='%m/%d/%Y', errors='coerce')
    if 'D. Nascimento' in df.columns:
        df['D. Nascimento'] = pd.to_datetime(df['D. Nascimento'], format='%m/%d/%Y', errors='coerce')
    
    return df

def analisar_qualidade_dados(df):
    metricas = {
        "total_registros": len(df),
        "pacientes_unicos": df['Paciente'].nunique() if 'Paciente' in df.columns else 0,
        "procedimentos_unicos": df['Procedimento'].nunique() if 'Procedimento' in df.columns else 0,
        "linhas_com_nulos": df.isnull().any(axis=1).sum(),
        "exames_por_data": df['Data'].value_counts().sort_index() if 'Data' in df.columns else pd.Series(dtype=int)
    }
    return metricas