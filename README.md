## Description

Raspberry Pi code to display crypto prices on a 1602 LCD, with a momentary switch (button) to cycle through a list of currencies. Uses CoinGecko's free API for prices.

## Running
Just run info.py. Edit CURRENCIES at the top of the file..

## Hardware
* Raspberry Pi
* 1602 LCD (16 chars X 2 rows)
* Momentary switch AKA "tactile button"
* 10K potentiometer (optional) to control LCD backlight brightness

## About the code
Care was taken to avoid busy loops. Everything is signal and event driven.

A button press cycles through two currencies in the list at the top of the file. New prices are fetched every 60 seconds to avoid API limits, regardless how often you press the button.

lcd.py comes from the sunfounder kits, and hard-codes GPIO pins that must be used to wire the LCD [instructions](http://wiki.sunfounder.cc/index.php?title=LCD1602_Module).
