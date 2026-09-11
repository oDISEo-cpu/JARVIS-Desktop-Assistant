# JARVIS-Desktop-Assistant
🤖 Tu propio J.A.R.V.I.S de escritorio: asistente con IA 100% local (Ollama + Gemma/Qwen) que entiende lenguaje natural, ejecuta tareas en tu PC y automatiza flujos de trabajo. Privado, offline y extensible.

# 🤖 J.A.R.V.I.S — Asistente Personal de Escritorio

> Un asistente de inteligencia artificial inspirado en el mítico mayordomo digital de Iron Man.
> Vive en tu PC, entiende lenguaje natural y ejecuta tareas por ti — con IA 100% local, sin nube ni APIs externas.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![Ollama](https://img.shields.io/badge/IA-Ollama_•_Gemma_•_Qwen-111111)
![Estado](https://img.shields.io/badge/estado-en_desarrollo_🚧-yellow)
![Privacidad](https://img.shields.io/badge/privacidad-100%25_local-green)

## ✨ ¿Qué es?

JARVIS interpreta solicitudes en lenguaje natural como:

- *"Abre mi editor de código"*
- *"Organiza mi carpeta de descargas"*
- *"Resume este documento"*
- *"¿Qué procesos están consumiendo más RAM?"*

...y las ejecuta directamente en tu equipo usando modelos de lenguaje locales
(**Gemma** y **Qwen** a través de **Ollama**). Sin enviar un solo byte a la nube. 🔒

##  Características

- 🧠 **Comprensión de lenguaje natural** con LLMs locales
- ⚡ **Ejecución de tareas locales**: apps, archivos, scripts y automatizaciones
- 🔒 **Privacidad total**: todo el procesamiento ocurre en tu máquina
- 🧩 **Arquitectura extensible**: sistema de comandos/plugins fácil de ampliar
- 🎯 **Prompt Engineering** especializado para parseo de intenciones (intent parsing)

## 🛠️ Tech Stack

| Capa        | Tecnología                              |
|-------------|------------------------------------------|
| Lenguaje    | Python 3.10+                             |
| Runtime IA  | Ollama                                   |
| Modelos     | Gemma, Qwen                              |
| Técnicas    | Prompt Engineering, intent parsing       |

## 📦 Instalación

```bash
# 1. Clona el repo
git clone https://github.com/oDISEo-cpu/JARVIS-Desktop-Assistant.git
cd JARVIS-Desktop-Assistant

# 2. Instala Ollama y descarga un modelo
#    https://ollama.com
ollama pull gemma3

# 3. Crea el entorno virtual e instala dependencias
python -m venv venv
source venv/bin/activate   # Linux/Mac
venv\Scripts\activate      # Windows
pip install -r requirements.txt

# 4. Ejecuta a JARVIS
python main.py
