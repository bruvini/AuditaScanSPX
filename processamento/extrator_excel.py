import pandas as pd

def carregar_dados_excel(caminho_arquivo):
    # Lemos o arquivo Excel
    df = pd.read_excel(caminho_arquivo)
    
    # Padronizamos os nomes das colunas para facilitar o acesso
    # Removendo espaços em branco extras nos nomes dos pacientes
    df['Paciente'] = df['Paciente'].str.strip().str.upper()
    
    # Convertendo colunas de data para o formato datetime do Python
    # O formato M/dd/yyyy é especificado para evitar erros de interpretação
    df['Data'] = pd.to_datetime(df['Data'], format='%m/%d/%Y', errors='coerce')
    df['D. Nascimento'] = pd.to_datetime(df['D. Nascimento'], format='%m/%d/%Y', errors='coerce')
    
    return df

def analisar_qualidade_dados(df):
    metricas = {
        "total_registros": len(df),
        "pacientes_unicos": df['Paciente'].nunique(),
        "procedimentos_unicos": df['Procedimento'].nunique(),
        "linhas_com_nulos": df.isnull().any(axis=1).sum(),
        "exames_por_data": df['Data'].value_counts().sort_index()
    }
    return metricas