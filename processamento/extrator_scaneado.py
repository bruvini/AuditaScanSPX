import pdfplumber
import re
from difflib import SequenceMatcher

def reparar_texto_fragmentado(texto):
    if not texto: return ""
    texto = re.sub(r'\b([A-Z])\s+(?=[A-Z]\b)', r'\1', texto)
    texto = re.sub(r'\s+', ' ', texto).strip()
    return texto

def limpar_texto_ocr(texto):
    if not texto: return ""
    texto = texto.replace('\n', ' ')
    texto = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', texto)
    return re.sub(r'\s+', ' ', texto).strip()

def similaridade(a, b):
    return SequenceMatcher(None, a, b).ratio()

def extrair_data_flexivel(texto, padrao_label, caracteres_busca=50):
    match_label = re.search(padrao_label, texto, re.IGNORECASE)
    if not match_label:
        return "NÃO DETECTADO"
    
    inicio = match_label.end()
    trecho_sujo = texto[inicio : inicio + caracteres_busca]
    
    mapa_ocr = {
        'O': '0', 'D': '0', 'Q': '0', 'U': '0',
        'L': '1', 'I': '1', '|': '1', 'l': '1', '/': '1', '\\': '1',
        'Z': '2', 'E': '3', 'A': '4', 'S': '5',
        'G': '6', 'b': '6', 'T': '7', 'B': '8'
    }
    
    trecho_limpo = trecho_sujo.upper().replace(" ", "")
    lista_chars = []
    for char in trecho_limpo:
        if char.isdigit():
            lista_chars.append(char)
        elif char in ['/', '.', '-']: 
            lista_chars.append('/')
        elif char in mapa_ocr:
            lista_chars.append(mapa_ocr[char])
            
    texto_reconstruido = "".join(lista_chars)
    match_data = re.search(r'(\d{2})/(\d{2})/(\d{4})', texto_reconstruido)
    if match_data:
        return f"{match_data.group(1)}/{match_data.group(2)}/{match_data.group(3)}"
        
    return "NÃO DETECTADO"

def limpar_nome_paciente(nome_bruto):
    if not nome_bruto: return "NÃO DETECTADO"
    
    nome_reparado = reparar_texto_fragmentado(nome_bruto)
    texto_upper = nome_reparado.upper()
    
    marcadores_fim = [
        "4-PRONT", "PRONTUÁRIO", "PRONTUARIO", "PRONT",
        "5-CNS", "5- CNS", "CNS", "CARTÃO", 
        "6-DATA", "DATA NASC", "DT NASC",
        "7-SEXO", "SEXO", 
        "8-RAÇA", "RACA", "COR",
        "9-MÃE", "MAE", 
        "10-FONE", "FONE", 
        "CF:S", "COMENTOS", "14-PRONT", "1Ï~", "1DSCILINO"
    ]
    
    menor_indice = len(texto_upper)
    for marcador in marcadores_fim:
        idx = texto_upper.find(marcador)
        if idx != -1 and idx < menor_indice:
            menor_indice = idx
            
    nome_limpo = nome_reparado[:menor_indice].strip()
    nome_limpo = re.sub(r'^.*(?:IDENTIFICAÇÃO|ESTABELECIMENTO|SOLICITANTE\)|SAÚDE)\s*', '', nome_limpo, flags=re.IGNORECASE)

    match_numero = re.search(r'\d{3,}', nome_limpo)
    if match_numero:
        nome_limpo = nome_limpo[:match_numero.start()].strip()

    nome_limpo = re.sub(r'^[\d\W_]+', '', nome_limpo)
    nome_limpo = re.sub(r'[\d\W_]+$', '', nome_limpo)
    
    if len(nome_limpo) < 3:
        return "NÃO DETECTADO"
        
    return nome_limpo.upper()

def limpar_nome_medico(nome):
    if not nome: return ""
    nome = re.split(r'(?:-|CRM|Data|Assinatura|CNES|CPF|\d{2}/\d{2}|:)', nome, flags=re.IGNORECASE)[0]
    nome = re.sub(r'^[\d\W_]+', '', nome)
    nome = re.sub(r'[\\/|()0-9]', '', nome)
    nome = nome.strip().upper()
    if len(nome) < 3 or len(set(nome)) == 1: return ""
    return nome

def validar_e_limpar_procedimento(texto):
    if not texto: return None
    
    limpo = texto.upper().strip()
    
    # --- 1. CORTE DE RODAPÉ (CRÍTICO PARA "A GTC") ---
    # Remove qualquer coisa a partir de padrões estranhos de rodapé
    padroes_rodape = [
        r'\s*Q(?:td|TD).*$',          # Padrão normal de Qtd
        r'G\s*O\s*N\s*T\s*O.*',       # Padrão específico citado "G O N T O"
        r'A\s*G\s*T\s*C.*',           # Padrão específico "A G T C"
        r'0\s*5\s*/\s*G.*'            # Padrão de final de linha estranho
    ]
    for padrao in padroes_rodape:
        limpo = re.sub(padrao, '', limpo, flags=re.IGNORECASE).strip()

    # --- 2. REMOÇÃO DE CABEÇALHOS ---
    padroes_lixo_inicio = [
        r'^PROCEDIMENTO\s*SOLICITADO\s*[-–]?\s*',
        r'^PROCEDIMENTO\s*[-–]?\s*',
        r'^SOLICITADO\s*[-–]?\s*',
        r'^AGTC\s*',
        r'^\d+\s*[-–]\s*'
    ]
    for padrao in padroes_lixo_inicio:
        limpo = re.sub(padrao, '', limpo).strip()

    # --- 3. LISTA NEGRA RÍGIDA ---
    termos_proibidos_exatos = [
        "SOLICITADO", "PROCEDIMENTO", "QTD", "QTD PROCEDIMENTO", 
        "AGTC", "A GTC", "MUNICIPIO", "JOINVILLE", 
        "ESTABELECIMENTO", "SAUDE", "SUS", "PAGINA",
        "PROCEDIMENTO SOLICITADO", "MUNICIPIO JOINVILLE",
        "PROCEDIMENTO PROCEDIMENTO", "A GTC PROCEDIMENTO"
    ]
    
    if limpo in termos_proibidos_exatos:
        return None

    # --- 4. LISTA NEGRA "CONTÉM" ---
    palavras_contaminadas = ["JOINVILLE", "MUNICIPIO", "AGTC", "ESTABELECIMENTO", "AUTORIZAÇÃO", "GTC"]
    for palavra in palavras_contaminadas:
        # Só descarta se a palavra for uma parte significativa ou solta, para não descartar procedimentos legítimos
        if f" {palavra} " in f" {limpo} ": 
            return None
        
    if "RUA" in limpo or "BAIRRO" in limpo or "CEP" in limpo:
        return None
        
    if len(limpo) < 5: # Aumentei régua mínima para 5 letras
        return None
        
    return limpo

def normalizar_para_comparacao(texto):
    """Remove espaços e pontuação para comparar 'TOMOGRAFIA' com 'M O GRAFIA'"""
    return re.sub(r'[\W_]+', '', texto.upper())

def extrair_procedimentos_complexos(texto):
    procedimentos_encontrados = []
    
    # --- ESTRATÉGIA 1: Busca por CÓDIGO (Confiança Alta) ---
    regex_codigo = r"((?:\d\s*){7,15})\s*[-–]?\s*([^\d]+?)(?=\s*Q(?:td|TD)|\s*JUSTIFICATIVA|\s*CID)"
    matches_codigo = re.findall(regex_codigo, texto, re.IGNORECASE)
    
    for cod_sujo, desc in matches_codigo:
        cod_limpo = re.sub(r'\s+', '', cod_sujo)
        desc_validada = validar_e_limpar_procedimento(desc)
        
        if desc_validada and len(cod_limpo) >= 7:
            procedimentos_encontrados.append((cod_limpo, desc_validada))

    # --- ESTRATÉGIA 2: Busca por RÓTULO (Fallback) ---
    # Só adiciona se NÃO for duplicata
    regex_texto = r"(?:[a-zA-Z\s]{1,20})[tT]\s*[oO]\s*[-–]?\s*([A-Z\s/ÁÉÍÓÚÇÃÕ\-\(\)]{5,150}?)(?=\s*Q(?:td|TD))"
    matches_texto = re.findall(regex_texto, texto, re.IGNORECASE)
    
    for desc in matches_texto:
        desc_validada = validar_e_limpar_procedimento(desc)
        
        if desc_validada:
            # --- VERIFICAÇÃO DE DUPLICIDADE ROBUSTA ---
            # Normaliza tudo (remove espaços) para comparar "TOMOGRAFIA" com "MOGRAFIA"
            novo_norm = normalizar_para_comparacao(desc_validada)
            duplicado = False
            
            for _, existente in procedimentos_encontrados:
                existente_norm = normalizar_para_comparacao(existente)
                
                # 1. Checa substring (resolvendo "MOGRAFIA" dentro de "TOMOGRAFIA")
                if novo_norm in existente_norm:
                    duplicado = True; break
                
                # 2. Checa se o existente está contido no novo (às vezes o novo pegou mais texto)
                # Nesse caso, ignoramos o novo pois a Estratégia 1 (com código) costuma ser mais precisa no corte
                if existente_norm in novo_norm:
                    duplicado = True; break
                    
                # 3. Similaridade alta
                if similaridade(novo_norm, existente_norm) > 0.75:
                    duplicado = True; break
            
            if not duplicado:
                procedimentos_encontrados.append(("", desc_validada))

    return procedimentos_encontrados

def extrair_dados_solicitacao(caminho_pdf):
    solicitacoes = []
    
    with pdfplumber.open(caminho_pdf) as pdf:
        for pagina in pdf.pages:
            texto_bruto = pagina.extract_text()
            if not texto_bruto: continue
            
            texto = limpar_texto_ocr(texto_bruto)
            
            # --- 1. PACIENTE ---
            paciente = "NÃO DETECTADO"
            padrao_paciente = r"(?:3\s*[-–._]?\s*)?P\s*a\s*c\s*i\s*e\s*n\s*t\s*e\s+(.{5,100})"
            match_pac = re.search(padrao_paciente, texto, re.IGNORECASE)
            
            if match_pac:
                paciente = limpar_nome_paciente(match_pac.group(1))
            else:
                padrao_resgate = r"(.{10,120}?)\s+(?:5\s*-\s*CNS|CNS\s*\d|6\s*-\s*Data)"
                match_resgate = re.search(padrao_resgate, texto, re.IGNORECASE)
                if match_resgate:
                    candidato = match_resgate.group(1).strip()
                    if "SOLICITANTE" in candidato.upper():
                        candidato = re.split(r'SOLICITANTE\)', candidato, flags=re.IGNORECASE)[-1]
                    elif "SAÚDE" in candidato.upper():
                        candidato = re.split(r'SAÚDE', candidato, flags=re.IGNORECASE)[-1]
                    paciente = limpar_nome_paciente(candidato)

            # --- 2. NASCIMENTO ---
            label_nasc = r"(?:6\s*[-–]\s*)?D\s*a\s*t\s*a\s*n\s*a\s*s\s*c"
            nascimento = extrair_data_flexivel(texto, label_nasc)
            
            # --- 3. DATA SOLICITAÇÃO ---
            label_sol = r"D\s*a\s*t\s*a\s*s\s*o\s*l"
            data_solicitacao = extrair_data_flexivel(texto, label_sol)
            
            if data_solicitacao == "NÃO DETECTADO":
                ancoras_resgate = [
                    r"C\s*i\s*d\s*c\s*a\s*u\s*s\s*a\s*s",
                    r"N\s*ú\s*m\s*e\s*r\s*o\s*d\s*o\s*c",
                    r"C\s*N\s*S",
                    r"A\s*U\s*T\s*O\s*R\s*I\s*Z\s*A"
                ]
                for ancora in ancoras_resgate:
                    dt_candidata = extrair_data_flexivel(texto, ancora, caracteres_busca=80)
                    if dt_candidata != "NÃO DETECTADO" and dt_candidata != nascimento:
                        data_solicitacao = dt_candidata
                        break

            # --- 4. MÉDICOS ---
            candidatos_medicos = []
            
            match_solic = re.search(r"S\s*o\s*l\s*i\s*c\s*i\s*t\s*a\s*n\s*t\s*e\s+(.*?)(?:\s-\s|CRM|Data|CNES|CPF|\d{2}/\d{2})", texto, re.IGNORECASE)
            if match_solic:
                med_limpo = limpar_nome_medico(match_solic.group(1))
                if med_limpo: candidatos_medicos.append(med_limpo)
                
            match_resp = re.search(r"R\s*e\s*s\s*p\s*o\s*n\s*s\s*á\s*v\s*e\s*l\s*.*?\s*d\s*o\s*c\s*u\s*m\s*e\s*n\s*t\s*o\s+(.*?)(?:\s-\s|CRM|Data|:)", texto, re.IGNORECASE)
            if match_resp:
                med_limpo = limpar_nome_medico(match_resp.group(1))
                if med_limpo: candidatos_medicos.append(med_limpo)
            
            medicos_finais = []
            for med in candidatos_medicos:
                eh_novo = True
                for existente in medicos_finais:
                    if similaridade(med, existente) > 0.85 or med in existente or existente in med:
                        eh_novo = False
                        break
                if eh_novo:
                    medicos_finais.append(med)
            
            str_medico = " / ".join(medicos_finais) if medicos_finais else "NÃO DETECTADO"

            # --- 5. PROCEDIMENTOS ---
            procedimentos_encontrados = extrair_procedimentos_complexos(texto)
            
            if procedimentos_encontrados:
                for cod, nome_proc in procedimentos_encontrados:
                    solicitacoes.append({
                        'Paciente': paciente,
                        'Nascimento': nascimento,
                        'Data Solicitação': data_solicitacao,
                        'Médico Solicitante': str_medico,
                        'Procedimento': nome_proc,
                        'Código': cod
                    })
            else:
                solicitacoes.append({
                    'Paciente': paciente,
                    'Nascimento': nascimento,
                    'Data Solicitação': data_solicitacao,
                    'Médico Solicitante': str_medico,
                    'Procedimento': "NÃO ENCONTRADO (OCR Falhou)",
                    'Código': ""
                })

    return solicitacoes