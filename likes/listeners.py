from utils.redis_helper import RedisHelper

def incr_likes_count(sender, instance, created, **kwargs):
    from tweets.models import Tweet
    from django.db.models import F

    if not created:
        return

    model_class = instance.content_type.model_class()
    if model_class != Tweet:
        return

    # 不可以使用tweet = instance.content_object; tweet.likes_count += 1; tweet.save()的方式
    # 因为这个操作不是原子操作，必须使用update语句才是原子操作
    # SQL query: UPDATE likes_count = likes_count + 1 from tweets_table where id = <instance.object.id>
    tweet = instance.content_object
    Tweet.objects.filter(id = tweet.id).update(likes_count = F('likes_count') + 1)
    RedisHelper.incr_count(tweet, 'likes_count')

def decr_likes_count(sender, instance, **kwargs):
    from tweets.models import Tweet
    from django.db.models import F

    model_class = instance.content_type.model_class()
    if model_class != Tweet:
        return

    # handle tweet likes cancel
    tweet = instance.content_object
    Tweet.objects.filter(id = tweet.id).update(likes_count = F('likes_count') - 1)
    RedisHelper.decr_count(tweet, 'likes_count')
