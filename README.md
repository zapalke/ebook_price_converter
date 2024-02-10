# Ebook Price Converter
Ebook Price Converter is a program that gets data about ebooks from iTunes API and converts their prices to Polish zloty (PLN) according to exchange rates from the National Bank of Poland (NBP).

## Requirements

To run the program, you need:

- Python 3.8 or higher
- Libraries: pandas, requests and tqdm
- A csv file with a list of ebooks to check in the format: author, title (example list is provided)

## Installation

To install the program, clone this repository and install the required dependencies:

```bash
git clone https://github.com/zapalke/ebook_price_converter.git
cd ebook_price_converter
pip install -r requirements.txt
```

## Usage
To run the program you have to provide path to the source list and path where results should be saved. Optionally you can also provide from which country should the iTunes results be.
You can either edit the code or run it direclty from **cmd** using this command:
```console
python ebook_price_converter.py <list of ebooks>.csv <results>.json <country code; defauld US>
```
As a result you will get a JSON file with given structure:
```json
[
  {
    "name": "Andrzej Sapkowski & Danusia Stok",
    "title": "The Last Wish",
    "curr": "USD",
    "price": 9.99,
    "date": "2008-12-14",
    "fromNBP": {
      "rate": 2.9709,
      "pricePLN": 29.679291,
      "tableNo": "243/A/NBP/2008"
    }
  },
  {
    "name": "Agatha Christie",
    "title": "The Mysterious Affair at Styles",
    "curr": "USD",
    "price": 0,
    "date": "2008-07-27",
    "fromNBP": {
      "rate": 2.042,
      "pricePLN": 0,
      "tableNo": "145/A/NBP/2008"
    }
  },
```