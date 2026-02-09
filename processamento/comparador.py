import pandas as pd
import re
from difflib import SequenceMatcher

def padronizar_texto_avancado(texto):
    if not texto or pd.isna(texto): return ""
    texto = str(texto).upper().strip()
    
    substituicoes_char = {
        'Á': 'A', 'À': 'A', 'Â': 'A', 'Ã': 'A', 'Ä': 'A',
        'É': 'E', 'È': 'E', 'Ê': 'E', 'Ë': 'E',
        'Í': 'I', 'Ì': 'I', 'Î': 'I', 'Ï': 'I',
        'Ó': 'O', 'Ò': 'O', 'Ô': 'O', 'Õ': 'O', 'Ö': 'O',
        'Ú': 'U', 'Ù': 'U', 'Û': 'U', 'Ü': 'U',
        'Ç': 'C', 'Ñ': 'N',
        '/': ' ', '-': ' ', '.': ' ' 
    }
    for original, novo in substituicoes_char.items():
        texto = texto.replace(original, novo)
    
    texto = re.sub(r'[^A-Z0-9\s]', ' ', texto)
    
    siglas = {
        r'\bTC\b': 'TOMOGRAFIA',
        r'\bTOMO\b': 'TOMOGRAFIA',
        r'\bRM\b': 'RESSONANCIA',
        r'\bRX\b': 'RAIO X',
        r'\bUSG\b': 'ULTRASSONOGRAFIA',
        r'\bUS\b': 'ULTRASSONOGRAFIA',
        r'\bECO\b': 'ULTRASSONOGRAFIA',
    }
    
    for sigla, expansao in siglas.items():
        texto = re.sub(sigla, expansao, texto)

    return " ".join(texto.split())

def calcular_similaridade(texto_a, texto_b):
    return SequenceMatcher(None, texto_a, texto_b).ratio()

def realizar_conciliacao(df_excel, df_laudos, df_scans=None):
    if df_excel is None or df_excel.empty: return pd.DataFrame()
    
    resultados = []
    
    # Preparação de datas
    df_excel['Data_Str'] = pd.to_datetime(df_excel['Data']).dt.strftime('%d/%m/%Y')
    col_nasc_excel = 'D. Nascimento' if 'D. Nascimento' in df_excel.columns else 'Nascimento'
    df_excel['Nasc_Str'] = pd.to_datetime(df_excel[col_nasc_excel], errors='coerce').dt.strftime('%d/%m/%Y')

    for idx, row in df_excel.iterrows():
        # Dados para COMPARAÇÃO (Normalizados)
        paciente_ex = padronizar_texto_avancado(row['Paciente'])
        nasc_ex = row['Nasc_Str']
        data_ex = row['Data_Str']
        proc_ex = padronizar_texto_avancado(row['Procedimento'])
        
        # Dados para EXIBIÇÃO (Originais)
        # Tenta pegar 'Médico Solicitante', se não tiver tenta 'Médico', se não tiver fica vazio.
        medico_original = row.get('Médico Solicitante', row.get('Médico', ''))
        if pd.isna(medico_original): medico_original = ""

        # -----------------------------------------------------------
        # 1. VERIFICAÇÃO DE LAUDOS
        # -----------------------------------------------------------
        laudo_status = "NÃO"
        laudo_obs = []
        
        if df_laudos is not None and not df_laudos.empty:
            candidatos_l = df_laudos[
                (df_laudos['Data Exame'] == data_ex) & 
                (df_laudos['Nascimento'] == nasc_ex)
            ].copy()
            
            candidatos_l['Pac_Norm'] = candidatos_l['Paciente'].apply(padronizar_texto_avancado)
            candidatos_l = candidatos_l[candidatos_l['Pac_Norm'].apply(lambda x: x in paciente_ex or paciente_ex in x)]

            if candidatos_l.empty:
                laudo_obs.append("Nenhum laudo encontrado nesta data")
            else:
                match_encontrado = False
                procedimentos_vistos = []

                for _, laudo in candidatos_l.iterrows():
                    proc_laudo = padronizar_texto_avancado(laudo['Procedimento'])
                    procedimentos_vistos.append(laudo['Procedimento'])
                    
                    # Lógica de Comparação (Match Exato / Subset / Similaridade)
                    set_ex = set(proc_ex.split())
                    set_la = set(proc_laudo.split())
                    intersecao = set_ex.intersection(set_la)
                    is_subset = set_la.issubset(set_ex) or set_ex.issubset(set_la)

                    match_proc = False
                    if proc_ex == proc_laudo: match_proc = True
                    elif len(intersecao) >= 2 and is_subset: match_proc = True
                    elif len(intersecao) / len(set_ex) >= 0.8: match_proc = True
                    elif calcular_similaridade(proc_ex, proc_laudo) > 0.8: match_proc = True

                    if match_proc:
                        match_encontrado = True
                        break 
                
                if match_encontrado:
                    laudo_status = "SIM"
                    laudo_obs = [] 
                else:
                    procs_unicos = sorted(list(set(procedimentos_vistos)))
                    laudo_obs.append(f"Divergência. Encontrado: {', '.join(procs_unicos)}")

        # -----------------------------------------------------------
        # 2. VERIFICAÇÃO DE SCANS
        # -----------------------------------------------------------
        scan_status = "NÃO"
        scan_obs = []
        
        if df_scans is not None and not df_scans.empty:
            candidatos_s = df_scans[df_scans['Nascimento'] == nasc_ex].copy()
            candidatos_s['Pac_Norm'] = candidatos_s['Paciente'].apply(padronizar_texto_avancado)
            candidatos_s = candidatos_s[candidatos_s['Pac_Norm'].apply(lambda x: x in paciente_ex or paciente_ex in x)]
            
            if candidatos_s.empty:
                scan_obs.append("Solicitação física não digitalizada")
            else:
                match_scan_encontrado = False
                procs_scan_vistos = []
                
                for _, scan in candidatos_s.iterrows():
                    proc_scan = padronizar_texto_avancado(scan['Procedimento'])
                    procs_scan_vistos.append(scan['Procedimento'])
                    
                    set_ex = set(proc_ex.split())
                    set_sc = set(proc_scan.split())
                    intersecao = set_ex.intersection(set_sc)
                    is_subset = set_sc.issubset(set_ex) or set_ex.issubset(set_sc)

                    if len(intersecao) >= 2 and is_subset: match_scan_encontrado = True
                    elif calcular_similaridade(proc_ex, proc_scan) > 0.75: match_scan_encontrado = True
                    elif len(intersecao) >= 2: match_scan_encontrado = True
                    
                    if match_scan_encontrado: break

                if match_scan_encontrado:
                    scan_status = "SIM"
                    scan_obs = []
                else:
                    procs_unicos_s = sorted(list(set(procs_scan_vistos)))
                    scan_obs.append(f"Divergência. No scan consta: {', '.join(procs_unicos_s)}")

        # -----------------------------------------------------------
        # MONTAGEM DA LINHA FINAL COM NOMES DAS COLUNAS ATUALIZADOS
        # -----------------------------------------------------------
        resultados.append({
            "Data do Exame": row['Data'], # Mantém objeto Data para ordenação
            "Paciente": row['Paciente'],
            "DN": row['Nasc_Str'], # Já formatado DD/MM/YYYY
            "Procedimento": row['Procedimento'],
            "Médico": medico_original,
            "Solicitação Física": scan_status,
            "Detalhe Scan": "; ".join(scan_obs),
            "Laudo Digital": laudo_status,
            "Detalhe Laudo": "; ".join(laudo_obs)
        })

    # Cria o DataFrame
    df_final = pd.DataFrame(resultados)
    
    # FORÇA A ORDEM EXATA DAS COLUNAS
    if not df_final.empty:
        colunas_ordem = [
            "Data do Exame", 
            "Paciente", 
            "DN", 
            "Procedimento", 
            "Médico", 
            "Solicitação Física", 
            "Detalhe Scan", 
            "Laudo Digital", 
            "Detalhe Laudo"
        ]
        # Garante que só retorna essas colunas e nessa ordem
        df_final = df_final[colunas_ordem]
        
    return df_final