from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from tweets.api.serializers import (
    TweetSerializer,
    TweetSerializerForCreate,
    TweetSerializerForDetail,
)
from tweets.models import Tweet
from newsfeeds.services import NewsFeedService
from utils.decorators import required_params
from utils.paginations import EndlessPagination
from tweets.services import TweetService


class TweetViewSet(viewsets.GenericViewSet):
    serializer_class = TweetSerializerForCreate
    queryset = Tweet.objects.all()
    pagination_class = EndlessPagination

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]

    def retrieve(self, request, *args, **kwargs):
        # <Homework 1> 通过某个query参数with_all_comments来决定是否要带上所有comments
        # <Homework 2> 通过某个query参数with_preview_comments来决定是否需要带上前三条comments
        tweet = self.get_object()
        serializer = TweetSerializerForDetail(
            tweet,
            context={'request': request},
        )
        return Response(serializer.data)

    @required_params(params=['user_id'])
    def list(self, request, *args, **kwargs):
        tweets = TweetService.get_cached_tweets(user_id = request.query_params['user_id'])
        tweets = self.paginate_queryset(tweets)
        serializer = TweetSerializer(
            tweets,
            context = {'request': request},
            many=True,
        ) # 传进去是是QuerySet，返回的是一个list of dict
        # 一般来说，json格式的response默认都要用的hash格式
        # 而不能用list的格式（约定俗成）
        # 所以在最外面需要套上一个dict
        return self.get_paginated_response(serializer.data)

    def create(self, request):
        serializer = TweetSerializerForCreate(
            data = request.data,
            context = {'request': request},
        )
        if not serializer.is_valid():
            return Response({
                "success": False,
                "message": "Please check input.",
                "errors": serializer.errors,
            }, status=400)
        # save will trigger create method in TweetSerializerForCreate
        tweet = serializer.save()
        # fanout这个方法需要较复杂的逻辑实现，而在view这一层中尽量做一些简单的显示视图的功能
        # 对于复杂的逻辑实现放到service这一层中去提供
        NewsFeedService.fanout_to_followers(tweet)
        return Response(
            TweetSerializer(tweet, context={'request': request}).data,
            status=201,
        )