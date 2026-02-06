import pandas as pd
import re

def normalizar_texto(texto):
    if not texto or pd.isna(texto): return ""
    texto = str(texto).upper()
    substituicoes = {
        'Á': 'A', 'À': 'A', 'Â': 'A', 'Ã': 'A', 'É': 'E', 'È': 'E', 'Ê': 'E',
        'Í': 'I', 'Ì': 'I', 'Î': 'I', 'Ó': 'O', 'Ò': 'O', 'Ô': 'O', 'Õ': 'O',
        'Ú': 'U', 'Ù': 'U', 'Û': 'U', 'Ç': 'C'
    }
    for original, novo in substituicoes.items():
        texto = texto.replace(original, novo)
    texto = re.sub(r'[^A-Z0-9]', ' ', texto)
    return " ".join(texto.split())

def verificar_keywords(texto_referencia, texto_busca):
    """
    Verifica se todas as palavras significativas de 'texto_busca' 
    estão presentes em 'texto_referencia'.
    """
    # Pegamos apenas palavras com mais de 1 letra (evita 'DE', 'O', 'A')
    palavras_busca = [p for p in texto_busca.split() if len(p) > 1]
    if not palavras_busca: return False
    
    # Se todas as palavras da busca estiverem na referência, retorna True
    return all(p in texto_referencia for p in palavras_busca)

def realizar_conciliacao(df_excel, df_pdf):
    if df_pdf.empty: return pd.DataFrame()

    datas_no_pdf = df_pdf['Data Exame'].unique().tolist()
    df_excel_copia = df_excel.copy()
    df_excel_copia['Data_Formatada'] = df_excel_copia['Data'].dt.strftime('%d/%m/%Y')
    df_filtrado = df_excel_copia[df_excel_copia['Data_Formatada'].isin(datas_no_pdf)].copy()
    
    resultados = []
    
    for _, linha in df_filtrado.iterrows():
        paciente_ex = normalizar_texto(linha['Paciente'])
        nasc_ex = linha['D. Nascimento'].strftime('%d/%m/%Y') if not pd.isna(linha['D. Nascimento']) else ""
        data_ex_ex = linha['Data_Formatada']
        proc_ex = normalizar_texto(linha['Procedimento'])
        medico_ex = normalizar_texto(linha.get('Médico Solicitante', linha.get('Médico', "")))
        
        # Busca flexível por Paciente + Nascimento + Data
        matches_paciente = df_pdf[
            df_pdf.apply(lambda x: 
                (paciente_ex in normalizar_texto(x['Paciente']) or 
                 normalizar_texto(x['Paciente']) in paciente_ex) and 
                (x['Nascimento'] == nasc_ex) and
                (x['Data Exame'] == data_ex_ex), axis=1)
        ]
        
        status = "❌ NÃO ENCONTRADO"
        obs = ""
        
        if not matches_paciente.empty:
            sucesso_exame = False
            for _, laudo in matches_paciente.iterrows():
                proc_pdf = normalizar_texto(laudo['Procedimento'])
                medico_pdf = normalizar_texto(laudo['Médico'])
                
                # EVOLUÇÃO: Usamos a verificação por palavras-chave (Keywords)
                # Isso resolve o caso do "MARTINS" no meio do procedimento
                bate_proc = verificar_keywords(proc_pdf, proc_ex) or verificar_keywords(proc_ex, proc_pdf)
                bate_medico = (medico_ex in medico_pdf or medico_pdf in medico_ex)
                
                if bate_proc and bate_medico:
                    sucesso_exame = True
                    break
                elif bate_proc and not bate_medico:
                    obs = f"Divergência de Médico: Planilha({medico_ex}) vs PDF({medico_pdf})"
                elif not bate_proc and bate_medico:
                    obs = f"Divergência de Exame: Planilha({proc_ex}) vs PDF({proc_pdf})"
            
            if sucesso_exame:
                status = "✅ OK"
                obs = ""
            else:
                status = "⚠️ DIVERGÊNCIA"
                if not obs: obs = "Dados de procedimento ou médico não conferem."

        res = linha.to_dict()
        res['Status Auditoria'] = status
        res['Observação'] = obs
        res.pop('Data_Formatada', None)
        resultados.append(res)
        
    return pd.DataFrame(resultados)