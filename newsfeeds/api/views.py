from rest_framework import viewsets, status
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from newsfeeds.api.serializers import NewsFeedSerializer
from newsfeeds.models import NewsFeed
from utils.paginations import EndlessPagination


class NewsFeedViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = EndlessPagination

    # def get_queryset(self):
    #     # 自定义 queryset， 因为newsfeed的查看是有权限的
    #     # 只能看user=当前登录用户的newsfeed
    #     # 也可以是 self.request.user.newsfeed_set.all()
    #     # 但是一般最好还是按照 NewsFeed.objects.filter 的方式写，更直观
    #     return NewsFeed.objects.filter(user=self.request.user)

    def list(self, request):
        queryset = NewsFeed.objects.filter(user = self.request.user)
        page = self.paginate_queryset(queryset)
        serializer = NewsFeedSerializer(
            page,
            context = {'request': request},
            many=True,
        )
        return self.get_paginated_response(serializer.data)