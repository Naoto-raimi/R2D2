# -*- coding:utf-8 -*-

import cv2
import os
import sys
import threading
import requests
import types
import base64
import json
import jtalk
import time
import socket
import pygame
import cStringIO
import traceback
from xml.etree.ElementTree import fromstring
import subprocess
import grovepi
import RPi.GPIO as GPIO

#julius
host = "192.168.1.80"
port = 10500

#touch sensor
touch_sensor = 4
grovepi.pinMode(touch_sensor,"INPUT")

#refrective senser
refrective_sensor = 5
grovepi.pinMode(refrective_sensor,"INPUT")

#led
led_1 = 7
led_2 = 2
led_3 = 3
numleds = 1
grovepi.pinMode(led_1,"OUTPUT")
grovepi.pinMode(led_2,"OUTPUT")
grovepi.pinMode(led_3,"OUTPUT")
time.sleep(1)

testColorBlack = 0   # 0b000 #000000
testColorBlue = 1    # 0b001 #0000FF
testColorGreen = 2   # 0b010 #00FF00
testColorCyan = 3    # 0b011 #00FFFF
testColorRed = 4     # 0b100 #FF0000
testColorMagenta = 5 # 0b101 #FF00FF
testColorYellow = 6  # 0b110 #FFFF00
testColorWhite = 7   # 0b111 #FFFFFF

grovepi.chainableRgbLed_init(led_1, numleds)
grovepi.chainableRgbLed_init(led_2, numleds)
grovepi.chainableRgbLed_init(led_3, numleds)
time.sleep(.5)

#servo
GPIO.setmode(GPIO.BCM)
gp_out = 4
GPIO.setup(gp_out, GPIO.OUT)
servo = GPIO.PWM(gp_out, 50)

#####
def parse_recogout(xml_data):
    # scoreを取得(どれだけ入力音声が、認識結果と合致しているか)
    shypo = xml_data.find(".//SHYPO")
    if shypo is not None:
        score = shypo.get("SCORE")

    # 認識結果の単語を取得
    whypo = xml_data.find(".//WHYPO")
    if whypo is not None:
        word = whypo.get("WORD")
    return score, word

def getEmotion(body, headers):
    url = 'https://api.projectoxford.ai/emotion/v1.0/recognize'
    r = requests.post(url, data=body, headers=headers)
    data = r.json()
    dict = data[0]['scores']
    max_key = max(dict, key=(lambda x: dict[x]))
    return max_key

def audioPlay(file, t):
    # mixerモジュールの初期化
    pygame.mixer.init()
    # 音楽ファイルの読み込み
    pygame.mixer.music.load(file)
    #音楽再生、および再生回数の設定(-1はループ再生)
    pygame.mixer.music.play(1)

    time.sleep(t)
    # 再生の終了
    pygame.mixer.music.stop()

def cameraStart():
    audioPlay('music/r2d2_12.mp3',3)

    # カメラをキャプチャ開始
    cap = cv2.VideoCapture(0)

    cap.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, 320)

    cap.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, 240)

    while True:
	ret, frame = cap.read()

	#frameを表示
	cv2.imshow('camera capture', frame)

	if(threading.activeCount() == 1):
		th = FaceThreadEmo(frame)
		th.start()

		#10msecキー入力待ち
		k = cv2.waitKey(10)
		#Escキーを押されたら終了
		if grovepi.digitalRead(touch_sensor) == 1:
				audioPlay('music/button.mp3',1)
    			audioPlay('music/r2d2_10.mp3',3)
				break

    #キャプチャを終了
    cap.release()
    cv2.destroyAllWindows()

def ledBrink(led_num,testColor):
    for x in xrange(3):
    	grovepi.chainableRgbLed_test(led_num, numleds, testColor)
		time.sleep(1)
		grovepi.chainableRgbLed_test(led_num, numleds, testColorBlack)
		time.sleep(1)

def servoTurn1():
    servo.start(0.0)

	for i in range(5):
    	servo.ChangeDutyCycle(2.5)
    	time.sleep(0.5)

    	servo.ChangeDutyCycle(12.0)
    	time.sleep(0.5)

	servo.stop()

def servoTurn2():
	servo.start(7.5)
	servo.ChangeDutyCycle(7.5)  # turn towards 90 degree
	time.sleep(0.5) # sleep 0.5 second
	servo.ChangeDutyCycle(2.5)  # turn towards 0 degree
	time.sleep(0.5) # sleep 0.5 second
	servo.ChangeDutyCycle(12.5) # turn towards 180 degree
    time.sleep(0.5) # sleep 0.5 second 

	servo.stop()

def servoTurn3():
	servo.start(12.5)
	servo.ChangeDutyCycle(12.5)  # turn towards 180 degree
	time.sleep(0.5) # sleep 0.5 second
	servo.ChangeDutyCycle(22.5)  # turn towards 360 degree
	time.sleep(0.5) # sleep 0.5 second
	servo.ChangeDutyCycle(12.5)  # turn towards 180 degree
	time.sleep(0.5) # sleep 0.5 second

	servo.stop()

def takePicture():
	cam = cv2.VideoCapture(0)
	cam.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, 320)
	cam.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, 240)

    while True:
		ret, frame = cam.read()
		cv2.imshow('camera capture', frame)
		if grovepi.digitalRead(refrective_sensor) == 1:
			audioPlay('music/button.mp3',1)
        	audioPlay('music/r2d2_10.mp3',3)
			picture_path = 'camera.jpg'
			cv2.imwrite(picture_path, frame)
			break

	cam.release()
    cv2.destroyAllWindows()

class FaceThreadEmo(threading.Thread):
	def __init__(self, frame):
		super(FaceThreadEmo, self).__init__()
		self._cascade_path = "haarcascade_frontalface_alt.xml"
		self._frame = frame

	def run(self):
		#グレースケール変換
		self._frame_gray = cv2.cvtColor(self._frame, cv2.COLOR_BGR2GRAY)

		#カスケード分類器の特徴量を取得する
		self._cascade = cv2.CascadeClassifier(self._cascade_path)

		#物体認識（顔認識）の実行
		self._facerect = self._cascade.detectMultiScale(self._frame_gray, scaleFactor=1.2, minNeighbors=3, minSize=(10, 10))

		if len(self._facerect) > 0:
			audioPlay('music/r2d2_3.mp3',3)
			self._color = (255, 255, 255) #白
			for self._rect in self._facerect:
				#検出した顔を囲む矩形の作成
				cv2.rectangle(self._frame, tuple(self._rect[0:2]),tuple(self._rect[0:2] + self._rect[2:4]), self._color, thickness=2)

			#認識結果の保存
			self._image_path = 'picture.jpg'
			cv2.imwrite(self._image_path, self._frame)

            		self.headers = {
                		'Content-Type': 'application/octet-stream',
                		'Ocp-Apim-Subscription-Key': '1d5be230f19f4f379abb38accfb0ae90',
            		}

            		self.body = open('picture.jpg','rb').read()

           		emo = getEmotion(self.body, self.headers)
				print emo

			if emo == 'neutral':
				jtalk.jtalk('ニュートラルと認識しました')
				time.sleep(2)
				jtalk.jtalk('そんなあなたをテンションを上げる曲をおかけします')
				time.sleep(4)
				audioPlay('music/dna.mp3',219)

			elif emo == 'happiness':
				jtalk.jtalk('ハピネスと認識しました')
				time.sleep(2)
				jtalk.jtalk('そんなあなたにぴったりな曲をおかけします')
				time.sleep(3)
				audioPlay('music/bloodsweattears.mp3',240)

			elif emo == 'sadness':
				jtalk.jtalk('サドネスと認識しました')
				time.sleep(2)
				jtalk.jtalk('そんなあなたを元気にする曲をおかけします')
				time.sleep(3)
				audioPlay('music/springday.mp3',240)

			elif emo == 'suprise':
				jtalk.jtalk('サプライズと認識しました')
				time.sleep(2)
				jtalk.jtalk('驚かせてしまい申し訳ありません、私は喋るアールツーディーツーです')
				time.sleep(3)
				audioPlay('music/butterfly.mp3',240)

			elif emo == 'anger':
				jtalk.jtalk('アンガーと認識しました')
				time.sleep(2)
				jtalk.jtalk('そんなあなたを落ち着かせる曲をおかけします')
				time.sleep(4)
				audioPlay('music/donteverleaveme.mp3',170)

			elif emo == 'contempt':
				jtalk.jtalk('コンテンプトと認識しました')
				time.sleep(2)
				jtalk.jtalk('劇中では喋りませんが、会話機能が最近追加されました')
				time.sleep(4)

			elif emo == 'disgust':
				jtalk.jtalk('ディスガストと認識しました')
				time.sleep(2)
				jtalk.jtalk('私のことが嫌いなようですね')
				time.sleep(4)

			elif emo == 'fear':
				jtalk.jtalk('フィアーと認識しました')
				time.sleep(2)
				jtalk.jtalk('私のことを怖がっているようですね、何もしません')
				time.sleep(4)

			else:
				jtalk.jtalk('顔を認識できません')

			time.sleep(2.0) #sleep(秒指定)

#####
def main():
	ledBrink(led_1,testColorYellow)
	time.sleep(0.5)
	audioPlay('music/r2d2_7.mp3',2)
    servoTurn1()
	

    try:
        # TCP/IPでjuliusに接続
        bufsize = 4096
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        sock_file = sock.makefile()

        xml_buff = ""
        in_recogout = False

        while True:
            # juliusから解析結果を取得
            data = cStringIO.StringIO(sock.recv(bufsize))

            # 解析結果から一行取得
            line = data.readline()

            while line:
                # 音声の解析結果を示す行だけ取り出して処理する。
                # RECOGOUTタグのみを抽出して処理する。
                if line.startswith("<RECOGOUT>"):
                    in_recogout = True
                    xml_buff += line
                elif line.startswith("</RECOGOUT>"):
                    xml_buff += line
                    xml_data = fromstring(xml_buff)
                    # XMLをパースして、解析結果を取得する
                    score, word = parse_recogout(xml_data)

                    if u'表情認識' in word:
                        cameraStart()

				elif u'防弾少年団' in word:
				audioPlay('music/r2d2_8.mp3',2)
				ledBrink(led_1,testColorCyan)
				audioPlay('music/dna.mp3',240)

				elif u'こんにちは' in word:
				audioPlay('music/r2d2_7.mp3',2)
				ledBrink(led_1,testColorMagenta)
				servoTurn2()

				elif u'アールツー' in word:
				audioPlay('music/r2d2_5.mp3',5)
				ledBrink(led_1,testColorWhite)
				servoTurn3()

				elif u'録音' in word:
				audioPlay('music/r2d2_13.mp3',2)
				audioPlay('file.wav',10)

				elif u'ジャズ再生' in word:
				audioPlay('music/r2d2_8.mp3',2)
				ledBrink(led_1,testColorBlue)
				audioPlay('music/newksfadeaway.mp3',200)

				elif u'スターウォーズ再生' in word:
				audioPlay('music/r2d2_6.mp3',3)
				ledBrink(led_1,testColorMagenta)
				audioPlay('music/darthvader.mp3',150)

				elif u'終了' in word:
				audioPlay('music/r2d2_4.mp3',3)
				GPIO.cleanup()
				sys.exit()

				elif u'撮影' in word:
				audioPlay('music/r2d2_9.mp3',3)
				ledBrink(led_1,testColorYellow)
				takePicture()

				else:
				ledBrink(led_1,testColorRed)
				servoTurn1()

                    in_recogout = False
                    xml_buff = ""
                else:
                    if in_recogout:
                        xml_buff += line
                # 解析結果から一行取得
                line = data.readline()
    except Exception as e:
        print "error occurred", e, traceback.format_exc()
    finally:
        pass

if __name__ == "__main__":
	main()

