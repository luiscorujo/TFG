import tkinter as tk
from tkinter import ttk
import classesBroker as alpha
import DBConnection as dbc
import time
import matplotlib
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import fxcmpy
import matplotlib.dates as mdates
from historicClasses import Agent
from historicClasses import Price
import threading
import os


matplotlib.use("TkAgg")

LARGE_FONT = ('Verdana', 20)

currency = '',
start_year = 0
end_year = 0
token = ''
threshold = 0.01
agents = []
historic_text = ''
historic_title = ''
cont = 0
data = None
live = True
con = None


def trade():
    global currency, agents, live

    initiate_traders()

    while live:
        time.sleep(3)

        try:
            last_price = con.get_last_price(currency)
            for agent in agents:
                agent.trade(last_price)
        except:
            time.sleep(10)
            con.close()
            initiate_traders()


def initiate_traders():
    global agents, con, currency

    con = fxcmpy.fxcmpy(access_token=token, log_level='error')
    con.subscribe_market_data(currency)
    agent_long = alpha.Agent(con, currency, 0.0001, agent_mode='long')
    agent_short = alpha.Agent(con, currency, 0.0001, agent_mode='short')

    agents = [agent_long, agent_short]


def run_historic():

    global currency, start_year, end_year, threshold, historic_text, historic_title, data

    dataset = dbc.get_dataset(currency, start_year, end_year)
    dbc.reset_database()
    time.sleep(1)

    agent_long = Agent(original_threshold=threshold, agent_mode='long')
    agent_short = Agent(original_threshold=threshold, agent_mode='short')

    for row in dataset:
        id = row[0]
        datetime = dbc.datetime_to_float(str(row[2]), str(row[3]))
        bid = float(row[5])
        ask = float(row[6])
        price = Price(id, ask, bid, datetime)
        agent_long.trade(price)
        agent_short.trade(price)

    dbc.get_total_stats()
    stats_data = dbc.print_stats()

    data = dbc.get_liquid_value()

    time.sleep(1)

    historic_text = \
        f'Opened orders: {stats_data.loc[0, "OPENED_ORDERS"]}\n\n' \
        f'Closed orders: {stats_data.loc[0, "CLOSED_ORDERS"]}\n\n' \
        f'Orders closed with profit: {stats_data.loc[0, "TAKE_PROFIT_ORDERS"]}\n\n' \
        f'Orders closed with stop loss: {stats_data.loc[0, "STOP_LOSS_ORDERS"]}\n\n' \
        f'Percentage of closed orders: {stats_data.loc[0, "CLOSED_ORDERS_PERCENTAGE"]} %\n\n' \
        f'Percentage of orders closed with profit: {stats_data.loc[0, "TAKE_PROFIT_PERCENTAGE"]} %\n\n' \
        f'Percentage of orders closed with stop loss: {stats_data.loc[0, "STOP_LOSS_PERCENTAGE"]} %\n\n'

    historic_title = f'{currency} results between {start_year} and {end_year}\n\n'
    print(0)


class Main(tk.Tk):

    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)

        tk.Tk.wm_title(self, 'AlphaPy')

        container = tk.Frame(self)
        container.pack(side="top", fill='both', expand=True)

        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}

        for F in (StartPage, LiveStart, HistoricStart, Live, Historic, GraphPage):
            frame = F(container, self)
            self.frames[F] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(StartPage)

    def show_frame(self, cont):
        frame = self.frames[cont]
        frame.tkraise()

    def stop_live(self, cont):
        global con
        con.close()
        os._exit(0)

    def change_to_live(self, cont, token_var, currency_var):
        global token, currency, live

        live = True
        token = token_var.get()
        currency_aux = currency_var.curselection()
        currency = currency_var.get(currency_aux)

        x = threading.Thread(target=trade)
        x.start()

        frame = self.frames[cont]
        frame.tkraise()

    def change_to_historic(self, cont, start, end, threshold_var, currency_var):
        global threshold, start_year, end_year, currency

        start_year = int(start.get())
        end_year = int(end.get())
        threshold = float(threshold_var.get())

        currency_aux = currency_var.curselection()
        currency = currency_var.get(currency_aux)

        run_historic()

        frame = self.frames[cont]
        frame.title.config(text=historic_title)
        frame.text.config(text=historic_text)
        frame.tkraise()

    def change_to_graph(self, cont):

        global data

        liquid_value = data['BALANCE'].tolist()
        dates = data['DATE'].tolist()

        frame = self.frames[cont]
        frame.a.clear()
        frame.a.set_title(f'Results of {currency} with threshold {threshold}\n\n')
        frame.a.plot(dates, liquid_value)
        frame.canvas.draw()
        frame.tkraise()


class StartPage(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        label = tk.Label(self, text='Welcome!!!', font=LARGE_FONT, width="20", height="3")
        label.pack(pady=70, padx=250)

        live_button = ttk.Button(self, text="Live Trading", command=lambda: controller.show_frame(LiveStart))
        live_button.pack(pady=50)

        historic_button = ttk.Button(self, text="Historic Trading",
                                     command=lambda: controller.show_frame(HistoricStart))
        historic_button.pack(pady=50)

        blank_space = tk.Label(self, text="", font=LARGE_FONT, width="20", height="3")
        blank_space.pack(pady=20)


class LiveStart(tk.Frame):

    global token

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        blank_space = tk.Label(self, text="", font=LARGE_FONT)
        blank_space.pack(pady=40, padx=400)

        label = tk.Label(self, text="Insert your token", font=17)
        label.pack(pady=10, padx=10)

        token_var = tk.StringVar()

        token_entry = ttk.Entry(self, width=30, textvariable=token_var)
        token_entry.pack(pady=10, padx=10)

        our_token = tk.Label(self, text="If you don't have a token, you can use ours: \n"
                                        "18d33b521cec247c413720caf82566dc17e4c816", font=14)
        our_token.pack(pady=5, padx=10)

        blank_space2 = tk.Label(self, text="", font=LARGE_FONT)
        blank_space2.pack(pady=20)

        label = tk.Label(self, text="Select your currency", font=17)
        label.pack(pady=10, padx=10)

        currencies = tk.StringVar(value=['EUR/USD', 'GBP/USD', 'USD/JPY', 'EUR/JPY', 'USD/CAD'])
        currency_entry = tk.Listbox(self, listvariable=currencies, height=5)
        currency_entry.pack()

        blank_space3 = tk.Label(self, text="", font=LARGE_FONT)
        blank_space3.pack(pady=20)

        start_button = ttk.Button(self, text="Start", command=lambda: controller.change_to_live(Live, token_var,
                                                                                                currency_entry))
        start_button.pack(pady=10, padx=10)

        back_button = ttk.Button(self, text="BACK", command=lambda: controller.show_frame(StartPage))
        back_button.pack(pady=10, padx=10)


class HistoricStart(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        blank_space0 = tk.Label(self, text="", font=LARGE_FONT)
        blank_space0.pack(pady=0.5)

        label = tk.Label(self, text="Select start year", font=17)
        label.pack(pady=3)

        start_date = ttk.Combobox(self, values=('2001', '2002', '2003', '2004', '2005', '2006', '2007', '2008',
                                                '2009', '2010', '2011', '2012', '2013', '2014', '2015', '2016',
                                                '2017', '2018', '2019'))
        start_date.pack()

        label = tk.Label(self, text="Select end year", font=17)
        label.pack(pady=10)

        finish_date = ttk.Combobox(self, values=('2001', '2002', '2003', '2004', '2005', '2006', '2007', '2008',
                                                 '2009', '2010', '2011', '2012', '2013', '2014', '2015', '2016',
                                                 '2017', '2018', '2019'))
        finish_date.pack()

        blank_space1 = tk.Label(self, text="", font=LARGE_FONT)
        blank_space1.pack(pady=5)

        label = tk.Label(self, text="Select a threshold", font=17)
        label.pack(pady=7, padx=10)

        threshold_entry = ttk.Combobox(self, values=('0.01', '0.005', '0.0025'))
        threshold_entry.pack()

        blank_space2 = tk.Label(self, text="", font=LARGE_FONT)
        blank_space2.pack(pady=5)

        label = tk.Label(self, text="Select your currency", font=17)
        label.pack(pady=7, padx=10)

        currencies = tk.StringVar(value=['eur_usd', 'gbp_usd', 'usd_cad', 'usd_jpy', 'eur_gbp', 'eur_jpy', 'eur_chf'])
        currency_entry = tk.Listbox(self, listvariable=currencies, height=7)
        currency_entry.pack()

        make_sure = tk.Label(self, text="Make sure that you have selected a currency pair before pressing start", font=17)
        make_sure.pack()

        blank_space3 = tk.Label(self, text="", font=17)
        blank_space3.pack(pady=5)

        wait_label = tk.Label(self, text=f'This process may take a while,\n\n'
                                         f'Please be patient\n', font=17)
        wait_label.pack()

        start_button = ttk.Button(self, text="Start", command=lambda: controller.change_to_historic(Historic, start_date, finish_date, threshold_entry, currency_entry))
        start_button.pack(pady=10, padx=10)

        back_button = ttk.Button(self, text="BACK", command=lambda: controller.show_frame(StartPage))
        back_button.pack(pady=10, padx=10)

        blank_space4 = tk.Label(self, text="", font=17)
        blank_space4.pack(pady=10)


class Live(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        blank_space0 = tk.Label(self, text="", font=LARGE_FONT)
        blank_space0.pack(pady=20)

        algo_status = tk.Label(self, text=f'The algorithm is now trading automatically', font=LARGE_FONT)
        algo_status.pack(pady=20)

        monitor_text = tk.Label(self, text=f'You can monitor your orders at https://tradingstation.fxcm.com', font=LARGE_FONT)
        monitor_text.pack(pady=20)

        user_info = tk.Label(self, text=f'If you are using our token, use this user and password to access the website: \n\n'
                                        f'User: D261155170\n'
                                        f'Password: 9549\n', font=LARGE_FONT)
        user_info.pack(pady=20)

        blank_space1 = tk.Label(self, text="", font=LARGE_FONT)
        blank_space1.pack(pady=20)

        back_button = ttk.Button(self, text="QUIT", command=lambda: controller.stop_live(StartPage))
        back_button.pack(padx=200)


class Historic(tk.Frame):

    global start_year, end_year, historic_text, currency, historic_title

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        blank_space0 = tk.Label(self, text="", font=LARGE_FONT)
        blank_space0.pack(pady=10)

        self.title = tk.Label(self, text=historic_title, font=LARGE_FONT)
        self.title.pack(pady=20, padx=10)

        self.text = tk.Label(self, text=historic_text, font=17)
        self.text.pack(pady=10, padx=10)

        graph_button = ttk.Button(self, text="Graph of the liquid value", command=lambda: controller.change_to_graph(GraphPage))
        graph_button.pack(pady=10, padx=10)

        back_button = ttk.Button(self, text="Home", command=lambda: controller.show_frame(StartPage))
        back_button.pack(pady=10, padx=10)


class GraphPage(tk.Frame):

    global start_year, end_year, historic_text, currency, historic_title, threshold

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)

        blank_space0 = tk.Label(self, text="", font=LARGE_FONT)
        blank_space0.pack(pady=3)

        plt.style.use('seaborn')
        plt.legend(loc='best', prop={'size': 20})

        self.fig = Figure(figsize=(12, 5), dpi=100)

        self.a = self.fig.add_subplot(111)

        self.a.xaxis.set_major_locator(mdates.YearLocator())
        self.a.xaxis.set_major_formatter(mdates.DateFormatter('%Y %m'))

        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.get_tk_widget().pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)
        self.canvas._tkcanvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        back_button = ttk.Button(self, text="back", command=lambda: controller.show_frame(Historic))
        back_button.pack(pady=10, padx=10)


app = Main()
app.mainloop()

