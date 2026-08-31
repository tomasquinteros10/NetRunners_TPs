from pathlib import Path


def buscar_candidatos_por_seq(ruta_archivo):

    grupos = [
        "#hidd",
        "aurac",
        "bitbr",
        "bitle",
        "click",
        "death",
        "ferne",
        "group",
        "grupo",
        "la la",
        "lan-g",
        "los r",
        "los s",
        "los_c",
        "los-t",
        "lost-",
        "macac",
        "milan",
        "netru",
        "panda",
        "ping ",
        "red h",
        "tcpan",
        "wan-d",
        "wireg"
    ]

    # -------------------------------------------------
    # Buscar frames.bin en la misma carpeta del programa
    # -------------------------------------------------

    ruta_archivo = Path(__file__).resolve().parent / ruta_archivo

    print("Buscando archivo en:")
    print(ruta_archivo)
    print()

    if not ruta_archivo.exists():
        print("ERROR: No se encontró el archivo frames.bin")
        print()
        print("El archivo debería estar en:")
        print(ruta_archivo)
        return

    # -------------------------------------------------
    # Leer archivo binario
    # -------------------------------------------------

    with open(ruta_archivo, "rb") as f:
        datos = f.read()

    print("Archivo encontrado correctamente.")
    print("Tamaño:", len(datos), "bytes")
    print()

    paquetes = []

    # -------------------------------------------------
    # Buscar candidatos
    # -------------------------------------------------

    for offset in range(len(datos) - 7):

        grupo_bytes = datos[offset:offset + 5]

        try:
            grupo = grupo_bytes.decode("ascii")
        except UnicodeDecodeError:
            continue

        if grupo not in grupos:
            continue

        # HEADER
        seq = datos[offset + 5]
        length = datos[offset + 6]

        inicio_payload = offset + 7
        fin_payload = inicio_payload + length

        if fin_payload > len(datos):
            continue

        payload_bytes = datos[inicio_payload:fin_payload]
        payload = payload_bytes.decode("latin-1")

        paquetes.append({
            "offset": offset,
            "grupo": grupo,
            "seq": seq,
            "length": length,
            "payload": payload
        })

    # ========================================
    # MOSTRAR CANDIDATOS POR SEQ
    # ========================================

    print("========================================")
    print(" CANDIDATOS PARA SEQ 1 - 32")
    print("========================================")
    print()

    candidatos_por_seq = {}

    for seq in range(1, 33):

        candidatos = [
            paquete
            for paquete in paquetes
            if paquete["seq"] == seq
        ]

        candidatos_por_seq[seq] = candidatos

        print(f"SEQ {seq:2d}")
        print("-" * 40)

        if not candidatos:
            print("  [NO ENCONTRADO]")
            print()
            continue

        for i, paquete in enumerate(candidatos, start=1):

            print(
                f"  Candidato {i:2d} | "
                f"OFFSET={paquete['offset']:4d} | "
                f"GROUP={paquete['grupo']:<5} | "
                f"LENGTH={paquete['length']:3d} | "
                f"PAYLOAD={paquete['payload']!r}"
            )

        print()

    # ========================================
    # CONCATENAR TODOS LOS PAYLOAD
    # ========================================

    print("========================================")
    print(" CONCATENACIÓN DE LOS RESULTADOS")
    print("========================================")
    print()

    mensaje = ""

    for seq in range(1, 33):

        candidatos = candidatos_por_seq[seq]

        if not candidatos:
            continue

        # Si hay un solo candidato, lo agregamos directamente
        if len(candidatos) == 1:

            payload = candidatos[0]["payload"]
            mensaje += payload

            print(
                f"SEQ {seq:2d} -> {payload!r}"
            )

        # Si hay varios candidatos, mostramos todos
        else:

            print(
                f"SEQ {seq:2d} -> HAY {len(candidatos)} CANDIDATOS"
            )

            for i, candidato in enumerate(candidatos, start=1):

                print(
                    f"          Candidato {i}: "
                    f"{candidato['payload']!r}"
                )

    print()
    print("========================================")
    print(" RESULTADO")
    print("========================================")
    print()
    print(mensaje)
    print()


if __name__ == "__main__":
    buscar_candidatos_por_seq("frames.bin")