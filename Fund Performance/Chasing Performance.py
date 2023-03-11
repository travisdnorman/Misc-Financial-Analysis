#data from https://www.kaggle.com/datasets/stefanoleone992/mutual-funds-and-etfs
#data set contains inherient survivorship bias
#nav doesn't account for any distributions

import pandas as pd
from pandas import IndexSlice as idx
import math

historical_review_period = 5 #years
#frequency at which we try different sortings
reselection_period = 12 #months
#how many years into the future do we track the returns of the deciles
post_selection_timeframe = 10 #years
months_per_year = 12

#Get list of funds
Funds = pd.read_csv('D:\Data\ETFs_MutualFunds\MutualFunds.csv')
#Remove funds without a category specified
Funds = Funds[Funds['fund_category'].notna()]

#convert inception date string to datetime
Funds['inception_date'] = pd.to_datetime(Funds['inception_date']).dt.date

Selected_Funds = Funds[Funds['fund_category'].str.contains('Small')]
selected_funds_categories = Selected_Funds['fund_category'].value_counts()
selected_funds_categories = selected_funds_categories[selected_funds_categories >= 30]

Selected_Funds = Selected_Funds[Selected_Funds['fund_category'].isin(selected_funds_categories.index.tolist())]

#read data and convert price_date column to datetime data type
data = pd.read_csv('D:\Data\ETFs_MutualFunds\MutualFund prices - A-E.csv')
data = pd.concat([data,pd.read_csv('D:\Data\ETFs_MutualFunds\MutualFund prices - F-K.csv')])
data = pd.concat([data,pd.read_csv('D:\Data\ETFs_MutualFunds\MutualFund prices - L-P.csv')])
data = pd.concat([data,pd.read_csv('D:\Data\ETFs_MutualFunds\MutualFund prices - Q-Z.csv')])
Selected_Funds_data = data[data['fund_symbol'].isin(Selected_Funds['fund_symbol'])]
Selected_Funds_data.loc[:,'price_date'] =  pd.to_datetime(Selected_Funds_data['price_date']).dt.date

#exclude dates where less than 30 funds existed
price_dates = Selected_Funds_data['price_date'].value_counts()
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

#pull funds data for determined price_dates from data
Selected_Funds_data = Selected_Funds_data[Selected_Funds_data['price_date'].isin(price_dates)]
#sort Selected_Funds_data on date and then on fund_symbol
Selected_Funds_data = Selected_Funds_data.sort_values(by=['price_date','fund_symbol'])
Selected_Funds_data = Selected_Funds_data.set_index(['fund_symbol','price_date'])
    
#determine date we sort into deciles
selection_dates = price_dates[historical_review_period*months_per_year:-post_selection_timeframe*months_per_year:reselection_period]

#for each selection date
for idx_selection, selection_date in enumerate(selection_dates):
    #which funds were open on that date
    selected_funds_beginning_of_period = Selected_Funds_data.xs(price_dates[idx_selection*reselection_period], level='price_date').index.tolist()
    #which funds are still open at end of review
    selected_funds_end_of_period = Selected_Funds_data.xs(price_dates[idx_selection*reselection_period+(historical_review_period+post_selection_timeframe)*months_per_year], level='price_date').index.tolist()
    selected_funds = list(set(selected_funds_beginning_of_period).intersection(selected_funds_end_of_period))
    beginning_values = Selected_Funds_data.xs(price_dates[idx_selection*reselection_period], level='price_date').loc[selected_funds,:]['nav_per_share']
    ending_values = Selected_Funds_data.xs(selection_date, level='price_date').loc[selected_funds,:]['nav_per_share']
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
            review_date = price_dates[(historical_review_period+j)*months_per_year+idx_selection*reselection_period]
            beginning_values = Selected_Funds_data.xs(selection_date, level='price_date').loc[decile,:]['nav_per_share']
            ending_values = Selected_Funds_data.xs(review_date, level='price_date').loc[decile,:]['nav_per_share']
            decile_annualized_period_returns = (ending_values/beginning_values)**(1/historical_review_period)-1
            temp[year_str] = [decile_annualized_period_returns.mean()]
        if i == 0:
            deciles_post_selection_returns = pd.DataFrame(temp, index=[1])
            deciles_post_selection_returns.index.name = 'Decile'
        else:
            deciles_post_selection_returns = pd.concat([deciles_post_selection_returns,pd.DataFrame(temp, index=[i+1])])
            
    if idx_selection == 0:
        average_deciles_post_selection_returns = deciles_post_selection_returns
    else:
        average_deciles_post_selection_returns = (average_deciles_post_selection_returns.mul(idx_selection) + deciles_post_selection_returns).div(idx_selection+1)
        
average_deciles_post_selection_returns.transpose().plot()