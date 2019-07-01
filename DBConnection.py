#!/usr/bin/python3
import pymysql as sql
import datetime as dt
import matplotlib as mpl
import pandas as pd

selected_currency = None

onlinehost = '160.153.142.193'
onlineuser = 'Forex_DB_TFG'
onlinepassword = 'UVx.P2Ps6V@L+.JL'
onlinedb = 'Forex_DB_TFG'
onlineport = 3306

balance = 0.0
opened_orders = 0
closed_orders = 0
take_profit_orders = 0
stop_loss_orders = 0
current_month = 1
current_year = 2001

db = sql.connect(host=onlinehost, user=onlineuser, password=onlinepassword, db=onlinedb, autocommit=True,
                 charset='utf8', port=onlineport)

end_year = 2019
start_year = 2001

mpl.rcParams.update({'figure.max_open_warning': 0})


def execute_sentence(sentence, cursor):
    """
    By calling this method, and using the PyMySQL library, you can execute a sentence in the connected database.
    :param sentence: the sentence you want to execute
    :return: the results of the sentence
    """

    try:
        if cursor.connection:
            cursor.execute(sentence)
            return cursor.fetchall()

        else:
            print("impossible to connect to the database")

    except Exception as e:
        return str(e)


def datetime_to_float(date, time):
    """
    Auxiliar method used to convert a date and a time into a floating time value (time value that isn't tied to a specific time zone)
    :param date: date of a row of the dataset. time: time of a row of the dataset
    :return: the datetime in floating format
    """

    year, month, day = date.split("-")
    hour, minute, second = time.split(":")
    date = dt.datetime(int(year), int(month), int(day), int(hour), int(minute), int(second))
    return date.timestamp()


def float_to_datetime(float):
    """
    Auxiliar method used to convert a floating datetime into a python datetime value
    :param float: floating datetime value
    :return: python datetime value
    """

    return str(dt.datetime.fromtimestamp(float))


def get_dataset(currency, start_y, end_y):
    global db
    global selected_currency
    global end_year
    global start_year
    global current_year

    reset_global_variables()

    selected_currency = currency
    assert selected_currency not in 'none', "{}, Not a valid currency selected".format(selected_currency)

    print("Select the dataset start year (min. 2001)")
    start_year = start_y
    assert (start_year >= 2001 and start_year <= 2019), "{}, Not a valid start year selected".format(start_year)
    current_year = start_year
    start_date = '{}-01-01'.format(start_year)

    print("Select the dataset end year (max. 2019)")
    end_year = end_y
    assert (end_year >= 2001 and start_year <= 2019), "{}, Not a valid start year selected".format(start_year)

    if end_year != 2019:
        end_date = '{}-12-31'.format(end_year)

    else:
        end_date = '{}-03-31'.format(end_year)

    get_dataset_sentence = "SELECT * FROM {} WHERE DATE_T BETWEEN \'{}\' AND \'{}\'".format(selected_currency,
                                                                                            start_date, end_date)

    dataset = execute_sentence(get_dataset_sentence, db.cursor())
    db.cursor().close()

    return dataset


def create_database_buy_order(order):
    global db
    global current_month
    global opened_orders
    global selected_currency

    order_date = float_to_datetime(order.time)
    order_date = order_date.split("-")

    if (int(order_date[1]) != current_month):
        update_stats()

    opened_orders += 1

    insert_sentence = "INSERT INTO {}_ORDERS (ORDER_ID, OPEN_PRICE, VOLUME, OPEN_DATE_TIME, AGENT_MODE, THRESHOLD_UP, THRESHOLD_DOWN, OPEN_EVENT, TAKE_PROFIT, STOP_LOSS, LIQUIDITY, INVENTORY, CLOSED) " \
                      "VALUES (\'{}\', {}, {}, \'{}\', \'{}\', {}, {}, \'{}\', {}, {}, {}, {}, 0);".format(
        selected_currency,
        order.order_id, order.open_price,
        order.volume,
        float_to_datetime(order.time),
        order.agent_mode,
        order.threshold_up,
        order.threshold_down,
        order.event_of_creation,
        order.take_profit,
        order.stop_loss,
        order.liquidity,
        order.inventory)

    execute_sentence(insert_sentence, db.cursor())
    print("DATABASE: Just created the database buy order with the following id: {}".format(order.order_id))

    update_the_balance_buy(order.open_price, float_to_datetime(order.time))


def create_database_sell_order(id, sell_price, close_time, close_event_name, close_option):
    global db
    global closed_orders
    global take_profit_orders
    global stop_loss_orders
    global selected_currency

    order_date = float_to_datetime(close_time)
    order_date = order_date.split("-")

    if (int(order_date[1]) != current_month):

        update_stats()

    closed_orders += 1

    if (close_option == 'StopLoss'):
        stop_loss_orders += 1

    elif (close_option == 'TakeProfit'):
        take_profit_orders += 1

    select_sentence = "SELECT * FROM {}_ORDERS WHERE ORDER_ID = \'{}\';".format(selected_currency, id)
    delete_sentence = "DELETE FROM {}_ORDERS WHERE ORDER_ID = \'{}\';".format(selected_currency, id)

    original_order = execute_sentence(select_sentence, db.cursor())
    execute_sentence(delete_sentence, db.cursor())

    for row in original_order:
        insert_sentence = "INSERT INTO {}_CLOSED_ORDERS (ORIGINAL_ID, OPEN_PRICE, CLOSE_PRICE, VOLUME, OPEN_DATE_TIME, CLOSE_DATE_TIME, AGENT_MODE, THRESHOLD_UP, THRESHOLD_DOWN, OPEN_EVENT, CLOSE_EVENT, TAKE_PROFIT, STOP_LOSS, LIQUIDITY, INVENTORY, CLOSE_OPTION) " \
                          "VALUES (\'{}\', {}, {}, {}, \'{}\', \'{}\', \'{}\', {}, {}, \'{}\', \'{}\', {}, {}, {}, {}, \'{}\');".format(
            selected_currency, row[0], row[1], sell_price, row[2], row[3], float_to_datetime(close_time), row[4],
            row[5], row[6], row[7], close_event_name, row[8], row[9], row[10], row[11], close_option)
        execute_sentence(insert_sentence, db.cursor())

    select_order_inserted = "SELECT * FROM {}_CLOSED_ORDERS WHERE ORIGINAL_ID = \'{}\';".format(selected_currency, id)

    sell_order = execute_sentence(select_order_inserted, db.cursor())

    update_the_balance_sell(sell_order, sell_price)


def update_stats():

    global selected_currency, opened_orders, closed_orders, take_profit_orders, stop_loss_orders, current_month, current_year


    if opened_orders != 0:
        if closed_orders != 0:
            if current_month >= 1 and current_month <= 9:
                insert_sentence = """
                                    INSERT INTO {}_MONTHLY_STATS (MONTH_YEAR, OPENED_ORDERS, CLOSED_ORDERS, TAKE_PROFIT_ORDERS, STOP_LOSS_ORDERS, CLOSED_ORDERS_PERCENTAGE, TAKE_PROFIT_PERCENTAGE, STOP_LOSS_PERCENTAGE)
                                    VALUES(\'0{}-{}\', {}, {}, {}, {}, {}, {}, {})
                                    """.format(selected_currency, current_month, current_year, opened_orders, closed_orders, take_profit_orders, stop_loss_orders, closed_orders / opened_orders * 100, take_profit_orders/closed_orders * 100, stop_loss_orders / closed_orders * 100)

            elif current_month >=10 and current_month<= 12:
                insert_sentence = """
                                    INSERT INTO {}_MONTHLY_STATS (MONTH_YEAR, OPENED_ORDERS, CLOSED_ORDERS, TAKE_PROFIT_ORDERS, STOP_LOSS_ORDERS, CLOSED_ORDERS_PERCENTAGE, TAKE_PROFIT_PERCENTAGE, STOP_LOSS_PERCENTAGE)
                                    VALUES(\'{}-{}\', {}, {}, {}, {}, {}, {}, {})
                                    """.format(selected_currency, current_month, current_year, opened_orders, closed_orders, take_profit_orders, stop_loss_orders, closed_orders / opened_orders * 100, take_profit_orders/closed_orders * 100, stop_loss_orders / closed_orders * 100)
            execute_sentence(insert_sentence, db.cursor())

        elif closed_orders == 0:
            if current_month >= 1 and current_month <= 9:
                insert_sentence = """
                                    INSERT INTO {}_MONTHLY_STATS (MONTH_YEAR, OPENED_ORDERS, CLOSED_ORDERS, TAKE_PROFIT_ORDERS, STOP_LOSS_ORDERS, CLOSED_ORDERS_PERCENTAGE, TAKE_PROFIT_PERCENTAGE, STOP_LOSS_PERCENTAGE)
                                    VALUES(\'0{}-{}\', {}, 0, 0, 0, 0, 0, 0)
                                    """.format(selected_currency, current_month, current_year, opened_orders)

            elif current_month >= 10 and current_month <= 12:
                insert_sentence = """
                                    INSERT INTO {}_MONTHLY_STATS (MONTH_YEAR, OPENED_ORDERS, CLOSED_ORDERS, TAKE_PROFIT_ORDERS, STOP_LOSS_ORDERS, CLOSED_ORDERS_PERCENTAGE, TAKE_PROFIT_PERCENTAGE, STOP_LOSS_PERCENTAGE)
                                    VALUES(\'{}-{}\', {}, 0, 0, 0, 0, 0, 0)
                                    """.format(selected_currency, current_month, current_year, opened_orders)
            execute_sentence(insert_sentence, db.cursor())

    opened_orders = 0
    closed_orders = 0
    take_profit_orders = 0
    stop_loss_orders = 0

    if current_month == 12:
        current_month = 1
        current_year += 1
    else:
        current_month += 1


def update_the_balance_buy(current_price, date):
    global db, balance

    select_all = "SELECT * FROM {}_ORDERS;".format(selected_currency)

    opened_orders = execute_sentence(select_all, db.cursor())

    current = 0.0

    for row in opened_orders:
        if row[4] == 'long':
            current += (current_price * row[2] - row[1] * row[2])

        elif row[4] == 'short':
            current += (row[1] * row[2] - current_price * row[2])

    insert_balance(balance + current, date)


def update_the_balance_sell(sell_order, current_price):
    global db, balance

    select_all = "SELECT * FROM {}_ORDERS;".format(selected_currency)

    opened_orders = execute_sentence(select_all, db.cursor())

    current = 0.0

    for row in sell_order:
        if row[7] == 'long':
            close_time = row[6]
            balance += row[4] * (row[3] - row[2])

        elif row[7] == 'short':
            close_time = row[6]
            balance += row[4] * (row[2] - row[3])

    for row in opened_orders:
        if row[4] == 'long':
            current += row[2] * (current_price - row[1])

        elif row[4] == 'short':
            current += row[2] * (row[1] - current_price)

    insert_balance(balance + current, close_time)


def insert_balance(price, date):
    global db, selected_currency

    price = round(price, 3)
    insert_sentence = "INSERT INTO {}_BALANCE (BALANCE, DATE) VALUES({}, \'{}\');".format(selected_currency, price,
                                                                                          date)

    execute_sentence(insert_sentence, db.cursor())


def get_liquid_value():
    global db
    global end_year
    global start_year

    mpl.style.use('classic')

    select_sentence = "SELECT DATE, BALANCE FROM {}_BALANCE;".format(selected_currency)

    data = pd.read_sql(select_sentence, db, parse_dates=['DATE'])

    window = int(round(data['DATE'].count() / ((end_year + 1 - start_year) * 20)))

    if window ==0:
        window = 1

    data['BALANCE'] = data.BALANCE.rolling(window=window).mean()

    return data


def get_total_stats():
    global db
    global selected_currency

    update_stats()

    select_sentence = """
                        SELECT SUM(OPENED_ORDERS), SUM(CLOSED_ORDERS), SUM(TAKE_PROFIT_ORDERS), SUM(STOP_LOSS_ORDERS)
                         FROM {}_MONTHLY_STATS WHERE OPENED_ORDERS IS NOT NULL;
                        """.format(selected_currency)
    total = execute_sentence(select_sentence, db.cursor())

    for row in total:
        opened = row[0]
        closed = row[1]
        take_profites = row[2]
        stop_losses = row[3]

    closed_percentage = closed / opened * 100

    if(closed != 0):
        tp_percentage = take_profites / closed * 100
        sl_percentage = stop_losses / closed * 100

    else:
        tp_percentage = 0.0
        sl_percentage = 0.0


    insert_sentence = "INSERT INTO {}_MONTHLY_STATS (MONTH_YEAR, OPENED_ORDERS, CLOSED_ORDERS, TAKE_PROFIT_ORDERS," \
                  " STOP_LOSS_ORDERS, CLOSED_ORDERS_PERCENTAGE, TAKE_PROFIT_PERCENTAGE, STOP_LOSS_PERCENTAGE) " \
                  "VALUES (\'EXECUTION\', \'{}\', \'{}\', \'{}\', \'{}\', {}, {}, {});".format(selected_currency,
                                                                                               str(opened), str(closed),
                                                                              str(take_profites), str(stop_losses),
                                                                              closed_percentage, tp_percentage,
                                                                              sl_percentage)

    execute_sentence(insert_sentence, db.cursor())


def print_stats():
    global db

    select_sentence = "SELECT * FROM {}_MONTHLY_STATS WHERE CLOSED_ORDERS_PERCENTAGE IS NOT NULL " \
                      "AND {}_MONTHLY_STATS.MONTH_YEAR = \'EXECUTION\';".format(selected_currency, selected_currency)

    data = pd.read_sql(select_sentence, db)

    return data


def reset_database():
    global db

    delete_sentence = "DELETE FROM {}_ALL_ORDERS;".format(selected_currency)
    execute_sentence(delete_sentence, db.cursor())

    delete_sentence2 = "DELETE FROM {}_ORDERS;".format(selected_currency)
    execute_sentence(delete_sentence2, db.cursor())

    delete_sentence3 = "DELETE FROM {}_CLOSED_ORDERS;".format(selected_currency)
    execute_sentence(delete_sentence3, db.cursor())

    delete_sentence4 = "DELETE FROM {}_BALANCE;".format(selected_currency)
    execute_sentence(delete_sentence4, db.cursor())

    delete_sentence5 = "DELETE FROM {}_MONTHLY_STATS;".format(selected_currency)
    execute_sentence(delete_sentence5, db.cursor())


def reset_global_variables():
    global balance, opened_orders, closed_orders, take_profit_orders, stop_loss_orders, current_month

    balance = 0.0
    opened_orders = 0
    closed_orders = 0
    take_profit_orders = 0
    stop_loss_orders = 0
    current_month = 1
