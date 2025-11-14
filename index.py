import serial
import time

# Настройка Serial (COM-порт и скорость должны совпадать с Arduino)
arduino = serial.Serial('COM16', 9600, timeout=1)
time.sleep(2)  # ждём подключение

# Стоимость ресурсов
COST_LIGHT = 6
COST_GAS   = 8
COST_WATER = 3

# Для хранения накопленных сумм
total_light = 0
total_gas   = 0
total_water = 0

def analog_to_value(analog, sensor_type):
    """
    Преобразование аналогового значения в "единицы потребления".
    Предположим, max analog 1023 = max cost единицы.
    """
    if sensor_type == 'light':
        return analog / 1023
    elif sensor_type == 'gas':
        return analog / 1023
    elif sensor_type == 'water':
        return analog / 1023

while True:
    try:
        line = arduino.readline().decode().strip()
        if not line:
            continue

        if line == "PAYMENT":
            print("\n==== ОПЛАТА ====")
            total_light = 0
            total_gas = 0
            total_water = 0
            print("Счёт оплачен!\n")
            continue

        # Пример строки: light:512,gas:300,water:800
        parts = line.split(',')
        sensor_data = {}
        for p in parts:
            k, v = p.split(':')
            sensor_data[k] = int(v)

        # Конвертируем аналог в манаты
        total_light += analog_to_value(sensor_data['light'], 'light') * COST_LIGHT
        total_gas   += analog_to_value(sensor_data['gas'], 'gas') * COST_GAS
        total_water += analog_to_value(sensor_data['water'], 'water') * COST_WATER

        total_bill = total_light + total_gas + total_water

        print(f"\rСчёт: Вода={total_water:.2f}₼, Газ={total_gas:.2f}₼, Свет={total_light:.2f}₼ | Итого={total_bill:.2f}₼", end='')

    except KeyboardInterrupt:
        print("\nВыход")
        break
    except Exception as e:
        print("Ошибка:", e)
