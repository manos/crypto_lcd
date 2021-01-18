#!/usr/bin/env python3
import os
import requests
import RPi.GPIO as GPIO
import signal
import sys
from functools import lru_cache
from itertools import cycle
from lcd import LCD
from time import sleep

lcd = LCD()
CURRENCIES = ["BTC", "ETH", "FARM", "GRAIN", "LINK", "MKR", "AAVE", "COMP"]
ITER = cycle(CURRENCIES)
CMC_LISTINGS = {}
CMC_PRO_KEY = os.getenv("CMC_KEY")


def get_json(url):
    """Fetches URL and returns JSON. """
    headers = {"X-CMC_PRO_API_KEY": CMC_PRO_KEY}
    res = requests.get(url, headers=headers)
    res.raise_for_status()
    return res.json()

def signal_handler(sig, frame):
    lcd.noDisplay()
    GPIO.cleanup()
    sys.exit(0)

def btn_1_press_callback(channel):
    update_cmc_data()
    lcd.clear()
    print("Button pressed!")
    lcd.message(create_lcd_str([next(ITER), next(ITER)]))

def create_lcd_str(coins):
    """ Returns string like "BTC: 34,500\nETH: 1200" for first two currencies in [coins] """
    return f"{coins[0]}: {get_price(coins[0])}\n{coins[1]}: {get_price(coins[1])}"

def get_price(ticker):
    """Returns current price (from coinmarketcap.com) for given symbol """
    res = [x["quote"]["USD"]["price"] for x in CMC_LISTINGS["data"] if x["symbol"] == ticker]
    if res:
        return round(res[0], 2)
    return 0

@lru_cache(maxsize=None)
def update_cmc_data():
    print("Updating price data from coinmarkecap...")
    global CMC_LISTINGS
    CMC_LISTINGS = get_json("https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest")

def clear_cmc_cache(sig, frame):
    update_cmc_data.cache_clear()
    signal.alarm(60)
    signal.pause()

def main():
    btn_1 = 21
    GPIO.setup(btn_1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(btn_1, GPIO.FALLING, callback=btn_1_press_callback, bouncetime=100)

    update_cmc_data()
    lcd.clear()
    lcd.message(create_lcd_str([next(ITER), next(ITER)]))

    signal.signal(signal.SIGALRM, clear_cmc_cache)
    signal.alarm(60)
    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()

if __name__ == '__main__':
    main()
