import os
import re
import fitz
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

# NOME DA MINHA CHAVE: Teste
# api_key = os.getenv("HF_TOKEN")
# client = OpenAI(
#     base_url="https://router.huggingface.co/v1",
#     api_key=api_key
# )

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

def organizar_perguntas(texto):
    pattern = r"\*\*Pergunta\s*\d+\*\*:\s*(.*)"  # --> Regex para pegar linhas que começam com número + ponto
    perguntas = re.findall(pattern,texto)
    perguntas_enumeradas = {f"pergunta{i+1}": p.strip() for i, p in enumerate(perguntas)}
    return perguntas_enumeradas

# USAR MODELO ->  mistralai/Mixtral-8x7B-Instruct-v0.1 #

# @app.post("/")
# async def fazer_perguntas(prompt: str = Form(...),file: UploadFile = File(...)):

#     if(file.filename.endswith(".pdf")):
#         texto_extraido = extrair_texto_pdf(file)
#     elif(file.filename.endswith(".md")):
#         texto_extraido = extrair_texto_md(file)
#     elif(file.filename.endswith(".docx")):
#         texto_extraido = extrair_texto_docx(file)
    
#     print(f"Extraindo texto de {file.filename}")

#     data = {
#         "model": "meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo",
#         "prompt": f"Crie perguntas deste texto: {texto_extraido}:\n\n",
#         "temperature": 0.7
#     }

    # completion = client.chat.completions.create(
    #     model="meta-llama/Llama-3.1-8B-Instruct:fireworks-ai",
    #     messages=[
    #         {
    #             "role": "user",
    #             "content":prompt_user
    #         }
    #     ],
    # )

    # response = client.chat.completions.create(
    #     model="meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo",
    #     messages=[
    #     {
    #         "role": "user",
    #         "content": prompt_user

    #     }
    #     ]
    # )

    # response = requests.post(
    #      "https://api.together.xyz/v1/completions",
    #     headers={
    #         "Authorization": f"Bearer {api_key}",
    #         "Content-Type": "application/json"
    #     },
    #     json=data,
    #     proxies=proxies
    # )

    # response_json = response.json()
    # print(response_json)
    # texto = response_json.get("output","sem saida")
    # perguntas_enumeradas = organizar_perguntas(texto)
    # print("texto extraito: ", texto_extraido)
    # print(perguntas_enumeradas)

    # return JSONResponse(content={
    #     "Prompt": f"{prompt}:\n", 
    #     "Perguntas:\n":perguntas_enumeradas,
    #     "Resposta completa": texto
    #     })

@app.post("/")
async def fazer_perguntas(prompt: str = Form(...), file: UploadFile = File(...)):
    # 1. Extrair texto conforme o tipo de arquivo
    if file.filename.endswith(".pdf"):
        texto_extraido = extrair_texto_pdf(file)
    elif file.filename.endswith(".md"):
        texto_extraido = extrair_texto_md(file.file.read())
    elif file.filename.endswith(".docx"):
        texto_extraido = extrair_texto_docx(file.file.read())
    else:
        return JSONResponse(status_code=400, content={"erro": "Formato de arquivo não suportado."})

    print(f"Extraindo texto de {file.filename}")

    # 2. Criar prompt com base no texto extraído
    prompt_final = f"{prompt}\n\n{texto_extraido}"

    # 3. Preparar payload da API
    data = {
        "model": "meta-llama/Llama-3.2-11B-Vision-Instruct-Turbo",
        "prompt": prompt_final,
        "max_tokens": 1024,
        "temperature": 0.7
    }

    # 4. Enviar requisição à Together API
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
    print("Resposta da API:", response_json)

    # 5. Pegar saída do modelo e organizar perguntas
    choices = response_json.get("choices", [])
    if choices and "text" in choices[0]:
        texto_modelo = choices[0]["text"]
    else:
        texto_modelo = "sem saída"

    perguntas_enumeradas = organizar_perguntas(texto_modelo)

    # 6. Retornar como resposta
    return JSONResponse(content={
        "Prompt original": prompt,
        "Perguntas geradas": perguntas_enumeradas,
        "Texto completo da IA": texto_modelo
    })
