# 🦙 Llama Document Prompt API

Uma API poderosa que combina modelos LLaMA da Hugging Face, OpenAI, FastAPI e Fitz para interpretar documentos e responder a perguntas personalizadas. Basta enviar um arquivo `.pdf`, `.md` ou `.docx` e fazer um prompt sobre o conteúdo!

---

## 📸 Visão Geral

> Transforme documentos em conhecimento com inteligência artificial.

---

## 🚀 Funcionalidades

- 📄 Suporte a arquivos `.pdf`, `.md`, `.docx`
- 🧠 Processamento com modelo LLaMA via [Hugging Face Router](https://router.huggingface.co/v1)
- 🤖 Geração de respostas com OpenAI
- ⚡ API rápida com FastAPI
- 🔍 Extração de texto com Fitz

---

## 🧰 Tecnologias Utilizadas

| Tecnologia           | Função Principal                          |
|----------------------|-------------------------------------------|
| LLaMA (Hugging Face) | Interpretação semântica dos documentos    |
| OpenAI               | Geração de respostas contextuais          |
| FastAPI              | Estrutura da API                          |
| Fitz                 | Extração de texto de arquivos PDF         |

---

## 📦 Como Usar

### 1. Instalação

```bash
git clone https://github.com/Joao-Adegas/QuestionGeneratorAI
cd QuestionGeneratorAI
pip install -r requirements.txt
```

## 🧑‍💻 Passo a Passo para Iniciar o Projeto

Este guia assume que você já possui um ambiente virtual Python ativo. Se ainda não tiver, você pode criar um com:

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

## 🚀 3. Iniciar a API com Uvicorn
Execute o servidor local com FastAPI:
```bash
uvicorn main:app --reload
```
