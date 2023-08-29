import pandas as pd
import numpy as np
import bs4
from typing import List

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

CURRENCY_DF_PATH = './data/priorbank_currency_exchange.csv'

class CurrencyParsing:
    BASIC_URL = 'https://www.priorbank.by/offers/services/currency-exchange'

    def __init__(self, url: str = None, save_link: str = CURRENCY_DF_PATH):
        self.url = url if url is not None else self.BASIC_URL
        self.save_link = save_link
        self.df: pd.DataFrame

    def save_dataframe_csv(self, df: pd.DataFrame):
        df.to_csv(self.save_link, sep="\t", index=False)
        return self

    def parse_rows(self, exchange_way: str, div_rows: bs4.element.ResultSet, is_conversion: bool) -> pd.DataFrame:
        df = pd.DataFrame(columns=['exchange_way', 'currency', 'buy', 'sell', 'buy_sell', 'conversion'])
        conversion_value = 0
        if is_conversion:
            conversion_value = 1
            buy_sell_value = 0
        else:
            conversion_value = 0
            buy_sell_value = 1

        columns = div_rows.find_all('div', attrs={'class': "homeModuleColumn"})
        currency_div_values = columns[0].find_all('p')
        buy_price_div = columns[1].find_all('p')
        sell_price_div = columns[2].find_all('p')

        for j in range(1, len(currency_div_values)):
            currency = currency_div_values[j].getText()
            sell_price = sell_price_div[j].getText()
            buy_price = buy_price_div[j].getText()
            df.loc[len(df)] = [exchange_way, currency, buy_price, sell_price, buy_sell_value, conversion_value]
        return df

    def create_currency_dataframe(self) -> pd.DataFrame:
        chrome_options = webdriver.chrome.options.Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        driver = webdriver.Chrome(options=chrome_options)

        df = pd.DataFrame(columns=['exchange_way', 'currency', 'buy', 'sell', 'buy_sell', 'conversion'])
        driver.get(self.url)
        driver_parser = bs4.BeautifulSoup(driver.page_source, features='html.parser')

        exchange_way_categories = driver_parser.find('ul', attrs={'class': 'toggle__list'})

        list_exchange_way = exchange_way_categories.find_all('li')
        divs_exchange_way = driver_parser.find_all('div', attrs={'class': 'smartfox--calc'})
        # [цифровой банк, по карточке, наличные]
        for i in range(len(list_exchange_way)):
            way = list_exchange_way[i].getText()
            # у раздела наличные специфический интерфейс
            if i == len(list_exchange_way) - 1:
                values_currency_rows = divs_exchange_way[i].find_all('div', attrs={'class': 'homeModuleRow--curr'})
                for values_currency_row in values_currency_rows:
                    df = pd.concat(
                        [df, self.parse_rows(exchange_way=way, div_rows=values_currency_row, is_conversion=False)])
                conversion_row = divs_exchange_way[i].find_all('div', attrs={'class': "homeModuleRow"})[3]
                df = pd.concat([df, self.parse_rows(exchange_way=way, div_rows=conversion_row, is_conversion=True)])
            else:
                buy_sell_row = divs_exchange_way[i].find_all('div', attrs={'class': "homeModuleRow"})[0]
                df = pd.concat([df, self.parse_rows(exchange_way=way, div_rows=buy_sell_row, is_conversion=False)])
                conversion_row = divs_exchange_way[i].find_all('div', attrs={'class': "homeModuleRow"})[1]
                df = pd.concat([df, self.parse_rows(exchange_way=way, div_rows=conversion_row, is_conversion=True)])
        self.df = df.reset_index(drop=True)
        self.save_dataframe_csv(self.df)
        return self.df


class CurrencyExchange:

    EXCHANGE_WAY = np.array(['Цифровой банк', 'По карточке', 'Наличные'])
    CURRENCY = np.array(['USD', 'EUR', 'RUB'])
    AIM = np.array(['buy', 'sell'])
    COLUMNS_TO_DELETE = np.array([
        'buy_sell',
        # 'conversion'
    ])

    CURRENCY_COLUMN_NAME = 'currency'
    EXCHANGE_WAY_COLUMN_NAME = 'exchange_way'
    CONVERSION_COLUMN_NAME = 'conversion'
    BUY_COLUMN_NAME = 'buy'
    SELL_COLUMN_NAME = 'sell'
    DEFAULT_CURRENCY = 'BYN'

    CURRENCY_DIVISION_SIGN = ' / '

    def __init__(self):
        self.df: pd.DataFrame

    def read_dataframe_csv(self, path: str = CURRENCY_DF_PATH) -> pd.DataFrame:
        self.df = pd.read_csv(path, sep='\t')
        return self.df

    def swap_words(self, input_string, separator) -> str:
        parts = input_string.split(separator)
        if len(parts) != 2:
            return input_string
        swapped_string = (" " + separator + " ").join([parts[1], parts[0]])
        return swapped_string

    # RUB / EUR => add EUR / RUB
    def df_expand_conversion(self) -> pd.DataFrame:
        expanded_df = self.df.copy()
        pattern = self.CURRENCY_DIVISION_SIGN
        rows_to_be_changed = expanded_df[
            expanded_df[self.CURRENCY_COLUMN_NAME].str.findall(pattern).astype(bool)].copy()
        rows_to_be_changed[self.CURRENCY_COLUMN_NAME] = rows_to_be_changed[self.CURRENCY_COLUMN_NAME].apply(
            lambda x: self.swap_words(x, '/'))
        rows_to_be_changed = rows_to_be_changed.rename(
            columns={self.BUY_COLUMN_NAME: self.SELL_COLUMN_NAME, self.SELL_COLUMN_NAME: self.BUY_COLUMN_NAME})
        expanded_df = pd.concat([expanded_df, rows_to_be_changed], axis=0)
        expanded_df = expanded_df.reset_index(drop=True)
        self.df = expanded_df
        return self.df

    def get_df_currency_from_limit(self, df: pd.DataFrame, currency_from: np.array = None) -> pd.DataFrame:
        df_modified = df.copy()
        if currency_from is None or not np.isin(currency_from, self.CURRENCY).all():
            currency_from = self.CURRENCY
        pattern = r'\b(?:{})\s?\b'.format('|'.join(currency_from))
        df_modified = df_modified[df_modified[self.CURRENCY_COLUMN_NAME].str.findall(pattern).astype(bool)]
        if len(currency_from) != len(self.CURRENCY):
            currency_from_edited = np.array(list(map(lambda string: "( / " + string + ")", currency_from)))
            pattern = r'\b{}\s?\b'.format('|'.join(currency_from_edited))
            df_modified = df_modified[~df_modified[self.CURRENCY_COLUMN_NAME].str.findall(pattern).astype(bool)]
        return df_modified

    def get_df_aim_limit(self, df: pd.DataFrame, aim: np.array = None) -> pd.DataFrame:
        df_modified = df.copy()
        if aim is None or not np.isin(aim, self.AIM).all():
            aim = self.AIM
        columns_to_drop = np.array(list(set(self.AIM) - set(aim)))
        for column_to_drop in columns_to_drop:
            df_modified = df_modified.drop(str(column_to_drop), axis=1)
        return df_modified

    def get_df_exchange_way_limit(self, df: pd.DataFrame, exchange_way: np.array = None) -> pd.DataFrame:
        df_modified = df.copy()
        if exchange_way is None or not np.isin(exchange_way, self.EXCHANGE_WAY).all():
            exchange_way = self.EXCHANGE_WAY
        pattern = r'\b(?:{})\s?\b'.format('|'.join(exchange_way))
        df_modified = df_modified[df_modified[self.EXCHANGE_WAY_COLUMN_NAME].str.findall(pattern).astype(bool)]
        return df_modified

    def get_df_conversion_limit(self, df: pd.DataFrame, currency_to: np.array = None) -> pd.DataFrame:
        df_modified = df.copy()

        if currency_to is not None:
            if not np.isin(currency_to, self.CURRENCY).all():
                currency_to = self.CURRENCY
            df_modified = df_modified[df_modified[self.CONVERSION_COLUMN_NAME].astype(bool)]
            currency_to_patterns = []
            for val in currency_to:
                currency_to_patterns.append('(/ ' + val + ')')
            pattern = r'{}'.format('|'.join(currency_to_patterns))
            df_modified = df_modified[df_modified[self.CURRENCY_COLUMN_NAME].str.findall(pattern).astype(bool)]
        else:
            df_modified = df_modified[~df_modified[self.CONVERSION_COLUMN_NAME].astype(bool)]
            currency_to_patterns = []
            for val in self.CURRENCY:
                currency_to_patterns.append('(/ ' + val + ')')
            pattern = r'{}'.format('|'.join(currency_to_patterns))
            df_modified = df_modified[~df_modified[self.CURRENCY_COLUMN_NAME].str.findall(pattern).astype(bool)]
        return df_modified

    def get_currency_exchange(self, currency_from: np.array = None, currency_to: np.array = None,
                              exchange_way: np.array = None, aim: np.array = None) -> pd.DataFrame:
        df = self.df.copy()

        # all with given currency_from
        df = self.get_df_currency_from_limit(df, currency_from)

        # buy, sell or both
        df = self.get_df_aim_limit(df, aim)

        # exchange_way
        df = self.get_df_exchange_way_limit(df, exchange_way)

        # currency_to => conversion
        df = self.get_df_conversion_limit(df, currency_to)

        for delete_column in self.COLUMNS_TO_DELETE:
            df = df.drop(str(delete_column), axis=1)

        df = df.reset_index(drop=True)
        return df

    def get_string_from_params(self, from_to: List, exchange_way: str, buy: str = None, sell: str = None) -> str:
        result = ""
        if buy is not None:
            result = result + " \n "
            result = result + "Покупка {} из {}".format(from_to[0], from_to[1])
            result = result + " по курсу {}".format(buy)
            result = result + " используя способ обмена {}".format(exchange_way)
        if sell is not None:
            result = result + " \n "
            result = result + "Продажа {} -> {}".format(from_to[0], from_to[1])
            result = result + " по курсу {}".format(sell)
            result = result + " используя способ обмена {}".format(exchange_way)
        return result

    def df_prettifier(self, df: pd.DataFrame) -> str:
        output = ""

        is_buy_column_exist = self.BUY_COLUMN_NAME in df.columns
        is_sell_column_exist = self.SELL_COLUMN_NAME in df.columns

        for index, row in df.iterrows():
            from_to = row[self.CURRENCY_COLUMN_NAME].split(' / ') if row[self.CONVERSION_COLUMN_NAME] else [
                row[self.CURRENCY_COLUMN_NAME], "BYN"]
            exchange_way = row[self.EXCHANGE_WAY_COLUMN_NAME]
            buy = row[self.BUY_COLUMN_NAME] if is_buy_column_exist else None
            sell = row[self.SELL_COLUMN_NAME] if is_sell_column_exist else None
            output = output + self.get_string_from_params(from_to=from_to, exchange_way=exchange_way, buy=buy,
                                                          sell=sell)

        return output