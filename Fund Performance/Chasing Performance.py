#data from https://www.kaggle.com/datasets/stefanoleone992/mutual-funds-and-etfs
#data set contains inherient survivorship bias

import pandas as pd
from pandas import IndexSlice as idx
import math

historical_review_period = 5 #years
post_selection_timeframe = 10 #years
months_per_year = 12

#Get list of funds
Funds = pd.read_csv('D:\Data\ETFs_MutualFunds\MutualFunds.csv')
#Remove funds without a category specified
Funds = Funds[Funds['fund_category'].notna()]

#convert inception date string to datetime
Funds['inception_date'] = pd.to_datetime(Funds['inception_date']).dt.date

Growth_Funds = Funds[Funds['fund_category'].str.contains('Growth')]
growth_fund_categories = Growth_Funds['fund_category'].value_counts()
growth_fund_categories = growth_fund_categories[growth_fund_categories >= 30]

Growth_Funds = Growth_Funds[Growth_Funds['fund_category'].isin(growth_fund_categories.index.tolist())]

#read data and convert price_date column to datetime data type
data = pd.read_csv('D:\Data\ETFs_MutualFunds\MutualFund prices - A-E.csv')
data = pd.concat([data,pd.read_csv('D:\Data\ETFs_MutualFunds\MutualFund prices - F-K.csv')])
data = pd.concat([data,pd.read_csv('D:\Data\ETFs_MutualFunds\MutualFund prices - L-P.csv')])
data = pd.concat([data,pd.read_csv('D:\Data\ETFs_MutualFunds\MutualFund prices - Q-Z.csv')])
Growth_Funds_data = data[data['fund_symbol'].isin(Growth_Funds['fund_symbol'])]
Growth_Funds_data.loc[:,'price_date'] =  pd.to_datetime(Growth_Funds_data['price_date']).dt.date

#exclude dates where less than 30 funds existed
price_dates = Growth_Funds_data['price_date'].value_counts()
price_dates = sorted(list(price_dates[price_dates >= 30].index))

#get prices for first trading day of each month
date = pd.to_datetime(pd.DataFrame({'year': [price_dates[0].year], 'month': [price_dates[0].month+1],'day': [1]})).dt.date
temp = []
while (pd.Timestamp(date[0]) < pd.Timestamp(price_dates[-1])):
    if (date[0] in price_dates):
        temp.append(date[0])
        if(date[0].month == 12):
            date = pd.to_datetime(pd.DataFrame({'year': [date[0].year+1], 'month': [1],'day': [1]})).dt.date
        else:
            date = pd.to_datetime(pd.DataFrame({'year': [date[0].year], 'month': [date[0].month+1],'day': [1]})).dt.date
    else:
        date = pd.to_datetime(date + pd.DateOffset(1)).dt.date

price_dates = temp
    
#pull Growth funds data for determined price_dates from data
Growth_Funds_data = Growth_Funds_data[Growth_Funds_data['price_date'].isin(price_dates)]
#sort Growth_Funds_data on date and then on fund_symbol
Growth_Funds_data = Growth_Funds_data.sort_values(by=['price_date','fund_symbol'])
Growth_Funds_data = Growth_Funds_data.set_index(['fund_symbol','price_date'])

# use nav values
# prev_month_data = Growth_Funds_data.xs(price_dates[0], level='price_date')
# for date in price_dates[1:]:
#     Growth_Funds_data_on_date = Growth_Funds_data.xs(date, level='price_date')
#     temp = (Growth_Funds_data_on_date['nav_per_share']-prev_month_data['nav_per_share'])/prev_month_data['nav_per_share']
#     temp = temp.to_frame()
#     temp['price_date'] = date
#     temp = temp.set_index('price_date',append=True)
#     Growth_Funds_data.loc[idx[: , date], 'monthly_return'] = temp['nav_per_share']
#     prev_month_data = Growth_Funds_data_on_date

# #rest indexes to remove indexes that no longer exist from index list
# Growth_Funds_data = Growth_Funds_data[Growth_Funds_data['monthly_return'].notna()].reset_index().set_index(['fund_symbol','price_date'])

#determine date we sort into deciles
#arbitrarily doing this once per year
selection_dates = price_dates[historical_review_period*months_per_year:-post_selection_timeframe*months_per_year:int(months_per_year)]

#for each selection date
for m, selection_date in enumerate(selection_dates):
    #which funds were open on that date
    selected_funds = Growth_Funds_data.xs(price_dates[m*months_per_year], level='price_date').index.tolist()
    beginning_values = Growth_Funds_data.xs(price_dates[m*months_per_year], level='price_date')['nav_per_share']
    ending_values = Growth_Funds_data.xs(selection_date, level='price_date').loc[selected_funds,:]['nav_per_share']
    #calculate the annualized returns of those funds which were open over the historical review period
    annualized_period_returns = (ending_values/beginning_values)**(1/historical_review_period)-1
    #sort those annualized returns
    annualized_period_returns = annualized_period_returns.sort_values(ascending=False)
    
    num_funds = len(selected_funds)
    num_funds_per_decile = math.floor(num_funds/10)
    
    deciles = [[]]*10
    ranked_annualized_period_returns = annualized_period_returns.index.tolist()
    #break selected funds into deciles based on annualized returns
    for i in range(9):
        deciles[i] = ranked_annualized_period_returns[(i*num_funds_per_decile):((i+1)*num_funds_per_decile)]
    
    #put remaining in last decile
    deciles[9] = ranked_annualized_period_returns[(9*num_funds_per_decile):]
    
    #for each decile find the annualized returns over each time horizon
    for i, decile in enumerate(deciles):
        temp = {}
        #for each year into the future of our post_selection_timeframe
        for j in range(1,post_selection_timeframe+1):
            year_str = 'Year ' + str(j)
            review_date = price_dates[(historical_review_period+j+m)*months_per_year]
            beginning_values = Growth_Funds_data.xs(selection_date, level='price_date').loc[decile,:]['nav_per_share']
            ending_values = Growth_Funds_data.xs(review_date, level='price_date').loc[decile,:]['nav_per_share']
            annualized_period_returns = (ending_values/beginning_values)**(1/historical_review_period)-1
            temp[year_str] = [annualized_period_returns.mean()]
        if i == 0:
            deciles_post_selection_returns = pd.DataFrame(temp, index=[1])
            deciles_post_selection_returns.index.name = 'Decile'
        else:
            deciles_post_selection_returns = pd.concat([deciles_post_selection_returns,pd.DataFrame(temp, index=[i+1])])
            
    if m == 0:
        average_deciles_post_selection_returns = deciles_post_selection_returns
    else:
        average_deciles_post_selection_returns = (average_deciles_post_selection_returns.mul(m) + deciles_post_selection_returns).div(m+1)
        
average_deciles_post_selection_returns.transpose().plot()