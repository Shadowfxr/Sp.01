import os
import subprocess
import zipfile
import shutil
import platform
import threading

try:
    import requests
    import pyperclip
except ImportError:
    print("❌ El módulo 'requests' no está instalado. Intentando instalar automáticamente...")
    try:
        subprocess.check_call(["pip", "install", "requests", "pyperclip"])
        import requests
        print("✅ 'requests' instalado correctamente.")
    except Exception as e:
        print(f"❌ No se pudo instalar 'requests': {e}")
        exit(1)

CARPETA_SERVER = "ServidorMinecraft"

versiones = {
    "Forge": {
        "1.12.2": "14.23.5.2860",
        "1.16.5": "36.2.39",
        "1.18.2": "40.2.17",
        "1.20.1": "47.2.0"
    },
    "Fabric": {
        "1.18.2": "0.14.21",
        "1.20.1": "0.15.7"
    },
    "Vanilla": {
        "1.20.1": "vanilla"
    }
}

def crear_carpetas():
    os.makedirs(CARPETA_SERVER, exist_ok=True)
    for carpeta in ["mods", "config", "world"]:
        os.makedirs(os.path.join(CARPETA_SERVER, carpeta), exist_ok=True)
    with open(os.path.join(CARPETA_SERVER, "eula.txt"), "w") as f:
        f.write("eula=true\n")

def descargar_jar(tipo, mc_version, sub_version):
    is_forge_old = tipo == "Forge" and mc_version == "1.12.2"

    if tipo == "Forge":
        if is_forge_old:
            jar_name = f"forge-{mc_version}-{sub_version}-installer.jar"
            url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{mc_version}-{sub_version}/{jar_name}"
        else:
            jar_name = f"forge-{mc_version}-{sub_version}-universal.jar"
            url = f"https://maven.minecraftforge.net/net/minecraftforge/forge/{mc_version}-{sub_version}/{jar_name}"
    elif tipo == "Fabric":
        jar_name = "fabric-server-launch.jar"
        url = f"https://meta.fabricmc.net/v2/versions/loader/{mc_version}/{sub_version}/server/jar"
    else:
        jar_name = f"minecraft_server.{mc_version}.jar"
        url = f"https://launcher.mojang.com/v1/objects/1b557e7b033b583cd9f66736f4f1c8d26d7f9f84/server.jar"

    ruta = os.path.join(CARPETA_SERVER, jar_name)
    if os.path.isfile(ruta):
        print(f"✅ El archivo {jar_name} ya está descargado.")
        if is_forge_old and not os.path.isfile(os.path.join(CARPETA_SERVER, f"forge-{mc_version}-{sub_version}.jar")):
            print("⚠️ Ejecutando instalador Forge antiguo para generar librerías...")
            subprocess.run(["java", "-jar", jar_name, "--installServer"], cwd=CARPETA_SERVER)
        return jar_name

    print(f"⬇️ Descargando {jar_name}...")
    try:
        r = requests.get(url)
        if r.status_code == 200:
            with open(ruta, "wb") as f:
                f.write(r.content)
            print("✅ Descarga completada.")
            if is_forge_old:
                print("⚙️ Ejecutando instalador para preparar servidor antiguo...")
                subprocess.run(["java", "-jar", jar_name, "--installServer"], cwd=CARPETA_SERVER)
            return jar_name
        else:
            print(f"❌ Error al descargar. Código: {r.status_code}")
    except Exception as e:
        print(f"❌ Excepción al descargar: {e}")
    return None

def verificar_java():
    print("🔍 Verificando instalación de Java...")
    try:
        result = subprocess.run(["java", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            print("✅ Java está instalado.")
            return True
        else:
            print("❌ Java no está instalado o no se encuentra en el PATH.")
            return False
    except FileNotFoundError:
        print("❌ Java no está instalado o no se encuentra en el PATH.")
        return False

def ejecutar_playit():
    print("🌐 Conectando con el agente Playit.gg...")

    agente_playit = os.path.join(CARPETA_SERVER, "playit-agent")
    if platform.system() == "Windows":
        agente_playit += ".exe"

    if not os.path.isfile(agente_playit):
        print("❌ No se encontró el archivo 'playit-agent' en la carpeta del servidor.")
        print("➡️ Asegúrate de haber colocado tu agente de Playit.gg en la ruta correcta.")
        return

    proceso = subprocess.Popen([agente_playit], cwd=CARPETA_SERVER, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    def mostrar_enlace():
        while True:
            linea = proceso.stdout.readline()
            if not linea:
                break
            print(linea.strip())
            if "https://" in linea:
                try:
                    pyperclip.copy(linea.strip())
                    print("📋 Enlace copiado al portapapeles.")
                except Exception as e:
                    print(f"⚠️ No se pudo copiar al portapapeles: {e}")
                print("🔗 Enlace público detectado:", linea.strip())

    threading.Thread(target=mostrar_enlace, daemon=True).start()

def ejecutar_servidor(jar_name, ram):
    print(f"🚀 Iniciando servidor: {jar_name} con {ram} GB de RAM...")
    os.chdir(CARPETA_SERVER)
    ejecutar_playit()

    proceso = subprocess.Popen(
        ["java", f"-Xmx{ram}G", f"-Xms{ram}G", "-jar", jar_name, "nogui"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    try:
        while True:
            salida = proceso.stdout.readline()
            if salida:
                print(salida.strip())
            if proceso.poll() is not None:
                break
            comando = input()
            if comando.strip() == "/stop":
                proceso.stdin.write("stop\n")
                proceso.stdin.flush()
    except KeyboardInterrupt:
        proceso.terminate()
        print("🛑 Servidor detenido manualmente.")

def main():
    config_path = "ultima_configuracion.txt"

    while True:
        ultima_config = {}
        if os.path.exists(config_path):
            with open(config_path, "r") as f:
                for linea in f:
                    if '=' in linea:
                        clave, valor = linea.strip().split("=", 1)
                        ultima_config[clave] = valor

        print("\n=== Instalador de Servidor Minecraft ===")
        print("1. Seleccionar tipo y versión de servidor")
        print("2. Iniciar servidor con configuración guardada")
        print("3. Editar configuración sin iniciar")
        print("4. Borrar configuración y salir")
        print("5. Salir")
        opcion = input("Selecciona una opción (1-5): ").strip()

        if opcion == "1":
            tipos = list(versiones.keys())
            for i, t in enumerate(tipos):
                print(f"{i+1}. {t}")
            while True:
                try:
                    tipo_idx = int(input("Tipo (número): ")) - 1
                    tipo = tipos[tipo_idx]
                    break
                except (ValueError, IndexError):
                    print("❌ Opción inválida. Intenta de nuevo.")

            vers = list(versiones[tipo].keys())
            for i, v in enumerate(vers):
                print(f"{i+1}. {v}")
            while True:
                try:
                    ver_idx = int(input("Versión (número): ")) - 1
                    break
                except (ValueError, IndexError):
                    print("❌ Versión inválida. Intenta de nuevo.")

            mc_version = vers[ver_idx]
            sub_version = versiones[tipo][mc_version]

            while True:
                ram = input("RAM en GB: ").strip() or "2"
                if ram.isdigit() and int(ram) > 0:
                    break
                else:
                    print("❌ Ingresa un número válido de GB de RAM.")

            with open(config_path, "w") as f:
                f.write(f"tipo={tipo}\nmc_version={mc_version}\nsub_version={sub_version}\nram={ram}\n")

            crear_carpetas()
            jar = descargar_jar(tipo, mc_version, sub_version)
            if jar and verificar_java():
                ejecutar_servidor(jar, ram)
            continue

        if opcion == "2":
            tipo = ultima_config.get("tipo")
            mc_version = ultima_config.get("mc_version")
            sub_version = ultima_config.get("sub_version")
            ram = ultima_config.get("ram", "2")
            if not tipo or not mc_version or not sub_version:
                print("❌ Configuración incompleta. Usa opción 1 primero.")
                continue
            jar = descargar_jar(tipo, mc_version, sub_version)
            if jar and verificar_java():
                ejecutar_servidor(jar, ram)
            continue

        if opcion == "3":
            tipos_validos = list(versiones.keys())
            tipo = input("Tipo (Forge/Fabric/Vanilla): ").strip().capitalize()
            if tipo not in tipos_validos:
                print("❌ Tipo no válido. Usa Forge, Fabric o Vanilla.")
                continue

            mc_version = input("Versión de Minecraft: ").strip()
            if mc_version not in versiones[tipo]:
                print(f"❌ Versión no válida para {tipo}.")
                continue

            sub_version = versiones[tipo][mc_version]
            ram = input("RAM GB: ").strip()
            if not ram.isdigit() or int(ram) <= 0:
                print("❌ RAM inválida.")
                continue

            with open(config_path, "w") as f:
                f.write(f"tipo={tipo}\nmc_version={mc_version}\nsub_version={sub_version}\nram={ram}\n")
            print("✅ Configuración actualizada.")
            continue

        if opcion == "4":
            if os.path.exists(config_path):
                os.remove(config_path)
            if os.path.exists(CARPETA_SERVER):
                shutil.rmtree(CARPETA_SERVER)
            print("🧹 Todo eliminado. Saliendo...")
            break

        if opcion == "5":
            print("👋 Hasta luego!")
            break

if __name__ == "__main__":
    main()
