import pdfplumber
import re

def limpar_texto(texto):
    """
    Remove quebras de linha e excesso de espaços, 
    ajudando a lidar com textos 'espaçados' (M é d i c o).
    """
    if not texto: return ""
    # Remove quebras de linha e tabs
    texto = texto.replace('\n', ' ').replace('\t', ' ')
    # Se o texto estiver com letras separadas (ex: M é d i c o), 
    # este regex tenta unir letras isoladas, mas é arriscado. 
    # Vamos focar em reduzir espaços múltiplos primeiro.
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()

def extrair_dados_cabecalho(texto_pagina):
    texto = limpar_texto(texto_pagina)
    dados = {}
    
    # Lista de padrões mais flexíveis (ignora case e aceita variações)
    # Usamos o prefixo (?i) para case-insensitive
    padroes = {
        'paciente': r"(?i)Nome:\s*(.*?)\s*Data\s*do\s*Laudo:",
        'nascimento': r"(?i)Data\s*Nascimento:\s*(\d{2}/\d{2}/\d{4})",
        'data_exame': r"(?i)Data\s*do\s*Exame:\s*(\d{2}/\d{2}/\d{4})",
        'medico': r"(?i)M\s*é\s*d\s*i\s*c\s*o\s*S\s*o\s*l\s*i\s*c\s*i\s*t\s*a\s*n\s*t\s*e:\s*(.*?)\s*(?:Estudo:|Idade:)",
        'procedimento': r"(?i)Estudo:\s*(.*?)\s*(?:SUS:|Idade:|Atendimento:)",
        'atendimento': r"(?i)Atendimento:\s*(\d+)"
    }
    
    for chave, padrao in padroes.items():
        match = re.search(padrao, texto)
        if match:
            valor = match.group(1).strip().upper()
            # Limpeza extra para o Procedimento
            if chave == 'procedimento':
                # Se o médico foi parar dentro do procedimento, nós o removemos
                valor = re.sub(r'MÉDICO\s*SOLICITANTE:.*', '', valor).strip()
            dados[chave] = valor
        else:
            dados[chave] = "NÃO ENCONTRADO"
            
    # Caso especial: se o médico não foi achado pelo padrão principal, 
    # tentamos buscar ele dentro do que foi capturado como 'procedimento' antes da limpeza
    if dados['medico'] == "NÃO ENCONTRADO":
        medico_match = re.search(r"(?i)M\s*é\s*d\s*i\s*c\s*o\s*S\s*o\s*l\s*i\s*c\s*t\s*a\s*n\s*t\s*e:\s*(.*?)\s*(?:INFERIOR|SUPERIOR|PESCOCO|PELVE|SUS:|$)", texto)
        if medico_match:
            dados['medico'] = medico_match.group(1).strip().upper()

    return dados

def processar_pdf_laudos(caminho_pdf):
    exames_encontrados = []
    chave_anterior = None

    with pdfplumber.open(caminho_pdf) as pdf:
        for pagina in pdf.pages:
            texto_bruto = pagina.extract_text()
            if not texto_bruto: continue
            
            dados = extrair_dados_cabecalho(texto_bruto)
            
            # EVOLUÇÃO: Adicionamos o médico e o número de atendimento na chave
            # Isso separa exames iguais (mesmo estudo) solicitados por médicos diferentes
            chave_atual = f"{dados['paciente']}-{dados['nascimento']}-{dados['procedimento']}-{dados['medico']}"
            
            if chave_atual != chave_anterior:
                exames_encontrados.append({
                    'Paciente': dados['paciente'],
                    'Nascimento': dados['nascimento'],
                    'Data Exame': dados['data_exame'],
                    'Médico': dados['medico'],
                    'Procedimento': dados['procedimento'],
                    'Atendimento': dados['atendimento'],
                    'Páginas': 1
                })
                chave_anterior = chave_atual
            else:
                if exames_encontrados:
                    exames_encontrados[-1]['Páginas'] += 1
                    
    return exames_encontrados