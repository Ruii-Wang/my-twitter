from rest_framework import serializers
from tweets.models import Tweet
from accounts.api.serializers import UserSerializerForTweet
from comments.api.serializers import CommentSerializer
from likes.services import LikeService
from likes.api.serializers import LikeSerializer

class TweetSerializer(serializers.ModelSerializer):
    user = UserSerializerForTweet() # who creates this tweet
    comments_count = serializers.SerializerMethodField()
    likes_count = serializers.SerializerMethodField()
    has_liked = serializers.SerializerMethodField()

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
        )

    def get_likes_count(self, obj):
        # 我们自己定义的属性
        return obj.like_set.count()

    def get_comments_count(self, obj):
        # Django定义的反查机制
        return obj.comment_set.count()

    def get_has_liked(self, obj):
        # current login user can be obtained from self.context['request'].user
        return LikeService.has_liked(self.context['request'].user, obj)


class TweetSerializerForCreate(serializers.ModelSerializer):
    content = serializers.CharField(min_length=6, max_length=140)

    class Meta:
        model = Tweet
        fields = ('content',)

    def create(self, validated_data):
        user = self.context['request'].user
        content = validated_data['content']
        tweet = Tweet.objects.create(user=user, content=content)
        return tweet


class TweetSerializerForDetail(TweetSerializer):
    user = UserSerializerForTweet()
    # <Homework> 使用serializers.SerializerMethodField的方式实现comments
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
        )