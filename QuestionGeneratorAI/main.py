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

load_dotenv()
app = FastAPI()

"""
 NOME DA MINHA CHAVE: Teste


 api_key = os.getenv("HF_TOKEN")
 client = OpenAI(
     base_url="https://router.huggingface.co/v1",
     api_key=api_key
 )

 USAR MODELO ->  mistralai/Mixtral-8x7B-Instruct-v0.1 


"""



proxies = {
    "http":"http://127.0.0.1:8080",
    "https":"http://127.0.0.1:8080"
}


api_key = os.getenv("TogetherApiKey")
client = Together(api_key=api_key)

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

# def organizar_perguntas(texto):
#     # Regex que aceita vários formatos de enumeração, com ou sem negrito
#     pattern = r"(?:\*\*)?Pergunta\s*\d+(?:\*\*)?[:\-\)]\s*(.*?)(?=\n(?:\*\*)?Pergunta\s*\d+(?:\*\*)?[:\-\)]|$)"
#     perguntas = re.findall(pattern, texto, flags=re.IGNORECASE | re.DOTALL)
#     perguntas_enumeradas = {f"pergunta{i+1}": p.strip() for i, p in enumerate(perguntas)}
#     return perguntas_enumeradas

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

# def extrair_primeiro_json_valido(texto):
#     padrao = r"\{(?:[^{}]|(?R))*\}"
#     matches = re.findall(padrao, texto, re.DOTALL)
    
#     for match in matches:
#         try:
#             return json.loads(match)
#         except json.JSONDecodeError:
#             continue
#     return {}

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
"""
@app.post("/")
async def fazer_perguntas(prompt: str = Form(...),file: UploadFile = File(...)):

    if(file.filename.endswith(".pdf")):
        texto_extraido = extrair_texto_pdf(file)
    elif(file.filename.endswith(".md")):
        texto_extraido = extrair_texto_md(file)
    elif(file.filename.endswith(".docx")):
        texto_extraido = extrair_texto_docx(file)

    print(f"Extraindo texto de {file.filename}")

    data = {
        "model": "meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo",
        "prompt": f"Crie perguntas deste texto: {texto_extraido}:\n\n",
        "temperature": 0.7
    }

    completion = client.chat.completions.create(
        model="meta-llama/Llama-3.1-8B-Instruct:fireworks-ai",
        messages=[
            {
                "role": "user",
                "content":prompt_user
            }
        ],
    )

    response = client.chat.completions.create(
        model="meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo",
        messages=[
        {
            "role": "user",
            "content": prompt_user

        }
        ]
    )

    response = requests.post(
        "https://api.together.xyz/v1/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json=data,
        proxies=proxies
    )

    response_json = response.json()
    print(response_json)
    texto = response_json.get("output","sem saida")
    perguntas_enumeradas = organizar_perguntas(texto)
    print("texto extraito: ", texto_extraido)
    print(perguntas_enumeradas)

    return JSONResponse(content={
        "Prompt": f"{prompt}:\n", 
        "Perguntas:\n":perguntas_enumeradas,
        "Resposta completa": texto
        })
"""



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


    data = {
        "model": "meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo",
        "prompt": prompt_final,
        "max_tokens": 1024,
        "temperature": 0.7
    }

    response = requests.post(
        "https://api.together.xyz/v1/completions",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        },
        json=data,
        # proxies=proxies
    )

    response_json = response.json()
    os.system("cls")
    print("Resposta da API:", response_json)

    choices = response_json.get("choices", [])
    if choices and "text" in choices[0]:
        texto_modelo = choices[0]["text"]
    else:
        texto_modelo = "sem saída"

    perguntas_enumeradas = extrair_perguntas_do_texto(texto_modelo)
    # 6. Retornar como resposta
    return JSONResponse(content={
        "Prompt original": prompt,
        "Perguntas geradas": perguntas_enumeradas
    })
