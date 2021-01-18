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
CUR_ITER = []
CMC_LISTINGS = {}
CMC_PRO_KEY = os.getenv("CMC_KEY")
CGO_URL = "https://api.coingecko.com/api/v3"
CGO_COINS = []

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
    """ Returns current price (from coinmarketcap.com) for given symbol, if listed there, otherwise uses coingecko """
    res = [x["quote"]["USD"]["price"] for x in CMC_LISTINGS["data"] if x["symbol"] == ticker]
    if res:
        return smart_round(res[0])
    else:
        get_cgo_coins()
        coin_id = [x["id"] for x in CGO_COINS if x["symbol"] == ticker.lower()][0]
        res = get_json(CGO_URL + f"/simple/price?ids={coin_id}&vs_currencies=usd")[coin_id]["usd"]
        return smart_round(res)

@lru_cache(maxsize=None)
def get_cgo_coins():
    full_list = get_json(CGO_URL + "/coins/list")
    # trim to ones we care about
    global CGO_COINS
    CGO_COINS = [x for x in full_list if x["symbol"] in [x.lower() for x in CURRENCIES]]

@lru_cache(maxsize=None)
def update_cmc_data():
    print("Updating price data from coinmarketcap...")
    global CMC_LISTINGS
    CMC_LISTINGS = get_json("https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest")

def clear_cmc_cache(sig, frame):
    """ Fetch new prices, and update currently-displayed currencies """
    update_cmc_data.cache_clear()
    update_cmc_data()
    lcd.clear()
    lcd.message(create_lcd_str(CUR_ITER))
    signal.alarm(60)
    signal.pause()

def main():
    btn_1 = 21
    GPIO.setup(btn_1, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.add_event_detect(btn_1, GPIO.FALLING, callback=btn_1_press_callback, bouncetime=100)

    update_cmc_data()
    lcd.clear()
    lcd.message(create_lcd_str(cycle_next()))

    signal.signal(signal.SIGALRM, clear_cmc_cache)
    signal.alarm(60)
    signal.signal(signal.SIGINT, signal_handler)
    signal.pause()

if __name__ == '__main__':
    main()
