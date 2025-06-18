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
    subprocess.check_call(["pip", "install", "requests", "pyperclip"])
    import requests
    import pyperclip

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
        if is_forge_old and not os.path.isfile(os.path.join(CARPETA_SERVER, f"forge-{mc_version}-{sub_version}.jar")):
            subprocess.run(["java", "-jar", jar_name, "--installServer"], cwd=CARPETA_SERVER)
        return jar_name

    try:
        r = requests.get(url)
        if r.status_code == 200:
            with open(ruta, "wb") as f:
                f.write(r.content)
            if is_forge_old:
                subprocess.run(["java", "-jar", jar_name, "--installServer"], cwd=CARPETA_SERVER)
            return jar_name
    except Exception as e:
        print(f"Error: {e}")
    return None

def verificar_java():
    try:
        result = subprocess.run(["java", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def ejecutar_playit():
    agente_playit = os.path.join(CARPETA_SERVER, "playit-agent")
    if platform.system() == "Windows":
        agente_playit += ".exe"
    if not os.path.isfile(agente_playit):
        print("No se encontró el agente de Playit.")
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
                    print("Enlace copiado al portapapeles.")
                except:
                    pass

    threading.Thread(target=mostrar_enlace, daemon=True).start()

def ejecutar_servidor(jar_name, ram):
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

        print("\n1. Seleccionar versión")
        print("2. Iniciar con última configuración")
        print("3. Editar configuración")
        print("4. Borrar todo y salir")
        print("5. Salir")
        opcion = input("Opción: ").strip()

        if opcion == "1":
            tipos = list(versiones.keys())
            for i, t in enumerate(tipos):
                print(f"{i+1}. {t}")
            tipo = tipos[int(input("Tipo: ")) - 1]

            vers = list(versiones[tipo].keys())
            for i, v in enumerate(vers):
                print(f"{i+1}. {v}")
            mc_version = vers[int(input("Versión: ")) - 1]
            sub_version = versiones[tipo][mc_version]
            ram = input("RAM GB: ").strip() or "2"

            with open(config_path, "w") as f:
                f.write(f"tipo={tipo}\nmc_version={mc_version}\nsub_version={sub_version}\nram={ram}\n")

            crear_carpetas()
            jar = descargar_jar(tipo, mc_version, sub_version)
            if jar and verificar_java():
                ejecutar_servidor(jar, ram)

        elif opcion == "2":
            tipo = ultima_config.get("tipo")
            mc_version = ultima_config.get("mc_version")
            sub_version = ultima_config.get("sub_version")
            ram = ultima_config.get("ram", "2")
            if not tipo or not mc_version or not sub_version:
                continue
            jar = descargar_jar(tipo, mc_version, sub_version)
            if jar and verificar_java():
                ejecutar_servidor(jar, ram)

        elif opcion == "3":
            tipo = input("Tipo: ").strip().capitalize()
            mc_version = input("Versión: ").strip()
            if tipo not in versiones or mc_version not in versiones[tipo]:
                continue
            sub_version = versiones[tipo][mc_version]
            ram = input("RAM GB: ").strip()
            with open(config_path, "w") as f:
                f.write(f"tipo={tipo}\nmc_version={mc_version}\nsub_version={sub_version}\nram={ram}\n")

        elif opcion == "4":
            if os.path.exists(config_path):
                os.remove(config_path)
            if os.path.exists(CARPETA_SERVER):
                shutil.rmtree(CARPETA_SERVER)
            break

        elif opcion == "5":
            break

if __name__ == "__main__":
    main()
