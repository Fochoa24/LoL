import requests
import os
import csv
from datetime import datetime
import time

def riot_request(url, headers, max_retries=5):
    """Realiza una petición a la API de Riot respetando los límites de retardo por Rate Limit (429)."""
    retries = 0
    while retries < max_retries:
        response = requests.get(url, headers=headers)
        if response.status_code == 429:
            # Si el header Retry-After está, esperamos esos segundos, sino 5s por defecto
            retry_after = int(response.headers.get("Retry-After", 5))
            print(f"Rate Limit alcanzado (429). Esperando {retry_after} segundos...")
            time.sleep(retry_after)
            retries += 1
        else:
            return response
    # Si falla todas las veces devolvemos la última respuesta (probablemente 429)
    return response



# Pega aquí tu API Key de Riot Games
API_KEY = "RGAPI-8f090076-e621-4117-99dd-dcbc1307420f" 

# La región para buscar el Riot ID suele ser americas, europe o asia.
# 'americas' incluye LAN, LAS, NA, BR.
REGION = "americas" 
# La región específica para datos de Summoner y Liga suele ser la de tu servidor (ej: la1 para LAS, la2 para LAN)
SERVER = "la2" # Cámbialo a "la1" si juegas en LAS, "na1" para NA, etc.

def get_puuid(game_name, tag_line):
    """Obtiene el identificador único (PUUID) del jugador a partir de su Riot ID."""
    url = f"https://{REGION}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{game_name}/{tag_line}"
    headers = {"X-Riot-Token": API_KEY}
    
    response = riot_request(url, headers)
    if response.status_code == 200:
        return response.json().get("puuid")
    else:
        print(f"Error al buscar el jugador {game_name}#{tag_line}. Código: {response.status_code}")
        return None

def get_player_elo(puuid):
    """Obtiene el rango actual de Solo/Duo del jugador usando el PUUID."""
    # Las ligas sí se buscan por servidor específico regional
    url = f"https://{SERVER}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
    headers = {"X-Riot-Token": API_KEY}
    
    response = riot_request(url, headers)
    if response.status_code == 200:
        ligas = response.json()
        for liga in ligas:
            # Buscamos específicamente el rango de Solo/Duo
            if liga.get("queueType") == "RANKED_SOLO_5x5":
                tier = liga.get("tier", "").capitalize() # Ej: "Gold" -> "Gold"
                rank = liga.get("rank", "") # Ej: "IV"
                lp = liga.get("leaguePoints", 0)
                return f"{tier} {rank} ({lp} LP)"
        return "Unranked" # Si no tiene rank en Solo/Duo
    else:
        # Pista para debug si falla
        # print(f"Error ELO: {response.status_code} - ID: {summoner_id}")
        return "Desconocido"

def get_match_ids(puuid, count=10):
    """
    Obtiene la lista de los IDs de las últimas partidas jugadas.
    Filtra por fechas en formato Epoch (Unix Timestamp).
    Start (25/02/2026 00:00:00): 1771988400 (UTC) o acorde a zona horaria
    End (04/03/2026 23:59:59): 1772679599 (UTC) o acorde a zona horaria
    Usaremos números seguros genéricos basados en febrero 2026.
    Para mayor seguridad, convertiremos desde datetime.
    """
    # 6 de marzo 2026
    start_time = int(datetime(2026, 3, 6).timestamp())
    # 13 de marzo 2026 (hasta el final del día)
    end_time = int(datetime(2026, 3, 13, 23, 59, 59).timestamp())
    
    url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids?startTime={start_time}&endTime={end_time}&start=0&count={count}"
    headers = {"X-Riot-Token": API_KEY}
    
    response = riot_request(url, headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error obteniendo el historial de partidas. Código: {response.status_code}")
        return []

def get_match_stats(match_id, puuid):
    """Obtiene los detalles de 1 partida en concreto y extrae KDA, oro y CS."""
    url = f"https://{REGION}.api.riotgames.com/lol/match/v5/matches/{match_id}"
    headers = {"X-Riot-Token": API_KEY}
    
    response = riot_request(url, headers)
    if response.status_code != 200:
        return None

    data = response.json()
    info = data.get("info", {})
    
    # Buscamos las estadísticas específicas de nuestro jugador en la partida
    participants = info.get("participants", [])
    player_data = None
    for p in participants:
        if p.get("puuid") == puuid:
            player_data = p
            break
            
    if not player_data:
        return None
        
    # Extraemos la información solicitada
    kills = player_data.get("kills", 0)
    deaths = player_data.get("deaths", 0)
    assists = player_data.get("assists", 0)
    
    total_gold = player_data.get("goldEarned", 0)
    
    # CS (Creep Score) = Minions de línea + Monstruos de la jungla
    total_cs = player_data.get("totalMinionsKilled", 0) + player_data.get("neutralMinionsKilled", 0)
    
    # Riot devuelve la duración en segundos
    game_duration_seconds = info.get("gameDuration", 0)
    game_duration_minutes = game_duration_seconds / 60.0
    
    # Calculamos valores por minuto
    if game_duration_minutes > 0:
        gold_per_minute = total_gold / game_duration_minutes
        cs_per_minute = total_cs / game_duration_minutes
    else:
        gold_per_minute = 0
        cs_per_minute = 0
        
    return {
        "champion": player_data.get("championName", "Desconocido"),
        "win": player_data.get("win", False),
        "duration": round(game_duration_minutes, 2),
        "kills": kills,
        "deaths": deaths,
        "assists": assists,
        # ALERTA EXCEL: Usamos espacios ' v ' en vez de '/' porque Excel
        # transforma automáticamente cosas como '5/3/10' en '10 de mayo del 2003'
        "kda": f"{kills} - {deaths} - {assists}",
        "total_gold": total_gold,
        "gpm": round(gold_per_minute, 2), # Gold per minute
        "total_cs": total_cs,
        "cspm": round(cs_per_minute, 2)   # CS per minute
    }

def process_player(game_name, tag_line, campeones_filtro, num_partidas=10):
    print(f"\n--- Analizando a {game_name}#{tag_line} ---")
    puuid = get_puuid(game_name, tag_line)
    
    if not puuid:
        return []
        
    # Obtener el ELO actual
    elo_actual = get_player_elo(puuid)
    print(f"ELO Actual (Solo/Duo): {elo_actual}")
        
    match_ids = get_match_ids(puuid, count=num_partidas)
    
    if not match_ids:
        print("No se encontraron partidas o hubo un error.")
        return []
        
    resultados = []
    
    for match_id in match_ids:
        stats = get_match_stats(match_id, puuid)
        if stats:
            # FILTRO DE DURACIÓN (Mínimo 12 minutos)
            if stats["duration"] < 12:
                continue
                
            # FILTRO DE VICTORIA / DERROTA
            nombres_excepcion = ['pixies', 'kore', 'destiny', 'park', 'll destiny', 'axios park']
            mostrar_derrotas = any(nombre in game_name.lower() for nombre in nombres_excepcion)
            
            # Si no es victoria y tampoco está en la lista de excepción, omitimos
            if not stats["win"] and not mostrar_derrotas:
                continue
                
            campeon_jugado = stats['champion'].lower()
            
            # Si hay un filtro de campeones y este campeón NO está en la lista, lo saltamos
            if campeones_filtro and campeon_jugado not in campeones_filtro:
                continue
                
            resultado_txt = "VICTORIA" if stats["win"] else "DERROTA"
            
            print(f"[{resultado_txt}] {stats['champion']} | KDA: {stats['kda']} | CS/m: {stats['cspm']}")
            
            # Preparamos la fila para el CSV
            fila = {
                "Jugador": f"{game_name}#{tag_line}",
                "ELO": elo_actual,
                "Resultado": resultado_txt,
                "Campeón": stats["champion"],
                "Duración (min)": stats["duration"],
                "Asesinatos": stats["kills"],
                "Muertes": stats["deaths"],
                "Asistencias": stats["assists"],
                "KDA": f'="{stats["kda"]}"', # Forzamos formato texto explícito en Excel (="5 - 3 - 10")
                "Oro Total": stats["total_gold"],
                "Oro/Min": stats["gpm"],
                "CS Total": stats["total_cs"],
                "CS/Min": stats["cspm"]
            }
            resultados.append(fila)
            
        # Evitar llegar al límite de la API rate limit (100 req / 2 minutos y 20 req / 1 segundo)
        # Si buscamos 100 partidas necesitamos un pequeño respiro después de cada una
        time.sleep(1.2)
            
    return resultados

def main():
    print("=== SCRIPT DE ANÁLISIS DE PARTIDAS PARA EQUIPO ===")
    
    archivo_jugadores = "jugadores.txt"
    
    # 1. GESTIÓN DE JUGADORES
    if not os.path.exists(archivo_jugadores):
        print(f"\n¡Hola! He creado un archivo llamado '{archivo_jugadores}'.")
        print("Ciérrame, escribe los nombres de tus jugadores y sus campeones.")
        print("Ejemplo de formato: AEG L0s pixies#AEGIS: Aurora, Gwen, Camille")
        print("Si no pones los dos puntos (:), buscaré todos sus campeones.")
        with open(archivo_jugadores, "w", encoding="utf-8") as f:
            f.write("T1 Faker#KR1: Azir, Orianna, Ahri\n")
            f.write("Hide on bush#KR1\n")
        return
        
    with open(archivo_jugadores, "r", encoding="utf-8") as f:
        lineas_jugadores = f.readlines()
        
    jugadores_raw = [linea.strip() for linea in lineas_jugadores if linea.strip() and "#" in linea]
    if not jugadores_raw:
        print(f"\nEl archivo '{archivo_jugadores}' está vacío o mal formateado.")
        return
        
    print(f"\nSe encontraron {len(jugadores_raw)} jugadores en la lista. ¡Comenzando análisis!")
    
    todos_los_resultados = []
    
    # Procesamos cada jugador
    for linea in jugadores_raw:
        campeones_filtro = []
        
        # Verificamos si la línea tiene campeones especificados con ":"
        if ":" in linea:
            parte_jugador, parte_campeones = linea.split(":", 1)
            # Limpiamos y guardamos en minúsculas los campeones
            campeones_filtro = [c.strip().lower() for c in parte_campeones.split(",") if c.strip()]
            jugador = parte_jugador.strip()
        else:
            jugador = linea.strip()
            
        partes = jugador.split("#", 1)
        game_name = partes[0].strip()
        tag_line = partes[1].strip()
        
        # Analizar 10 partidas por jugador (puedes cambiar este número)
        if campeones_filtro:
            print(f"\n[Filtro] Solo analizando: {', '.join([c.capitalize() for c in campeones_filtro])}")
            
        resultados_jugador = process_player(game_name, tag_line, campeones_filtro, num_partidas=100)
        todos_los_resultados.extend(resultados_jugador)
        
    # Exportar a CSV si hay resultados
    if todos_los_resultados:
        fecha_actual = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        nombre_csv = f"reporte_equipo_{fecha_actual}.csv"
        
        # Nombres de las columnas
        campos = [
            "Jugador", "ELO", "Resultado", "Campeón", "Duración (min)", 
            "Asesinatos", "Muertes", "Asistencias", "KDA", 
            "Oro Total", "Oro/Min", "CS Total", "CS/Min"
        ]
        
        print(f"\nGuardando resultados en {nombre_csv}...")
        
        # utf-8-sig para que Excel reconozca bien los acentos
        with open(nombre_csv, "w", newline="", encoding="utf-8-sig") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=campos)
            writer.writeheader()
            for fila in todos_los_resultados:
                writer.writerow(fila)
                
        print(f"¡Listo! Se ha creado el archivo Excel/CSV: '{nombre_csv}'")
        
if __name__ == "__main__":
    if API_KEY == "TU_API_KEY_AQUI":
        print("¡ATENCIÓN! Coloca tu API Key real arriba en el código.")
    else:
        main()
