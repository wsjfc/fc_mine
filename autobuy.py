# -*- coding: utf-8 -*-

from fcoin3 import Fcoin
import argparse
import os
import time
import smtplib
from email.mime.text import MIMEText

msg_from = '157373692@qq.com' # 发送方邮箱
passwd = os.environ["MAIL_PW"] # 填入发送方邮箱的授权码
msg_to = '157373692@qq.com' # 收件人邮箱

def check(fcoin):
    usdt_balance = 0
    btc_balance = 0
    eth_balance = 0
    ft_balance = 0
    balances = fcoin.get_balance()
    for bl in balances['data']:
        if bl['currency'] == 'usdt':
            usdt_balance = float(bl['available'])
        elif bl['currency'] == 'btc':
            btc_balance = float(bl['available'])
        elif bl['currency'] == 'eth':
            eth_balance = float(bl['available'])
        elif bl['currency'] == 'ft':
            ft_balance = float(bl['available'])

    print("initial balance: %f, %f, %f, %f" % (usdt_balance, btc_balance, eth_balance, ft_balance))

    while True:
        time.sleep(5)
        balances = fcoin.get_balance()
        while balances == None:
            time.sleep(5)
            balances = fcoin.get_balance()
        for bl in balances['data']:
            if bl['currency'] == 'usdt':
                if float(bl['available']) > 8000:
                    usdt_balance = float(bl['available'])
                    mail_subject = float(bl['available'])
                    mail_subject = str('your usdt comes :)')
                    msg = MIMEText("usdt volume: %f" % usdt_balance)
                    msg['Subject'] = mail_subject
                    msg['From'] = msg_from
                    msg['To'] = msg_to

                    try:
                        s = smtplib.SMTP_SSL("smtp.qq.com", 465)
                        s.login(msg_from, passwd)
                        s.sendmail(msg_from, msg_to, msg.as_string())
                        return 'mail send success'

                    except s.SMTPException:
                        return 'mail send failed'

                    #fcoin.buy()
            elif bl['currency'] == 'btc':
                if float(bl['available']) > btc_balance:
                    btc_balance = float(bl['available'])
                    #fcoin.buy()
            elif bl['currency'] == 'eth':
                if float(bl['available']) > eth_balance:
                    eth_balance = float(bl['available'])
                    #fcoin.buy()
            elif bl['currency'] == 'ft':
                if float(bl['available']) > 4000:
                    mail_subject = float(bl['available'])
                    msg = MIMEText("sell!")
                    msg['Subject'] = mail_subject
                    msg['From'] = msg_from
                    msg['To'] = msg_to

                    try:
                        s = smtplib.SMTP_SSL("smtp.qq.com", 465)
                        s.login(msg_from, passwd)
                        s.sendmail(msg_from, msg_to, msg.as_string())
                        return 'mail send success'

                    except s.SMTPException:
                        return 'mail send failed'

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default='check',  help="model type: check; mine")
    args = parser.parse_args()

    fcoin = Fcoin()
    api_key = os.environ["FCOIN_API_KEY_0"]
    api_sec = os.environ["FCOIN_API_SECRET_0"]
    fcoin.auth(api_key, api_sec)

    MODE = args.mode
    if MODE == 'check':
        check(fcoin=fcoin)
