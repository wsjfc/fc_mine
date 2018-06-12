# -*- coding: utf-8 -*-

from fcoin3 import Fcoin
import os
import operator
import argparse
import concurrent.futures
import asyncio
import time
import copy

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

    return usdt_trades

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

def mining(fcoin0, fcoin1):
    # get initial balance
    usdt_balance = 0
    balances = fcoin0.get_balance()
    for bl in balances['data']:
        if bl['currency'] == 'eth':
            usdt_balance = float(bl['available'])

    etc_balance = 0
    balances = fcoin1.get_balance()
    for bl in balances['data']:
        if bl['currency'] == 'omg':
            etc_balance = float(bl['available'])

    print("initial balance eth: %f" % usdt_balance)
    print("initial balance omg: %f" % etc_balance)

    trading_amont = 0.01
    while etc_balance > 0 and usdt_balance > 0:
        print("####### start trading session########")
        trading_sym = 'omgeth'

        ret = fcoin0.get_market_depth('L20', trading_sym)
        if ret['status'] == 0 and \
                len(ret['data']['bids']) and \
                len(ret['data']['asks']) > 0:
            lowest_ask = ret['data']['asks'][0]
            highest_bid = ret['data']['bids'][0]
            print('lowest ask: %f, highest bid: %f.'
                  % (lowest_ask, highest_bid))
            trade_price = ((lowest_ask + highest_bid)/2)
            print('trading price:%f' % trade_price)

            # get etc amount
            usdt_balance = 0
            etc_balance = 0
            balances_usdt = fcoin0.get_balance()
            balances_etc  = fcoin1.get_balance()
            if balances_usdt != None and balances_etc != None:
                for bl in balances_usdt['data']:
                    if bl['currency'] == 'eth':
                        usdt_balance = float(bl['available'])
                for bl in balances_etc['data']:
                    if bl['currency'] == 'omg':
                        etc_balance = float(bl['available'])

                need_usdt_amount = trade_price * etc_balance * 0.99
                trading_usdt_amount = usdt_balance * 0.99
                if need_usdt_amount < trading_usdt_amount:
                    trading_usdt_amount = need_usdt_amount

                trading_amont = (trading_usdt_amount/trade_price)
                print('trading amount: %f' % trading_amont)
                input("Press Enter to continue...")
                trade_price = "{0:.4f}".format(trade_price)
                trade_price = float(trade_price)

                trading_amont = "{0:.4f}".format(trading_amont)
                trading_amont = float(trading_amont)
                trading_amont -= 0.001
                if trading_amont > 0.0001:
                    print("sell&buy...")
                    #fcoin.sell(trading_sym, str(trade_price), trading_amont)
                    #fcoin.buy(trading_sym, str(trade_price), trading_amont)

                    def sell_(params):
                        trading_sym, trade_price, trading_amont = params
                        print('sell at %s' % time.time())
                        fcoin1.sell(trading_sym, str(trade_price), trading_amont)

                    def buy_(params):
                        trading_sym, trade_price, trading_amont = params
                        print('buy  at %s' % time.time())
                        fcoin0.buy(trading_sym, str(trade_price), trading_amont * 0.99)

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

                #time.sleep(1)
                print("-------- end --------")

                # check to decide which is 'fcoin0' account, according to usdt balance
                usdt_balance_0 = 0
                balances = fcoin0.get_balance()
                for bl in balances['data']:
                    if bl['currency'] == 'eth':
                        usdt_balance_0 = float(bl['available'])

                usdt_balance_1 = 0
                balances = fcoin1.get_balance()
                for bl in balances['data']:
                    if bl['currency'] == 'eth':
                        usdt_balance_1 = float(bl['available'])

                if usdt_balance_0 < usdt_balance_1:
                    print("switch default usdt account.")
                    tmp_fcoin = copy.deepcopy(fcoin0)
                    fcoin0 = copy.deepcopy(fcoin1)
                    fcoin1 = copy.deepcopy(tmp_fcoin)

        #input("Press Enter to continue...")

    usdt_balance = 0
    balances = fcoin0.get_balance()
    for bl in balances['data']:
        if bl['currency'] == 'eth':
            usdt_balance = float(bl['available'])

    etc_balance = 0
    balances = fcoin1.get_balance()
    for bl in balances['data']:
        if bl['currency'] == 'omg':
            etc_balance = float(bl['available'])
    print("final balance etc: %f" % etc_balance)
    print("final balance usdt: %f" % usdt_balance)

    return

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default='check',  help="model type: check; mine")
    args = parser.parse_args()

    fcoin0 = Fcoin()
    api_key_0 = os.environ["FCOIN_API_KEY_0"]
    api_sec_0 = os.environ["FCOIN_API_SECRET_0"]
    fcoin0.auth(api_key_0, api_sec_0)

    fcoin1 = Fcoin()
    api_key_1 = os.environ["FCOIN_API_KEY_1"]
    api_sec_1 = os.environ["FCOIN_API_SECRET_1"]
    fcoin1.auth(api_key_1, api_sec_1)

    MODE = args.mode
    if MODE == 'check':
        check(fcoin=fcoin0)
    elif MODE == 'mine':
        usdt_balance_0 = 0
        balances = fcoin0.get_balance()
        for bl in balances['data']:
            if bl['currency'] == 'eth':
                usdt_balance_0 = float(bl['available'])

        usdt_balance_1 = 0
        balances = fcoin1.get_balance()
        for bl in balances['data']:
            if bl['currency'] == 'eth':
                usdt_balance_1 = float(bl['available'])

        if usdt_balance_0 < usdt_balance_1:
            print("switch default usdt account.")
            tmp_fcoin = copy.deepcopy(fcoin0)
            fcoin0 = copy.deepcopy(fcoin1)
            fcoin1 = copy.deepcopy(tmp_fcoin)
        mining(fcoin0=fcoin0, fcoin1=fcoin1)
    elif MODE == 'test':
        balances = (fcoin0.get_balance())
        currencies = []
        for bl in balances['data']:
            currencies.append(bl['currency'])
        print(currencies)