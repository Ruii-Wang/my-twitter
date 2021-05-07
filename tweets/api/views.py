from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from tweets.api.serializers import TweetSerializer, TweetSerializerForCreate
from tweets.models import Tweet
from newsfeeds.services import NewsFeedService


class TweetViewSet(viewsets.GenericViewSet):
    serializer_class = TweetSerializerForCreate

    def get_permissions(self):
        if self.action == 'list':
            return [AllowAny()]
        return [IsAuthenticated()]

    def list(self, request):
        if 'user_id' not in request.query_params:
            return Response('missing user_id', status=400)
        # 这句SQL查询会用到user和created_at的联合索引
        user_id = request.query_params['user_id']
        tweets = Tweet.objects.filter(user_id = user_id).order_by('-created_at')
        serializer = TweetSerializer(tweets, many=True) # 传进去是是QuerySet，返回的是一个list of dict
        # 一般来说，json格式的response默认都要用的hash格式
        # 而不能用list的格式（约定俗成）
        # 所以在最外面需要套上一个dict
        return Response({'tweets': serializer.data})

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
        return Response(TweetSerializer(tweet).data, status=201)