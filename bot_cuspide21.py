# -*- coding: utf-8 -*-
# Bot de trading simulado - Estrategia Cúspide21
# Ejecutar con: python3 bot_cuspide21.py desde la terminal

import time
import requests

# --- CONFIGURACIÓN ---
TELEGRAM_TOKEN = "8301014669:AAF_qU0WN5SzBlXZc9tOQ3m1-CMn-1Yta8k"
TELEGRAM_USER_ID = 1115962487

SCAN_INTERVAL = 5 * 60  # cada 5 minutos
MAX_POSITIONS = 3
CAPITAL_TOTAL = 30.0
capital_libre = CAPITAL_TOTAL
ganancia_acumulada = 0.0
posiciones = []

trading_activo = False
last_update_id = 0


# --- FUNCIONES ---
def enviar_mensaje(texto):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_USER_ID, "text": texto}
    try:
        requests.post(url, data=data)
    except:
        print("❌ Error enviando mensaje a Telegram")


def obtener_precio(symbol):
    try:
        r = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}")
        return float(r.json()["price"])
    except:
        return None


def escanear_mercado():
    try:
        r = requests.get("https://api.binance.com/api/v3/ticker/24hr")
        data = r.json()
        candidatos = []
        for item in data:
            if item["symbol"].endswith("USDT") and float(item["quoteVolume"]) > 5_000_000:
                cambio = float(item["priceChangePercent"])
                if cambio > 0.5:
                    candidatos.append((item["symbol"], cambio))
        candidatos.sort(key=lambda x: x[1], reverse=True)
        return [c[0] for c in candidatos[:5]]
    except:
        return []


def abrir_posicion(symbol):
    global capital_libre, posiciones
    precio = obtener_precio(symbol)
    if not precio:
        return
    inversion = CAPITAL_TOTAL * 0.2
    if inversion > capital_libre:
        return

    take_profit = precio * 1.02
    stop_loss = precio * 0.99
    ganancia_neta = (take_profit * (1 - 0.001)) - (precio * (1 + 0.001))
    if ganancia_neta / precio < 0.002:
        return

    cantidad = inversion / precio
    posiciones.append({
        "symbol": symbol,
        "precio": precio,
        "cantidad": cantidad,
        "stop_loss": stop_loss,
        "take_profit": take_profit
    })
    capital_libre -= inversion
    enviar_mensaje(f"🟢 Compra simulada: {symbol} @ ${precio:.4f}")


def revisar_posiciones():
    global capital_libre, ganancia_acumulada, posiciones
    nuevas_posiciones = []
    for p in posiciones:
        actual = obtener_precio(p["symbol"])
        if not actual:
            nuevas_posiciones.append(p)
            continue
        inversion = p["precio"] * p["cantidad"]
        venta = actual * p["cantidad"]
        comision_compra = inversion * 0.001
        comision_venta = venta * 0.001
        ganancia_neta = venta - inversion - comision_compra - comision_venta
        if actual >= p["take_profit"] or actual <= p["stop_loss"]:
            capital_libre += venta - comision_venta
            ganancia_acumulada += ganancia_neta
            estado = "✅ TP" if actual >= p["take_profit"] else "🔴 SL"
            enviar_mensaje(f"{estado} {p['symbol']} @ ${actual:.4f} | G/P: ${ganancia_neta:.2f}")
        else:
            nuevas_posiciones.append(p)
    posiciones = nuevas_posiciones


def procesar_comandos():
    global trading_activo, last_update_id, capital_libre, CAPITAL_TOTAL
    try:
        r = requests.get(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id + 1}")
        updates = r.json()["result"]
        for u in updates:
            last_update_id = u["update_id"]
            msg = u["message"]["text"]
            if u["message"]["chat"]["id"] != TELEGRAM_USER_ID:
                continue
            if msg.startswith("/start"):
                trading_activo = True
                enviar_mensaje("✅ Bot activado")
            elif msg.startswith("/stop"):
                trading_activo = False
                enviar_mensaje("🛑 Bot detenido")
            elif msg.startswith("/capital"):
                try:
                    nuevo = float(msg.split()[1])
                    CAPITAL_TOTAL = nuevo
                    capital_libre = nuevo
                    enviar_mensaje(f"💰 Capital ajustado a ${nuevo:.2f}")
                except:
                    enviar_mensaje("❌ Usa el formato: /capital 50")
            elif msg.startswith("/status"):
                enviar_mensaje(
                    f"📊 Estado:\nCapital: ${CAPITAL_TOTAL:.2f}\nLibre: ${capital_libre:.2f}\nG/P: ${ganancia_acumulada:.2f}\nActivas: {len(posiciones)}"
                )
    except:
        pass


# --- EJECUCIÓN ---
enviar_mensaje("🤖 Bot listo. Usa /start para comenzar.")
tiempo_ultimo = 0

while True:
    procesar_comandos()
    if trading_activo and time.time() - tiempo_ultimo > SCAN_INTERVAL:
        revisar_posiciones()
        candidatos = escanear_mercado()
        for c in candidatos:
            if len(posiciones) >= MAX_POSITIONS:
                break
            abrir_posicion(c)
        enviar_mensaje(
            f"📈 Reporte:\nCapital: ${CAPITAL_TOTAL:.2f}\nLibre: ${capital_libre:.2f}\nG/P: ${ganancia_acumulada:.2f}\nActivas: {len(posiciones)}"
        )
        tiempo_ultimo = time.time()
    time.sleep(5)
