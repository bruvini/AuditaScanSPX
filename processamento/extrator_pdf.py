import pdfplumber
import re

def limpar_texto(texto):
    """
    Limpeza robusta para juntar linhas quebradas de forma segura.
    """
    if not texto: return ""
    # Substitui quebras de linha por espaço
    texto = texto.replace('\n', ' ').replace('\t', ' ')
    # Remove caracteres estranhos, mantendo pontuação básica
    texto = re.sub(r'\s+', ' ', texto)
    return texto.strip()

def extrair_dados_cabecalho(texto_pagina):
    texto = limpar_texto(texto_pagina)
    dados = {}
    
    # NOVAS ÂNCORAS: Adicionamos mais palavras que costumam aparecer DEPOIS do procedimento
    # Isso ajuda o Regex a não parar cedo demais nem tarde demais.
    stop_words = r"(?:SUS:|Idade:|Atendimento:|Data|M[ée]dico|Solicitante|Conv[êe]nio|Prontu[áa]rio|Nasc)"
    
    padroes = {
        'paciente': r"(?i)Nome:\s*(.*?)\s*Data\s*do\s*Laudo:",
        'nascimento': r"(?i)Data\s*Nascimento:\s*(\d{2}/\d{2}/\d{4})",
        'data_exame': r"(?i)Data\s*do\s*Exame:\s*(\d{2}/\d{2}/\d{4})",
        'medico': r"(?i)M\s*é\s*d\s*i\s*c\s*o\s*S\s*o\s*l\s*i\s*c\s*i\s*t\s*a\s*n\s*t\s*e:\s*(.*?)\s*(?:Estudo:|Idade:)",
        
        # MELHORIA AQUI: Usamos a lista stop_words para delimitar o fim do procedimento
        'procedimento': fr"(?i)Estudo:\s*(.*?)\s*{stop_words}",
        
        'atendimento': r"(?i)Atendimento:\s*(\d+)"
    }
    
    for chave, padrao in padroes.items():
        match = re.search(padrao, texto)
        if match:
            valor = match.group(1).strip().upper()
            if chave == 'procedimento':
                # Remove lixo caso tenha pego o rótulo do médico junto
                valor = re.sub(r'MÉDICO\s*SOLICITANTE:.*', '', valor).strip()
            dados[chave] = valor
        else:
            dados[chave] = "NÃO ENCONTRADO"
            
    # Fallback para médico (lógica mantida)
    if dados['medico'] == "NÃO ENCONTRADO":
        medico_match = re.search(r"(?i)M\s*é\s*d\s*i\s*c\s*o\s*S\s*o\s*l\s*i\s*c\s*t\s*a\s*n\s*t\s*e:\s*(.*?)\s*(?:INFERIOR|SUPERIOR|PESCOCO|PELVE|SUS:|$)", texto)
        if medico_match:
            dados['medico'] = medico_match.group(1).strip().upper()

    return dados

def processar_pdf_laudos(caminho_pdf):
    exames_encontrados = []
    
    # Dicionário para evitar duplicatas exatas na mesma página/documento
    # Chave única: Paciente + Data + Procedimento (normalizado)
    chaves_processadas = set()

    with pdfplumber.open(caminho_pdf) as pdf:
        for pagina in pdf.pages:
            texto_bruto = pagina.extract_text()
            if not texto_bruto: continue
            
            dados = extrair_dados_cabecalho(texto_bruto)
            
            # Validação mínima: só processa se achou paciente e data
            if dados['paciente'] != "NÃO ENCONTRADO":
                
                # Cria uma chave única para evitar que a página 2 do mesmo laudo
                # conte como um segundo exame igual.
                chave_unica = f"{dados['paciente']}|{dados['data_exame']}|{dados['procedimento']}"
                
                if chave_unica not in chaves_processadas:
                    exames_encontrados.append({
                        'Paciente': dados['paciente'],
                        'Nascimento': dados['nascimento'],
                        'Data Exame': dados['data_exame'],
                        'Médico': dados['medico'],
                        'Procedimento': dados['procedimento'],
                        'Atendimento': dados['atendimento']
                    })
                    chaves_processadas.add(chave_unica)
                    
    return exames_encontrados