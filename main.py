import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import sqlite3
import seaborn as sns
from datetime import datetime
from datetime import timedelta

# Define the start and end dates for the data and remove the time component
start_date = pd.Timestamp('2000-12-01')
end_date = pd.Timestamp('2023-04-03') + timedelta(days=1)  # Add one day to the end date
ticker = 'SQQQ'

# Try to connect to the database and load the data
try:
    # Connect to the database and load the data into a DataFrame
    conn = sqlite3.connect('SQQQ.db')
    print('Connected to database')

    # Check if the table exists in the database
    query = f"SELECT name FROM sqlite_master WHERE type='table' AND name='{ticker}'"
    table_exists = pd.read_sql_query(query, conn).shape[0] > 0

    if table_exists:
        # Load the data from the database
        query = f"SELECT * FROM {ticker}"
        df = pd.read_sql_query(query, conn, index_col='Date', parse_dates=True)
        print(f"Successfully loaded data for {ticker} from the database.")
        # Convert index to datetime
        df.index = pd.to_datetime(df.index)

        # Check if the data in the database is up-to-date
        latest_date_in_database = df.index.max()
        if latest_date_in_database < end_date - timedelta(days=1):
            print(f"Data in the database is outdated. Downloading missing data from Yahoo Finance...")
            missing_data = yf.download(ticker, start=latest_date_in_database + timedelta(days=1), end=end_date)
            missing_data.index = pd.to_datetime(missing_data.index)
            df = pd.concat([df, missing_data], axis=0)
            # Save the updated data to the database
            df.to_sql(ticker, conn, if_exists='replace')
            print(f"Successfully updated the database with missing data for {ticker}.")

        # Filter the DataFrame based on the desired start and end dates
        df = df.loc[start_date:end_date]

    else:
        # Download the data from Yahoo Finance
        print(f"No data found for {ticker} in the database. Downloading from Yahoo Finance...")
        df = yf.download(ticker, start=start_date, end=end_date)

        df.index = pd.to_datetime(df.index)

        # Filter the DataFrame based on the desired start and end dates
        df = df.loc[start_date:end_date]

        # Save the data to the database
        df.to_sql(ticker, conn, if_exists='replace')
        print(f"Successfully created new database and saved data for {ticker} to the database.")

    # Close the database connection
    conn.close()

# If there is an error, print an error message and exit
except Exception as e:
    print(f"Error loading data: {e}")
    exit()


print(df.columns)

# Add a column for the daily return
df['Daily Return'] = df['Adj Close'].pct_change()

#calculate change in price
df['Price Change'] = df['Adj Close'].diff()




# Calculate the inverse of the daily return for SQQQ, representing the daily return of a short position
df['Inverse Daily Return'] = 1 / (1 + df['Daily Return'])

# Calculate the cumulative return of the short position using the 'Inverse Daily Return'
df['Short Cumulative Return'] = df['Inverse Daily Return'].cumprod()

# Calculate the daily return of the short position by finding the percentage change in the 'Short Cumulative Return'
df['Short Daily Return'] = df['Short Cumulative Return'].pct_change()

# Add a column for the cumulative return
df['Cumulative Return'] = (1 + df['Daily Return']).cumprod()
df['50 day moving average'] = df['Adj Close'].rolling(window=50).mean()

# If price crosses above 50 day, open a short position at the open the next day
df['Signal'] = np.where(df['Adj Close'] > df['50 day moving average'], 1.0, 0.0)

#add a column where 1 and 0 are replaced by buy and sell as appropriate
df['Buy or Sell'] = np.where(df['Signal'] == 1, 'Buy', 'Sell')

# Calculate the daily return of the strategy using the 'Short Daily Return'
df['Strategy Daily Return'] = df['Signal'].shift(1) * df['Short Daily Return']

# Calculate the cumulative return of the strategy
df['Strategy Cumulative Return'] = (1 + df['Strategy Daily Return']).cumprod()

#calculate the number of trades
df['Number of Trades'] = df['Signal'].diff().fillna(0).abs()

#initialize a portfolio with $100,000
portfolio_start = 100

#calculate the number of shares to buy or sell
df['Number of Shares'] = portfolio_start * df['Signal'].shift(1) / df['Adj Close']

# Calculate the change in portfolio value
df['Portfolio Value Change'] = df['Price Change'] * - df['Number of Shares']

# Calculate the portfolio value by adding the change in value to the previous day's value
df['Portfolio Value'] = df['Portfolio Value Change'].cumsum() + portfolio_start

# Calculate the total return of the portfolio
df['Portfolio Return'] = df['Portfolio Value Change'] / df['Portfolio Value'].shift(1)

# Calculate the cumulative return of the portfolio
df['Portfolio Cumulative Return'] = (1 + df['Portfolio Return']).cumprod()

#plot portfolio value
df['Portfolio Value'].plot(figsize=(12,8), title='Portfolio Value')

#index SQQQ to 100000
df['Cumulative Return'] = df['Cumulative Return'] * portfolio_start

#add SQQQ returns
df['Cumulative Return'].plot(figsize=(12,8), title='Portfolio Value', color='green')

#add legend
plt.legend(['Portfolio Value', 'SQQQ'])

plt.show()

#create a list of all the trades with their date and the price and the buy or sell
trades = []
for i in range(len(df)):
    if df['Number of Trades'][i] == 1:
        trades.append([df.index[i], df['Adj Close'][i], df['Buy or Sell'][i]])

#print last five trades
print(trades[-5:])

