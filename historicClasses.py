import random
import string
import math
from math import exp
from math import log
from math import pow
from math import sqrt

from scipy.stats import norm

import DBConnection as dbc


class Agent:
    """
    Trader, manages positions
    """

    def __init__(self, original_threshold=0.01, agent_mode='long'):

        self.original_threshold = original_threshold

        self.agent_mode = agent_mode

        self.opened_orders_long = []
        self.opened_orders_short = []

        # unit size is the percentage of the cash that will be bid in each position
        self.unit_size = 10

        self.inventory = 0

        self.liquidity_indicator = LiquidityIndicator(self.original_threshold)

        self.events_recorder = EventsRecorder(original_threshold, 'up')

    def trade(self, price):
        """
        this method opens new positions or closes already opened positions depending on intrinsics events
        directionalChangeToDown: directional change to down mode
        directionalChangeToDown: directional change to down mode
        downOvershoot: overshoot given a downwards direction
        upOvershoot: overshoot given a upwards direction
        :param price:
        :return:
        """

        self.liquidity_indicator.run(price)

        event = self.events_recorder.record_event(price)

        assert event in ('NOevent', 'upOvershoot', 'downOvershoot', 'directionalChangeToUp',
                         'directionalChangeToDown'), "{} this is not a valid event".format(event)
        assert self.agent_mode in ('long', 'short'), "{} not a valid long_short value".format(self.agent_mode)

        if event != 'NOevent':

            if self.agent_mode == 'long':

                if event == 'downOvershoot' or event == 'directionalChangeToUp':
                    self.open_new_order(price, event)

                elif event == 'upOvershoot':
                    self.sell_opened_positions(price, event)

            else:
                if event == 'upOvershoot' or event == 'directionalChangeToDown':
                    self.open_new_order(price, event)
                elif event == 'downOvershoot':
                    self.sell_opened_positions(price, event)

        return 0

    def open_new_order(self, price, event):
        if self.agent_mode == 'long':
            size_adjustment = self.liquidity_indicator.adjust_sizing()

            if event is 'downOvershoot':
                take_profit = self.compute_take_profit(price.ask, self.events_recorder.threshold_down, 'long')
                stop_loss = self.compute_stop_loss(price.ask, self.events_recorder.threshold_down, 'long')
                new_order = Order(price.ask, self.unit_size * size_adjustment, price.time, self.agent_mode,
                                  self.events_recorder.threshold_up, self.events_recorder.threshold_down, event,
                                  take_profit, stop_loss, self.liquidity_indicator.liquidity, self.inventory)
            elif event is 'directionalChangeToUp':
                take_profit = self.compute_take_profit(price.ask, self.events_recorder.threshold_up, 'long')
                stop_loss = self.compute_stop_loss(price.ask, self.events_recorder.threshold_up, 'long')
                new_order = Order(price.ask, self.unit_size * size_adjustment, price.time, self.agent_mode,
                                  self.events_recorder.threshold_up, self.events_recorder.threshold_down, event,
                                  take_profit, stop_loss, self.liquidity_indicator.liquidity, self.inventory)

            self.opened_orders_long.append(new_order)
            self.inventory += self.unit_size * size_adjustment
            self.events_recorder.adjust_thresholds(self.inventory)
            self.liquidity_indicator.adjust_thresholds(self.inventory)
            dbc.create_database_buy_order(new_order)

        else:
            size_adjustment = self.liquidity_indicator.adjust_sizing()

            if event is 'upOvershoot':
                take_profit = self.compute_take_profit(price.ask, self.events_recorder.threshold_up, 'short')
                stop_loss = self.compute_stop_loss(price.ask, self.events_recorder.threshold_up, 'short')
                new_order = Order(price.ask, self.unit_size * size_adjustment, price.time, self.agent_mode,
                                  self.events_recorder.threshold_up, self.events_recorder.threshold_down, event,
                                  take_profit, stop_loss, self.liquidity_indicator.liquidity, self.inventory)
            elif event is 'directionalChangeToDown':
                take_profit = self.compute_take_profit(price.ask, self.events_recorder.threshold_down, 'short')
                stop_loss = self.compute_stop_loss(price.ask, self.events_recorder.threshold_down, 'short')
                new_order = Order(price.ask, self.unit_size * size_adjustment, price.time, self.agent_mode,
                                  self.events_recorder.threshold_up, self.events_recorder.threshold_down, event,
                                  take_profit, stop_loss, self.liquidity_indicator.liquidity, self.inventory)
            self.opened_orders_short.append(new_order)
            self.inventory -= self.unit_size * size_adjustment
            self.events_recorder.adjust_thresholds(self.inventory)
            self.liquidity_indicator.adjust_thresholds(self.inventory)
            dbc.create_database_buy_order(new_order)

    def sell_opened_positions(self, price, event):
        if self.agent_mode == 'long':
            for order in self.opened_orders_long:
                if price.bid >= order.take_profit:
                    self.opened_orders_long.remove(order)
                    self.inventory -= order.volume
                    self.events_recorder.adjust_thresholds(self.inventory)
                    self.liquidity_indicator.adjust_thresholds(self.inventory)
                    dbc.create_database_sell_order(order.order_id, price.bid, price.time, event, 'TakeProfit')

                elif price.bid <= order.stop_loss:
                    self.opened_orders_long.remove(order)
                    self.inventory -= order.volume
                    self.events_recorder.adjust_thresholds(self.inventory)
                    self.liquidity_indicator.adjust_thresholds(self.inventory)
                    dbc.create_database_sell_order(order.order_id, price.bid, price.time, event, 'StopLoss')
        else:
            for order in self.opened_orders_short:
                if price.ask <= order.take_profit:
                    self.opened_orders_short.remove(order)
                    self.inventory += order.volume
                    self.events_recorder.adjust_thresholds(self.inventory)
                    self.liquidity_indicator.adjust_thresholds(self.inventory)
                    dbc.create_database_sell_order(order.order_id, price.ask, price.time, event, 'TakeProfit')

                elif price.ask >= order.stop_loss:
                    self.opened_orders_short.remove(order)
                    self.inventory += order.volume
                    self.events_recorder.adjust_thresholds(self.inventory)
                    self.liquidity_indicator.adjust_thresholds(self.inventory)
                    dbc.create_database_sell_order(order.order_id, price.ask, price.time, event, 'StopLoss')

    def compute_take_profit(self, price, threshold, mode):
            if mode is 'long':
                return exp(log(price) + threshold)
            elif mode is 'short':
                return exp(log(price) - threshold)

    def compute_stop_loss(self, price, threshold, mode):
        if mode is 'long':
            return price * (1 - (0.15 - (0.1 - (self.liquidity_indicator.liquidity * threshold * 10))))
        elif mode is 'short':
            return price * (1 + (0.15 - (0.1 - (self.liquidity_indicator.liquidity * threshold * 10))))


class EventsRecorder:
    """
    Records events (overshoots and directional changes)
    """

    def __init__(self, original_threshold, market_mode='up'):

        self.original_threshold = original_threshold
        self.threshold_up = original_threshold
        self.threshold_down = original_threshold

        self.market_mode = market_mode
        self.reference = None
        self.extreme = None
        self.expected_overshoot_price = None
        self.expected_directional_change_price = None
        self.initialized = False

    def record_event(self, price):
        """
        Records an event given a price
        :param price
        :return: NOevent, directionalChangeToDown, directionalChangeToDown, downOvershoot, upOvershoot
        """

        assert self.market_mode in ('up', 'down'), '{} is not a valid market mode'.format(self.market_mode)
        if not self.initialized:
            self.initialized = True
            self.reference = self.extreme = price.get_mid()
            self.compute_expected_directional_change()
            self.compute_expected_overshoot()
            return 'NOevent'

        if self.market_mode == 'up':

            if price.get_bid() > self.extreme:
                self.extreme = price.get_bid()
                self.compute_expected_directional_change()
                if price.get_bid() > self.expected_overshoot_price:
                    self.reference = self.extreme
                    self.compute_expected_overshoot()
                    return 'upOvershoot'

            elif price.get_ask() <= self.expected_directional_change_price:
                self.reference = self.extreme = price.get_ask()
                self.market_mode = 'down'
                self.compute_expected_directional_change()
                self.compute_expected_overshoot()
                return 'directionalChangeToDown'

        else:
            if price.get_ask() < self.extreme:
                self.extreme = price.get_ask()
                self.compute_expected_directional_change()

                if price.get_ask() < self.expected_overshoot_price:
                    self.reference = self.extreme
                    self.compute_expected_overshoot()
                    return 'downOvershoot'

            elif price.get_bid() >= self.expected_directional_change_price:
                self.reference = self.extreme = price.get_bid()
                self.market_mode = 'up'
                self.compute_expected_directional_change()
                self.compute_expected_overshoot()
                return 'directionalChangeToUp'

        return 'NOevent'

    def compute_expected_overshoot(self):
        assert self.market_mode in ('up', 'down'), '{} not a valid market mode in method get_expected_OS'.format(self.market_mode)
        if self.market_mode == 'up':
            self.expected_overshoot_price = exp(log(self.reference) + self.threshold_up)
        else:
            self.expected_overshoot_price = exp(log(self.reference) - self.threshold_down)

    def compute_expected_directional_change(self):
        assert self.market_mode in ('up', 'down'), '{} not a valid market mode in method get_expected_DC'.format(self.market_mode)
        if self.market_mode == 'up':
            self.expected_directional_change_price = exp(log(self.reference) - self.threshold_down)
        else:
            self.expected_directional_change_price = exp(log(self.reference) + self.threshold_up)

    def adjust_thresholds(self, inventory):

        #LONG
        if inventory >= 150 and inventory < 300:
            self.threshold_up = self.original_threshold * 0.75
            self.threshold_down = self.original_threshold * 1.5
        elif inventory >= 300:
            self.threshold_up = self.original_threshold * 0.5
            self.threshold_down = self.original_threshold * 2

        #SHORT
        elif inventory > -300 and inventory <= -150:
            self.threshold_up = self.original_threshold * 1.5
            self.threshold_down = self.original_threshold * 0.75
        elif inventory <= -300:
            self.threshold_up = self.original_threshold * 2
            self.threshold_down = self.original_threshold * 0.5

        else:
            self.threshold_up = self.original_threshold
            self.threshold_down = self.original_threshold


class Price:
    """
    This class represents the price object, which will be passed to the agent with every new
    tick of the market.
    """

    def __init__(self, id, ask, bid, time):
        self.id = id
        self.ask = ask
        self.bid = bid
        self.time = time

    def clone(self):
        return Price(self.id, self.ask, self.bid, self.time)

    def get_id(self):
        return self.id

    def get_ask(self):
        return self.ask

    def get_bid(self):
        return self.bid

    def get_spread(self):
        return self.ask - self.bid

    def get_mid(self):
        return (self.ask + self.bid) / 2

    def get_time(self):
        return self.time


class LiquidityIndicator:

    def __init__(self, original_threshold):
        self.liquidity = 0.0
        self.original_threshold = original_threshold
        self.threshold_up = original_threshold
        self.threshold_down = original_threshold
        self.K = 50.0
        self.alpha_weight = math.exp(-2.0/(self.K + 1.0))
        self.H1 = self.compute_h1()
        self.H2 = self.compute_h2()
        self.surprise = 0.0
        self.initialized = False
        self.extreme = None
        self.reference = None
        self.mode = 'up'

    def compute_h1(self):

        return -exp(-self.original_threshold * 2.52579 / self.original_threshold) * log(exp(-self.original_threshold * 2.52579 / self.original_threshold)) - (1.0 - exp(-self.original_threshold * 2.52579 / self.original_threshold)) * log(1 - exp(-self.original_threshold * 2.52579 / self.original_threshold))

    def compute_h2(self):

        return exp(-self.original_threshold * 2.52579 / self.original_threshold) * pow(log(exp(-self.original_threshold * 2.52579 / self.original_threshold)), 2) - (1.0 - exp(-self.original_threshold * 2.52579 / self.original_threshold)) * pow(log(1 - exp(-self.original_threshold * 2.52579 / self.original_threshold)),2) - self.H1 * self.H1

    def adjust_sizing(self):

        assert 0 <= self.liquidity <= 1, "{} not a valid value".format(self.liquidity)

        if 0.1 < self.liquidity < 0.5:
            return 0.5
        elif self.liquidity <= 0.1:
            return 0.1
        else:
            return 1

    def compute_surprise(self, event):
        if event == 'directionalChange':
            return self.alpha_weight * 0.08338161 + (1.0 - self.alpha_weight) * self.surprise
        elif event == 'overshoot':
            return self.alpha_weight * 2.52579 + (1.0 - self.alpha_weight) * self.surprise

    def compute_liquidity(self, event):

        if event != 'NOevent':

            self.surprise = self.compute_surprise(event)

            self.liquidity = 1.0 - norm.cdf(sqrt(self.K) * (self.surprise - self.H1) / sqrt(self.H2))


    def run(self, price):

        if not self.initialized:
            self.extreme = self.reference = price.get_mid()
            self.initialized = True
            self.compute_liquidity('NOevent')

        if self.mode is 'down':
            if math.log(price.get_bid() / self.extreme) >= self.threshold_up:
                self.mode = 'up'
                self.extreme = price.get_bid()
                self.reference = price.get_bid()
                self.compute_liquidity('directionalChange')

            if price.get_ask() < self.extreme:
                self.extreme = price.get_ask()

            if math.log(self.reference/self.extreme) >= self.threshold_down * 2.52579:
                self.reference = self.extreme
                self.compute_liquidity('overshoot')

        elif self.mode is 'up':
            if math.log(price.get_ask()/self.extreme) <= -self.threshold_down:
                self.mode = 'down'
                self.extreme = price.get_ask()
                self.reference = price.get_ask()
                self.compute_liquidity('directionalChange')

            if price.get_bid() > self.extreme:
                self.extreme = price.get_bid()

            if math.log(self.reference / self.extreme) <= -self.threshold_up * 2.52579:
                self.reference = self.extreme
                self.compute_liquidity('overshoot')


    def adjust_thresholds(self, inventory):
        #LONG
        if inventory >= 150 and inventory < 300:
            self.threshold_up = self.original_threshold * 0.75
            self.threshold_down = self.original_threshold * 1.5
        elif inventory >= 300:
            self.threshold_up = self.original_threshold * 0.5
            self.threshold_down = self.original_threshold * 2

        #SHORT
        elif inventory > -300 and inventory <= -150:
            self.threshold_up = self.original_threshold * 1.5
            self.threshold_down = self.original_threshold * 0.75
        elif inventory <= -300:
            self.threshold_up = self.original_threshold * 2
            self.threshold_down = self.original_threshold * 0.5

        else:
            self.threshold_up = self.original_threshold
            self.threshold_down = self.original_threshold


class Order:
    """
    This class represents a position
    Positions will be opened and closed by agents when operating
    """

    def __init__(self, open_price=0.0, volume=0, time=0.0, agent_mode='long', threshold_up=0.01, threshold_down=0.01, event_of_creation='UpOvershoot', take_profit=0.0, stop_loss=0.0, liquidity = 0.0, inventory = 0):
        self.order_id = ''.join([random.choice(string.ascii_letters + string.digits) for _ in range(25)])
        self.open_price = open_price
        self.volume = volume
        self.time = time
        self.agent_mode = agent_mode
        self.threshold_up = threshold_up
        self.threshold_down = threshold_down
        self.event_of_creation = event_of_creation
        self.take_profit = take_profit
        self.stop_loss = stop_loss
        self.liquidity = liquidity
        self.inventory = inventory

