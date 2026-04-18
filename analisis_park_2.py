import sys
import os
import time
sys.path.append(r'c:\Users\Administrator\Documents\LoL')
import analizador

def run_custom():
    jugadores = [
        ("Axios Park", "MAGIA", ["caitlyn", "xayah", "jhin"])
    ]
    
    resultados_totales = []
    with open('salida_limpia_2.txt', 'w', encoding='utf-8') as f:
        for game_name, tag_line, campeones in jugadores:
            f.write(f"\n--- Analizando a {game_name}#{tag_line} ---\n")
            try:
                res = analizador.process_player(game_name, tag_line, campeones, num_partidas=100)
                resultados_totales.extend(res)
            except Exception as e:
                f.write(f"Error procesando {game_name}: {e}\n")
                
        if resultados_totales:
            for r in resultados_totales:
                f.write(f"{r['Jugador']} | {r['Campeón']} | {r['Resultado']} | KDA: {r['KDA']} | CS/m: {r['CS/Min']} | Mins: {r['Duración (min)']}\n")

if __name__ == "__main__":
    time.sleep(2) # just a tiny breather
    run_custom()
