from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from tweets.models import Tweet
from tweets.constants import TWEET_PHOTOS_UPLOAD_LIMIT
from tweets.services import TweetService
from accounts.api.serializers import UserSerializerForTweet
from comments.api.serializers import CommentSerializer
from likes.services import LikeService
from likes.api.serializers import LikeSerializer
from utils.redis_helper import RedisHelper

class TweetSerializer(serializers.ModelSerializer):
    user = UserSerializerForTweet(source = 'cached_user') # who creates this tweet
    comments_count = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    has_liked = serializers.SerializerMethodField()
    photo_urls = serializers.SerializerMethodField()

    class Meta:
        model = Tweet
        fields = (
            'id',
            'user',
            'created_at',
            'content',
            'comments_count',
            'likes_count',
            'has_liked',
            'photo_urls',
        )

    def get_likes_count(self, obj):
        # select count(*) -> redis get
        # N + 1 queries
        # N 如果是 db queries -> 不可以接受
        # N 如果是 redis/memcached queries -> 可以接受
        return RedisHelper.get_count(obj, 'likes_count')
        # return obj.like_set.count()

    def get_comments_count(self, obj):
        # Django定义的反查机制
        return RedisHelper.get_count(obj, 'comments_count')
        # return obj.comment_set.count()

    def get_has_liked(self, obj):
        # current login user can be obtained from self.context['request'].user
        return LikeService.has_liked(self.context['request'].user, obj)

    def get_photo_urls(self, obj):
        photo_urls = []
        for photo in obj.tweetphoto_set.all().order_by('order'):
            photo_urls.append(photo.file.url)
        return photo_urls


class TweetSerializerForCreate(serializers.ModelSerializer):
    content = serializers.CharField(min_length=6, max_length=140)
    files = serializers.ListField(
        child = serializers.FileField(),
        allow_empty = True,
        required = False,
    )

    class Meta:
        model = Tweet
        fields = ('content', 'files')

    def validate(self, data):
        if len(data.get('files', [])) > TWEET_PHOTOS_UPLOAD_LIMIT:
            raise ValidationError({
                'message': f'You can upload {TWEET_PHOTOS_UPLOAD_LIMIT} photos at most'
            })
        return data

    def create(self, validated_data):
        user = self.context['request'].user
        content = validated_data['content']
        tweet = Tweet.objects.create(user=user, content=content)
        if validated_data.get('files'):
            TweetService.create_photo_from_files(
                tweet,
                validated_data['files'],
            )
        return tweet


class TweetSerializerForDetail(TweetSerializer):
    likes = LikeSerializer(source='like_set', many=True)
    comments = CommentSerializer(source='comment_set', many=True)

    class Meta:
        model = Tweet
        fields = (
            'id',
            'user',
            'comments',
            'created_at',
            'content',
            'likes',
            'likes_count',
            'comments_count',
            'has_liked',
            'photo_urls',
        )