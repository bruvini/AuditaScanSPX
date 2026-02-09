import pdfplumber
import re

def limpar_nome_medico(nome):
    """
    Remove caracteres residuais (números, parênteses, barras) 
    que ficam no início ou fim do nome extraído.
    """
    if not nome: return ""
    # 1. Remove tudo que não é letra no início da string (ex: ') 1 / ')
    nome = re.sub(r'^[^A-Z]+', '', nome)
    # 2. Remove espaços extras
    return nome.strip()

def extrair_dados_solicitacao(caminho_pdf):
    solicitacoes = []
    
    with pdfplumber.open(caminho_pdf) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text()
            if not texto: continue
            
            texto_limpo = " ".join(texto.split())
            
            # 1. PACIENTE E NASCIMENTO
            pac_match = re.search(r"3-Paciente\s*(.*?)\s*(?:4-Prontuário|5-CNS|IDENTIFICAÇÃO)", texto_limpo, re.I)
            paciente = pac_match.group(1).strip().upper() if pac_match else "NÃO DETECTADO"
            
            nasc_match = re.search(r"6-Data nasc\.\s*(\d{2}/\d{2}/\d{4})", texto_limpo, re.I)
            nascimento = nasc_match.group(1) if nasc_match else "NÃO DETECTADO"
            
            # 2. DATA DA SOLICITAÇÃO
            data_sol_match = re.search(r"Data sol\.\s*(\d{2}/\d{2}/\d{4})", texto_limpo, re.I)
            data_solicitacao = data_sol_match.group(1) if data_sol_match else "NÃO DETECTADO"
            
            # 3. CAPTURA DOS MÉDICOS COM LIMPEZA REFINADA
            solic_match = re.search(r"Solicitante\s*(.*?)\s*(?:-|Data|CRM|Assinatura)", texto_limpo, re.I)
            nome_solic = limpar_nome_medico(solic_match.group(1).upper()) if solic_match else ""

            resp_match = re.search(r"R\s*e\s*s\s*p\s*o\s*n\s*s\s*á\s*v\s*e\s*l\s*d\s*o\s*c\s*u\s*m\s*e\s*n\s*t\s*o\s*(.*?)\s*(?:-|Data|CRM|Assinatura)", texto_limpo, re.I)
            nome_resp = limpar_nome_medico(resp_match.group(1).upper()) if resp_match else ""
            
            medicos_set = {n for n in [nome_solic, nome_resp] if n}
            medicos_encontrados = " / ".join(list(medicos_set)) if medicos_set else "NÃO DETECTADO"

            # 4. PROCEDIMENTOS
            procedimentos_raw = re.findall(r"(\d{10}\s*-\s*[A-Z\s]+?)(?:\sQtd|$)", texto_limpo, re.I)
            
            if procedimentos_raw:
                for proc_bruto in procedimentos_raw:
                    nome_exame = re.sub(r"^\d{10}\s*-\s*", "", proc_bruto).strip().upper()
                    solicitacoes.append({
                        'Paciente': paciente,
                        'Nascimento': nascimento,
                        'Data Solicitação': data_solicitacao,
                        'Médico Solicitante': medicos_encontrados,
                        'Procedimento': nome_exame
                    })
            else:
                solicitacoes.append({
                    'Paciente': paciente,
                    'Nascimento': nascimento,
                    'Data Solicitação': data_solicitacao,
                    'Médico Solicitante': medicos_encontrados,
                    'Procedimento': "NÃO ENCONTRADO"
                })
                
    return solicitacoes