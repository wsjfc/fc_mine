# -*- coding: utf-8 -*-

from fcoin3 import Fcoin
import os
import operator
import argparse
import concurrent.futures
import asyncio
import time
import inspect
from pretty_dict import pretty_str

api_access_interval = 0.3

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

def fcoin_get_order(fcoin, sym, state, limits=20):
    orders = None
    while orders == None:
        orders = fcoin.list_orders(symbol=sym, states=state, limit=limits)
        if orders != None:
            return orders
        else:
            time.sleep(3)

def get_balance(fcoin, target_cur, base_cur):
    target_cur_balance = 0
    base_cur_balance = 0
    balances = None
    while balances == None:
        balances = fcoin.get_balance()
        if balances != None:
            for bl in balances['data']:
                if bl['currency'] == target_cur:
                    target_cur_balance = float(bl['available'])
                elif bl['currency'] == base_cur:
                    base_cur_balance = float(bl['available'])
        else:
            time.sleep(api_access_interval)

    return target_cur_balance, base_cur_balance


def auto_balance():
    target_cur_balance, base_cur_balance = get_balance(fcoin, target_currency, base_currency)
    print("initial balance %s: %f" % (target_currency, target_cur_balance))
    print("initial balance %s: %f" % (base_currency, base_cur_balance))
    trading_sym = target_currency + base_currency
    ret = fcoin.get_market_depth('L20', trading_sym)
    lowest_ask = ret['data']['asks'][0]
    highest_bid = ret['data']['bids'][0]
    initial_price = ((lowest_ask + highest_bid) / 2)

    initial_assets = initial_price * target_cur_balance + base_cur_balance
    split_target = initial_assets / 2
    if base_cur_balance < split_target:
        order_side = 'sell'
        price = highest_bid
        amount = (initial_price * target_cur_balance - split_target) / initial_price
        amount *= 0.98
        trading_amont = ("{0:.%df}" % (2)).format(amount)
        trading_amont = float(trading_amont)
        if trading_amont > 5:
            status = fcoin.sell(trading_sym, str(price), trading_amont)
            print('buy  status: ' + pretty_str(str(status)))
            if status == None:
                status = {'status': -1}
            while status['status'] != 0:
                time.sleep(api_access_interval)
                status = fcoin.sell(trading_sym, str(price), trading_amont)
                if status == None:
                    status = {'status': -1}
    else:
        order_side = 'buy'
        price = lowest_ask
        amount = (base_cur_balance - split_target) / initial_price
        amount *= 0.98
        trading_amont = ("{0:.%df}" % (2)).format(amount)
        trading_amont = float(trading_amont)
        if trading_amont > 5:
            status = fcoin.buy(trading_sym, str(price), trading_amont)
            print('buy  status: ' + pretty_str(str(status)))
            if status == None:
                status = {'status': -1}
            while status['status'] != 0:
                time.sleep(api_access_interval)
                status = fcoin.buy(trading_sym, str(price), trading_amont)
                if status == None:
                    status = {'status': -1}

def mining(fcoin, target_cur, base_cur, price_precision, amount_precision, debug=False, ignore_loss=False):
    # get initial balance
    target_cur_balance, base_cur_balance = get_balance(fcoin, target_cur, base_cur)
    print("initial balance %s: %f" % (target_cur, target_cur_balance))
    print("initial balance %s: %f" % (base_cur, base_cur_balance))
    input("Press Enter to continue...")

    trading_sym = target_cur + base_currency
    ret = fcoin.get_market_depth('L20', trading_sym)
    lowest_ask = ret['data']['asks'][0]
    highest_bid = ret['data']['bids'][0]
    initial_price = ((lowest_ask + highest_bid) / 2)

    initial_assets = initial_price * target_cur_balance + base_cur_balance

    trading_amont = 1
    prev_trading_amount = trading_amont
    trade_ctr = 0
    trading_loss = 0
    trade_dict = {}
    cumulative_exchange = 0
    ori_ts = time.time()
    ori_ts = ori_ts * 1000
    last_check_ts = ori_ts
    orders = []
    while target_cur_balance > 0 and base_cur_balance > 0:
        per_trade_start_time = time.time()
        print("------- start trading session -------")

        time.sleep(3.3)
        # get assets amount
        target_cur_balance = 0
        base_cur_balance = 0
        balances = None
        while balances == None:
            time.sleep(api_access_interval)
            balances = fcoin.get_balance()
            if balances != None:
                for bl in balances['data']:
                    if bl['currency'] == target_cur:
                        target_cur_balance = float(bl['available'])
                    elif bl['currency'] == base_cur:
                        base_cur_balance = float(bl['available'])
            else:
                time.sleep(api_access_interval)

        time.sleep(api_access_interval)
        ret = fcoin.get_market_depth('L20', trading_sym)
        ready = False
        while not ready:
            if ret == None:
                time.sleep(api_access_interval)
                ret = fcoin.get_market_depth('L20', trading_sym)
                continue
            elif ret['status'] == 0 and \
                len(ret['data']['bids']) and \
                len(ret['data']['asks']) > 0:
                ready = True

        lowest_ask = ret['data']['asks'][0]
        highest_bid = ret['data']['bids'][0]
        print('lowest ask: %f, highest bid: %f.'
              % (lowest_ask, highest_bid))
        trade_price = ((lowest_ask + highest_bid)/2)
        print('trading price:%f' % trade_price)

        need_basecurrency_amount = trade_price * target_cur_balance * 0.99
        trading_basecurrency_amount = base_cur_balance * 0.99
        if need_basecurrency_amount < trading_basecurrency_amount:
            trading_basecurrency_amount = need_basecurrency_amount

        trading_amont = (trading_basecurrency_amount/trade_price)

        trade_price = ("{0:.%df}" % (price_precision)).format(trade_price)
        trade_price = float(trade_price)

        trading_amont = ("{0:.%df}" % (amount_precision)).format(trading_amont)
        trading_amont = float(trading_amont)
        print('trading amount: ###--- %f ---### %f' % (trading_amont, trading_amont/prev_trading_amount))
        if trading_amont > 5:
            print("sell&buy...")
            def sell_(params):
                trading_sym, trade_price, trading_amont = params
                #time.sleep(1)
                status = fcoin.sell(trading_sym, str(trade_price), trading_amont)
                print('sell status: ' + str(status))
                if status == None:
                    status = {'status': -1}
                while status['status'] != 0:
                    time.sleep(api_access_interval)
                    status = fcoin.sell(trading_sym, str(trade_price), trading_amont)
                    if status == None:
                        status = {'status':-1}
                #cumulative_exchange += trade_price * trading_amont
                trade_dict['sell'] = (trade_price, trading_amont)

            def buy_(params):
                trading_sym, trade_price, trading_amont = params
                #time.sleep(1)
                status = fcoin.buy(trading_sym, str(trade_price), trading_amont)
                print('buy  status: ' + str(status))
                if status == None:
                    status = {'status': -1}
                while status['status'] != 0:
                    time.sleep(api_access_interval)
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
            if debug:
                input('Press Enter to check order status.')
            while waiting:
                time.sleep(1.5)
                orders_submitted = fcoin_get_order(fcoin, trading_sym, 'submitted')
                time.sleep(api_access_interval)
                orders_partial_filled = fcoin_get_order(fcoin, trading_sym, 'partial_filled')
                orders_data = orders_submitted['data'] + orders_partial_filled['data']
                print(pretty_str(orders_data))
                if len(orders_data) == 0:
                    waiting = False
                else:
                    wait_ctr += 1
                    time.sleep(1)

                if wait_ctr >= 1:
                    time.sleep(api_access_interval)
                    orders_submitted = fcoin_get_order(fcoin, trading_sym, 'submitted')
                    time.sleep(api_access_interval)
                    orders_partial_filled = fcoin_get_order(fcoin, trading_sym, 'partial_filled')
                    orders_data = orders_submitted['data'] + orders_partial_filled['data']
                    dealed_order_ids = []
                    for order in orders_data:
                        if order['id'] in dealed_order_ids:
                            continue
                        dealed_order_ids.append(order['id'])
                        if debug:
                            input('Press Enter to cancel order.')

                        time.sleep(api_access_interval)

                        cancel_status = fcoin.cancel_order(order['id'])
                        print('cancel status: %s' % cancel_status)

                        canceled = False
                        detail_status = ""

                        while cancel_status == None:
                            time.sleep(3)
                            status = fcoin.get_order(order_id=order['id'])
                            print(pretty_str(status))
                            while status == None:
                                time.sleep(5)
                                status = fcoin.get_order(order_id=order['id'])
                            if status['data']['state'] == "filled" or \
                                status['data']['state'] == "partial_canceled":
                                cancel_status = {'status' : 0}
                            elif status['data']['state'] == "submitted" :
                                cancel_status = fcoin.cancel_order(order['id'])
                            elif status['data']['state'] == "partial_filled":
                                order = status['data']
                                cancel_status = {'status': 0}
                                canceled = True
                                detail_status = "partial_filled"
                            elif status['data']['state'] == "canceled":
                                order = status['data']
                                cancel_status = {'status': 0}
                                canceled = True
                                detail_status = "canceled"

                        while not canceled:
                            status = None
                            while status == None:
                                time.sleep(3)
                                status = fcoin.get_order(order_id=order['id'])
                                if status != None:
                                    print(pretty_str(status))
                                    detail_status = status['data']['state']
                                    if detail_status == "canceled" or \
                                                    detail_status == "filled" or \
                                                    detail_status == "partial_canceled":
                                        print("cancel order result: %s" % detail_status)
                                        order = status['data']
                                        canceled = True
                                    else:
                                        print('not canceled yet: %s.' % detail_status)
                                        time.sleep(2)
                                else:
                                    time.sleep(1)
                        if detail_status == "canceled" \
                                or detail_status == "partial_canceled" \
                                or detail_status == "partial_filled":
                            if debug:
                                input('Press Enter to replace the order.')

                            order_amount_total = order['amount']
                            order_amount_executed = order['filled_amount']
                            order_amount = float(order_amount_total) - float(order_amount_executed)
                            order_price = order['amount']
                            order_side = order['side']
                            order_amount = ("{0:.%df}" % amount_precision).format(float(order_amount))
                            order_amount = float(order_amount)

                            if cancel_status != None and cancel_status['status'] == 0 and order_amount > 5:
                                if order_side == 'buy':
                                    canceld_order_price, canceld_order_amount = trade_dict['buy']
                                    print("canceled order price: %f" % canceld_order_price)
                                    cumulative_exchange -= canceld_order_price * canceld_order_amount
                                    usdt_balance = 0
                                    balances = None
                                    while balances == None:
                                        time.sleep(api_access_interval)
                                        balances = fcoin.get_balance()
                                        if balances != None:
                                            for bl in balances['data']:
                                                if bl['currency'] == 'usdt':
                                                    usdt_balance = float(bl['available'])
                                        else:
                                            time.sleep(api_access_interval)

                                    time.sleep(api_access_interval)
                                    ret = fcoin.get_market_depth('L20', trading_sym)
                                    while ret == None:
                                        time.sleep(api_access_interval)
                                        ret = fcoin.get_market_depth('L20', trading_sym)

                                    lowest_ask = ret['data']['asks'][0]
                                    highest_bid = ret['data']['bids'][0]

                                    if usdt_balance < lowest_ask * order_amount:
                                        order_amount = 0.99 * usdt_balance / lowest_ask
                                        order_amount = (("{0:.%df}" % amount_precision).format(order_amount))
                                        order_amount = float(order_amount)
                                    if order_amount > 5:
                                        time.sleep(api_access_interval)
                                        status = fcoin.buy(trading_sym, str(lowest_ask), order_amount)
                                        print(pretty_str(str(status)) + str(lineno()))
                                        if status == None:
                                            status = {'status': -1}
                                        elif status['status'] == 0:
                                            cumulative_exchange += lowest_ask * order_amount
                                            trade_dict['buy'] = (lowest_ask, order_amount)
                                        while status['status'] != 0:
                                            time.sleep(4)
                                            status = fcoin.buy(trading_sym, str(lowest_ask), order_amount)
                                            print(pretty_str(str(status)) + str(lineno()))
                                            if status == None:
                                                status = {'status': -1}
                                            elif status['status'] == 1002:
                                                time.sleep(api_access_interval)
                                            elif status['status'] == 0:
                                                cumulative_exchange += lowest_ask * order_amount
                                                trade_dict['buy'] = (lowest_ask, order_amount)

                                elif order_side == 'sell':
                                    canceld_order_price, canceld_order_amount = trade_dict['sell']
                                    print("canceled order price: %f" % canceld_order_price)
                                    cumulative_exchange -= canceld_order_price * canceld_order_amount

                                    time.sleep(api_access_interval)
                                    ret = fcoin.get_market_depth('L20', trading_sym)
                                    while ret == None:
                                        time.sleep(api_access_interval)
                                        ret = fcoin.get_market_depth('L20', trading_sym)

                                    lowest_ask = ret['data']['asks'][0]
                                    highest_bid = ret['data']['bids'][0]

                                    time.sleep(api_access_interval)
                                    status = fcoin.sell(trading_sym, str(highest_bid), order_amount)
                                    print(pretty_str(str(status)) + str(lineno()))
                                    if status == None:
                                        status = {'status': -1}
                                    elif status['status'] == 0:
                                        cumulative_exchange += highest_bid * order_amount
                                        trade_dict['buy'] = (highest_bid, order_amount)
                                    while status['status'] != 0:
                                        time.sleep(4)
                                        status = fcoin.sell(trading_sym, str(highest_bid), order_amount)
                                        print(pretty_str(str(status)) + ' ' + str(lineno()))
                                        if status == None:
                                            status = {'status': -1}
                                        elif status['status'] == 0:
                                            cumulative_exchange += highest_bid * order_amount
                                            trade_dict['buy'] = (highest_bid, order_amount)
                                time.sleep(api_access_interval)
                                wait_ctr = 0

            prev_trading_amount = trading_amont
            trade_ctr += 1
            print("trade counter: %d" % trade_ctr)

            if trade_ctr % 20 == 0:
                auto_balance()

            if trade_ctr % 30 == 0 and not ignore_loss:
                print(' $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ ')
                max_order_limit = 100
                time.sleep(api_access_interval)
                orders_filled = fcoin_get_order(fcoin, 'ftusdt', 'filled', max_order_limit)
                while orders_filled == None:
                    time.sleep(api_access_interval)
                    orders_filled = fcoin_get_order(fcoin, 'ftusdt', 'filled', max_order_limit)

                time.sleep(api_access_interval)
                orders_partial_canceled = fcoin_get_order(fcoin, 'ftusdt', 'partial_canceled', max_order_limit)
                while orders_partial_canceled == None:
                    time.sleep(api_access_interval)
                    orders_partial_canceled = fcoin_get_order(fcoin, 'ftusdt', 'partial_canceled', max_order_limit)

                time.sleep(api_access_interval)
                orders_partial_filled = fcoin_get_order(fcoin, 'ftusdt', 'partial_filled', max_order_limit)
                while orders_partial_filled == None:
                    time.sleep(api_access_interval)
                    orders_partial_filled = fcoin_get_order(fcoin, 'ftusdt', 'partial_filled', max_order_limit)

                orders_finished = orders_filled['data'] + orders_partial_canceled['data'] + orders_partial_filled['data']

                for order in orders_finished:
                    ts = order['created_at']
                    if ts > last_check_ts and order['id'] not in orders:
                        side = order['side']
                        executed_val = order['executed_value']
                        price = order['price']
                        if side == 'buy':
                            trading_loss += float(executed_val) * float(price)
                        else:
                            trading_loss -= float(executed_val) * float(price)
                        orders.append(order['id'])
                print("trading loss: %f, loss fraction: %f, estimated profit fraction: %f" %
                      (trading_loss, trading_loss/initial_assets, (1-(0.999**trade_ctr))*0.2))
                last_check_ts = time.time()
                last_check_ts *= 1000
                print(' $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ ')

        else:
            print("trading_amount should above 5.")
            auto_balance()

        print("trade time: " "{0:.2f}".format(time.time() - per_trade_start_time))
        print("-------- end --------")

    target_cur_balance, base_cur_balance = get_balance(fcoin=fcoin)
    print("final balance %s: %f" % (target_cur, target_cur_balance))
    print("final balance %s: %f" % (base_cur, base_cur_balance))

    return

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default='check',  help="model type: check; mine; test.")
    parser.add_argument("--cur", default='ft_usdt',  help="currency type: ft_usdt, etc_usdt, omg_eth ...")
    parser.add_argument("--debug", default=False, action='store_true')
    parser.add_argument("--ignore", default=False, action='store_true')

    args = parser.parse_args()

    fcoin = Fcoin()
    api_key = os.environ["FCOIN_API_KEY_0"]
    api_sec = os.environ["FCOIN_API_SECRET_0"]
    fcoin.auth(api_key, api_sec)

    precision_dict = {
        'ft_usdt': (6, 2),
        'etc_usdt': (2, 4),
        'omg_eth' : (6, 4),
        'ft_eth' : (8, 2)
    }

    MODE = args.mode
    sym_pair = args.cur
    DEBUG = args.debug
    ignore_loss = args.ignore
    target_currency = sym_pair.split('_')[0]
    base_currency = sym_pair.split('_')[1]

    if MODE == 'check':
        check(fcoin=fcoin)
    elif MODE == 'mine':
        price_precision, amount_precision = precision_dict[sym_pair]
        mining(fcoin, target_currency, base_currency, price_precision, amount_precision, debug=DEBUG, ignore_loss=ignore_loss)
    elif MODE == 'cancel':
        orders_submitted = fcoin_get_order(fcoin, 'ftusdt', 'submitted')
        orders_partial_filled = fcoin_get_order(fcoin, 'ftusdt', 'partial_filled')
        for order in orders_submitted['data'] + orders_partial_filled['data']:
            cancel_status = fcoin.cancel_order(order['id'])
            print('cancel status: %s' % pretty_str(cancel_status))
            if cancel_status == None:
                cancel_status = {'status': -1}
            while cancel_status['status'] != 0 and cancel_status['status'] != 3008:
                time.sleep(1)
                cancel_status = fcoin.cancel_order(order['id'])
                if cancel_status == None:
                    cancel_status = {'status': -1}
        print('done')

    elif MODE == 'split':
        auto_balance()

        target_cur_balance, base_cur_balance = get_balance(fcoin, target_currency, base_currency)
        print("balance of %s: %f" % (target_currency, target_cur_balance))
        print("balance of %s: %f" % (base_currency, base_cur_balance))


