# 🔍 AuditaScan SPX

> **Sistema de Inteligência e Auditoria de Diagnósticos por Imagem** > *Desenvolvido para o Hospital Municipal São José (Coordenação NIR)*

![Python Version](https://img.shields.io/badge/python-3.9%2B-blue?logo=python)
![Streamlit](https://img.shields.io/badge/frontend-streamlit-red?logo=streamlit)
![Status](https://img.shields.io/badge/status-active-success)
![Proprietary](https://img.shields.io/badge/license-proprietary-lightgrey)

---

## 📋 Sobre o Projeto

O **AuditaScan SPX** é uma ferramenta de alta performance desenvolvida para automatizar e otimizar o fluxo de auditoria médica. O sistema realiza o **cruzamento triplo de dados** (Triple-Way Matching) para identificar divergências de faturamento e produção médica, reduzindo drasticamente o tempo de conferência manual e mitigando glosas.

### O Problema
A conferência manual entre planilhas de faturamento, laudos digitais e solicitações físicas escaneadas é lenta, propensa a erros humanos e exaustiva.

### A Solução
Um motor de conciliação inteligente que utiliza **Regex**, **OCR (Optical Character Recognition)** e **Lógica Fuzzy** para ler, interpretar e validar milhares de exames em segundos.

---

## ✨ Principais Funcionalidades

* **📊 Ingestão de Dados Multiformato:** Processamento simultâneo de arquivos Excel (.xlsx), Laudos Digitais (.pdf) e Scans Físicos (.pdf).
* **🧠 Algoritmo de Comparação Inteligente:**
    * **Normalização Avançada:** Tratamento de acentuação, siglas médicas (ex: TC -> TOMOGRAFIA) e formatação.
    * **Lógica de Subconjunto (Subset Matching):** Identifica compatibilidade parcial (ex: "TC CRANIO" contido em "TC CRANIO RECONSTRUCAO").
    * **Fuzzy Matching:** Uso de `difflib` para detectar similaridade textual e tolerar pequenos erros de digitação.
* **⏱️ Cálculo de ROI em Tempo Real:** Monitoramento da eficiência operacional com cálculo automático de tempo economizado versus auditoria manual.
* **🎨 Relatórios Visuais:** Geração de planilhas Excel com coloração condicional (Verde/Vermelho) para fácil visualização de divergências.

---

## 🛠️ Stack Tecnológica

O projeto foi construído utilizando as melhores bibliotecas para ciência de dados e interfaces web rápidas:

| Componente | Tecnologia | Função |
| :--- | :--- | :--- |
| **Frontend** | `Streamlit` | Interface interativa e reativa. |
| **Manipulação de Dados** | `Pandas` | Estruturação e filtragem de datasets. |
| **Extração de Texto** | `pdfplumber` | Leitura de PDFs textuais e OCR básico. |
| **Lógica de Texto** | `RegEx` & `Difflib` | Padronização e comparação semântica. |
| **Exportação** | `XlsxWriter` | Geração de relatórios Excel estilizados. |

---

## 📂 Estrutura do Projeto

```text
AuditaScan-SPX/
├── 📁 processamento/          # Módulos Core do Backend
│   ├── __init__.py
│   ├── comparador.py         # Motor lógico de conciliação (Fuzzy/Subset)
│   ├── extrator_excel.py     # Leitura e limpeza da planilha
│   ├── extrator_pdf.py       # Extração de Laudos Digitais
│   ├── extrator_scaneado.py  # Extração de Solicitações (OCR)
│   └── exportador.py         # Geração do Excel colorido
├── streamlit_app.py          # Aplicação Principal (Frontend)
├── requirements.txt          # Dependências do projeto
└── README.md                 # Documentação

## 🚀 Como Executar

Siga os passos abaixo para rodar a aplicação localmente.

**Pré-requisitos**
- Python 3.9 ou superior instalado.
- Gerenciador de pacotes pip.

**Instalação**

1. **Clone o repositório** (ou baixe os arquivos):
```git clone https://seu-repositorio/auditascan-spx.git
cd auditascan-spx´´´

2. **Crie um ambiente virtual** (Recomendado):
```# Windows
python -m venv venv
.\venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate´´´

3. **Instale as dependências**:
```pip install -r requirements.txt´´´

4. **Execute a aplicação**:
```streamlit run streamlit_app.py´´´

## Guia de Utilização

1. **Dados da Planilha:** Faça o upload da planilha de produção contendo as colunas Data, Paciente, Procedimento, etc.
2. **Laudos Médicos:** Carregue os PDFs contendo os laudos digitais. O sistema extrairá metadados automaticamente.
3. **PDF das Solicitações:** Carregue os arquivos escaneados das guias físicas.
4. **Auditoria:** Selecione o período desejado e clique em "AUDITAR AGORA".
5. **Análise:** Visualize o ROI (tempo economizado) e baixe o relatório final em Excel.

## Créditos e Propriedade

**Desenvolvido para:** Coordenação NIR - Hospital Municipal São José
**Responsável Técnico:** Enf. Bruno Vinícius
**Versão:** 2.4 (Stable)