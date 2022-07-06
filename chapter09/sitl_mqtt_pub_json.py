#!usr/bin/env python
# -*- coding: utf-8 -*-
print( "dronekitスタート" )    # 開始メッセージ

# 必要なライブラリをインポート
from kbhit import *                 # kbhitを使うために必要(同じフォルダにkbhit.pyを置くこと)
from subprocess import Popen        # subprocessの中から、Popenをインポート
from signal import signal, SIGINT   # Ctrl+C(SIGINT)の送出のために必要 
from dronekit import connect        # connectを使いたいのでインポート
from dronekit import VehicleMode    # VehicleModeも使いたいのでインポート
from dronekit import LocationGlobal, LocationGlobalRelative   # ウェイポイント移動に使いたいのでインポート
import time                         # ウェイト関数time.sleepを使うために必要
import paho.mqtt.client as mqtt     # MQTTのライブラリをインポート
import json                         # json.dumps関数を使いたいのでインポート

#==MQTTでpubするJSONのベースになる辞書===========================================
drone_info = {	"status":{	"isArmable":"false",
			    			"Arm":"false",
                            "FlightMode":"false"
			    		},
			    "position":{ "latitude":"35.0000", 
				    		"longitude":"135.0000",
				    		"altitude":"20",
				    		"heading":"0"
                        }
            }

#==MQTT関数の定義===========================================
# ブローカーに接続できたときの処理
def on_connect(client, userdata, flag, rc):
  print("Connected with result code " + str(rc))

# ブローカーが切断したときの処理
def on_disconnect(client, userdata, rc):
  if rc != 0:
     print("Unexpected disconnection.")

# publishが完了したときの処理
def on_publish(client, userdata, mid):
  print("publish: {0}".format(mid))

#==ここからプログラムスタート===========================================
# kbhit()を使うための「おまじない」を最初に２つ書く
atexit.register(set_normal_term)
set_curses_term()

# dronekit SITL の起動情報
# example: 'dronekit-sitl copter --home=35.079624,136.905453,50.0,3.0 --instance 0'
sitl_frame          = 'copter'          # rover, plane, copterなどのビークルタイプ
sitl_home_latitude  = '35.894087'       # 緯度(度)  柏の葉キャンパス駅前ロータリー
sitl_home_longitude = '139.952447'      # 経度(度)
sitl_home_altitude  = '17.0'            # 高度(m)
sitl_home_direction = '0.0'             # 機首方位(度)
sitl_instance_num   = 0                 # 0〜


# コマンドライン入力したい文字列をリスト形式で作成
sitl_boot_list = ['dronekit-sitl',sitl_frame,
                  '--home=%s,%s,%s,%s' % (sitl_home_latitude,sitl_home_longitude,sitl_home_altitude,sitl_home_direction),
                  '--instance=%s'%(sitl_instance_num)]

print '# sitl command: ', sitl_boot_list        # 文字列を表示
p = Popen(sitl_boot_list)   # サブプロセスの起動
time.sleep(1)   # 起動完了のために1秒待つ

#connection_stringの生成
connection_string = 'tcp:localhost:' + str(5760 + int(sitl_instance_num) * 10 ) # インスタンスが増えるとポート番号が10増える

# フライトコントローラ(FC)へ接続
print( "FCへ接続: %s" % (connection_string) )    # 接続設定文字列を表示
vehicle = connect(connection_string, wait_ready=True)    # 接続

#==MQTTの初期化===========================================
client = mqtt.Client()                  # クラスのインスタンス(実体)の作成
client.on_connect = on_connect          # 接続時のコールバック関数を登録
client.on_disconnect = on_disconnect    # 切断時のコールバックを登録
client.on_publish = on_publish          # メッセージ送信時のコールバック
client.connect("localhost", 1883, 60)   # 接続先は自分自身
client.loop_start()                     # 通信処理スタート

#Ctrl+cが押されるまでループ
try:
    while True:
        if kbhit():     # 何かキーが押されるのを待つ
            key = getch()   # 1文字取得

            # keyの中身に応じて分岐
            if key=='g':                # guided
                vehicle.mode = VehicleMode( 'GUIDED' )
            elif key=='l':              # land
                vehicle.mode = VehicleMode( 'LAND' )
            elif key=='a':              # arm
                vehicle.armed = True
            elif key=='d':              # disarm
                vehicle.armed = False
            elif key=='t':              # takeoff
                vehicle.simple_takeoff(alt=10)
            elif key=='1':              # simple_goto
                # 柏の葉キャンパス交番上空30mへ
                point = LocationGlobalRelative( 35.893246, 139.954909 , 30 )
                vehicle.simple_goto(point)
            elif key=='2':              # simple_goto
                # 三井ガーデンホテル上空50mへ
                point = LocationGlobalRelative( 35.895236, 139.952468 , 50 )
                vehicle.simple_goto(point)
            elif key=='r':              # RTL
                vehicle.mode = VehicleMode( 'RTL' )


        # ここはif文と同じインデントなので，キーに関係なく1秒に1回実行される
        # 現在の状態を表示
        print("--------------------------" )
        print(" System status: %s" % vehicle.system_status.state)
        print(" Is Armable?: %s" % vehicle.is_armable)
        print(" Armed: %s" % vehicle.armed) 
        print(" Mode: %s" % vehicle.mode.name )
        print(" Global Location: %s" % vehicle.location.global_frame)


        drone_info["status"]["isArmable"] = str(vehicle.is_armable)                 # ARM可能か？
        drone_info["status"]["Arm"] = str(vehicle.armed)                            # ARM状態
        drone_info["status"]["FlightMode"] = str(vehicle.mode.name)                 # フライトモード
        drone_info["position"]["latitude"] = str(vehicle.location.global_frame.lat)	# 緯度
        drone_info["position"]["longitude"] = str(vehicle.location.global_frame.lon)# 経度
        drone_info["position"]["altitude"] = str(vehicle.location.global_frame.alt)	# 高度
        drone_info["position"]["heading"] = str(vehicle.heading)					# 方位
        print( drone_info )

        #==MQTTの送信===========================================
        json_message = json.dumps( drone_info )		# 辞書型をJSON型に変換
        client.publish("drone/001", json_message )   # トピック名は以前と同じ"drone/001"

        time.sleep(1)   # 1秒ウェイト

except( KeyboardInterrupt, SystemExit):    # Ctrl+cが押されたら離脱
    print( "SIGINTを検知" )

# フライトコントローラとの接続を閉じる
vehicle.close()

 # サブプロセスにもSIGINT送信
p.send_signal(SIGINT)
p.communicate()
time.sleep(1)   # 終了完了のために1秒待つ

print("終了．")    # 終了メッセージ
