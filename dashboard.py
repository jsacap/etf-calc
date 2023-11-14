import os
import time
import math
import sqlite3

import yfinance as yf
import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title='JSAX Calc')

st.header('JSAX CALC')
# Hide ST HTML
hide_st_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        </style>
"""
st.markdown(hide_st_style, unsafe_allow_html=True)
hide_footer_style = """
<style>
.reportview-container .main footer {visibility: hidden;}    
"""
st.markdown(hide_footer_style, unsafe_allow_html=True)
if 'text_input_value' not in st.session_state:
    st.session_state.text_input_value = ''

st.write('Enter your ticker here')
ticker = st.text_input('Enter ticker here', key='text_input',
                       value=st.session_state.text_input_value)
st.session_state.text_input_value = ticker

tickers = [ticker.strip() for ticker in ticker.split(',')]


start_date = st.date_input('Select start date')
end_date = st.date_input('Select end date')

initial_deposit = st.number_input(
    'Enter your initial deposit amount ($):', min_value=1)


def calculate_return(tickers):
    try:
        # merged_data = pd.DataFrame()

        for ticker in tickers:
            ticker_download = yf.download(
                ticker, start=start_date, end=end_date).reset_index()
            ticker_download['Date'] = pd.to_datetime(
                ticker_download['Date']).dt.date
            ticker_buy_price = ticker_download['Open'][0]
            total_shares_purchased = math.floor(
                initial_deposit / ticker_buy_price)
            remainder = initial_deposit % ticker_buy_price
            initial_share_purchase = total_shares_purchased
            st.write(
                f'Purchasing \${initial_deposit} worth of {ticker} at the price of \${ticker_buy_price:.2f} buys {total_shares_purchased:.0f} shares with a remainder of \${remainder:.2f}')

            # Extract Dividend Data
            ticker_dividend_download = yf.Ticker(ticker).dividends
            ticker_dividends_df = pd.DataFrame(ticker_dividend_download)
            ticker_dividends_df.reset_index(inplace=True)
            ticker_dividends_df['Date'] = pd.to_datetime(
                ticker_dividends_df['Date']).dt.date
            ticker_dividends_df['Dividends'] = ticker_dividends_df['Dividends'].astype(
                float)
            merged_data = pd.DataFrame()

            # Filtering dividend data to match the selected period
            ticker_dividends_df = ticker_dividends_df[(
                ticker_dividends_df['Date'] >= start_date) & (ticker_dividends_df['Date'] <= end_date)]

            cumulative_value = []
            total_investment_dollars = initial_deposit

            for index, row in ticker_dividends_df.iterrows():
                dividend_date = row['Date']
                dividend_amount = row['Dividends']

                dividend_income = total_shares_purchased * dividend_amount

                matching_rows = ticker_download[ticker_download['Date']
                                                == dividend_date]

                if not matching_rows.empty:
                    additional_shares = dividend_income / \
                        matching_rows['Close'].values[0]
                    additional_shares = round(additional_shares)

                    total_shares_purchased += additional_shares
            total_shares_drp = total_shares_purchased - initial_share_purchase
            st.write(
                f'The total amount of shares that were purchased from DRP was {total_shares_drp} totaling a holding of {total_shares_purchased} shares!')

            end_price = ticker_download['Close'].iloc[-1]
            end_value = total_shares_purchased * end_price
            gain_dollars = round(end_value - initial_deposit, 2)
            percentage_gain = (gain_dollars / initial_deposit) * 100

            

            # Create a new column 'Daily_Close' to track the daily close
            ticker_download['Daily_Close'] = ticker_download['Close']

            for index, row in ticker_dividends_df.iterrows():
                dividend_date = row['Date']
                dividend_amount = row['Dividends']

                matching_rows = ticker_download[ticker_download['Date']
                                                == dividend_date]

                if not matching_rows.empty:
                    # Update the 'Daily_Close' column with reinvested dividends
                    ticker_download.loc[ticker_download['Date'] ==
                                        dividend_date, 'Daily_Close'] += dividend_amount

            # Append the data to the merged_data DataFrame
            ticker_download['ticker'] = ticker
            merged_data_list = [merged_data, ticker_download]
            merged_data = pd.concat(merged_data_list, ignore_index=True)
        if not merged_data.empty:

            fig = px.line(merged_data, x='Date', y=['Close', 'Daily_Close'], title='Your Investment Over Time',
                          color='ticker')

            # Create a DataFrame to store investment values without DRP
            investment_without_drp = merged_data.groupby('Date')['Close'].sum() * initial_share_purchase

            # Create a DataFrame to store investment values without DRP
            investment_without_drp_df = pd.DataFrame({
                'Date': investment_without_drp.index,
                'Investment Without DRP': investment_without_drp.values
            })

            # Calculate investment performance with and without DRP
            investment_without_drp = merged_data.groupby('Date')['Close'].sum() * initial_share_purchase
            investment_with_drp = merged_data.groupby('Date')['Daily_Close'].sum() * total_shares_purchased
            
            closing_without_drp = investment_without_drp.iloc[-1]
            dollar_gain_without_drp = round(closing_without_drp - initial_deposit, 2)
            percent_gain_wihtout_drp = dollar_gain_without_drp / initial_deposit * 100

            # st.metrics for each ticker
            st.subheader(f'{ticker.upper()}')
            cl1, cl2, cl3, cl4 = st.columns(4)
            cl1.metric(
                f'Initial Investment', f'${initial_deposit:.0f}')
            cl2.metric(f'Closing Balance', f'${end_value:.2f}', f'${closing_without_drp:.2f} (NO DRP)', delta_color='off')
            cl3.metric(f'Gain ($)', f'${gain_dollars:.2f}', f'${dollar_gain_without_drp} (NO DRP)', delta_color='off')
            cl4.metric(f'Gain (%)', f'{percentage_gain:.2f}%', f'{percent_gain_wihtout_drp:.2f}% (NO DRP)',delta_color='off')


            # Add the investment without DRP to the DataFrame
            investment_without_drp_df['Investment Without DRP'] = investment_without_drp.values

            # Add the investment with DRP to the DataFrame
            investment_without_drp_df['Investment With DRP'] = investment_with_drp.values

            # Plot the comparison
            fig_comparison = px.line(investment_without_drp_df, x='Date', y=['Investment Without DRP', 'Investment With DRP'],
                                    labels={'value': 'Investment Value', 'variable': 'DRP'},
                                    title=f'Investment Performance Comparison for {ticker.upper()} (with and without DRP)',
                                    color_discrete_map={'Investment Without DRP': 'blue', 'Investment With DRP': 'orange'})

            # Add legend and labels
            fig_comparison.update_layout(legend_title_text='', xaxis_title='Date', yaxis_title='Investment Value ($)',
                                        legend=dict(title='', orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1))

            # Show the comparison plot
            st.plotly_chart(fig_comparison)
            return fig, merged_data
        else:
            st.warning(
                "No data available for the entered tickers. Please check your ticker symbols.")
    except ValueError as ve:
        st.error(f"ValueError: {ve}. Please enter a valid ticker.")
    except Exception as e:
        st.error(f"An error occurred: {str(e)}. Please enter a valid ticker.")

    return None, None


if st.button('Calculate'):
    with st.spinner("Downloading Data. Please Wait..."):
        try:
            fig, download_data = calculate_return(tickers)

            if fig is not None:
                st.balloons()
            # If data download is unsuccessful, display a message
            else:
                st.warning("Please enter valid ticker symbols.")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}. Please try again.")
