#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
JARVIS INIT - Instalador y Lanzador Inteligente
Autor: Diego Molina

Este script automatiza la configuración inicial de JARVIS.
Detecta Python, crea el entorno virtual, instala dependencias
y lanza el asistente. Ideal para usuarios que quieren empezar
rápido sin configurar nada manualmente.

Uso: python jarvis_init.py
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

# Colores para la terminal
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_banner():
    banner = f"""
    {Colors.OKCYAN}╔════════════════════════════════════════════╗
    ║  🤖 J.A.R.V.I.S. - Iniciando Protocolo       ║
    ║  Asistente Personal de Escritorio            ║
    ╚════════════════════════════════════════════╝{Colors.ENDC}
    """
    print(banner)

def check_python():
    """Verifica que Python 3.10+ esté instalado."""
    print(f"{Colors.OKBLUE}[1/5] Verificando Python...{Colors.ENDC}")
    try:
        version = sys.version_info
        if version.major < 3 or (version.major == 3 and version.minor < 10):
            print(f"{Colors.FAIL}Error: Se requiere Python 3.10 o superior.{Colors.ENDC}")
            print(f"Versión detectada: {version.major}.{version.minor}")
            return False
        print(f"{Colors.OKGREEN}✓ Python {version.major}.{version.minor} detectado.{Colors.ENDC}")
        return True
    except Exception as e:
        print(f"{Colors.FAIL}Error al verificar Python: {e}{Colors.ENDC}")
        return False

def setup_venv():
    """Crea un entorno virtual si no existe."""
    venv_path = Path(".venv")
    print(f"{Colors.OKBLUE}[2/5] Configurando entorno virtual...{Colors.ENDC}")
    
    if not venv_path.exists():
        print("Creando entorno virtual (.venv)...")
        try:
            subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
            print(f"{Colors.OKGREEN}✓ Entorno virtual creado.{Colors.ENDC}")
        except subprocess.CalledProcessError as e:
            print(f"{Colors.FAIL}Error creando entorno virtual: {e}{Colors.ENDC}")
            return False
    else:
        print(f"{Colors.OKGREEN}✓ Entorno virtual ya existe.{Colors.ENDC}")
    
    return True

def get_pip_path():
    """Obtiene la ruta del pip dentro del venv."""
    if os.name == 'nt': # Windows
        return Path(".venv/Scripts/pip.exe")
    else: # Linux/Mac
        return Path(".venv/bin/pip")

def install_dependencies():
    """Instala las dependencias desde requirements.txt."""
    print(f"{Colors.OKBLUE}[3/5] Instalando dependencias...{Colors.ENDC}")
    
    req_file = Path("requirements.txt")
    if not req_file.exists():
        print(f"{Colors.WARNING}⚠ No se encontró requirements.txt, saltando instalación.{Colors.ENDC}")
        return True

    pip_path = get_pip_path()
    if not pip_path.exists():
        print(f"{Colors.FAIL}Error: No se encontró pip en el entorno virtual.{Colors.ENDC}")
        return False

    try:
        # Actualizar pip primero
        subprocess.run([str(pip_path), "install", "--upgrade", "pip"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Instalar requisitos
        subprocess.run([str(pip_path), "install", "-r", "requirements.txt"], check=True)
        print(f"{Colors.OKGREEN}✓ Dependencias instaladas correctamente.{Colors.ENDC}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"{Colors.FAIL}Error instalando dependencias: {e}{Colors.ENDC}")
        return False

def check_ollama():
    """Verifica si Ollama está accesible."""
    print(f"{Colors.OKBLUE}[4/5] Verificando conexión con Ollama...{Colors.ENDC}")
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            print(f"{Colors.OKGREEN}✓ Ollama detectado y respondiendo.{Colors.ENDC}")
            return True
        else:
            print(f"{Colors.WARNING}⚠ Ollama respondió pero con estado extraño: {response.status_code}{Colors.ENDC}")
            return True
    except ImportError:
        # Si requests no está instalado aún (raro en este punto), asumimos ok
        print(f"{Colors.WARNING}⚠ No se pudo verificar Ollama (librería requests pendiente), continuando...{Colors.ENDC}")
        return True
    except requests.exceptions.ConnectionError:
        print(f"{Colors.FAIL}✗ No se pudo conectar a Ollama en http://localhost:11434{Colors.ENDC}")
        print(f"{Colors.WARNING}💡 Consejo: Asegúrate de tener Ollama instalado y ejecutándose ('ollama serve').{Colors.ENDC}")
        print(f"{Colors.WARNING}💡 JARVIS intentará iniciar de todos modos, pero las funciones de IA fallarán.{Colors.ENDC}")
        return True # Retornamos True para no bloquear el inicio, pero el usuario sabe el error
    except Exception as e:
        print(f"{Colors.WARNING}⚠ Error verificando Ollama: {e}{Colors.ENDC}")
        return True

def launch_jarvis():
    """Lanza el script principal de JARVIS."""
    print(f"{Colors.OKBLUE}[5/5] Iniciando J.A.R.V.I.S...{Colors.ENDC}")
    
    main_script = Path("jarvis/main.py")
    if not main_script.exists():
        # Intentar ruta alternativa si estamos en la raíz y main.py está aquí
        main_script = Path("main.py")
        
    if not main_script.exists():
        print(f"{Colors.FAIL}Error crítico: No se encontró el script principal (main.py).{Colors.ENDC}")
        return

    python_path = sys.executable
    if Path(".venv").exists():
        if os.name == 'nt':
            python_path = Path(".venv/Scripts/python.exe")
        else:
            python_path = Path(".venv/bin/python")

    print(f"\n{Colors.HEADER}┌────────────────────────────────────────────┐")
    print(f"│  🚀 Lanzando interfaz de terminal...         │")
    print(f"└────────────────────────────────────────────┘{Colors.ENDC}\n")
    
    try:
        # Ejecutar main.py pasando el control a la nueva instancia
        subprocess.run([str(python_path), str(main_script)])
    except KeyboardInterrupt:
        print(f"\n{Colors.OKCYAN}JARVIS detenido por el usuario.{Colors.ENDC}")

def main():
    print_banner()
    
    if not check_python():
        sys.exit(1)
    
    if not setup_venv():
        sys.exit(1)
        
    if not install_dependencies():
        sys.exit(1)
        
    check_ollama() # Solo informativo
    
    launch_jarvis()

if __name__ == "__main__":
    main()
