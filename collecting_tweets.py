# -*- coding: utf-8 -*-
"""
Created on Tue Nov 30 20:59:28 2021

@author: brenda
"""

# Libraries
import os
import requests
import pandas as pd
from dotenv import load_dotenv

import warnings
warnings.filterwarnings('ignore')

# loadinng credenttials as environmen variables
load_dotenv('twitter_kafka_credentials.env', override = True)


# getting twitter credentials
twitter_key = os.environ.get('api_key')
twitter_secret_key = os.environ.get('secret_key')
bearer_token = os.environ.get('bearer_token')


def search_tweets(query, bearer_token = bearer_token, next_token = None):    
    
    """
    Function to request tweets according to a specific query.
    
    Inputs:
        - query: A string that will be used to find tweets.
                 Tweets must match this string to be returned.
        - bearer_token: Security token from Twitter API.
        - next_token: ID of the next page that matches the specified query.
        
    Outputs: Dictionary (json type) with the requested data.  
    """
    
    headers = {"Authorization": "Bearer {}".format(bearer_token)}
    
    # end point
    url = f"https://api.twitter.com/2/tweets/search/recent?query={query}&"

    params = {
        # select specific Tweet fields from each returned Tweet object
        'tweet.fields': 'text,created_at,lang,possibly_sensitive', # public_metrics
        
        # maximum number of search results to be returned (10 - 100)
        'max_results': 100,
        
        # additional data that relate to the originally returned Tweets
        'expansions': 'author_id,referenced_tweets.id,geo.place_id',
        
        # select specific place fields 
        "place.fields": 'country,full_name,name',
        
        # select specific user fields
        "user.fields": 'location',
        
        # get the next page of results.
        "next_token": next_token
    }
    
    # request
    response = requests.get(url = url, params = params, headers = headers)

    # verify successfull request
    if response.status_code != 200:
        raise Exception(response.status_code, response.text)
        
    else:
        return response.json()
 
    
# search term
search_tweet = search_tweets(query = "Black Widow")

# 4 main keys
search_tweet.keys()
    
    
def create_dataframes(json_tweets):
    
    """
    Function to create and organize different data into specific data frames.
    
    Inputs:
        - json_tweets: A dictionary with tweets data.
    
    Outputs: 
        - tweets: Pandas dataframe with relevant information about tweets (to
                  further perform text classification).
                  
        - users: Pandas dataframe with users information.
        
        - places (optional): Pandas dataframe about places where users tweeted. If not a 
                  single tweets contains the place where it was tweeted, then
                  this dataframe will not be returned.
    """

    # Not all users enable their location when tweeting, so
    # we need to check if there are available locations for
    # the tweets returned.
    if "places" in json_tweets['includes'].keys():
        
        # If the field exists, create a dataframe with the corresponding data
        places = pd.json_normalize(json_tweets['includes']['places']).rename(columns = {"id":"geo.place_id"})
        
        # Create users dataframe
        users = pd.json_normalize(json_tweets['includes']['users']).rename(columns = {"id":"user_id"})
    
        # Create df with tweet's data
        tweets = pd.json_normalize(json_tweets['data']).rename(columns = {"id":"tweet_id"})
        
        # Get tweet's type
        tweets['type'] = tweets.referenced_tweets.apply(lambda x: x[0]["type"] if type(x) == list else None)
        
        # Drop retweeted tweets
        tweets = tweets[tweets["type"] != "retweeted"].reset_index(drop = True)
        
        # id to string
        tweets["tweet_id"] = tweets["tweet_id"].astype(str)
        
        # List of users in tweets dataframe to only 
        # keep users from tweets dataframe
        user_list = tweets.author_id.unique()
        users = users.loc[users.user_id.isin(user_list)].reset_index(drop = True)
        
        # id to string
        users["user_id"] = users["user_id"].astype(str)
        
        # Drop cols
        tweets = tweets.drop(['referenced_tweets','author_id','geo.place_id'], axis = 1)
        return tweets, users, places
    
    # Only return users and tweets dataframes since any tweet 
    # contained information about the place where it was tweeted.
    else: 
        # Create users dataframe
        users = pd.json_normalize(json_tweets['includes']['users']).rename(columns = {"id":"user_id"})
    
        # Create df with tweet's data
        tweets = pd.json_normalize(json_tweets['data']).rename(columns = {"id":"tweet_id"})
        
        # Get tweet's type
        tweets['type'] = tweets.referenced_tweets.apply(lambda x: x[0]["type"] if type(x) == list else None)
        
        # Drop retweeted tweets
        tweets = tweets[tweets["type"] != "retweeted"].reset_index(drop = True)
        
        # id to string
        tweets["tweet_id"] = tweets["tweet_id"].astype(str)
        
        # List of users in tweets dataframe
        user_list = tweets.author_id.unique()

        # Only keep users from tweets dataframe
        users = users.loc[users.user_id.isin(user_list)].reset_index(drop = True)
        
        # id to string
        users["user_id"] = users["user_id"].astype(str)
        
        # Drop cols
        tweets = tweets.drop(['referenced_tweets','author_id'], axis = 1)
        return tweets, users
    

def more_tweets(max_requests, search_tweet,  main_tweets, main_users, main_places):
    for i in range(1, max_requests):
    
        # Check if there is a next token (another page)
        # that matches the desired query
        if 'next_token' in search_tweet['meta'].keys():
            print(i, search_tweet["meta"]["next_token"])
    
            # Collect data from next token
            new_tweets = search_tweets(query = "Black Widow", next_token = search_tweet['meta']['next_token'])
            search_tweet = new_tweets
    
            # Check if any tweet has enabled the location,
            # so we can create the places dataframe.
            if "places" in search_tweet['includes'].keys():
                tweets, users, places = create_dataframes(search_tweet)
    
                # Append data to main tweets
                main_tweets = main_tweets.append(tweets)
                main_users = main_users.append(users)
                main_places = main_places.append(places)
    
                # Reset index
                main_tweets = main_tweets.reset_index(drop = True)
                main_users = main_users.reset_index(drop = True)
                main_places = main_places.reset_index(drop = True)
    
            # If any tweet has its location enabled, then only
            # create the other two dataframes.
            else: 
                tweets, users = create_dataframes(search_tweet)
    
                # Append data to main tweets
                main_tweets = main_tweets.append(tweets)
                main_users = main_users.append(users)
    
                # Reset index
                main_tweets = main_tweets.reset_index(drop = True)
                main_users = main_users.reset_index(drop = True)
    
        # If there are not more results regarding the
        # requested topic, then just stop requesting 
        # more data.
        else:
            break
        
    if main_places.empty:
        return main_tweets, main_users
    
    else:
        return main_tweets, main_users, main_places
    
    
    
    
    
    
    
