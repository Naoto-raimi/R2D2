import time
import RPi.GPIO as GPIO

GPIO.setmode(GPIO.BCM)

gp_out = 4
GPIO.setup(gp_out, GPIO.OUT)
servo = GPIO.PWM(gp_out, 50) 

servo.start(0.0)

for i in range(10):
    servo.ChangeDutyCycle(2.5)
    time.sleep(0.5)

    servo.ChangeDutyCycle(12.0)
    time.sleep(0.5)

GPIO.cleanup()