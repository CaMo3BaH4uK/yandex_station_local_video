import sys
import os
from PySide2 import QtWidgets
import design
import keyring
import requests
import json
import multiprocessing
import ssl
from flask import Flask
from flask import Response
from werkzeug import serving


SERVER_NAME = 'gvs 1.0'
class localFlask(Flask):
    def process_response(self, response):
        response.headers['Connection'] = 'close'
        response.headers['Expires'] = response.headers['Date']
        response.headers['Cache-Control'] = str(response.headers['Cache-Control']).replace('public', 'private')
        response.headers['Alt-Svc'] = 'quic=":443"; ma=2592000; v="46,43",h3-Q050=":443"; ma=2592000,h3-Q049=":443"; ma=2592000,h3-Q048=":443"; ma=2592000,h3-Q046=":443"; ma=2592000,h3-Q043=":443"; ma=2592000,h3-T050=":443"; ma=2592000'
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['server'] = SERVER_NAME
        del response.headers['ETag']
        return(response)


web = localFlask(__name__)

context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
context.load_verify_locations("cert/ca_bundle.crt")
context.load_cert_chain("cert/certificate.crt", "cert/private.key")


DEBUG = 1


ip = requests.get('https://api.ipify.org').text + ':443'
servicename = 'yandex_station_local_video'


class MainApp(QtWidgets.QMainWindow, design.Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.update.clicked.connect(self.updateFiles)
        self.filesList.itemDoubleClicked.connect(self.playFile)
        self.save.clicked.connect(self.savePassword)
        self.ip.setText('IP: ' + ip)
        self.login.setText(keyring.get_password(servicename, 'email'))
        if(self.login.text() == ''):
            self.tabWidget.setCurrentIndex(1)
            self.logMSG('ERROR: Auth error')
        self.updateFiles()

    def logMSG(self, msg=''):
        self.log.setText(msg)
        if DEBUG:
            print('DEBUG: ' + msg)

    def sendToScreen(self, video_url):
        self.logMSG('Sending ' + video_url)
        auth_data = {
                'login': keyring.get_password(servicename, 'email'), 
                'passwd': keyring.get_password(servicename, keyring.get_password(servicename, 'email')) 
                }
                
        s = requests.Session()
        s.get("https://passport.yandex.ru/")
        s.post("https://passport.yandex.ru/passport?mode=auth&retpath=https://yandex.ru", data=auth_data)
            
        

        token = s.get('https://frontend.vh.yandex.ru/csrf_token').text
        if "Can't get token" in token:
            self.tabWidget.setCurrentIndex(1)
            self.logMSG('ERROR: Auth error')
        else:
            devices_online_stats = s.get("https://quasar.yandex.ru/devices_online_stats").text
            devices = json.loads(devices_online_stats)["items"]

            headers = {
                "x-csrf-token": token,
            }

            data = {
                "msg": {
                    "provider_item_id": video_url
                },
                "device": devices[0]["id"]
            }

            res = s.post("https://yandex.ru/video/station", data=json.dumps(data), headers=headers)
            self.logMSG(res.text)

    def updateFiles(self):
        files = [ f for f in os.listdir('./static') if os.path.isfile(os.path.join('./static',f)) ]
        self.filesList.clear()
        self.filesList.addItems(files)

    def playFile(self):
        selectedFile = self.filesList.currentItem().text()
        self.sendToScreen('https://ethernet.su/static/' + selectedFile)

    def savePassword(self):
        keyring.set_password(servicename, 'email', self.login.text())
        keyring.set_password(servicename, keyring.get_password(servicename, 'email'), self.password.text())
        self.logMSG()

def main(flaskProcess):
    app = QtWidgets.QApplication(sys.argv)
    window = MainApp()
    window.show()
    app.exec_()
    flaskProcess.terminate()
    sys.exit(0)

def runWeb():
    web.run(host='0.0.0.0', port=443, ssl_context = context)

if __name__ == '__main__': # Это знать надо
    flaskProcess = multiprocessing.Process(target=runWeb)
    flaskProcess.start()
    main(flaskProcess)