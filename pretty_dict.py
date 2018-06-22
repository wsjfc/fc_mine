import time

price_precision, amount_precision = (6, 2)

need_item = {'status': str,
             'data': lambda x: x,
             'msg': str,
             'side': str,
             'amount': lambda x: ('%%%df' % amount_precision) % float(x),
             'filled_amount': lambda x: ('%%%df' % amount_precision) % float(x),
             'state': str,
             'price': lambda x: ('%%%df' % price_precision) % float(x),
             'created_at': lambda x: '/'.join(time.ctime(x / 1000.0).split()[1:-1])
             }

green_start = '\033[1;32m'
red_start = '\033[1;31m'
blue_start = '\033[1;34m'
grey_start = '\033[0;37;40m'
color_end = '\033[0m'


def key_value(key, value):
    value_len = value.find('\n')
    value_len = value_len if value_len != -1 else len(value)
    max_len = max(len(key), value_len)
    return ('%%-%ds' % max_len) % key, ('%%-%ds' % max_len) % value


def pretty_str(obj, pre_blank=0):
    ret = ''
    keys = ''
    values = ' ' * pre_blank
    if isinstance(obj, (tuple, list)):
        sep = '\n' if obj and isinstance(obj[0], dict) else ''
        for i, ele in enumerate(obj):
            added = pretty_str(ele, pre_blank=pre_blank)
            if isinstance(ele, dict) and i > 0:
                added = ' ' * 7 + added
            ret += added + sep
            pre_blank = 7
        return ret[:-1]
    if isinstance(obj, dict):
        for item in need_item:
            if item in obj:
                key, value = key_value(item, pretty_str(need_item[item](obj[item]), pre_blank=pre_blank))
                keys += key + ' '
                values += value + ' '
                pre_blank += len(keys)
        if 'sell' in values:
            return grey_start + keys[:-1] + color_end + '\n' + red_start + values[:-1] + color_end
        if 'buy' in values:
            return grey_start + keys[:-1] + color_end + '\n' + green_start + values[:-1] + color_end
        return blue_start + keys[:-1] + color_end + '\n' + values[:-1]

    return str(obj)

if __name__ == "__main__":
    d = {'id': '2CmZjhaE46v0I85YOjwXzF6dVKqgQmdzzhA_55AWLmY=', 'side': 'buy', 'fill_fees': '0.000000000000000000',
    'source': 'api', 'amount': '294.760000000000000000', 'created_at': 1529361386780, 'symbol': 'ftusdt',
    'filled_amount': '0.000000000000000000', 'type': 'limit', 'executed_value': '0.000000000000000000',
    'state': 'partial_filled', 'price': '0.808367000000000000'}
    f = {'status': 0, 'data': [d, d]}
    g = {'status': 0, 'data': d}

    print(pretty_str(d))
    print('---')
    print(pretty_str(f))
    print('---')
    print(pretty_str(g))