# RPi-TM1637-LCD1602-Clock & weather information
Reloj basado en RPi + TM1637 + LCD1602 i2c  
  
<img src="https://user-images.githubusercontent.com/53425312/62407813-fa581100-b5be-11e9-94c8-d77e3e2bd80b.jpg" width="350"/>

## Componentes
  * RPi 3+
  * TM1637
  * LCD1602 i2c
  
## Descripción  
Reloj con información meteorológica.  
Funciones:
 * hora + minutos mostrados en un módulo de 4x7segmentos TM1637
 * Fecha + información meteorológica mostrados en un LCD1602  
 * Alarma: Seteo día hora de alarma mediante un mensaje MQTT. A vencimiento llamo a una API en mini que hará sonar un timbre
  
  La información metorológica la obtiene de una cuenta gratuita de openweathermap.  
  Se consulta mediante nodered instalado en el mismo host.  
  La información se publica via MQTT para su uso por este reloj y por otras aplicaciones.
 
  
