from machine import Pin, PWM
import network
import socket
import time
import dht
from machine import Pin
import uasyncio
from time import sleep

onboard = Pin("LED", Pin.OUT, value=0)
sensor = dht.DHT22(Pin(3))
pwm = PWM(Pin(0))
pwm.freq(50)
rollers_state_log = open("rollers_state_log.txt", "w")

ssid = "wifi name"
password = "password"
html = """<!DOCTYPE html>
    <html>
    <head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pico W</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.2.0/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-gH2yIJqKdNHPEq0n4Mqa/HGKIhSkIHeL5AyhkYV8i59U5AR6csBvApHHNl/vI1Bx" crossorigin="anonymous">
     <script src="https://kit.fontawesome.com/ce45432c36.js" crossorigin="anonymous"></script>
    </head>
    <body>
    <div class="container px-4 p-2 my-4 mx-auto text-center border border-2 h-100" style="background-color: rgba(0,0,255,.03)">
    <h1>Smart Home Pico W </h1>
      <div class="row justify-content-around">
        <div class="col-md-auto">
        <div class="row p-2"><p><h4><i class="fa-solid fa-temperature-three-quarters"></i> Temperature is %s &degC</h4></p></div>
        <div class="row p-2"><p><h4><i class="fa-solid fa-droplet"></i> Humidity is %s &percnt;</h4></p></div>    
            
        </div>
        <div class="col-md-auto">
            <div class="row p-2"><a class="btn btn-success btn-lg" role="button" href="/rollersup?">Rollers up </a></div>
            <div class="row p-2"><a class="btn btn-danger btn-lg" role="button" href="/rollersdown?">Rollers down </a></div>
    <p><h4>Rollers are <b>%s</b></h4></p>
        </div>
      </div>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.2.0/dist/js/bootstrap.bundle.min.js" integrity="sha384-A3rJD856KowSb7dwlZdYEkO39Gagi7vIsF0jrRAoQmDKKtQBHUuLZ9AsSv4jD4Xa" crossorigin="anonymous"></script>
    </div>
    </body>
</html>
"""

webdocs="/webroot/"

wlan = network.WLAN(network.STA_IF)

def WriteFileData(data):
    rollers_state_log.write(data)
    rollers_state_log.write("\n")
    rollers_state_log.flush()

def ReadLastLine(data):
    state = open(data, 'r')
    lines = state.readlines()
    if lines:
        last_line = lines[-1].rstrip()#remove white chars
        print("Last line: ", last_line)
    return str(last_line)

def setServoCycle (position):
    pwm.duty_u16(position)
    sleep(0.01)

def move_servo(direction):
    if direction == 'UP':
        for pos in range(1000,9000,50):
            setServoCycle(pos)
    if direction == 'DOWN':
        for pos in range(9000,1000,-50):
            setServoCycle(pos)

def connect_to_network():
    wlan.active(True)
    wlan.config(pm = 0xa11140) # Disable power-save mode
    wlan.connect(ssid, password)
    
    max_wait = 10
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1

        print('waiting for connection...')
        time.sleep(1)
    
    if wlan.status() != 3:
        raise RuntimeError('network connection failed')
    else:
        print('connected')
        status = wlan.ifconfig()

        print('ip = ' + status[0])

async def serve_client(reader, writer): #only when demanded
    print("Client connected")
    request_line = await reader.readline()
    print("Request:", request_line)
    
    # We are not interested in HTTP request headers, skip them
    while await reader.readline() != b"\r\n":
        pass
        
    request = str(request_line)
    sensor.measure()
    temperature = sensor.temperature()
    humidity = sensor.humidity()
    rollers_up = request.find('/rollersup?')
    rollers_down = request.find('/rollersdown?')
    css = request.find('.css')
    rollers_state = ""
    rollers_state = ReadLastLine('rollers_state_log.txt')
    if rollers_up == 6:
        print(rollers_state)
        if rollers_state !="UP":
            move_servo('UP')
        rollers_state = "UP"
        WriteFileData(rollers_state)
        
    if rollers_down == 6:
        if rollers_state !="DOWN":
            move_servo('DOWN')
        rollers_state = "DOWN"
        WriteFileData(rollers_state)
    
    response = html % (temperature, humidity, rollers_state)#display
    
    if css > 0:    
        requestedfile  = request[6:css+4]
        print("CSS requested:" + requestedfile)
        f = open(webdocs + requestedfile)
        response = f.read()
        f.close()
        
        writer.write('HTTP/1.0 200 OK\r\nContent-type: text/css\r\n\r\n')
        writer.write(response)
    else:
        writer.write('HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n')
        writer.write(response)
  
    await writer.drain()
    await writer.wait_closed()
    print("Client disconnected")
    
async def main():
    print('Connecting to Network...')
    connect_to_network()
    
    print('Setting up')
    uasyncio.create_task(uasyncio.start_server(serve_client, "0.0.0.0", 80))
    while True:
        onboard.on()
        print("pulse")
        await uasyncio.sleep(0.25)
        onboard.off()
        await uasyncio.sleep(5)
           
try:
    uasyncio.run(main())
finally:
    uasyncio.new_event_loop()



