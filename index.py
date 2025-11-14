import serial
import time
import tkinter as tk
from tkinter import ttk

# ====== Serial connection ======
arduino = serial.Serial('COM16', 9600, timeout=1)   # ← измени на свой порт!
time.sleep(2)

# ====== Thresholds ======
LIGHT_THRESHOLD = 300   # теперь счёт идёт, если light < LIGHT_THRESHOLD
GAS_THRESHOLD = 350
WATER_THRESHOLD = 400

# ====== Accumulators =====
total_light = 0
total_gas = 0
total_water = 0

# =========================================================
#                          GUI
# =========================================================
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

# Sensor values
lbl_light = ttk.Label(frame, text="Light: 0")
lbl_light.grid(row=0, column=0, padx=20, pady=5)

lbl_gas = ttk.Label(frame, text="Gas: 0")
lbl_gas.grid(row=1, column=0, padx=20, pady=5)

lbl_water = ttk.Label(frame, text="Water: 0")
lbl_water.grid(row=2, column=0, padx=20, pady=5)

# Costs
lbl_cost_light = ttk.Label(frame, text="Light cost: 0.00 ₼")
lbl_cost_light.grid(row=0, column=1, padx=20, pady=5)

lbl_cost_gas = ttk.Label(frame, text="Gas cost: 0.00 ₼")
lbl_cost_gas.grid(row=1, column=1, padx=20, pady=5)

lbl_cost_water = ttk.Label(frame, text="Water cost: 0.00 ₼")
lbl_cost_water.grid(row=2, column=1, padx=20, pady=5)

# TOTAL
lbl_total = ttk.Label(root, text="TOTAL: 0.00 ₼", font=("Segoe UI", 15, "bold"))
lbl_total.pack(pady=10)

# RFID status
lbl_rfid = ttk.Label(root, text="RFID: Not detected", font=("Segoe UI", 12))
lbl_rfid.pack(pady=5)

# =========================================================
#                     Logic functions
# =========================================================

def analog_to_value(analog):
    return analog / 1023  # нормализация 0-1


def update_data():
    global total_light, total_gas, total_water

    try:
        line = arduino.readline().decode().strip()

        if line == "":
            root.after(200, update_data)
            return

        # Format: "light;gas;water;cardID"
        parts = line.split(";")

        if len(parts) < 4:
            root.after(200, update_data)
            return

        light = int(parts[0])
        gas = int(parts[1])
        water = int(parts[2])
        cardID = parts[3]

        # Update sensor labels
        lbl_light.configure(text=f"Light: {light}")
        lbl_gas.configure(text=f"Gas: {gas}")
        lbl_water.configure(text=f"Water: {water}")

        # Update RFID label
        if cardID != "NONE":
            lbl_rfid.configure(text=f"RFID: {cardID}")
        else:
            lbl_rfid.configure(text="RFID: Not detected")

        # ============================
        #        COST CALCULATOR
        # ============================

        # --- LIGHT (кВт·ч) ---
        if light < LIGHT_THRESHOLD:  # инвертированная логика
            unit = analog_to_value(light)  # псевдо-кВт
            # Тарифы
            if total_light <= 200:
                total_light += unit * 0.084
            elif total_light <= 300:
                total_light += unit * 0.10
            else:
                total_light += unit * 0.15

        # --- GAS (м³) ---
        if gas > GAS_THRESHOLD:
            unit = analog_to_value(gas)  # псевдо-куб
            if total_gas <= 1200:
                total_gas += unit * 0.125
            elif total_gas <= 2200:
                total_gas += unit * 0.20
            else:
                total_gas += unit * 0.30

        # --- WATER (м³) ---
        if water > WATER_THRESHOLD:
            unit = analog_to_value(water)
            total_water += unit * 1.0  # 1 м³ = 1₼

        # Update labels
        lbl_cost_light.configure(text=f"Light cost: {total_light:.2f} ₼")
        lbl_cost_gas.configure(text=f"Gas cost: {total_gas:.2f} ₼")
        lbl_cost_water.configure(text=f"Water cost: {total_water:.2f} ₼")

        # Total
        total = total_light + total_gas + total_water
        lbl_total.configure(text=f"TOTAL: {total:.2f} ₼")

        # CARD PAYMENT LOGIC — если приложили карту → сброс
        if cardID != "NONE":
            total_light = 0
            total_gas = 0
            total_water = 0

            lbl_cost_light.configure(text="Light cost: 0.00 ₼")
            lbl_cost_gas.configure(text="Gas cost: 0.00 ₼")
            lbl_cost_water.configure(text="Water cost: 0.00 ₼")
            lbl_total.configure(text="TOTAL: 0.00 ₼")

    except Exception as e:
        print("Error:", e)

    root.after(200, update_data)


# Start loop
update_data()
root.mainloop()
