# -*- coding: utf-8 -*-

from fcoin3 import Fcoin
import os
import operator
import argparse
import concurrent.futures
import asyncio
import time
import inspect

def lineno():
    """Returns the current line number in our program."""
    return inspect.currentframe().f_back.f_lineno

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

def fcoin_get_order(fcoin, sym, state):
    orders = None
    while orders == None:
        orders = fcoin.list_orders(symbol=sym, states=state)
        if orders != None:
            return orders
        else:
            time.sleep(2)

def get_balance(fcoin, target_cur, base_cur):
    omg_balance = 0
    eth_balance = 0
    balances = None
    while balances == None:
        balances = fcoin.get_balance()
        if balances != None:
            for bl in balances['data']:
                if bl['currency'] == target_cur:
                    omg_balance = float(bl['available'])
                elif bl['currency'] == base_cur:
                    eth_balance = float(bl['available'])
        else:
            time.sleep(2)

    return omg_balance, eth_balance

def mining(fcoin, target_cur, base_cur, price_precision, amount_precision):
    # get initial balance
    omg_balance, eth_balance = get_balance(fcoin, target_cur, base_cur)
    print("initial balance %s: %f" % (target_cur, omg_balance))
    print("initial balance %s: %f" % (base_cur, eth_balance))
    input("Press Enter to continue...")

    trading_sym = target_cur + base_currency
    ret = fcoin.get_market_depth('L20', trading_sym)
    lowest_ask = ret['data']['asks'][0]
    highest_bid = ret['data']['bids'][0]
    initial_price = ((lowest_ask + highest_bid) / 2)

    total_assets = initial_price * omg_balance + eth_balance

    trading_amont = 1
    prev_trading_amount = trading_amont
    trade_ctr = 0
    trading_loss = 0
    trade_dict = {}
    while omg_balance > 0 and eth_balance > 0:
        print("------- start trading session -------")

        ret = fcoin.get_market_depth('L20', trading_sym)
        if ret == None:
            continue

        if ret['status'] == 0 and \
                len(ret['data']['bids']) and \
                len(ret['data']['asks']) > 0:
            # get eth amount
            omg_balance = 0
            eth_balance = 0
            balances = None
            while balances == None:
                balances = fcoin.get_balance()
                if balances != None:
                    for bl in balances['data']:
                        if bl['currency'] == target_cur:
                            omg_balance = float(bl['available'])
                        elif bl['currency'] == base_cur:
                            eth_balance = float(bl['available'])
                else:
                    time.sleep(2)

            lowest_ask = ret['data']['asks'][0]
            highest_bid = ret['data']['bids'][0]
            print('lowest ask: %f, highest bid: %f.'
                  % (lowest_ask, highest_bid))
            trade_price = ((lowest_ask + highest_bid)/2)
            print('trading price:%f' % trade_price)

            need_eth_amount = trade_price * omg_balance * 0.99
            trading_eth_amount = eth_balance * 0.99
            if need_eth_amount < trading_eth_amount:
                trading_eth_amount = need_eth_amount

            trading_amont = (trading_eth_amount/trade_price)

            trade_price = ("{0:.%df}" % (price_precision)).format(trade_price)
            trade_price = float(trade_price)

            trading_amont = ("{0:.%df}" % (amount_precision)).format(trading_amont)
            trading_amont = float(trading_amont)
            print('trading amount: ###--- %f ---### %f' % (trading_amont, trading_amont/prev_trading_amount))
            cumulative_exchange = 0
            if trading_amont > 5:
                print("sell&buy...")
                def sell_(params):
                    trading_sym, trade_price, trading_amont = params
                    status = fcoin.sell(trading_sym, str(trade_price), trading_amont)
                    print('sell status' + str(status))
                    if status != None:
                        while status['status'] != 0:
                            time.sleep(2)
                            status = fcoin.sell(trading_sym, str(trade_price), trading_amont)
                            if status == None:
                                status = {'status':-1}
                        #cumulative_exchange += trade_price * trading_amont
                    trade_dict['sell'] = (trade_price, trading_amont)

                def buy_(params):
                    trading_sym, trade_price, trading_amont = params
                    status = fcoin.buy(trading_sym, str(trade_price), trading_amont)
                    print('buy  status' + str(status))
                    if status != None:
                        while status['status'] != 0:
                            time.sleep(2)
                            status = fcoin.buy(trading_sym, str(trade_price), trading_amont)
                            if status == None:
                                status = {'status':-1}
                        #cumulative_exchange += trade_price * trading_amont
                    trade_dict['buy'] = (trade_price, trading_amont)

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

                # check orders status
                waiting = True
                wait_ctr = 0
                while waiting:
                    time.sleep(3)
                    #orders = fcoin.list_orders(symbol=trading_sym, states='submitted')
                    orders = fcoin_get_order(fcoin, trading_sym, 'submitted')
                    print(orders)
                    if len(orders['data']) == 0:
                        waiting = False
                    else:
                        wait_ctr += 1
                        time.sleep(1)

                    if wait_ctr > 3:
                        ret = fcoin.get_market_depth('L20', trading_sym)

                        lowest_ask = ret['data']['asks'][0]
                        highest_bid = ret['data']['bids'][0]

                        orders_submitted = fcoin_get_order(fcoin, trading_sym, 'submitted')
                        #orders_partial_canceled = fcoin_get_order(fcoin, trading_sym, 'partial_canceled')
                        #orders_partial_filled = fcoin_get_order(fcoin, trading_sym, 'partial_filled')
                        orders_data = orders_submitted['data']
                                      #orders_partial_canceled['data'] + \
                                      #orders_partial_filled['data']
                        for order in orders_data:
                            cancel_status = fcoin.cancel_order(order['id'])
                            canceled = False
                            detail_status = ""
                            while not canceled:
                                status = None
                                while status == None:
                                    status = fcoin.get_order(order_id=order['id'])
                                    if status != None:
                                        print(status)
                                        detail_status = status['data']['state']
                                        if detail_status == "canceled" or \
                                                        detail_status == "filled":
                                            print("cancel order result: %s" % detail_status)
                                            canceled = True
                                        else:
                                            print('not canceled yet: %s.'% detail_status)
                                            time.sleep(3)
                                    else:
                                        time.sleep(2)
                            if detail_status == "canceled":
                                order_amount = order['amount']
                                order_price = order['amount']
                                order_side = order['side']
                                order_amount = ("{0:.%df}" % amount_precision).format(float(order_amount))
                                order_amount = float(order_amount)

                                if cancel_status != None and cancel_status['status'] == 0:
                                    if order_side == 'buy':
                                        canceld_order_price, canceld_order_amount = trade_dict['buy']
                                        cumulative_exchange -= canceld_order_price * canceld_order_amount
                                        usdt_balance = 0
                                        balances = None
                                        while balances == None:
                                            balances = fcoin.get_balance()
                                            if balances != None:
                                                for bl in balances['data']:
                                                    if bl['currency'] == 'usdt':
                                                        usdt_balance = float(bl['available'])
                                            else:
                                                time.sleep(2)
                                        if usdt_balance < lowest_ask * order_amount:
                                            order_amount = 0.99 * usdt_balance / lowest_ask
                                            order_amount = (("{0:.%df}" % amount_precision).format(order_amount))
                                            order_amount = float(order_amount)
                                        status = fcoin.buy(trading_sym, str(lowest_ask), order_amount)
                                        print(str(status) + str(lineno()))
                                        if status == None:
                                            status = {'status': -1}
                                        elif status['status'] == 0:
                                            cumulative_exchange += lowest_ask * order_amount
                                            trade_dict['buy'] = (lowest_ask, order_amount)
                                        while status['status'] != 0:
                                            time.sleep(2)
                                            status = fcoin.buy(trading_sym, str(lowest_ask), order_amount)
                                            print(str(status) + str(lineno()))
                                            if status == None:
                                                status = {'status': -1}
                                            elif status['status'] == 1002:
                                                time.sleep(10)
                                            elif status['status'] == 0:
                                                cumulative_exchange += lowest_ask * order_amount
                                                trade_dict['buy'] = (lowest_ask, order_amount)

                                    elif order_side == 'sell':
                                        canceld_order_price, canceld_order_amount = trade_dict['sell']
                                        cumulative_exchange -= canceld_order_price * canceld_order_amount
                                        status = fcoin.sell(trading_sym, str(highest_bid), order_amount)
                                        print(str(status) + str(lineno()))
                                        if status == None:
                                            status = {'status': -1}
                                        elif status['status'] == 0:
                                            cumulative_exchange += highest_bid * order_amount
                                            trade_dict['buy'] = (highest_bid, order_amount)
                                        while status['status'] != 0:
                                            time.sleep(2)
                                            status = fcoin.sell(trading_sym, str(highest_bid), order_amount)
                                            print(str(status) + ' ' + str(lineno()))
                                            if status == None:
                                                status = {'status': -1}
                                            elif status['status'] == 0:
                                                cumulative_exchange += lowest_ask * order_amount
                                                trade_dict['buy'] = (lowest_ask, order_amount)
                                    time.sleep(2)
                        waiting = False

                prev_trading_amount = trading_amont
                trade_ctr += 1
                print("trade times: %d" % trade_ctr)
                if len(trade_dict) > 0:
                    buy_price, buy_amount = trade_dict['buy']
                    sell_price, sell_amount = trade_dict['sell']
                    diff_amount = buy_amount if buy_amount < sell_amount else sell_amount
                    trading_loss += (buy_price - sell_price) * diff_amount

                    print("trading loss: %f" % trading_loss)
            else:
                print("trading_amont should above 5.")

            print("-------- end --------")

    omg_balance, eth_balance = get_balance(fcoin=fcoin)
    print("final balance %s: %f" % (target_cur, omg_balance))
    print("final balance %s: %f" % (base_cur, eth_balance))

    return

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default='check',  help="model type: check; mine")
    parser.add_argument("--cur", default='ft_usdt',  help="currency type: ft_usdt, etc_usdt ...")
    args = parser.parse_args()

    fcoin = Fcoin()
    api_key = os.environ["FCOIN_API_KEY_1"]
    api_sec = os.environ["FCOIN_API_SECRET_1"]
    fcoin.auth(api_key, api_sec)

    precision_dict = {
        'ft_usdt': (6, 2),
        'etc_usdt': (2, 4)
    }

    MODE = args.mode
    sym_pair = args.cur
    target_currency = sym_pair.split('_')[0]
    base_currency = sym_pair.split('_')[1]
    if MODE == 'check':
        check(fcoin=fcoin)
    elif MODE == 'mine':
        price_precision, amount_precision = precision_dict[sym_pair]
        mining(fcoin, target_currency, base_currency, price_precision, amount_precision)
    elif MODE == 'test':
        status = fcoin.sell('ftusdt', str(1.3), 10)
        print(status)
