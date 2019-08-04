#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" Reloj.py

   Saca la hora actual en un display de 4x7 segmentos (TM1637)
   En un LCD (LCD1602) saca:
      - En la primera fila fecha
      - En la segunda datos meteorológicos obtenidos por MQTT.
        Estos datos los obtiene nodered de lasky.
      - Conectado buzzer que dará los cuartos y las horas
   Las razones por la que usar nodered para obtener los datos meteorologicos son:
      1.- Tener los datos disponibles para esta y otras aplicaciones.
      2.- Desacoplar la ejecución del reloj de la obtención y tratamiento
          de los datos.

   Por MQTT puedo recibir una petición de alarma de un determinado número
   de minutos. Topic: /torredembarra/reloj7/setalarma
   En este caso:
      - Publico el día y hora de lanzamiento de la alarma.
        Topic: /torredembarra/reloj7/alarma
      - A la hora de vencimiento llamo a una API que hace sonar un
        timbre en mini. Publico "" como hora de vencimiento

"""

import sys
from time import sleep
from datetime import datetime
import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
import tm1637                    # 7 segmentos
import i2c_LCD_driver            # va por i2c (bus 1)
from subprocess import call

# GPIOs TM1637
# CLK -> GPIO23 (Pin 16)
# Di0 -> GPIO24 (Pin 18)
Display = tm1637.TM1637(23,24,tm1637.BRIGHT_TYPICAL)

# LCD1602
lcd = i2c_LCD_driver.lcd()

# Cliente MQTT
MQTT_USER = 'pi'
MQTT_PASS = 'picom222'
MQTT_HOST = 'localhost'
MQTT_PORT = 1883     #default
MQTT_RAIZ = '/torredembarra/DatosMeteo/#'
MQTT_KEEP = 65535    # Un montón de segundos
mqttc = mqtt.Client(client_id='Reloj_de_la_cajita', clean_session=True, userdata=None,
      protocol=mqtt.MQTTv311, transport='tcp')

# Variables globales
dias = ['Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab', 'Dom']
meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul',
         'Ago', 'Set', 'Oct', 'Nov', 'Dic']
direcciones = ['Tramuntana', 'Gregal', 'Llevant', 'Xaloc',
               'Migjorn', 'Garbi', 'Ponent', 'Mestral']
fuerzas = ['F0-Calma', 'F1-Ventolina', 'F2-Flojito  ',
           'F3-Flojo', 'F4-Bonancible', 'F5-Fresquito',
           'F6-Fresco', 'F7-Frescacho', 'F8-Temporal ',
           'F9-T fuerte', 'F10-T duro', 'F11-T muy duro',
           'F12-T huracanado']

# Variables globales de estado del tiempo
temperatura = 'desc'
humedad     = 'desc'
presion     = 'desc'
viento_vel  = 0
viento_dir  = 0
amanecer    = 'desc'
anochecer   = 'desc'
cielo       = 'desc'

# Cada cuanto tiempo cambio de información meteorológica
T_CARRUSEL  = 5   # en segundos
MAX_INFO    = 7   # Número de informaciones que saco en el carrusel
turno    = 0

def carrusel():
   # Va sacando generando información meteorológica
   global turno

   if turno == 0:
      c = cielo
   elif turno == 1: # temperatura y humedad
      c = 'T:%s%cC  H:%s%%' % (temperatura, chr(0b11011111), humedad)
   elif turno == 2: # presión
      c = 'P:%sHPa' % presion
   elif turno == 3: # velocidad del viento
      c = 'V:%dkm/h - %dKn' % CalcKmKn()
   elif turno == 4: # Fuerza del viento
      c = CalcFuerza(CalcKmKn()[1])
   elif turno == 5: # dirección viento
      c = dirViento()
   elif turno == 6: # amanecer
      amh = int(amanecer.split(':')[0])
      amm = int(amanecer.split(':')[1])
      anh = int(anochecer.split(':')[0])
      anm = int(anochecer.split(':')[1])
      c = '%02d:%02d - %02d:%02d' % (amh, amm, anh, anm)
   turno = (turno+1) % MAX_INFO
   return(c)



def on_message(client, userdata, message):
   # cuando recibo un mensaje MQTT actualizo las
   # variables globales correspondientes
   global temperatura, humedad, viento_vel, viento_dir
   global amanecer, anochecer, cielo, presion

   if message.topic == '/torredembarra/DatosMeteo/tempExt/estado':
      temperatura = message.payload
   elif message.topic == '/torredembarra/DatosMeteo/humedadExt/estado':
      humedad = message.payload
   elif message.topic == '/torredembarra/DatosMeteo/VientoVel/estado':
      viento_vel = float(message.payload)
   elif message.topic == '/torredembarra/DatosMeteo/VientoDir/estado':
      viento_dir = int(message.payload)
   elif message.topic == '/torredembarra/DatosMeteo/amanecer/estado':
      amanecer = message.payload
   elif message.topic == '/torredembarra/DatosMeteo/anochecer/estado':
      anochecer = message.payload
   elif message.topic == '/torredembarra/DatosMeteo/detalle/estado':
      cielo = message.payload
   elif message.topic == '/torredembarra/DatosMeteo/presion/estado':
      presion = message.payload





def CalcKmKn():
   # La velocidad del vientollega en m/s
   # devuelvo en Km/h y Kn
   return (round(viento_vel * 3.6), round(viento_vel * 3.6 / 1.852))

def CalcFuerza(velKn):
   # En base a la velocidad del viento en Kn
   # debuelve la Fuerza del viento segun escala Beaufort

   if(velKn == 0): 
      DescF = fuerzas[0]
   elif (velKn >=  1 and velKn <= 3):
      DescF = fuerzas[1]
   elif (velKn >=  4 and velKn <= 6):
      DescF = fuerzas[2]
   elif (velKn >=  7 and velKn <= 10):
      DescF = fuerzas[3]
   elif (velKn >= 11 and velKn <= 16):
      DescF = fuerzas[4]
   elif (velKn >= 17 and velKn <= 21):
      DescF = fuerzas[5]
   elif (velKn >= 22 and velKn <= 27):
      DescF = fuerzas[6]
   elif (velKn >= 28 and velKn <= 33):
    DescF = fuerzas[7]
   elif (velKn >= 44 and velKn <= 40):
      DescF = fuerzas[8]
   elif (velKn >= 41 and velKn <= 47):
      DescF = fuerzas[9]
   elif (velKn >= 48 and velKn <= 55):
      DescF = fuerzas[10]
   elif (velKn >= 56 and velKn <= 63):
      DescF = fuerzas[11]
   elif (velKn > 64):
      DescF = fuerzas[12]
   return(DescF)


def dirViento():
   # Redondea la dirección del viento a cuartos y
   # devuelve el nombre del viento
   aux1 = viento_dir % 45;
   aux2 = 45 if aux1 >= 22.5 else 0
   aux3 = viento_dir - aux1
   if aux2+aux3 == 360:
      dir = 0
   else:
      dir = (aux2 + aux3) / 45
   return('%03d %s' % (viento_dir, direcciones[dir]))



def ini():
   Display.Clear()
   lcd.lcd_clear()
   Display.ShowDoublepoint(1)
   Display.Show([8,8,8,8])
   lcd.lcd_display_string('Inicializando', 1)
   lcd.lcd_display_string('conexion MQTT', 2)

   mqttc.on_message = on_message
   mqttc.username_pw_set(MQTT_USER, MQTT_PASS)
   mqttc.connect(MQTT_HOST, MQTT_PORT, MQTT_KEEP)
   mqttc.subscribe(MQTT_RAIZ, qos=0)
   mqttc.loop_start()
   lcd.lcd_clear()


def main():
   ini()
   ult_dia  = 'desc'
   ult_hora = -1
   ult_min  = -1
   ult_seg  = -1
   escrito  = False
   sonado   = False

   while True:
      now = datetime.now()
      #ahora = now.strftime('%H:%M:%S')
      hora = now.hour
      min  = now.minute
      seg  = now.second
      if seg != ult_seg:
         ult_seg = seg
         Display.ShowDoublepoint((int(seg)+1)%2)
      if min != ult_min:
         ult_min = min
         Display.Show([0 if hora < 10 else hora/10, hora%10, 0 if min < 10 else min/10, min%10])
      if now.day != ult_dia:
         ult_dia = now.day
         c = '%s  %d-%s-%d ' % (dias[now.weekday()], now.day, meses[now.month-1], now.year)
         lcd.lcd_display_string('                ', 1)
         lcd.lcd_display_string(c, 1)
      if int(seg)%T_CARRUSEL == 0:
         if not escrito:
            lcd.lcd_display_string('                ', 2)
            lcd.lcd_display_string(carrusel(), 2)
            escrito = True
      else:
         escrito = False

      if not sonado and seg == '00' and min in('00', '15', '30', '45'):
         sonado = True
         comando = "python campanadas.py 25 %d %d &" % (hora, min)
         call(comando, shell=True)
      if sonado and seg == 1:
         sonado = False

      sleep(.1)


if __name__ == "__main__":
   try:
      main()
   except KeyboardInterrupt:
      print('')
      exit(0)

