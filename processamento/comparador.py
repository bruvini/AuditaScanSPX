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
        '/': ' ', '-': ' ', '.': ' ', ':': ' ', ';': ' '
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
        r'\bANGIOTOMOGRAFIA\b': 'ANGIOTOMO',
        r'\bANGIO TC\b': 'ANGIOTOMO',
    }
    
    for sigla, expansao in siglas.items():
        texto = re.sub(sigla, expansao, texto)

    return " ".join(texto.split())

def calcular_similaridade(texto_a, texto_b):
    if not texto_a or not texto_b: return 0.0
    return SequenceMatcher(None, texto_a, texto_b).ratio()

def comparar_procedimentos_robusto(proc_a, proc_b):
    """
    Compara dois procedimentos ignorando espaços e erros pequenos.
    Retorna True se forem equivalentes.
    """
    if not proc_a or not proc_b: return False
    
    # 1. Comparação Direta
    if proc_a == proc_b: return True
    
    # 2. Comparação Sem Espaços (Resolve "ANGIO TOMO" vs "ANGIOTOMO")
    norm_a = proc_a.replace(" ", "")
    norm_b = proc_b.replace(" ", "")
    
    # Verifica igualdade exata sem espaços
    if norm_a == norm_b: return True
    
    # Verifica continência sem espaços (ex: "ANGIOTOMOGRAFIA" in "ANGIOTOMOGRAFIAARTERIAL")
    if norm_a in norm_b or norm_b in norm_a: return True
    
    # 3. Interseção de Palavras
    set_a = set(proc_a.split())
    set_b = set(proc_b.split())
    intersecao = set_a.intersection(set_b)
    
    # Se tiver pelo menos 2 palavras iguais e não for genérico demais
    if len(intersecao) >= 2: return True 
    
    # 4. Similaridade Fuzzy
    if calcular_similaridade(proc_a, proc_b) > 0.8: return True
    if calcular_similaridade(norm_a, norm_b) > 0.85: return True
    
    return False

def verificar_divergencia_scan(row_excel, df_scans, paciente_norm, nasc_excel):
    if df_scans is None or df_scans.empty:
        return "NÃO", ["Solicitação física não digitalizada"]

    melhor_match = None
    maior_score = 0
    observacoes_match = []

    df_scans = df_scans.copy()
    if 'Pac_Norm' not in df_scans.columns:
        df_scans['Pac_Norm'] = df_scans['Paciente'].apply(padronizar_texto_avancado)
    
    for idx, scan in df_scans.iterrows():
        paciente_scan = scan['Pac_Norm']
        nasc_scan = scan['Nascimento']
        
        sim_nome = calcular_similaridade(paciente_norm, paciente_scan)
        match_nasc = (nasc_excel == nasc_scan)
        
        ocr_nome_fail = "NAO DETECTADO" in str(scan['Paciente']).upper()
        ocr_nasc_fail = "NAO DETECTADO" in str(scan['Nascimento']).upper() or len(str(scan['Nascimento'])) < 8

        score = 0
        obs_temp = []
        eh_candidato = False

        if sim_nome > 0.85: 
            score += 50
            if match_nasc:
                score += 50
                eh_candidato = True
            elif ocr_nasc_fail:
                score += 40
                obs_temp.append("Data Nasc. não detectada no PDF")
                eh_candidato = True
            else:
                score += 30
                obs_temp.append(f"Divergência DN (Planilha: {nasc_excel} / PDF: {nasc_scan})")
                eh_candidato = True

        elif match_nasc:
            score += 50
            if ocr_nome_fail:
                score += 40
                obs_temp.append("Nome não detectado no PDF")
                eh_candidato = True
            elif sim_nome > 0.6: 
                score += 35
                obs_temp.append(f"Divergência Nome (Planilha: {row_excel.get('Paciente', '')} / PDF: {scan.get('Paciente', '')})")
                eh_candidato = True

        elif ocr_nome_fail and ocr_nasc_fail:
            pass

        if eh_candidato:
            proc_excel = padronizar_texto_avancado(row_excel.get('Procedimento', ''))
            proc_scan = padronizar_texto_avancado(scan.get('Procedimento', ''))
            
            # Usa a nova função de comparação robusta
            if comparar_procedimentos_robusto(proc_excel, proc_scan):
                score += 20
            
            if score > maior_score:
                maior_score = score
                melhor_match = scan
                observacoes_match = obs_temp

    if melhor_match is not None:
        status = "SIM"
        if observacoes_match:
            status = "SIM (Ressalva)"
        return status, observacoes_match
    
    return "NÃO", ["Solicitação física não digitalizada"]

def realizar_conciliacao(df_excel, df_laudos, df_scans=None):
    if df_excel is None or df_excel.empty: return pd.DataFrame()
    
    resultados = []
    
    df_excel['Data_Str'] = pd.to_datetime(df_excel['Data']).dt.strftime('%d/%m/%Y')
    col_nasc_excel = 'D. Nascimento' if 'D. Nascimento' in df_excel.columns else 'Nascimento'
    df_excel['Nasc_Str'] = pd.to_datetime(df_excel[col_nasc_excel], errors='coerce').dt.strftime('%d/%m/%Y')

    for idx, row in df_excel.iterrows():
        paciente_ex_norm = padronizar_texto_avancado(row.get('Paciente', ''))
        nasc_ex = row.get('Nasc_Str', '')
        data_ex = row.get('Data_Str', '')
        proc_ex = padronizar_texto_avancado(row.get('Procedimento', ''))
        
        medico_original = row.get('Médico Solicitante', row.get('Médico', ''))
        if pd.isna(medico_original): medico_original = ""

        # --- 1. VERIFICAÇÃO DE LAUDOS ---
        laudo_status = "NÃO"
        laudo_obs = []
        
        if df_laudos is not None and not df_laudos.empty:
            candidatos_l = df_laudos[
                (df_laudos['Data Exame'] == data_ex) & 
                (df_laudos['Nascimento'] == nasc_ex)
            ].copy()
            
            candidatos_l['Pac_Norm'] = candidatos_l['Paciente'].apply(padronizar_texto_avancado)
            
            match_encontrado = False
            procedimentos_vistos = []

            for _, laudo in candidatos_l.iterrows():
                # Verifica Nome (Contém ou Similar)
                nome_laudo = laudo['Pac_Norm']
                if paciente_ex_norm in nome_laudo or nome_laudo in paciente_ex_norm or calcular_similaridade(paciente_ex_norm, nome_laudo) > 0.8:
                    
                    proc_laudo = padronizar_texto_avancado(laudo['Procedimento'])
                    procedimentos_vistos.append(laudo['Procedimento'])
                    
                    # Usa a função robusta para comparar laudos também
                    if comparar_procedimentos_robusto(proc_ex, proc_laudo):
                        match_encontrado = True
                        break 
            
            if match_encontrado:
                laudo_status = "SIM"
            elif not candidatos_l.empty:
                # Se achou paciente mas não procedimento, reporta o que achou
                procs_unicos = sorted(list(set(procedimentos_vistos)))
                laudo_obs.append(f"Divergência Procedimento. Laudo consta: {', '.join(procs_unicos)}")
            else:
                laudo_obs.append("Nenhum laudo encontrado nesta data/DN")

        # --- 2. VERIFICAÇÃO DE SCANS ---
        scan_status, scan_obs = verificar_divergencia_scan(row, df_scans, paciente_ex_norm, nasc_ex)

        resultados.append({
            "Data do Exame": row.get('Data', ''),
            "Paciente": row.get('Paciente', ''),
            "DN": row.get('Nasc_Str', ''),
            "Procedimento": row.get('Procedimento', ''),
            "Médico": medico_original,
            "Solicitação Física": scan_status,
            "Detalhe Scan": "; ".join(scan_obs),
            "Laudo Digital": laudo_status,
            "Detalhe Laudo": "; ".join(laudo_obs)
        })

    df_final = pd.DataFrame(resultados)
    
    if not df_final.empty:
        colunas_ordem = [
            "Data do Exame", "Paciente", "DN", "Procedimento", "Médico", 
            "Solicitação Física", "Detalhe Scan", 
            "Laudo Digital", "Detalhe Laudo"
        ]
        df_final = df_final[colunas_ordem]
        
    return df_final