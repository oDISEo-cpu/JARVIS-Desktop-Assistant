# JARVIS — Asistente Virtual estilo Iron Man

Asistente de escritorio modular en Python con conversación natural, control de PC y degradación elegante. Funciona **100% por texto** sin instalar dependencias de voz.

## Requisitos

- **Windows 10/11** (optimizado; partes funcionan en Linux/macOS)
- **Python 3.11+**
- Conexión a internet (solo si usa OpenAI/Anthropic; Ollama funciona offline)

## Instalación rápida (PowerShell)

```powershell
cd "C:\Users\HomePC\Documents\Asistente 3.0\jarvis"
.\scripts\setup.ps1
```

El script `setup.ps1`:
1. Crea un entorno virtual `.venv`
2. Instala `requirements.txt` (sin voz)
3. Copia `.env.example` → `.env` si no existe

### Instalación manual

```powershell
cd jarvis
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

## Configuración (.env)

Edite `.env` con su editor favorito:

```env
JARVIS_INPUT_MODE=text
USUARIO_TRATO=señor
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-su-clave-aqui
```

### Proveedores LLM

| Proveedor | Variables | Costo |
|-----------|-----------|-------|
| **OpenAI** | `LLM_PROVIDER=openai`, `OPENAI_API_KEY` | De pago |
| **Anthropic** | `LLM_PROVIDER=anthropic`, `ANTHROPIC_API_KEY` | De pago |
| **Ollama** | `LLM_PROVIDER=ollama`, `LLM_MODEL=llama3.2` | **Gratis, local** |

### Ollama (uso gratis local)

```powershell
# 1. Instalar Ollama desde https://ollama.com
# 2. Descargar un modelo
ollama pull llama3.2

# 3. Configurar .env
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434
```

## Ejecución

### Modo texto (default)

```powershell
python main.py
```

Interfaz de chat en terminal con Rich. No requiere micrófono ni PyAudio.

### Modo dry-run (simular acciones)

```powershell
python main.py --dry-run
```

Genera planes y muestra el JSON del LLM **sin ejecutar nada** en el sistema.

### Chat web

```powershell
python main.py --web
```

Abre un chat en el navegador: **http://localhost:8000**

Combina con otros modos:

```powershell
python main.py --web --dry-run
```

### Modo voz (opcional)

Requiere dependencias extra:

```powershell
pip install -r requirements-voice.txt
python main.py --input-mode voice
```

Modo híbrido (voz + texto):

```powershell
python main.py --input-mode hybrid
```

## Comandos útiles dentro de JARVIS

| Comando | Descripción |
|---------|-------------|
| `ayuda` | Lista capacidades (modo básico) |
| `/rutinas` o `rutinas` | Muestra patrones detectados |
| `salir` / `hasta luego` | Cierra JARVIS |

## Modo básico (sin LLM)

Si no hay API key, internet o cuota agotada, JARVIS activa **modo básico** con comandos por palabras clave:

- "abre notepad"
- "busca informe.pdf"
- "busca en google Python tutorial"
- "lista ventanas abiertas"
- "bloquea pantalla"
- "apaga el pc" (con confirmación)

## Rutinas automáticas

JARVIS registra sus acciones y detecta patrones. Si repite la misma acción 3+ veces en horarios similares, la sugiere al iniciar:

> *"Son las 08:00. ¿Abro su espacio de trabajo habitual?"*

## Tests

```powershell
pip install pytest
python -m pytest tests/ -v
```

Los tests usan dry-run y mocks — **no tocan el sistema real**.

## Estructura del proyecto

```
jarvis/
├── main.py              # Punto de entrada
├── config.py            # Configuración global
├── core/
│   ├── brain.py         # Motor LLM + modo básico
│   ├── personality.py   # Personalidad JARVIS
│   ├── memory.py        # Memoria y rutinas (SQLite)
│   └── subsystems.py    # Chequeo de módulos
├── action/              # Control de PC
├── perception/          # Entrada texto/voz
├── ui/web_chat.py       # Chat web
├── security/guard.py    # Whitelist y confirmaciones
├── scripts/setup.ps1    # Instalador Windows
└── tests/test_safe.py   # Tests seguros
```

## Seguridad

- Comandos destructivos requieren confirmación explícita
- Whitelist de comandos shell en `config.py`
- Log de acciones en `logs/actions.log`
- `--dry-run` para validar planes sin riesgo

## Solución de problemas

| Problema | Solución |
|----------|----------|
| "Modo básico activo" | Configure API key en `.env` o use Ollama |
| Error de micrófono | Use `JARVIS_INPUT_MODE=text` (default) |
| Ollama no responde | Verifique que `ollama serve` esté corriendo |
| PyAudio falla | Solo necesario para voz; omita `requirements-voice.txt` |
