from fcoin3 import Fcoin
import os

fcoin = Fcoin()

print(fcoin.get_symbols())

print(fcoin.get_currencies())

api_key = os.environ["FCOIN_API_KEY"]
api_sec = os.environ["FCOIN_API_SECRET"]

fcoin.auth(api_key, api_sec)

print(fcoin.get_balance())

print(fcoin.buy('fteth', 0.0001, 10))
#print(fcoin.sell('fteth', 0.002, 5))
#print(fcoin.cancel_order('6TfBZ-eORp4_2nO5ar6zhg0gLLvuWzTTmL1OzOy9OYg='))
#print(fcoin.get_candle('M1','fteth'))
