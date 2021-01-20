#!/usr/bin/env python3
import json
import logging as logger
import os
import requests
import RPi.GPIO as GPIO
import signal
import sys
from functools import lru_cache
from itertools import cycle
from lcd import LCD
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from time import sleep
from urllib3.exceptions import MaxRetryError

lcd = LCD()
CURRENCIES = ["BTC", "ETH", "FARM", "GRAIN", "LINK", "MKR", "AAVE", "COMP"]
# conflicting symbols on coingecko - specify which $id we really want (see cgo URL)
CGO_ID_OVERRIDES = {"COMP": "compound-governance-token", "FARM": "harvest-finance"}
ITER = cycle(CURRENCIES)
CUR_ITER = []
MINS = 0
CGO_URL = "https://api.coingecko.com/api/v3"
CGO_COINS = []
logger.basicConfig(level=os.environ.get('LOG_LEVEL', 'WARNING').upper())

def get_json(url):
    """Fetches URL and returns JSON. """
    try:
        retry = Retry(total=99, backoff_factor=0.1)
        adapter = HTTPAdapter(max_retries=retry)
        session = requests.Session()
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        res = session.request("GET", url, timeout=(3, 10))
    except MaxRetryError as err:
        logger.info(f"MaxRetries reached. Returning empty data. Error: {err}")
        return {}
    res.raise_for_status()
    return json.loads(res.content)

def int_signal_handler(sig, frame):
    lcd.clear()
    lcd.noDisplay()
    GPIO.cleanup()
    sys.exit(0)

def btn_1_press_callback(channel):
    """ Button press cycles to next pair; cache cleared every 60s """
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
    logger.debug(f"rounding {val}")
    if "." not in str(val):
        return val
    num, exp = str(val).split(".")
    if int(num) > 0:
        return round(val, 3)
    leading_zeroes = len(exp) - len(exp.strip("0"))
    return round(val, leading_zeroes + 3)
    
@lru_cache(maxsize=None)
def get_price(ticker):
    """ Returns current price (from coingecko.com) for given symbol """
    get_cgo_coins()
    coin_id = CGO_ID_OVERRIDES.get(ticker) or [x["id"] for x in CGO_COINS if x["symbol"] == ticker.lower()][0]
    res = get_json(CGO_URL + f"/simple/price?ids={coin_id}&vs_currencies=usd").get(coin_id, {}).get("usd", 0)
    return smart_round(res)

@lru_cache(maxsize=None)
def get_cgo_coins():
    full_list = get_json(CGO_URL + "/coins/list")
    if not full_list:
        logger.info(f"Error updating coingecko list of coin IDs. Resonse was: {full_list}")
        return False
    # trim to ones we care about
    global CGO_COINS
    trimmed_list = CGO_COINS = [x for x in full_list if x["symbol"] in [x.lower() for x in CURRENCIES]]
    logger.debug(f"CoinGecko coins list: {trimmed_list}")

def clear_cgo_cache():
    get_cgo_coins.cache_clear()

def wake_every_min(sig, frame):
    # updates display with new prices every iteration, and updates coin list daily
    get_price.cache_clear()
    lcd.clear()
    lcd.message(create_lcd_str(CUR_ITER))
    global MINS
    MINS += 1
    if MINS > 1440:
        MINS = 0
        clear_cgo_cache()
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

    signal.signal(signal.SIGALRM, wake_every_min)
    signal.alarm(60)
    signal.signal(signal.SIGINT, int_signal_handler)
    signal.pause()

if __name__ == '__main__':
    main()
