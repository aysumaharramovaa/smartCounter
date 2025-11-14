import serial
import time
import threading
from datetime import datetime
import tkinter as tk
from tkinter import ttk
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

# ====== Serial connection with Arduino ======
arduino = serial.Serial('COM16', 9600, timeout=1)
time.sleep(2)

# ====== Thresholds ======
LIGHT_THRESHOLD = 300
GAS_THRESHOLD = 350
WATER_THRESHOLD = 400

# ====== Accumulators ======
total_light = 0
total_gas = 0
total_water = 0
last_payment_time = None

# Current sensor readings
current_values = {"light":0, "gas":0, "water":0}
current_cardID = "NONE"

# Default language
user_language = "EN"

# =========================================================
# Language messages
# =========================================================
MESSAGES = {
    "EN": {
        "start": "Hello! I am SmartCounter bot.\nCommands:\n/water - show water bill\n/gas - show gas bill\n/light - show light bill\n/total - show total bill\n/last_payment - show last payment info\n/language - select language",
        "water": "Water:\nUsed: {used:.2f} m³\nBill since last payment: {bill:.2f} ₼",
        "gas": "Gas:\nUsed: {used:.2f} m³\nBill since last payment: {bill:.2f} ₼",
        "light": "Light:\nUsed: {used:.2f} kWh\nBill since last payment: {bill:.2f} ₼",
        "total": "Total bill since last payment:\nLight: {light:.2f} ₼\nGas: {gas:.2f} ₼\nWater: {water:.2f} ₼\nTotal: {total:.2f} ₼",
        "last_payment": "Last payment: {time}\nBill since last payment:\nLight: {light:.2f} ₼, Gas: {gas:.2f} ₼, Water: {water:.2f} ₼",
        "no_payment": "No payments have been made yet.",
        "choose_language": "Please choose your language:"
    },
    "RU": {
        "start": "Привет! Я бот SmartCounter.\nКоманды:\n/water - показать счёт за воду\n/gas - показать счёт за газ\n/light - показать счёт за свет\n/total - показать общий счёт\n/last_payment - информация о последней оплате\n/language - выбрать язык",
        "water": "Вода:\nИспользовано: {used:.2f} м³\nСчёт с последней оплаты: {bill:.2f} ₼",
        "gas": "Газ:\nИспользовано: {used:.2f} м³\nСчёт с последней оплаты: {bill:.2f} ₼",
        "light": "Свет:\nИспользовано: {used:.2f} кВт·ч\nСчёт с последней оплаты: {bill:.2f} ₼",
        "total": "Общий счёт с последней оплаты:\nСвет: {light:.2f} ₼\nГаз: {gas:.2f} ₼\nВода: {water:.2f} ₼\nИтого: {total:.2f} ₼",
        "last_payment": "Последняя оплата: {time}\nСчёт с последней оплаты:\nСвет: {light:.2f} ₼, Газ: {gas:.2f} ₼, Вода: {water:.2f} ₼",
        "no_payment": "Оплаты ещё не было.",
        "choose_language": "Пожалуйста, выберите язык:"
    },
    "AZ": {
        "start": "Salam! Mən SmartCounter botam.\nƏmrlər:\n/water - su haqqını göstər\n/gas - qaz haqqını göstər\n/light - işıq haqqını göstər\n/total - ümumi hesab\n/last_payment - son ödəniş məlumatı\n/language - dili seç",
        "water": "Su:\nİstifadə: {used:.2f} m³\nSon ödənişdən bəri hesab: {bill:.2f} ₼",
        "gas": "Qaz:\nİstifadə: {used:.2f} m³\nSon ödənişdən bəri hesab: {bill:.2f} ₼",
        "light": "İşıq:\nİstifadə: {used:.2f} kWh\nSon ödənişdən bəri hesab: {bill:.2f} ₼",
        "total": "Son ödənişdən bəri ümumi hesab:\nİşıq: {light:.2f} ₼\nQaz: {gas:.2f} ₼\nSu: {water:.2f} ₼\nÜmumi: {total:.2f} ₼",
        "last_payment": "Son ödəniş: {time}\nSon ödənişdən bəri hesab:\nİşıq: {light:.2f} ₼, Qaz: {gas:.2f} ₼, Su: {water:.2f} ₼",
        "no_payment": "Hələ ödəniş edilməyib.",
        "choose_language": "Zəhmət olmasa dilinizi seçin:"
    },
    "TR": {
        "start": "Merhaba! Ben SmartCounter botum.\nKomutlar:\n/water - su faturası göster\n/gas - gaz faturası göster\n/light - elektrik faturası göster\n/total - toplam faturayı göster\n/last_payment - son ödeme bilgisi\n/language - dili seç",
        "water": "Su:\nKullanım: {used:.2f} m³\nSon ödemeden beri fatura: {bill:.2f} ₼",
        "gas": "Gaz:\nKullanım: {used:.2f} m³\nSon ödemeden beri fatura: {bill:.2f} ₼",
        "light": "Elektrik:\nKullanım: {used:.2f} kWh\nSon ödemeden beri fatura: {bill:.2f} ₼",
        "total": "Son ödemeden beri toplam fatura:\nElektrik: {light:.2f} ₼\nGaz: {gas:.2f} ₼\nSu: {water:.2f} ₼\nToplam: {total:.2f} ₼",
        "last_payment": "Son ödeme: {time}\nSon ödemeden beri fatura:\nElektrik: {light:.2f} ₼, Gaz: {gas:.2f} ₼, Su: {water:.2f} ₼",
        "no_payment": "Henüz ödeme yapılmadı.",
        "choose_language": "Lütfen dilinizi seçin:"
    }
}

# =========================================================
# Telegram bot functions
# =========================================================
BOT_TOKEN = "7978466946:AAF4gBpJRY0ZKFHVEE0l0lDUAU_JpVq30h8"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ /start command """
    await update.message.reply_text(MESSAGES[user_language]["start"])

async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ Show language selection buttons """
    keyboard = [
        [InlineKeyboardButton("English", callback_data="EN"),
         InlineKeyboardButton("Русский", callback_data="RU")],
        [InlineKeyboardButton("Azərbaycan", callback_data="AZ"),
         InlineKeyboardButton("Türkçe", callback_data="TR")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(MESSAGES[user_language]["choose_language"], reply_markup=reply_markup)

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ Handle language selection """
    global user_language
    query = update.callback_query
    await query.answer()
    user_language = query.data
    await query.edit_message_text(text=f"Language set to {user_language}")

# Command handlers for bills
async def water(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        MESSAGES[user_language]["water"].format(used=current_values["water"], bill=total_water)
    )

async def gas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        MESSAGES[user_language]["gas"].format(used=current_values["gas"], bill=total_gas)
    )

async def light(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        MESSAGES[user_language]["light"].format(used=current_values["light"], bill=total_light)
    )

async def total(update: Update, context: ContextTypes.DEFAULT_TYPE):
    total_sum = total_light + total_gas + total_water
    await update.message.reply_text(
        MESSAGES[user_language]["total"].format(
            light=total_light, gas=total_gas, water=total_water, total=total_sum
        )
    )

async def last_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if last_payment_time:
        await update.message.reply_text(
            MESSAGES[user_language]["last_payment"].format(
                time=last_payment_time.strftime('%Y-%m-%d %H:%M:%S'),
                light=total_light, gas=total_gas, water=total_water
            )
        )
    else:
        await update.message.reply_text(MESSAGES[user_language]["no_payment"])

def run_telegram_bot():
    """ Run Telegram bot in separate thread """
    asyncio.set_event_loop(asyncio.new_event_loop())
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("language", language))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(CommandHandler("water", water))
    app.add_handler(CommandHandler("gas", gas))
    app.add_handler(CommandHandler("light", light))
    app.add_handler(CommandHandler("total", total))
    app.add_handler(CommandHandler("last_payment", last_payment))
    print("Telegram bot running...")
    app.run_polling()

# =========================================================
# Arduino reading thread
# =========================================================
def analog_to_value(analog):
    return analog / 1023

def read_from_arduino():
    global total_light, total_gas, total_water, last_payment_time, current_values, current_cardID
    while True:
        try:
            line = arduino.readline().decode().strip()
            if line == "":
                continue
            parts = line.split(";")
            if len(parts) < 4:
                continue
            light = int(parts[0])
            gas = int(parts[1])
            water = int(parts[2])
            cardID = parts[3]
            current_values["light"] = light
            current_values["gas"] = gas
            current_values["water"] = water
            current_cardID = cardID
            # --- LIGHT calculation ---
            if light < LIGHT_THRESHOLD:
                unit = analog_to_value(light)
                if total_light <= 200:
                    total_light += unit * 0.084
                elif total_light <= 300:
                    total_light += unit * 0.10
                else:
                    total_light += unit * 0.15
            # --- GAS calculation ---
            if gas > GAS_THRESHOLD:
                unit = analog_to_value(gas)
                if total_gas <= 1200:
                    total_gas += unit * 0.125
                elif total_gas <= 2200:
                    total_gas += unit * 0.20
                else:
                    total_gas += unit * 0.30
            # --- WATER calculation ---
            if water > WATER_THRESHOLD:
                unit = analog_to_value(water)
                total_water += unit * 1.0
            # Payment
            if cardID != "NONE":
                total_light = 0
                total_gas = 0
                total_water = 0
                last_payment_time = datetime.now()
        except Exception as e:
            print("Arduino read error:", e)

# =========================================================
# GUI update loop
# =========================================================
def update_gui():
    lbl_light.configure(text=f"Light: {current_values['light']}")
    lbl_gas.configure(text=f"Gas: {current_values['gas']}")
    lbl_water.configure(text=f"Water: {current_values['water']}")
    if current_cardID != "NONE":
        lbl_rfid.configure(text=f"RFID: {current_cardID}")
    else:
        lbl_rfid.configure(text="RFID: Not detected")
    lbl_cost_light.configure(text=f"Light cost: {total_light:.2f} ₼")
    lbl_cost_gas.configure(text=f"Gas cost: {total_gas:.2f} ₼")
    lbl_cost_water.configure(text=f"Water cost: {total_water:.2f} ₼")
    lbl_total.configure(text=f"TOTAL: {total_light + total_gas + total_water:.2f} ₼")
    root.after(200, update_gui)

# =========================================================
# Main execution
# =========================================================
threading.Thread(target=read_from_arduino, daemon=True).start()
threading.Thread(target=run_telegram_bot, daemon=True).start()
update_gui()
root.mainloop()
