# -*- coding: utf-8 -*-

from fcoin3 import Fcoin
import os
import operator
import argparse
import concurrent.futures
import asyncio
import time
import inspect

api_access_interval = 0.3


def line_no():
    """Returns the current line number in our program."""
    return inspect.currentframe().f_back.f_lineno


def check():
    symbols = fcoin.get_symbols()

    # get trade symbol pairs
    usdt_trades = []
    for sym in symbols:
        if sym['quote_currency'] == 'usdt':
            usdt_trades.append(sym['base_currency'] + 'usdt')
    print(usdt_trades)

    btc_trades = []
    for sym in symbols:
        if sym['quote_currency'] == 'btc':
            btc_trades.append(sym['base_currency'] + 'btc')
    print(btc_trades)

    eth_trades = []
    for sym in symbols:
        if sym['quote_currency'] == 'eth':
            eth_trades.append(sym['base_currency'] + 'eth')
    print(eth_trades)

    # get sorted symbol with the diff betweem lowest asks and highest bids
    for trades in [usdt_trades, btc_trades, eth_trades]:
        print('#######################################')
        diffs = {}
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
        sorted_diff = sorted(diffs.items(), key=operator.itemgetter(1))
        print(sorted_diff)

    return eth_trades


def fcoin_get_order(sym, state, limits=20):
    orders = None
    while orders is None:
        orders = fcoin.list_orders(symbol=sym, states=state, limit=limits)
        if orders is not None:
            return orders
        else:
            time.sleep(api_access_interval)


def get_balance():
    target_cur_balance = 0
    base_cur_balance = 0
    while True:
        balances = fcoin.get_balance()
        if balances is None:
            time.sleep(api_access_interval)
            continue
        for bl in balances['data']:
            if bl['currency'] == target_currency:
                target_cur_balance = float(bl['available'])
            elif bl['currency'] == base_currency:
                base_cur_balance = float(bl['available'])
        return target_cur_balance, base_cur_balance


def mining(debug=False, ignore_loss=False):
    # get initial balance
    target_cur_balance, base_cur_balance = get_balance()
    print("initial balance %s: %f" % (target_currency, target_cur_balance))
    print("initial balance %s: %f" % (base_currency, base_cur_balance))
    input("Press Enter to continue...")

    trading_sym = target_currency + base_currency
    # ret = fcoin.get_market_depth('L20', trading_sym)
    # lowest_ask = ret['data']['asks'][0]
    # highest_bid = ret['data']['bids'][0]
    # initial_price = ((lowest_ask + highest_bid) / 2)

    # initial_assets = initial_price * target_cur_balance + base_cur_balance

    trading_amount = 1
    prev_trading_amount = trading_amount
    trade_ctr = 0
    # trading_loss = 0
    trade_dict = {}
    cumulative_exchange = 0
    ori_ts_ = time.time()
    ori_ts_ = ori_ts_ * 1000
    last_check_ts = ori_ts_
    orders = []
    while target_cur_balance > 0 and base_cur_balance > 0:
        print("------- start trading session -------")

        time.sleep(3.3)
        # get assets amount
        target_cur_balance, base_cur_balance = get_balance()

        time.sleep(api_access_interval)
        ret = fcoin.get_market_depth('L20', trading_sym)
        while (not ret
               or ret['status'] != 0
               or len(ret['data']['bids']) * len(ret['data']['asks']) == 0):
            time.sleep(api_access_interval)
            ret = fcoin.get_market_depth('L20', trading_sym)

        lowest_ask = ret['data']['asks'][0]
        highest_bid = ret['data']['bids'][0]
        print('lowest ask: %f, highest bid: %f.'
              % (lowest_ask, highest_bid))
        trading_price = ((lowest_ask + highest_bid) / 2)
        print('trading price: %f' % trading_price)

        need_base_currency_amount = trading_price * target_cur_balance * 0.99
        trading_base_currency_amount = base_cur_balance * 0.99
        if need_base_currency_amount < trading_base_currency_amount:
            trading_base_currency_amount = need_base_currency_amount

        trading_amount = trading_base_currency_amount / trading_price

        trading_price = ("{0:.%df}" % price_precision).format(trading_price)
        trading_price = float(trading_price)

        trading_amount = ("{0:.%df}" % amount_precision).format(trading_amount)
        trading_amount = float(trading_amount)
        print('trading amount: ###--- %f ---### %f' % (trading_amount, trading_amount / prev_trading_amount))
        if trading_amount <= 5:
            print("trading_amount should above 5.")
            print("-------- end --------")
            continue

        print("sell&buy...")

        def sell_(params):
            trade_sym, trade_price, trade_amount = params
            # time.sleep(1)
            status_ = fcoin.sell(trade_sym, str(trade_price), trade_amount)
            print('sell status' + str(status_))

            while status_ is None or status_['status'] != 0:
                time.sleep(api_access_interval)
                status_ = fcoin.sell(trade_sym, str(trade_price), trade_amount)

            # cumulative_exchange += trade_price * trading_amont
            trade_dict['sell'] = (trade_price, trade_amount)

        def buy_(params):
            trade_sym, trade_price, trade_amount = params
            # time.sleep(1)
            status_ = fcoin.buy(trade_sym, str(trade_price), trade_amount)
            print('buy  status' + str(status_))

            while status_ is None or status_['status'] != 0:
                time.sleep(api_access_interval)
                status_ = fcoin.buy(trade_sym, str(trade_price), trade_amount)

            # cumulative_exchange += trade_price * trading_amont
            trade_dict['buy'] = (trade_price, trade_amount)

        async def buy_sell():
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                loop_ = asyncio.get_event_loop()
                futures = [
                    loop_.run_in_executor(
                        executor,
                        sell_,
                        (trading_sym, trading_price, trading_amount)
                    ),
                    loop_.run_in_executor(
                        executor,
                        buy_,
                        (trading_sym, trading_price, trading_amount)
                    )
                ]
                for _ in await asyncio.gather(*futures):  # response
                    pass

        loop = asyncio.get_event_loop()
        loop.run_until_complete(buy_sell())

        # check orders status
        waiting = True
        wait_ctr = 0
        if debug:
            input('Press Enter to check order status.')
        while waiting:
            time.sleep(3)
            orders_submitted = fcoin_get_order(trading_sym, 'submitted')
            time.sleep(api_access_interval)
            orders_partially_filled = fcoin_get_order(trading_sym, 'partial_filled')
            orders_data = orders_submitted['data'] + orders_partially_filled['data']
            print(orders_data)
            if not orders_data:
                waiting = False
            else:
                wait_ctr += 1
                time.sleep(1)

            if wait_ctr <= 1:
                continue
            time.sleep(api_access_interval)
            orders_submitted = fcoin_get_order(trading_sym, 'submitted')
            time.sleep(api_access_interval)
            orders_partially_filled = fcoin_get_order(trading_sym, 'partial_filled')
            orders_data = orders_submitted['data'] + orders_partially_filled['data']
            for order_data in orders_data:
                if debug:
                    input('Press Enter to cancel order.')

                time.sleep(api_access_interval)
                while True:
                    cancel_status = fcoin.cancel_order(order_data['id'])
                    if cancel_status and cancel_status['status'] == 0:
                        break
                    time.sleep(api_access_interval)
                canceled = False
                detail_status = ""
                while not canceled:
                    status = None
                    while status is None:
                        time.sleep(api_access_interval)
                        status = fcoin.get_order(order_id=order_data['id'])
                        if status is not None:
                            print(status)
                            detail_status = status['data']['state']
                            if detail_status in ["canceled", "filled", "partial_canceled"]:
                                print("cancel order result: %s" % detail_status)
                                canceled = True
                            else:
                                print('not canceled yet: %s.' % detail_status)
                                # fcoin.cancel_order(order['id'])
                                time.sleep(2)
                        else:
                            time.sleep(1)
                if detail_status not in ["canceled", "partial_canceled"]:
                    continue
                if debug:
                    input('Press Enter to replace the order.')
                order_amount_total = order_data['amount']
                order_amount_executed = order_data['filled_amount']
                order_amount = float(order_amount_total) - float(order_amount_executed)
                # order_price = order_data['amount']
                order_side = order_data['side']
                order_amount = ("{0:.%df}" % amount_precision).format(float(order_amount))
                order_amount = float(order_amount)

                if not (cancel_status is not None and cancel_status['status'] == 0 and order_amount > 5):
                    continue
                if order_side == 'buy':
                    cancelled_order_price, cancelled_order_amount = trade_dict['buy']
                    print("canceled order price: %f" % cancelled_order_price)
                    cumulative_exchange -= cancelled_order_price * cancelled_order_amount
                    _, usdt_balance = get_balance()

                    time.sleep(api_access_interval)
                    ret = fcoin.get_market_depth('L20', trading_sym)
                    while ret is None:
                        time.sleep(api_access_interval)
                        ret = fcoin.get_market_depth('L20', trading_sym)

                    lowest_ask = ret['data']['asks'][0]
                    # highest_bid = ret['data']['bids'][0]

                    if usdt_balance < lowest_ask * order_amount:
                        order_amount = 0.99 * usdt_balance / lowest_ask
                        order_amount = (("{0:.%df}" % amount_precision).format(order_amount))
                        order_amount = float(order_amount)
                    if order_amount > 5:
                        time.sleep(api_access_interval)
                        status = fcoin.buy(trading_sym, str(lowest_ask), order_amount)
                        print(str(status) + str(line_no()))
                        while status is None or status['status'] != 0:
                            time.sleep(api_access_interval)
                            status = fcoin.buy(trading_sym, str(lowest_ask), order_amount)
                            print(str(status) + str(line_no()))
                            if status['status'] == 1002:
                                time.sleep(api_access_interval)
                        cumulative_exchange += lowest_ask * order_amount
                        trade_dict['buy'] = (lowest_ask, order_amount)

                elif order_side == 'sell':
                    cancelled_order_price, cancelled_order_amount = trade_dict['sell']
                    cumulative_exchange -= cancelled_order_price * cancelled_order_amount

                    time.sleep(api_access_interval)
                    ret = fcoin.get_market_depth('L20', trading_sym)
                    while ret is None:
                        time.sleep(api_access_interval)
                        ret = fcoin.get_market_depth('L20', trading_sym)

                    # lowest_ask = ret['data']['asks'][0]
                    highest_bid = ret['data']['bids'][0]

                    time.sleep(api_access_interval)
                    status = fcoin.sell(trading_sym, str(highest_bid), order_amount)
                    print(str(status) + str(line_no()))
                    while status is None or status['status'] != 0:
                        time.sleep(api_access_interval)
                        status = fcoin.sell(trading_sym, str(highest_bid), order_amount)
                        print(str(status) + ' ' + str(line_no()))
                    cumulative_exchange += highest_bid * order_amount
                    trade_dict['buy'] = (highest_bid, order_amount)
                time.sleep(api_access_interval)
                wait_ctr = 0

        prev_trading_amount = trading_amount
        trade_ctr += 1
        print("trade times: %d" % trade_ctr)

        if trade_ctr % 30 == 0 and not ignore_loss:
            print(' $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ ')
            max_order_limit = 100
            time.sleep(api_access_interval)
            filled_orders = fcoin_get_order('ftusdt', 'filled', max_order_limit)
            while filled_orders is None:
                time.sleep(api_access_interval)
                filled_orders = fcoin_get_order('ftusdt', 'filled', max_order_limit)

            time.sleep(api_access_interval)
            orders_partially_canceled = fcoin_get_order('ftusdt', 'partial_canceled', max_order_limit)
            while orders_partially_canceled is None:
                time.sleep(api_access_interval)
                orders_partially_canceled = fcoin_get_order('ftusdt', 'partial_canceled', max_order_limit)

            time.sleep(api_access_interval)
            orders_partially_filled = fcoin_get_order('ftusdt', 'partial_filled', max_order_limit)
            while orders_partially_filled is None:
                time.sleep(api_access_interval)
                orders_partially_filled = fcoin_get_order('ftusdt', 'partial_filled', max_order_limit)

            finished_orders = filled_orders['data'] + orders_partially_canceled['data'] + orders_partially_filled[
                'data']

            trading_loss = 0
            for order_data in finished_orders:
                ts_ = order_data['created_at']
                if ts_ > last_check_ts and order['id'] not in orders:
                    side_ = order_data['side']
                    executed_value = order_data['executed_value']
                    price_ = order_data['price']
                    if side_ == 'buy':
                        trading_loss += float(executed_value) * float(price_)
                    else:
                        trading_loss -= float(executed_value) * float(price_)
                    orders.append(order['id'])
            print("trading loss: %f" % trading_loss)
            last_check_ts = time.time()
            last_check_ts *= 1000
            print(' $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$ ')

            # if len(trade_dict) > 0:
            #     buy_price, buy_amount = trade_dict['buy']
            #     sell_price, sell_amount = trade_dict['sell']
            #     diff_amount = buy_amount if buy_amount < sell_amount else sell_amount
            #     trading_loss += (buy_price - sell_price) * diff_amount
            #
            #     print("trading loss: %f" % trading_loss)

        print("-------- end --------")

    target_cur_balance, base_cur_balance = get_balance()
    print("final balance %s: %f" % (target_currency, target_cur_balance))
    print("final balance %s: %f" % (base_currency, base_cur_balance))

    return


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", default='check', help="model type: check; mine; test.")
    parser.add_argument("--cur", default='ft_usdt', help="currency type: ft_usdt, etc_usdt, omg_eth ...")
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
        'omg_eth': (6, 4),
        'ft_eth': (8, 2)
    }

    MODE = args.mode
    sym_pair = args.cur
    DEBUG = args.debug
    ignore_loss_ = args.ignore
    target_currency, base_currency = sym_pair.split('_')

    if MODE == 'check':
        check()
    elif MODE == 'mine':
        price_precision, amount_precision = precision_dict[sym_pair]
        mining(debug=DEBUG, ignore_loss=ignore_loss_)
    elif MODE == 'test':
        trade_ctr_est = 3000
        ori_ts = 1529338603 * 1000
        time.sleep(api_access_interval)
        orders_filled = fcoin_get_order('ftusdt', 'filled', trade_ctr_est * 2)
        while orders_filled is None:
            time.sleep(api_access_interval)
            orders_filled = fcoin_get_order('ftusdt', 'filled', trade_ctr_est * 2)

        time.sleep(api_access_interval)
        orders_partial_canceled = fcoin_get_order('ftusdt', 'partial_canceled', trade_ctr_est * 2)
        while orders_partial_canceled is None:
            time.sleep(api_access_interval)
            orders_partial_canceled = fcoin_get_order('ftusdt', 'partial_canceled', trade_ctr_est * 2)

        time.sleep(api_access_interval)
        orders_partial_filled = fcoin_get_order('ftusdt', 'partial_filled', trade_ctr_est * 2)
        while orders_partial_filled is None:
            time.sleep(api_access_interval)
            orders_partial_filled = fcoin_get_order('ftusdt', 'partial_filled', trade_ctr_est * 2)

        print("get %d filled orders, %d partial_canceled orders, %d partial_filled orders" %
              (len(orders_filled['data']), len(orders_partial_canceled['data']), len(orders_partial_filled['data'])))
        orders_finished = orders_filled['data'] + orders_partial_canceled['data'] + orders_partial_filled['data']
        trading_fee = 0
        for order in orders_finished:
            ts = order['created_at']
            if ts > ori_ts:
                side = order['side']
                executed_val = order['executed_value']
                price = order['price']
                trading_fee += float(executed_val) * float(price) * 0.001

        print("trading fee: %f" % trading_fee)
