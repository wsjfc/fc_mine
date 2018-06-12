# -*- coding: utf-8 -*-

from fcoin3 import Fcoin
import os
import operator
import argparse
import concurrent.futures
import asyncio
import time

def check(fcoin):
    symbols = fcoin.get_symbols()

    # get trade symbol pairs
    usdt_trades = []
    for sym in symbols:
        if sym['quote_currency'] == 'usdt':
            usdt_trades.append(sym['base_currency']+'usdt')
    print(usdt_trades)

    btc_trades = []
    for sym in symbols:
        if sym['quote_currency'] == 'btc':
            btc_trades.append(sym['base_currency']+'btc')
    print(btc_trades)

    eth_trades = []
    for sym in symbols:
        if sym['quote_currency'] == 'eth':
            eth_trades.append(sym['base_currency']+'eth')
    print(eth_trades)

    # get sorted symbol with the diff betweem lowest asks and highest bids
    for trades in [usdt_trades, btc_trades, eth_trades]:
        print('#######################################')
        diffs = {}
        for trade_symbol in trades:
            ret = fcoin.get_market_depth('L20', trade_symbol)
            if ret['status'] == 0 and  \
                len(ret['data']['bids']) and \
                len(ret['data']['asks']) > 0:
                lowest_ask = ret['data']['asks'][0]
                highest_bid = ret['data']['bids'][0]
                print('lowest ask: %f, highest bid: %f.'
                      % (lowest_ask, highest_bid))
                normed_diff = (lowest_ask - highest_bid)/highest_bid
                diffs[trade_symbol] = normed_diff
        sorted_diff = sorted(diffs.items(), key=operator.itemgetter(1))
        print(sorted_diff)

    return eth_trades

def mine_(trades, fcoin):
    print("####### start trading sesion########")
    diffs = {}
    detais = {}
    for trade_symbol in trades:
        ret = fcoin.get_market_depth('L20', trade_symbol)
        if ret['status'] == 0 and \
                len(ret['data']['bids']) and \
                        len(ret['data']['asks']) > 0:
            lowest_ask = ret['data']['asks'][0]
            highest_bid = ret['data']['bids'][0]
            print('lowest ask: %f, highest bid: %f.'
                  % (lowest_ask, highest_bid))
            normed_diff = (lowest_ask - highest_bid) / highest_bid
            diffs[trade_symbol] = normed_diff
            detais[trade_symbol] = (lowest_ask, highest_bid)
    sorted_diff = sorted(diffs.items(), key=operator.itemgetter(1))
    print(sorted_diff)
    trading_sym = sorted_diff[-1][0]
    trade_price = ((detais[trading_sym][0] + detais[trading_sym][1])/2)
    print(trade_price)

    fcoin.sell(trading_sym, 0.002, 5)
    fcoin.buy(trading_sym, 0.0001, 10)
    print("-------- end --------")

    return

def get_balance(fcoin):
    eth_balance = 0
    usdt_balance = 0
    balances = fcoin.get_balance()
    for bl in balances['data']:
        if bl['currency'] == 'eth':
            eth_balance = float(bl['available'])
        elif bl['currency'] == 'usdt':
            usdt_balance = float(bl['available'])

    return eth_balance, usdt_balance

def mining(fcoin):
    # get initial balance
    eth_balance, usdt_balance = get_balance(fcoin=fcoin)
    print("initial balance eth: %f" % eth_balance)
    print("initial balance usdt: %f" % usdt_balance)

    trading_amont = 0.01
    while eth_balance > 0 and usdt_balance > 0:
    #while True:
        print("####### start trading session########")
        trading_sym = 'ethusdt'

        ret = fcoin.get_market_depth('L20', trading_sym)
        if ret['status'] == 0 and \
                len(ret['data']['bids']) and \
                len(ret['data']['asks']) > 0:
            lowest_ask = ret['data']['asks'][0]
            highest_bid = ret['data']['bids'][0]
            print('lowest ask: %f, highest bid: %f.'
                  % (lowest_ask, highest_bid))
            trade_price = ((lowest_ask + highest_bid)/2)
            print('trading price:%f' % trade_price)

            # get eth amount
            eth_balance = 0
            usdt_balance = 0
            balances = fcoin.get_balance()
            if balances != None:
                for bl in balances['data']:
                    if bl['currency'] == 'eth':
                        eth_balance = float(bl['available'])
                    elif bl['currency'] == 'usdt':
                        usdt_balance = float(bl['available'])

                need_usdt_amount = trade_price * eth_balance * 0.99
                trading_usdt_amount = usdt_balance * 0.99
                if need_usdt_amount < trading_usdt_amount:
                    trading_usdt_amount = need_usdt_amount

                trading_amont = (trading_usdt_amount/trade_price)
                print('trading amount: %f' % trading_amont)

                trade_price = "{0:.2f}".format(trade_price)
                trade_price = float(trade_price)

                trading_amont = "{0:.4f}".format(trading_amont)
                trading_amont = float(trading_amont)
                if trading_amont > 0.01:
                    print("sell&buy...")
                    #fcoin.sell(trading_sym, str(trade_price), trading_amont)
                    #fcoin.buy(trading_sym, str(trade_price), trading_amont)

                    def sell_(params):
                        trading_sym, trade_price, trading_amont = params
                        print('sell at %s' % time.time())
                        fcoin.sell(trading_sym, str(trade_price), trading_amont)

                    def buy_(params):
                        trading_sym, trade_price, trading_amont = params
                        print('buy  at %s' % time.time())
                        fcoin.buy(trading_sym, str(trade_price), trading_amont)

                    async def buyNsell():
                        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                            loop = asyncio.get_event_loop()
                            futures = [
                                loop.run_in_executor(
                                    executor,
                                    sell_,
                                    (trading_sym, trade_price, trading_amont)
                                ),
                                loop.run_in_executor(
                                    executor,
                                    buy_,
                                    (trading_sym, trade_price, trading_amont)
                                )
                            ]
                            for response in await asyncio.gather(*futures):
                                pass

                    loop = asyncio.get_event_loop()
                    loop.run_until_complete(buyNsell())
                else:
                    print("trading_amont should above 0.")
                print("-------- end --------")
            time.sleep(2)

    eth_balance, usdt_balance = get_balance(fcoin=fcoin)
    print("final balance eth: %f" % eth_balance)
    print("final balance usdt: %f" % usdt_balance)

    return

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default='check',  help="model type: check; mine")
    args = parser.parse_args()

    fcoin = Fcoin()
    api_key = os.environ["FCOIN_API_KEY"]
    api_sec = os.environ["FCOIN_API_SECRET"]
    fcoin.auth(api_key, api_sec)

    MODE = args.mode
    if MODE == 'check':
        check(fcoin=fcoin)
    elif MODE == 'mine':
        #eth_trades = ['fteth', 'zileth', 'icxeth', 'zipeth', 'omgeth']
        mining(fcoin=fcoin)
    elif MODE == 'test':
        balances = (fcoin.get_balance())
        currencies = []
        for bl in balances['data']:
            currencies.append(bl['currency'])
        print(currencies)