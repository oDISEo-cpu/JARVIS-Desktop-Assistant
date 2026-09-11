# JARVIS — Asistente Virtual estilo Iron Man

Asistente de escritorio modular en Python con conversación natural, control de PC y degradación elegante. Funciona **100% por terminal** sin interfaz web ni dependencias de voz obligatorias.

## Requisitos

- **Windows 10/11** (optimizado; partes funcionan en Linux/macOS)
- **Python 3.11+**
- Conexión a internet (solo si usa OpenAI/Anthropic; Ollama funciona offline)

## Instalación rápida

### 🚀 Nuevo: Instalador Automático Inteligente (Recomendado)

He añadido un script innovador que automatiza TODO el proceso de instalación. Solo necesitas tener Python instalado.

**Windows, Linux o macOS:**

```bash
# Navega a la carpeta del proyecto (ajusta la ruta según donde lo tengas)
cd ruta/a/tu/proyecto/jarvis

# Ejecuta el instalador inteligente
python jarvis_init.py
```

Este script hace lo siguiente automáticamente:
1. ✅ Verifica que tienes Python 3.10+ instalado
2. ✅ Crea el entorno virtual (.venv) si no existe
3. ✅ Instala todas las dependencias de `requirements.txt`
4. ✅ Verifica la conexión con Ollama (y te avisa si falta)
5. ✅ Lanza JARVIS automáticamente

¡Listo! Sin comandos complicados, sin errores de rutas, sin configurar nada manualmente.

---

### Instalación manual (alternativa)

Si prefieres hacerlo paso a paso:

#### Windows (PowerShell)

```powershell
# Navega a la carpeta del proyecto (ajusta la ruta según donde lo tengas)
cd "C:\Ruta\A\Tu\Proyecto\jarvis"

# Crea y activa el entorno virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Instala dependencias
pip install -r requirements.txt
```

#### Linux/macOS (Bash)

```bash
cd /ruta/a/tu/proyecto/jarvis
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
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

### 🆕 Modo GUI: Widget de Escritorio con Esfera Reactiva (Opcional)

¡Ahora JARVIS puede tener un widget visual estilo "Arc Reactor" que flota en tu escritorio!

**Requisito previo:** Instalar PyQt6
```bash
pip install PyQt6
# O usar el extra: pip install -e ".[gui]"
```

**Ejecutar con GUI:**
```powershell
python main.py --gui
```

**¿Qué hace el widget?**
- 🎨 Muestra una **esfera 3D animada** flotando sobre tu escritorio
- 🔵 **Azul tranquilo**: JARVIS está en espera (idle)
- 🔵 **Cyan pulsante**: JARVIS está escuchando (listening)
- 🟠 **Dorado giratorio**: JARVIS está pensando o respondiendo (thinking/speaking)
- 📱 **Icono en la bandeja del sistema**: Acceso rápido desde la barra de tareas
- 🖱️ **Doble clic en el icono**: Activa la interacción
- 📋 **Menú contextual**: Ver estado, última respuesta o apagar JARVIS

**La esfera reacciona en tiempo real** a lo que está haciendo JARVIS, igual que el Arc Reactor de Iron Man.

---

### Modo dry-run (simular acciones)

```powershell
python main.py --dry-run
```

Genera planes y muestra el JSON del LLM **sin ejecutar nada** en el sistema.

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
| `/diag` | Re-ejecuta diagnóstico del LLM |

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
├── gui/                 # Módulo GUI opcional (PyQt6)
│   ├── tray.py          # Widget de esfera reactiva y bandeja
│   └── __init__.py
├── core/
│   ├── brain.py         # Motor LLM + modo básico
│   ├── personality.py   # Personalidad JARVIS
│   ├── memory.py        # Memoria, rutinas y contexto (SQLite)
│   ├── context.py       # Sistema de contexto persistente
│   └── subsystems.py    # Chequeo de módulos
├── action/              # Control de PC
├── perception/          # Entrada texto/voz
├── security/guard.py    # Whitelist y confirmaciones
├── scripts/setup.ps1    # Instalador Windows
├── jarvis_init.py       # Instalador automático inteligente
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

## Notas importantes

- **JARVIS es una aplicación de terminal**: No abre servidores web ni tiene interfaz gráfica. Toda la interacción ocurre en la consola.
- **La ruta de instalación es relativa**: No uses rutas absolutas como `C:\Users\HomePC\Documents\...` en la documentación. Cada usuario debe navegar a su propia carpeta del proyecto.
- **Web eliminado**: La funcionalidad de chat web (`--web`) ha sido removida. JARVIS ahora es exclusivamente un asistente de terminal conversacional.

---

## 🆕 Novedades y Actualizaciones Recientes

### [ÚLTIMO] Widget de Escritorio con Esfera Reactiva (Arc Reactor)

**¿Qué es?** Un widget visual opcional que muestra una esfera 3D animada flotando sobre tu escritorio, reaccionando en tiempo real al estado de JARVIS.

**Características:**
- 🎨 **Esfera estilo "Arc Reactor"**: Diseño inspirado en Iron Man con anillos giratorios y núcleo brillante
- 🔄 **Animación en tiempo real**: La esfera gira y pulsa según lo que está haciendo JARVIS
- 🎭 **4 estados visuales**:
  - 🔵 **Azul tranquilo**: Idle (esperando comandos)
  - 🔵 **Cyan pulsante**: Listening (escuchando voz o esperando input)
  - 🟠 **Dorado giratorio rápido**: Thinking/Speaking (procesando o respondiendo)
- 📱 **Icono en bandeja del sistema**: Acceso desde la barra de tareas
- 🖱️ **Interacción completa**: Doble clic para activar, menú contextual con opciones
- 🪟 **Ventana flotante**: Siempre visible sobre otras ventanas (always on top)
- ⚙️ **Opcional**: No requiere instalación si no usas `--gui`

**Cómo activarlo:**
```bash
# 1. Instalar PyQt6 (solo la primera vez)
pip install PyQt6

# 2. Ejecutar JARVIS con GUI
python main.py --gui
```

**La esfera reacciona automáticamente** a cada acción:
- Cuando hablas o escribes → se pone cyan y pulsa
- Cuando JARVIS piensa → gira dorado rápidamente
- Cuando responde → mantiene dorado mientras habla
- Cuando termina → vuelve a azul tranquilo

---

### Sistema de Contexto Persistente de Usuario

**¿Qué es?** Una nueva capacidad que permite a JARVIS recordar preferencias, proyectos activos y notas de sesión entre diferentes ejecuciones.

**Características:**
- 📋 **Preferencias personales**: Editor favorito, navegador predilecto, aplicaciones más usadas
- 📁 **Gestión de proyectos**: Registra tus proyectos activos con nombre, ruta y descripción
- 📝 **Notas de sesión**: Notas temporales que persisten durante la sesión (máximo 10)
- 🧠 **Patrones aprendidos**: JARVIS puede aprender patrones de comportamiento recurrentes
- 💾 **Persistencia automática**: Todo se guarda en `data/user_context.json`

**Comandos nuevos:**
- `contexto` o `/contexto`: Muestra resumen de tu configuración y proyectos
- `recuerda que mi editor es VSCode`: Guarda una preferencia
- Proyectos se registran automáticamente cuando trabajas en carpetas específicas

**Ejemplo de uso:**
```
🤖 JARVIS: ¿En qué te ayudo, señor?

Usted: contexto

📋 **Resumen de Contexto:**
   • Editor: VSCode
   • Navegador: Chrome
   • Proyectos activos: 2
     - JARVIS: /home/diego/jarvis
     - MiWeb: /home/diego/proyectos/web
```

**Cómo se integra:** El contexto se muestra automáticamente al iniciar si hay datos guardados, y está disponible en todo momento mediante el comando `contexto`.

---

### Instalador Automático Inteligente (`jarvis_init.py`)

**¿Qué hace?** Un script todo-en-uno que detecta tu sistema, prepara el entorno y lanza JARVIS sin que tengas que escribir múltiples comandos.

**Características:**
- ✅ Detección automática de Python 3.10+
- ✅ Creación inteligente de entorno virtual (.venv)
- ✅ Instalación automática de dependencias
- ✅ Verificación proactiva de Ollama (te avisa si no está corriendo)
- ✅ Lanzamiento automático de JARVIS tras la instalación
- ✅ Compatible con Windows, Linux y macOS
- ✅ Interfaz visual con colores y mensajes claros

**Cómo usarlo:**
```bash
cd ruta/a/tu/proyecto/jarvis
python jarvis_init.py
```

¡Y listo! El script se encarga de todo lo demás.

### Otras mejoras recientes:
- **Eliminación completa del modo web**: JARVIS es ahora 100% terminal, más rápido y sin dependencias innecesarias.
- **README actualizado**: Instrucciones claras sin rutas absolutas, adaptables a cualquier sistema operativo.
- **Arquitectura simplificada**: Menos complejidad, más enfoque en la experiencia de terminal conversacional.
- **Comando /contexto**: Consulta rápida de preferencias y proyectos del usuario.

---

## Próximos pasos recomendados (Roadmap)

1. **🎤 Soporte de voz nativo**: Integrar reconocimiento de voz (Whisper local) y síntesis de voz (TTS) para hablar con JARVIS sin teclado.
2. **🔌 Sistema de plugins comunitarios**: Permitir que otros desarrolladores creen e instalen intenciones personalizadas fácilmente.
3. **📊 Dashboard de estadísticas**: Mostrar métricas de uso, comandos más frecuentes y tiempo de actividad.
4. **🎨 Personalización del widget**: Permitir cambiar colores, tamaño y posición de la esfera.
5. **🧠 Mejoras de contexto**: Que JARVIS use el contexto para personalizar respuestas automáticamente.
