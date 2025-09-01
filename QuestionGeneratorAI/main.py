import os
import re
import fitz
import json
import requests

from openai import OpenAI
from together import Together
from dotenv import load_dotenv
from docx import Document
from fastapi import FastAPI, File, UploadFile,Form
from fastapi.responses import JSONResponse
from io import BytesIO
from fastapi.responses import FileResponse
from datetime import datetime

load_dotenv()
app = FastAPI()

client = OpenAI(
    base_url="https://router.huggingface.co/v1",
    api_key=os.environ["HF_TOKEN"],
)
"""
 NOME DA MINHA CHAVE: Teste
 USAR MODELO ->  mistralai/Mixtral-8x7B-Instruct-v0.1 
"""


proxies = {
    "http":"http://127.0.0.1:8080",
    "https":"http://127.0.0.1:8080"
}

def extrair_texto_pdf(caminho_pdf):
    pdf_bytes = caminho_pdf.file.read()

    texto = ""
    with fitz.open(stream=pdf_bytes,filetype="pdf") as doc:
        for pagina in doc:
            texto += pagina.get_text()
    return texto

def extrair_texto_md(arquivo):
    return arquivo.decode("utf-8")

def extrair_texto_docx(arquivo):
    doc_stream = BytesIO(arquivo)
    doc = Document(doc_stream)
    texto = "\n".join([par.text for par in doc.paragraphs])
    return texto

def organizar_perguntas_json(texto):
    try:
        return json.loads(texto)
    except json.JSONDecodeError:
        return {}

def extrair_json_do_texto(texto):
    # Regex para pegar o primeiro objeto JSON que aparece no texto
    padrao = r"\{(?:[^{}]|(?R))*\}"
    match = re.search(padrao, texto, re.DOTALL)
    if match:
        json_str = match.group(0)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            return {}
    return {}

def organizar_perguntas_num(texto_resposta):
    perguntas = re.findall(r"\d+\.\s+(.*)", texto_resposta)
    perguntas_enumeradas = {f"pergunta{i+1}": p.strip() for i, p in enumerate(perguntas)}
    return perguntas_enumeradas

def organizar_perguntas_num(texto_resposta):
    perguntas = re.findall(r"\d+\.\s+(.*)", texto_resposta)
    perguntas_enumeradas = {
        f"pergunta{i+1}": p.strip().replace("\n", "\\n")
        for i, p in enumerate(perguntas)
    }
    return perguntas_enumeradas

def extrair_primeiro_json_valido(texto: str):
    decoder = json.JSONDecoder()
    i = 0
    n = len(texto)
    while i < n:
        ch = texto[i]
        if ch in '{[':
            try:
                obj, end = decoder.raw_decode(texto, i)
                return obj  # retorna o primeiro JSON bem-formado
            except json.JSONDecodeError:
                pass
        i += 1
    return {}

def normalizar_perguntas(obj):
    if not isinstance(obj, dict):
        return {}
    saida = {}
    for k, v in obj.items():
        if isinstance(k, str) and k.lower().strip().startswith("pergunta"):
            chave = re.sub(r"\s+", "", k.lower())  # "Pergunta 2" -> "pergunta2"
            if isinstance(v, str):
                saida[chave] = " ".join(v.split())  # normaliza espaços/linhas
    return saida

def extrair_perguntas_do_texto(texto: str):
    # 1) tenta decodificar o primeiro JSON válido
    obj = extrair_primeiro_json_valido(texto)
    perguntas = normalizar_perguntas(obj)
    if perguntas:
        return perguntas

    # 2) fallback: captura pares "perguntaN": "..."
    # - ignora maiúsculas/minúsculas
    # - DOTALL para capturar quebras de linha dentro das aspas
    pairs = re.findall(r'"(pergunta\s*\d+)"\s*:\s*"(.*?)"', texto, flags=re.IGNORECASE | re.DOTALL)
    if pairs:
        saida = {}
        for k, v in pairs:
            chave = re.sub(r"\s+", "", k.lower())
            saida[chave] = " ".join(v.split())
        return saida

    return {}

@app.post("/")
async def fazer_perguntas(prompt: str = Form(...), file: UploadFile = File(...)):
    
    if file.filename.endswith(".pdf"):
        texto_extraido = extrair_texto_pdf(file)
    elif file.filename.endswith(".md"):
        texto_extraido = extrair_texto_md(file.file.read())
    elif file.filename.endswith(".docx"):
        texto_extraido = extrair_texto_docx(file.file.read())
    else:
        return JSONResponse(status_code=400, content={"erro": "Formato de arquivo não suportado."})

    print(f"Extraindo texto de {file.filename}")

    prompt_final = prompt_final = f"""
        {prompt}

        Por favor, gere as perguntas sobre o texto abaixo. Formate cada pergunta assim:

        {{
        "pergunta1": "...",
        "pergunta2": "...",
        ...
        }}


        E assim por diante. Não coloque nada além das perguntas e não repita nenhuma pergunta.  
        Texto:
        {texto_extraido}
    """

    completion = client.chat.completions.create(
        model="meta-llama/Llama-3.1-8B-Instruct:fireworks-ai",
        messages=[
            {
                "role": "user",
                "content":prompt_final
            }
        ],
    )

    os.system("cls")
    print("Resposta da API:", completion)

    if completion.choices:
        texto_modelo = completion.choices[0].message.content  # ou .text
    else:
        texto_modelo = "sem saída"

    perguntas_enumeradas = extrair_perguntas_do_texto(texto_modelo)
    print(perguntas_enumeradas)

    # 6. Retornar como resposta
    return JSONResponse(content={
        "Prompt original": prompt,
        "Perguntas geradas": perguntas_enumeradas
    })


@app.post("/gerar_perguntas_md/")
async def fazer_perguntas_md(prompt: str = Form(...), file: UploadFile = File(...)):
    
    # 1. Extrair texto do arquivo
    if file.filename.endswith(".pdf"):
        texto_extraido = extrair_texto_pdf(file)
    elif file.filename.endswith(".md"):
        texto_extraido = extrair_texto_md(file.file.read())
    elif file.filename.endswith(".docx"):
        texto_extraido = extrair_texto_docx(file.file.read())
    else:
        return JSONResponse(status_code=400, content={"erro": "Formato de arquivo não suportado."})

    print(f"Extraindo texto de {file.filename}")

    # 2. Preparar prompt para o modelo
    prompt_final = f"""
        {prompt}

        Por favor, gere as perguntas sobre o texto abaixo. Formate cada pergunta assim:

        {{
        "pergunta1": "...",
        "pergunta2": "...",
        ...
        }}

        Não coloque nada além das perguntas e não repita nenhuma pergunta.  
        Texto:
        {texto_extraido}
    """

    # 3. Gerar perguntas com o modelo
    completion = client.chat.completions.create(
        model="meta-llama/Llama-3.1-8B-Instruct:fireworks-ai",
        messages=[{"role": "user", "content": prompt_final}],
    )

    # 4. Extrair texto do modelo
    if completion.choices:
        texto_modelo = completion.choices[0].message.content
    else:
        texto_modelo = "sem saída"

    # 5. Extrair perguntas enumeradas
    perguntas_enumeradas = extrair_perguntas_do_texto(texto_modelo)
    print(perguntas_enumeradas)

    # 6. Criar arquivo .md com um nome único usando timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    md_filename = f"perguntas_geradas_{timestamp}.md"
    with open(md_filename, "w", encoding="utf-8") as md_file:
        md_file.write("# Perguntas Geradas\n\n")
        for chave, pergunta in perguntas_enumeradas.items():
            md_file.write(f"*{chave}*: {pergunta}\n\n")

    # 7. Retornar arquivo para download
    return FileResponse(md_filename, media_type="text/markdown", filename=md_filename)