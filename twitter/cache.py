# memcached
# following的数量不会很大。相反follower的数量可能会巨大，而且变动很快，不适合cache
FOLLOWINGS_PATTERN = 'followings:{user_id}'
USER_PROFILE_PATTERN = 'userprofile:{user_id}'

# redis
USER_TWEETS_PATTERN = 'user_tweets:{user_id}'
USER_NEWSFEEDS_PATTERN = 'user_newsfeeds:{user_id}'