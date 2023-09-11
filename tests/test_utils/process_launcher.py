import multiprocessing
import subprocess
import argparse
import os
from test_FIFO import access_resource_FIFO


def process_launcher(n_processes, n_sc, service):
    # Crear lista para almacenar los procesos
    processes = []

    access_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTY4NzQ0OTgyOCwianRpIjoiNDI4MjYwNTYtZTdlMC00Y2MxLWE1MzYtMmZiZmQzYzcxMjdlIiwidHlwZSI6ImFjY2VzcyIsInN1YiI6InRlc3QiLCJuYmYiOjE2ODc0NDk4MjgsImV4cCI6MTY4NzQ1MDcyOH0.0C2HvI8zPKqsOd4MC2_XtYWD8kD3Wxs6Cu4WyfhMLr4"

    # Crear y lanzar los procesos
    for i in range(n_processes):
        if service == "FIFO":
            process = multiprocessing.Process(target=access_resource_FIFO, args=(access_token, i, n_sc))
        process.start()
        processes.append(process)

    # Esperar a que todos los procesos terminen
    for process in processes:
        process.join()

    #borramos log anteriores
    subprocess.run("rm logs_FIFO/log.txt", shell=True)
    subprocess.run("rm logs_FIFO/logOrdenado.txt", shell=True)

    # Combinar archivos de registro en uno solo
    subprocess.run("cat logs_FIFO/log-*.txt > logs_FIFO/log.txt", shell=True)

    # Ordenar el archivo combinado por campo de tiempo
    subprocess.run("sort -k 3 logs_FIFO/log.txt > logs_FIFO/logOrdenado.txt", shell=True)

    # Eliminar los archivos de registro individuales
    subprocess.run("rm logs_FIFO/log-*.txt", shell=True)

if __name__ == "__main__":
    # Parsear argumentos de línea de comandos
    parser = argparse.ArgumentParser()
    parser.add_argument("--n_processes", type=int, default=6, help="Número de procesos")
    parser.add_argument("--n_sc", type=int, default=10, help="Número de secciones críticas por proceso")
    parser.add_argument("--service", type=str, default="FIFO", help="Tipo de servicio")
    args = parser.parse_args()

    # Llamar a la función process_launcher con los argumentos
    process_launcher(args.n_processes, args.n_sc, args.service)