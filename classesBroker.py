from math import exp
from math import log
from math import pow
from math import sqrt
import math


class Agent:
    """
    Trader, manages positions
    """

    def __init__(self, con, currency_pair='EUR/USD', original_threshold=0.01, agent_mode='long'):
        self.original_threshold = original_threshold
        self.agent_mode = agent_mode

        self.currency_pair = currency_pair

        # unit size is the percentage of the cash that will be bid in each position
        self.unit_size = 100

        self.inventory = 0

        self.liquidity_indicator = LiquidityIndicator(self.original_threshold)

        self.events_recorder = EventsRecorder(self.original_threshold)

        self.broker = con

    def trade(self, last_price):
        """
        this method opens new positions or closes already opened positions depending on intrinsics events
        directionalChangeToDown: directional change to down mode
        directionalChangeToDown: directional change to down mode
        downOvershoot: overshoot given a downwards direction
        upOvershoot: overshoot given a upwards direction
        :return:
        """

        print(f'connection status: {self.broker.is_connected()}')

        print(f'last price is : {last_price}')
        # call liquidity here
        self.liquidity_indicator.run(last_price)

        event = self.events_recorder.record_event(last_price)
        print(f'event: {event}')

        assert event in ('NOevent', 'upOvershoot', 'downOvershoot', 'directionalChangeToUp',
                         'directionalChangeToDown'), "{} this is not a valid event".format(event)
        assert self.agent_mode in ('long', 'short'), "{} not a valid long_short value".format(self.agent_mode)

        if event != 'NOevent':

            if self.agent_mode == 'long':

                if event == 'downOvershoot' or event == 'directionalChangeToUp':
                    self.open_new_order()
                elif event == 'upOvershoot':
                    self.sell_opened_positions(last_price)
                else:
                    pass

            else:
                if event == 'upOvershoot' or event == 'directionalChangeToDown':
                    self.open_new_order()
                elif event == 'downOvershoot':
                    self.sell_opened_positions(last_price)
                else:
                    pass

        return 0

    def open_new_order(self):

        if self.agent_mode == 'long':
            size = self.liquidity_indicator.adjust_sizing()
            self.broker.create_market_buy_order(self.currency_pair, self.unit_size * size)
            self.inventory += self.unit_size * size
        else:
            size = self.liquidity_indicator.adjust_sizing()
            self.broker.create_market_sell_order(self.currency_pair, self.unit_size * size)
            self.inventory -= self.unit_size * size

        self.events_recorder.adjust_thresholds(self.inventory)
        self.liquidity_indicator.adjust_thresholds(self.inventory)


    def sell_opened_positions(self, last_price):
        orders_list = self.broker.get_open_positions(kind='list')
        for order in orders_list:
            print(f'inside for loop in sell order with pl: {order["visiblePL"]}')
            if self.stop_loss(order, last_price) or self.profit(order):
                self.broker.close_trade(order['tradeId'], order['amountK'])
                self.adjust_inventory(order)

    def stop_loss(self, order, last_price):
        if order['isBuy']:
            stop = order['open'] * (1 - (0.15 - (0.1 - (self.liquidity_indicator.liquidity * self.events_recorder.threshold_up * 10))))
            return True if last_price['Ask'] < stop else False
        else:
            stop = order['open'] * (1 + (0.15 - (0.1 - (self.liquidity_indicator.liquidity * self.events_recorder.threshold_down * 10))))
            return True if last_price['Ask'] > stop else False

    def profit(self, order):
        return True if order['visiblePL'] > 0.5 else False

    def adjust_inventory(self, order):
        if order['isBuy']:
            self.inventory += order['amountK']
        else:
            self.inventory -= order['amountK']


class EventsRecorder:
    """
    Records events (overshoots and directional changes)
    """

    def __init__(self, original_threshold):
        self.original_threshold = original_threshold
        self.threshold_up = original_threshold
        self.threshold_down = original_threshold
        self.market_mode = 'up'
        self.reference = None
        self.extreme = None
        self.expected_overshoot_price = None
        self.expected_directional_change_price = None
        self.initialized = False

    def record_event(self, last_price):
        """
        Records an event given a price
        :param last_price
        :return: NOevent, directionalChangeToDown, directionalChangeToDown, downOvershoot, upOvershoot
        """

        assert self.market_mode in ('up', 'down'), '{} is not a valid market mode'.format(self.market_mode)
        if not self.initialized:
            self.initialized = True
            self.reference = self.extreme = (last_price.Bid + last_price.Ask) / 2
            self.compute_expected_directional_change()
            self.compute_expected_overshoot()
            return 'NOevent'

        if self.market_mode == 'up':

            if last_price.Bid > self.extreme:
                self.extreme = last_price.Bid
                self.compute_expected_directional_change()

                if last_price.Bid > self.expected_overshoot_price:
                    self.reference = self.extreme
                    self.compute_expected_overshoot()
                    return 'upOvershoot'

            elif last_price.Ask <= self.expected_directional_change_price:
                self.reference = self.extreme = last_price.Ask
                self.market_mode = 'down'
                self.compute_expected_directional_change()
                self.compute_expected_overshoot()
                return 'directionalChangeToDown'
        else:
            if last_price.Ask < self.extreme:
                self.extreme = last_price.Ask
                self.compute_expected_directional_change()

                if last_price.Ask < self.expected_overshoot_price:
                    self.reference = self.extreme
                    self.compute_expected_overshoot()
                    return 'downOvershoot'

            elif last_price.Bid >= self.expected_directional_change_price:
                self.reference = self.extreme = last_price.Bid
                self.market_mode = 'up'
                self.compute_expected_directional_change()
                self.compute_expected_overshoot()
                return 'directionalChangeToUp'

        return 'NOevent'

    def compute_expected_overshoot(self):
        assert self.market_mode in ('up', 'down'), f'{self.market_mode} not a valid market mode in method get_expected_OS'
        if self.market_mode == 'up':
            self.expected_overshoot_price = exp(log(self.reference) + self.threshold_up)
        else:
            self.expected_overshoot_price = exp(log(self.reference) - self.threshold_down)

    def compute_expected_directional_change(self):
        assert self.market_mode in ('up', 'down'), f'{self.market_mode} not a valid market mode in method get_expected_DC'
        if self.market_mode == 'up':
            self.expected_directional_change_price = exp(log(self.reference) - self.threshold_down)
        else:
            self.expected_directional_change_price = exp(log(self.reference) + self.threshold_up)

    def adjust_thresholds(self, inventory):
        if inventory >= 1500 and inventory < 3000:
            self.threshold_up = self.original_threshold * 0.75
            self.threshold_down = self.original_threshold * 1.5
        elif inventory >= 3000:
            self.threshold_up = self.original_threshold * 0.5
            self.threshold_down = self.original_threshold * 2

        elif inventory > -3000 and inventory <= -1500:
            self.threshold_up = self.original_threshold * 1.5
            self.threshold_down = self.original_threshold * 0.75
        elif inventory <= -3000:
            self.threshold_up = self.original_threshold * 2
            self.threshold_down = self.original_threshold * 0.5
        else:
            self.threshold_up = self.original_threshold
            self.threshold_down = self.original_threshold


class LiquidityIndicator:

    def __init__(self, original_threshold):
        self.original_threshold = original_threshold
        self.threshold_up = original_threshold
        self.threshold_down = original_threshold
        self.liquidity = 0.0
        self.K = 50.0
        self.alpha_weight = math.exp(-2.0 / (self.K + 1.0))
        self.H1 = self.compute_h1()
        self.H2 = self.compute_h2()
        self.surprise = 0.0
        self.initialized = False
        self.extreme = None
        self.reference = None
        self.mode = 'up'

    def compute_h1(self):
        return -exp(-self.original_threshold * 2.52579 / self.original_threshold) * log(
            exp(-self.original_threshold * 2.52579 / self.original_threshold)) - (
                       1.0 - exp(-self.original_threshold * 2.52579 / self.original_threshold)) * log(
            1 - exp(-self.original_threshold * 2.52579 / self.original_threshold))

    def compute_h2(self):

        return exp(-self.original_threshold * 2.52579 / self.original_threshold) * pow(
            log(exp(-self.original_threshold * 2.52579 / self.original_threshold)), 2.0) - (
                       1.0 - exp(-self.original_threshold * 2.52579 / self.original_threshold)) * pow(
            log(1.0 - exp(-self.original_threshold * 2.52579 / self.original_threshold)), 2.0) - self.H1 * self.H1

    def adjust_sizing(self):

        assert 0 <= self.liquidity <= 1, f'{self.liquidity} not a valid value'

        if 0.1 < self.liquidity < 0.5:
            return 0.5
        elif self.liquidity <= 0.1:
            return 0.1
        else:
            return 1

    def compute_surprise(self, event):
        if event == 'directionalChange':
            return self.alpha_weight * 0.08338161 + (1.0 - self.alpha_weight) * self.surprise
        else:
            return self.alpha_weight * 2.52579 + (1.0 - self.alpha_weight) * self.surprise

    def compute_liquidity(self, event):

        if event != 'NOevent':
            self.surprise = self.compute_surprise(event)

            self.liquidity = 1.0 - self.normal_distribution_cumulative(
                sqrt(self.K) * (self.surprise - self.H1) / sqrt(self.H2))

    def normal_distribution_cumulative(self, x):

        if x > 6.0:
            return 1.0
        if x < -6.0:
            return 0.0

        b1 = 0.31938153
        b2 = -0.356563782
        b3 = 1.781477937
        b4 = -1.821255978
        b5 = 1.330274429
        p = 0.2316419
        c2 = 0.3989423

        a = abs(x)
        t = 1.0 / (1.0 + a * p)
        b = c2 * exp((-x) * (x / 2.0))
        n = ((((b5 * t + b4) * t + b3) * t + b2) * t + b1) * t
        n = 1.0 - b * n

        if x < 0.0:
            n = 1.0 - n

        return n

    def run(self, last_price):

        if not self.initialized:
            self.extreme = self.reference = (last_price.Ask + last_price.Bid) / 2
            self.initialized = True
            self.compute_liquidity('NOevent')

        if self.mode is 'down':
            if math.log(last_price.Bid / self.extreme) >= self.threshold_up:
                self.mode = 'up'
                self.extreme = last_price.Bid
                self.reference = last_price.Bid
                self.compute_liquidity('directionalChange')

            if last_price.Ask < self.extreme:
                self.extreme = last_price.Ask

            if math.log(self.reference / self.extreme) >= self.threshold_down * 2.52579:
                self.reference = self.extreme
                self.compute_liquidity('overshoot')

        elif self.mode is 'up':
            if math.log(last_price.Ask / self.extreme) <= -self.threshold_down:
                self.mode = 'down'
                self.extreme = last_price.Ask
                self.reference = last_price.Ask
                self.compute_liquidity('directionalChange')

            if last_price.Bid > self.extreme:
                self.extreme = last_price.Bid

            if math.log(self.reference / self.extreme) <= -self.threshold_up * 2.52579:
                self.reference = self.extreme
                self.compute_liquidity('overshoot')

    def adjust_thresholds(self, inventory):

        if inventory >= 1500 and inventory < 3000:
            self.threshold_up = self.original_threshold * 0.75
            self.threshold_down = self.original_threshold * 1.5
        elif inventory >= 3000:
            self.threshold_up = self.original_threshold * 0.5
            self.threshold_down = self.original_threshold * 2

        elif inventory > -3000 and inventory <= -1500:
            self.threshold_up = self.original_threshold * 1.5
            self.threshold_down = self.original_threshold * 0.75
        elif inventory <= -3000:
            self.threshold_up = self.original_threshold * 2
            self.threshold_down = self.original_threshold * 0.5

        else:
            self.threshold_up = self.original_threshold
            self.threshold_down = self.original_threshold
