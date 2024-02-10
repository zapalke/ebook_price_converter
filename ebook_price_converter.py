import pandas as pd
from datetime import datetime, timedelta
import requests
from time import sleep
from tqdm import tqdm

class EbookPriceConverter():
    def __init__(self, ebook_list_path, result_save_path, country='US'):
        """
        Initialize EbookPriceConverter object
        Args:
        ebook_list_path (str) - path to csv file with ebooks to check
        result_save_path (str) - path to save result file
        country (str) - country code for iTunes API
        """
        self.ebook_data = []
        self.country = country
        self.ebook_list_path = ebook_list_path
        self.result_save_path = result_save_path
        self.ebooks_to_check = None

        try:
            self.exchange_rates = pd.read_csv('exchange_rates.csv')
        except FileNotFoundError:
            self.exchange_rates = pd.DataFrame(columns=['date', 'currency', 'rate','tableNo'])
            self.exchange_rates.to_csv('exchange_rates.csv', index=False)
    
    def read_data(self):
        """
        Read data from csv file
        If file does not exists or error occurs, print error message.
        Returns:
        list - list of tuples with author and ebook name
        """

        print(f'{"="*10} Reading data from CSV {"="*27}')

        try:
            self.ebooks_to_check = pd.read_csv(self.ebook_list_path,header=0).to_numpy()
            print(f"Found {len(self.ebooks_to_check)} ebooks in file {self.ebook_list_path}")
            
        except FileNotFoundError:
            print(f"File {self.ebook_list_path} not found")
            return 
        except Exception as e:
            print(f"Error occured during reading file {self.ebook_list_path}: {e}")
        return self.ebooks_to_check
    
    def get_ebook_data_from_itunes(self):
        """
        Function to get data about ebooks from iTunes API based on given
        search terms and country
        Returns:
        list - list of dictionaries with data about ebooks
        """

        print(f'{"="*10} Getting data from iTunes {"="*24}')

        if self.ebooks_to_check is None:
            print("No data to check")
            return 
        
        error_msg_list = []
        ebook_errors = 0

        for ebook in tqdm(range(len(self.ebooks_to_check)),ncols=60):
            try:
                ebook_author, ebook_name = self.ebooks_to_check[ebook]
            except ValueError:
                error_msg_list.append(f"Invalid data: {self.ebooks_to_check[ebook]}")
                continue
            
            search_term = f"{ebook_author.replace(' ','+')}+{ebook_name.replace(' ','+')}"
            ebook_itunes_request = requests.get(f"https://itunes.apple.com/search?term={search_term}&country={self.country}&media=ebook")
            if ebook_itunes_request.status_code != 200:
                error_msg_list.append(f'Request for {ebook_author} {ebook_name} failed with status code {ebook_itunes_request.status_code}')
                ebook_errors += 1
                continue
            elif len(ebook_itunes_request.json()['results']) == 0:
                error_msg_list.append(f"No ebook found for {ebook_author} {ebook_name}")
                ebook_errors += 1
                continue

            ebook_itunes_data = ebook_itunes_request.json()['results'][0]
            self.ebook_data.append({
                'name'      : ebook_itunes_data['artistName'],
                'title'     : ebook_itunes_data['trackName'],
                'curr'      : ebook_itunes_data['currency'],
                'price'     : ebook_itunes_data['price'],
                'date'      : datetime.strftime(datetime.strptime(ebook_itunes_data['releaseDate'],"%Y-%m-%dT%H:%M:%SZ"),"%Y-%m-%d"),
                'fromNBP'   : {
                    'rate'      : None,
                    'pricePLN'  : None,
                    'tableNo'   : None
                }
            })
            sleep(0.1)  #Added lag to avoid being blocked by iTunes API
        
        if len(error_msg_list) > 0:
            print(f'Errors occured during getting data from iTunes:')
            for error in error_msg_list:
                print(error)
        print(f'Could not retrieve data from iTunes for {ebook_errors} ebooks.')
        return self.ebook_data
    
    def check_if_exchange_rate_is_already_saved(self, ebook):
        """
        Helper function for get_exchange_rates_data_and_convert_price_to_PLN
        Check if exchange rate for given date and currency is already saved in exchange_rates.csv
        If yes, save exchange rate to ebook_data and return True.
        Returns:
        bool - True if exchange rate is already saved, False if not
        """
        if self.exchange_rates[(self.exchange_rates['date'] == self.ebook_data[ebook]['date']) & (self.exchange_rates['currency'] == self.ebook_data[ebook]['curr'])].shape[0] > 0:
            self.ebook_data[ebook]['fromNBP']['rate'] = self.exchange_rates[(self.exchange_rates['date'] == self.ebook_data[ebook]['date']) & (self.exchange_rates['currency'] == self.ebook_data[ebook]['curr'])]['rate'].values[0]
            self.ebook_data[ebook]['fromNBP']['tableNo'] = self.exchange_rates[(self.exchange_rates['date'] == self.ebook_data[ebook]['date']) & (self.exchange_rates['currency'] == self.ebook_data[ebook]['curr'])]['tableNo'].values[0]
            self.ebook_data[ebook]['fromNBP']['pricePLN'] = self.ebook_data[ebook]["price"] * self.ebook_data[ebook]['fromNBP']['rate']
            return True
        else:
            return False

    def get_exchange_rates_data_and_convert_price_to_PLN(self):
        """
        A function that gets exchange rates from NBP
        based on given currency and date. Then it converts prices to PLN
        Args:
        ebook_data: list - list of dictionaries with ebook data
        Returns:
        list - list of dictionaries with ebook data and prices in PLN
        """

        print(f'{"="*10} Getting exchange rates from NBP {"="*16}')

        error_msg_list = []
        NBP_erros = 0

        for ebook in tqdm(range(len(self.ebook_data)),ncols=60):
            release_date = datetime.strptime(self.ebook_data[ebook]['date'],"%Y-%m-%d")

            if release_date < datetime(2002,1,2):
                # Earliest exchange rates available from NBP API is from 2002-01-02
                NBP_erros += 1
                error_msg_list.append(f'Cannot get exchange rates for ebook {self.ebook_data[ebook]["name"]} released on {release_date}. NBP API does not provide data for dates before 2002-01-02.')
                continue
            
            elif self.check_if_exchange_rate_is_already_saved(ebook):
                continue

            else:
                nbp_request = requests.get(f'http://api.nbp.pl/api/exchangerates/rates/A/{self.ebook_data[ebook]["curr"]}/{self.ebook_data[ebook]["date"]}/')
                if nbp_request.status_code == 200:
                    self.ebook_data[ebook]['fromNBP']['rate'] = nbp_request.json()['rates'][0]['mid']
                    self.ebook_data[ebook]['fromNBP']['tableNo'] = nbp_request.json()['rates'][0]["no"]
                    self.ebook_data[ebook]['fromNBP']['pricePLN'] = self.ebook_data[ebook]["price"] * self.ebook_data[ebook]['fromNBP']['rate']
                else:
                    #If exchange rate for given date is not available, try to get exchange rate for previous days
                    i = 1
                    max_days_ago = 10 
                    for i in range(1, max_days_ago):
                        previous_date = datetime.strftime(release_date - timedelta(days=i),"%Y-%m-%d")
                        if self.check_if_exchange_rate_is_already_saved(ebook):
                            break
                        else:
                            nbp_request = requests.get(f'http://api.nbp.pl/api/exchangerates/rates/A/{self.ebook_data[ebook]["curr"]}/{previous_date}/')
                            if nbp_request.status_code == 200:
                                #error_msg_list.append(f'Exchange rate for {self.ebook_data[i]["name"]} found {i} days before release date {self.ebook_data[i]["date"]}.')
                                self.ebook_data[ebook]['fromNBP']['rate'] = nbp_request.json()['rates'][0]['mid']
                                self.ebook_data[ebook]['fromNBP']['tableNo'] = nbp_request.json()['rates'][0]["no"]
                                self.ebook_data[ebook]['fromNBP']['pricePLN'] = self.ebook_data[ebook]["price"] * self.ebook_data[ebook]['fromNBP']['rate']
                                break

                if self.ebook_data[ebook]['fromNBP']['rate'] is None:
                    error_msg_list.append(f'Cannot get exchange rates for ebook {self.ebook_data[ebook]["name"]} released on {release_date} and currency {self.ebook_data[ebook]["curr"]} up to {max_days_ago} days before. Status code {nbp_request.status_code}.')
                    NBP_erros += 1
                else:
                    # Save exchange rate to exchange_rates.csv
                    new_exchange_rate = {
                        'date'      : self.ebook_data[ebook]['date'],
                        'currency'  : self.ebook_data[ebook]['curr'],
                        'rate'      : self.ebook_data[ebook]['fromNBP']['rate'],
                        'tableNo'   : self.ebook_data[ebook]['fromNBP']['tableNo']
                    }
                    self.exchange_rates.loc[len(self.exchange_rates)] = new_exchange_rate
                    self.exchange_rates.to_csv('exchange_rates.csv', index=False)

            sleep(0.1) #Added lag to not overload NBP API

        if len(error_msg_list) > 0:
            print(f'Errors occured during getting data from NBP:')
            for error in error_msg_list:
                print(error)
        print(f'Could not retrieve exchange rates from NBP for {NBP_erros} eboooks')
        return self.ebook_data
    
    def save_ebook_data_to_json(self):
        """
        Save data to json file
        Args:
        Returns:
        df - DataFrame with ebook data
        """
        
        print(f'{"="*10} Saving data to JSON file {"="*24}')

        try:
            df = pd.DataFrame(self.ebook_data)
            df.to_json(self.result_save_path, orient='records')
            print(f"Data saved to {self.result_save_path}")
        except Exception as e:
            print(f"Error occured during saving file {self.result_save_path}: {e}")
            return 
        return df
    

if __name__ == "__main__":

    ebook_list_path = 'example_list.csv'
    result_save_path = 'ebooks_data.json'
    country = 'US'

    ebook_price_converter = EbookPriceConverter(ebook_list_path=ebook_list_path, result_save_path=result_save_path,country=country)
    ebook_price_converter.read_data()
    ebook_price_converter.get_ebook_data_from_itunes()
    ebook_price_converter.get_exchange_rates_data_and_convert_price_to_PLN()
    ebook_price_converter.save_ebook_data_to_json()