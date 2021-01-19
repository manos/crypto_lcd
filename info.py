#!/usr/bin/env python3
import logging as logger
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
# conflicting symbols on coingecko - specify which $id we really want (see cgo URL)
CGO_ID_OVERRIDES = {"COMP": "compound-governance-token", "FARM": "harvest-finance"}
ITER = cycle(CURRENCIES)
CUR_ITER = []
CGO_URL = "https://api.coingecko.com/api/v3"
CGO_COINS = []
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'WARNING').upper()
logger.basicConfig(level=LOG_LEVEL)

def get_json(url):
    """Fetches URL and returns JSON. """
    res = requests.get(url)
    res.raise_for_status()
    return res.json()

def int_signal_handler(sig, frame):
    lcd.clear()
    lcd.noDisplay()
    GPIO.cleanup()
    sys.exit(0)

def btn_1_press_callback(channel):
    lcd.clear()
    print("Button pressed!")
    lcd.message(create_lcd_str(cycle_next()))

def create_lcd_str(coins):
    """ Returns string like "BTC: 34,500\nETH: 1200" for first two currencies in [coins], limited to 16 chars """
    return f"{coins[0]}: {get_price(coins[0])}"[:16] + "\n" + f"{coins[1]}: {get_price(coins[1])}"[:16]

def cycle_next():
    """ Returns two steps on the cycle [a,b], and records current value in CUR_ITER for re-use """
    next1 = next(ITER)
    next2 = next(ITER)
    global CUR_ITER
    CUR_ITER = [next1, next2]
    return CUR_ITER

def smart_round(val):
    """ If we have a number > 0, give 3 decimals, otherwise, give 3 past leading zeroes """
    if "." not in str(val):
        return val
    num, exp = str(val).split(".")
    if int(num) > 0:
        return round(val, 3)
    leading_zeroes = len(exp) - len(exp.strip("0"))
    return round(val, leading_zeroes + 3)
    
def get_price(ticker):
    """ Returns current price (from coingecko.com) for given symbol """
    get_cgo_coins()
    coin_id = CGO_ID_OVERRIDES.get(ticker) or [x["id"] for x in CGO_COINS if x["symbol"] == ticker.lower()][0]
    res = get_json(CGO_URL + f"/simple/price?ids={coin_id}&vs_currencies=usd")[coin_id]["usd"]
    return smart_round(res)

@lru_cache(maxsize=None)
def get_cgo_coins():
    full_list = get_json(CGO_URL + "/coins/list")
    # trim to ones we care about
    global CGO_COINS
    trimmed_list = CGO_COINS = [x for x in full_list if x["symbol"] in [x.lower() for x in CURRENCIES]]
    logger.debug(f"CoinGecko coins list: {trimmed_list}")

def clear_cgo_cache():
    get_cgo_coins.cache_clear()

def update_display(sig, frame):
    lcd.clear()
    lcd.message(create_lcd_str(CUR_ITER))
    signal.alarm(60)
    signal.pause()

def main():
    btn_1 = 21
    GPIO.setup(btn_1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(btn_1, GPIO.FALLING, callback=btn_1_press_callback, bouncetime=100)

    lcd.display()
    lcd.clear()
    lcd.home()
    lcd.message(create_lcd_str(cycle_next()))

    signal.signal(signal.SIGALRM, update_display)
    signal.alarm(60)
    signal.signal(signal.SIGINT, int_signal_handler)
    signal.pause()

if __name__ == '__main__':
    main()
