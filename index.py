import serial
import time
import tkinter as tk
from tkinter import ttk
import threading
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ===========================
# ==== Arduino Setup =======
# ===========================
arduino = serial.Serial('COM16', 9600, timeout=1)  # change to your COM port
time.sleep(2)

# Thresholds
LIGHT_THRESHOLD = 300
GAS_THRESHOLD = 350
WATER_THRESHOLD = 400

# Accumulators
total_light = 0
total_gas = 0
total_water = 0
current_values = {'light': 0, 'gas': 0, 'water': 0, 'cardID': 'NONE'}

# ===========================
# ==== GUI Setup ===========
# ===========================
root = tk.Tk()
root.title("Smart Counter Monitor")
root.geometry("480x320")
root.resizable(False, False)

style = ttk.Style()
style.configure("TLabel", font=("Segoe UI", 12))

title = ttk.Label(root, text="SMART COUNTER STATUS", font=("Segoe UI", 16, "bold"))
title.pack(pady=10)

frame = ttk.Frame(root)
frame.pack(pady=10)

# Sensor labels
lbl_light = ttk.Label(frame, text="Light: 0")
lbl_light.grid(row=0, column=0, padx=20, pady=5)

lbl_gas = ttk.Label(frame, text="Gas: 0")
lbl_gas.grid(row=1, column=0, padx=20, pady=5)

lbl_water = ttk.Label(frame, text="Water: 0")
lbl_water.grid(row=2, column=0, padx=20, pady=5)

# Cost labels
lbl_cost_light = ttk.Label(frame, text="Light cost: 0.00 ₼")
lbl_cost_light.grid(row=0, column=1, padx=20, pady=5)

lbl_cost_gas = ttk.Label(frame, text="Gas cost: 0.00 ₼")
lbl_cost_gas.grid(row=1, column=1, padx=20, pady=5)

lbl_cost_water = ttk.Label(frame, text="Water cost: 0.00 ₼")
lbl_cost_water.grid(row=2, column=1, padx=20, pady=5)

# Total
lbl_total = ttk.Label(root, text="TOTAL: 0.00 ₼", font=("Segoe UI", 15, "bold"))
lbl_total.pack(pady=10)

# RFID status
lbl_rfid = ttk.Label(root, text="RFID: Not detected", font=("Segoe UI", 12))
lbl_rfid.pack(pady=5)

# ===========================
# ==== Telegram Bot Setup ===
# ===========================
TOKEN = "7978466946:AAF4gBpJRY0ZKFHVEE0l0lDUAU_JpVq30h8"

# Language dictionary
LANGUAGES = {'en': 'English', 'az': 'Azerbaijani', 'ru': 'Russian', 'tr': 'Turkish'}
user_language = 'en'

# ===========================
# ==== Logic Functions =====
# ===========================
def analog_to_value(analog):
    return analog / 1023  # normalize 0-1

def update_data():
    """Read data from Arduino and update GUI and totals."""
    global total_light, total_gas, total_water, current_values

    try:
        line = arduino.readline().decode().strip()
        if line == "":
            root.after(200, update_data)
            return

        parts = line.split(";")
        if len(parts) < 4:
            root.after(200, update_data)
            return

        light = int(parts[0])
        gas = int(parts[1])
        water = int(parts[2])
        cardID = parts[3]

        current_values = {'light': light, 'gas': gas, 'water': water, 'cardID': cardID}

        # Update GUI
        lbl_light.configure(text=f"Light: {light}")
        lbl_gas.configure(text=f"Gas: {gas}")
        lbl_water.configure(text=f"Water: {water}")
        lbl_rfid.configure(text=f"RFID: {cardID}" if cardID != "NONE" else "RFID: Not detected")

        # --- LIGHT ---
        if light < LIGHT_THRESHOLD:  # inverted logic
            unit = analog_to_value(light)
            if total_light <= 200:
                total_light += unit * 0.084
            elif total_light <= 300:
                total_light += unit * 0.10
            else:
                total_light += unit * 0.15

        # --- GAS ---
        if gas > GAS_THRESHOLD:
            unit = analog_to_value(gas)
            if total_gas <= 1200:
                total_gas += unit * 0.125
            elif total_gas <= 2200:
                total_gas += unit * 0.20
            else:
                total_gas += unit * 0.30

        # --- WATER ---
        if water > WATER_THRESHOLD:
            unit = analog_to_value(water)
            total_water += unit * 1.0  # 1 m³ = 1₼

        # Update costs
        lbl_cost_light.configure(text=f"Light cost: {total_light:.2f} ₼")
        lbl_cost_gas.configure(text=f"Gas cost: {total_gas:.2f} ₼")
        lbl_cost_water.configure(text=f"Water cost: {total_water:.2f} ₼")
        lbl_total.configure(text=f"TOTAL: {total_light + total_gas + total_water:.2f} ₼")

        # CARD PAYMENT: reset totals if card detected
        if cardID != "NONE":
            total_light = total_gas = total_water = 0
            lbl_cost_light.configure(text="Light cost: 0.00 ₼")
            lbl_cost_gas.configure(text="Gas cost: 0.00 ₼")
            lbl_cost_water.configure(text="Water cost: 0.00 ₼")
            lbl_total.configure(text="TOTAL: 0.00 ₼")

    except Exception as e:
        print("Error:", e)

    root.after(200, update_data)

# ===========================
# ==== Telegram Handlers ====
# ===========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Welcome! Use /status to get current consumption.\nUse /language to change language."
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send current readings and costs to user."""
    light = current_values['light']
    gas = current_values['gas']
    water = current_values['water']
    total = total_light + total_gas + total_water
    msg = f"Current readings:\nLight: {light}\nGas: {gas}\nWater: {water}\nTotal cost: {total:.2f} ₼"
    await update.message.reply_text(msg)

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[lang] for lang in LANGUAGES.values()]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    await update.message.reply_text("Choose language:", reply_markup=reply_markup)

async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global user_language
    text = update.message.text
    for key, val in LANGUAGES.items():
        if val == text:
            user_language = key
            await update.message.reply_text(f"Language changed to {val}")
            return

# ===========================
# ==== Register Telegram Bot
# ===========================
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("status", status))
app.add_handler(CommandHandler("language", set_language))
app.add_handler(CommandHandler("lang", change_language))

def run_bot():
    app.run_polling()

# ===========================
# ==== Run Bot in Thread ====
# ===========================
bot_thread = threading.Thread(target=run_bot)
bot_thread.start()

# ===========================
# ==== Start GUI Loop =======
# ===========================
update_data()
root.mainloop()
