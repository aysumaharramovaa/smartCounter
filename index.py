# ===============================
# SmartCounter + Telegram Bot with multilingual support
# ===============================

import serial
import time
import tkinter as tk
from tkinter import ttk
from datetime import datetime
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
import threading

# -------------------------------
# Serial connection to Arduino
# -------------------------------
arduino = serial.Serial('COM16', 9600, timeout=1)
time.sleep(2)

# -------------------------------
# Thresholds
# -------------------------------
LIGHT_THRESHOLD = 300
GAS_THRESHOLD = 350
WATER_THRESHOLD = 400

# -------------------------------
# Usage accumulators
# -------------------------------
total_light = 0
total_gas = 0
total_water = 0
usage_since_last = {'light': 0, 'gas': 0, 'water': 0}
last_payment_date = None
current_values = {'light': 0, 'gas': 0, 'water': 0, 'cardID': "NONE"}

# -------------------------------
# GUI
# -------------------------------
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

lbl_light = ttk.Label(frame, text="Light: 0")
lbl_light.grid(row=0, column=0, padx=20, pady=5)
lbl_gas = ttk.Label(frame, text="Gas: 0")
lbl_gas.grid(row=1, column=0, padx=20, pady=5)
lbl_water = ttk.Label(frame, text="Water: 0")
lbl_water.grid(row=2, column=0, padx=20, pady=5)

lbl_cost_light = ttk.Label(frame, text="Light cost: 0.00 ₼")
lbl_cost_light.grid(row=0, column=1, padx=20, pady=5)
lbl_cost_gas = ttk.Label(frame, text="Gas cost: 0.00 ₼")
lbl_cost_gas.grid(row=1, column=1, padx=20, pady=5)
lbl_cost_water = ttk.Label(frame, text="Water cost: 0.00 ₼")
lbl_cost_water.grid(row=2, column=1, padx=20, pady=5)

lbl_total = ttk.Label(root, text="TOTAL: 0.00 ₼", font=("Segoe UI", 15, "bold"))
lbl_total.pack(pady=10)
lbl_rfid = ttk.Label(root, text="RFID: Not detected", font=("Segoe UI", 12))
lbl_rfid.pack(pady=5)

# -------------------------------
# Functions
# -------------------------------
def analog_to_value(analog):
    return analog / 1023

def update_data():
    global total_light, total_gas, total_water, usage_since_last, last_payment_date, current_values

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

        current_values.update({'light': light, 'gas': gas, 'water': water, 'cardID': cardID})

        # Update GUI
        lbl_light.configure(text=f"Light: {light}")
        lbl_gas.configure(text=f"Gas: {gas}")
        lbl_water.configure(text=f"Water: {water}")
        lbl_rfid.configure(text=f"RFID: {cardID}" if cardID != "NONE" else "RFID: Not detected")

        # Light calculation
        if light < LIGHT_THRESHOLD:
            unit = analog_to_value(light)
            if total_light <= 200:
                total_light += unit * 0.084
            elif total_light <= 300:
                total_light += unit * 0.10
            else:
                total_light += unit * 0.15
            usage_since_last['light'] += unit

        # Gas calculation
        if gas > GAS_THRESHOLD:
            unit = analog_to_value(gas)
            if total_gas <= 1200:
                total_gas += unit * 0.125
            elif total_gas <= 2200:
                total_gas += unit * 0.20
            else:
                total_gas += unit * 0.30
            usage_since_last['gas'] += unit

        # Water calculation
        if water > WATER_THRESHOLD:
            unit = analog_to_value(water)
            total_water += unit * 1.0
            usage_since_last['water'] += unit

        # Update GUI costs
        lbl_cost_light.configure(text=f"Light cost: {total_light:.2f} ₼")
        lbl_cost_gas.configure(text=f"Gas cost: {total_gas:.2f} ₼")
        lbl_cost_water.configure(text=f"Water cost: {total_water:.2f} ₼")
        total = total_light + total_gas + total_water
        lbl_total.configure(text=f"TOTAL: {total:.2f} ₼")

        # Payment logic
        if cardID != "NONE":
            total_light = total_gas = total_water = 0
            usage_since_last = {'light': 0, 'gas': 0, 'water': 0}
            last_payment_date = datetime.now()
            lbl_cost_light.configure(text="Light cost: 0.00 ₼")
            lbl_cost_gas.configure(text="Gas cost: 0.00 ₼")
            lbl_cost_water.configure(text="Water cost: 0.00 ₼")
            lbl_total.configure(text="TOTAL: 0.00 ₼")

    except Exception as e:
        print("Error:", e)

    root.after(200, update_data)

update_data()

# ================================
# Telegram Bot
# ================================
TOKEN = "7978466946:AAF4gBpJRY0ZKFHVEE0l0lDUAU_JpVq30h8"

LANGUAGES = {
    "English": {"start":"Welcome to SmartCounterBot! Select a language:","light":"Light","gas":"Gas","water":"Water","usage":"Usage since last payment","cost":"Cost","last_payment":"Last payment","full_status":"Full Status","total_cost":"Total cost"},
    "Russian": {"start":"Добро пожаловать в SmartCounterBot! Выберите язык:","light":"Свет","gas":"Газ","water":"Вода","usage":"Использовано с последней оплаты","cost":"Стоимость","last_payment":"Последняя оплата","full_status":"Общий статус","total_cost":"Общая стоимость"},
    "Azerbaijani": {"start":"SmartCounterBot-a xoş gəlmisiniz! Zəhmət olmasa dili seçin:","light":"İşıq","gas":"Qaz","water":"Su","usage":"Son ödənişdən bəri istifadə","cost":"Qiymət","last_payment":"Son ödəniş","full_status":"Ümumi vəziyyət","total_cost":"Ümumi məbləğ"},
    "Turkish": {"start":"SmartCounterBot'a hoş geldiniz! Lütfen bir dil seçin:","light":"Işık","gas":"Gaz","water":"Su","usage":"Son ödemeden beri kullanım","cost":"Maliyet","last_payment":"Son ödeme","full_status":"Genel Durum","total_cost":"Toplam maliyet"}
}

user_lang = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [["English", "Russian"], ["Azerbaijani", "Turkish"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)
    await update.message.reply_text("Welcome! Select your language:", reply_markup=reply_markup)

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = update.message.text
    if lang in LANGUAGES:
        user_lang[update.effective_user.id] = lang
        await update.message.reply_text(LANGUAGES[lang]["start"] + "\nCommands: /light /gas /water /status_all")
    else:
        await update.message.reply_text("Invalid selection. Choose language from keyboard.")

def format_status(update, command_name):
    uid = update.effective_user.id
    lang = user_lang.get(uid, "English")
    d = LANGUAGES[lang]
    payment_info = last_payment_date.strftime("%Y-%m-%d %H:%M:%S") if last_payment_date else "No payment yet"

    if command_name == "status_all":
        return (
            f"{d['full_status']}:\n"
            f"{d['light']}: {current_values['light']} | {d['usage']}: {usage_since_last['light']:.2f} | {d['cost']}: {total_light:.2f} ₼\n"
            f"{d['gas']}: {current_values['gas']} | {d['usage']}: {usage_since_last['gas']:.2f} | {d['cost']}: {total_gas:.2f} ₼\n"
            f"{d['water']}: {current_values['water']} | {d['usage']}: {usage_since_last['water']:.2f} | {d['cost']}: {total_water:.2f} ₼\n"
            f"{d['total_cost']}: {total_light+total_gas+total_water:.2f} ₼\n"
            f"{d['last_payment']}: {payment_info}"
        )
    else:
        key = command_name
        val = current_values[key]
        usage = usage_since_last[key]
        cost = {"light": total_light, "gas": total_gas, "water": total_water}[key]
        return f"{d[key]}:\nValue: {val}\n{d['usage']}: {usage:.2f}\n{d['cost']}: {cost:.2f} ₼\n{d['last_payment']}: {payment_info}"

async def light_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(format_status(update, "light"))

async def gas_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(format_status(update, "gas"))

async def water_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(format_status(update, "water"))

async def status_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(format_status(update, "status_all"))

# -------------------------------
# Start Telegram bot in separate thread
# -------------------------------
def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("light", light_status))
    app.add_handler(CommandHandler("gas", gas_status))
    app.add_handler(CommandHandler("water", water_status))
    app.add_handler(CommandHandler("status_all", status_all))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, set_language))

    loop.run_until_complete(app.run_polling())

threading.Thread(target=run_bot, daemon=True).start()

# Start GUI mainloopp
root.mainloop()
