from django.contrib.auth.models import User
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from friendships.models import Friendship
from friendships.api.serializers import (
    FollowingSerializer,
    FollowerSerializer,
    FriendshipSerializerForCreate,
)
from friendships.api.paginations import FriendshipPagination
from django.utils.decorators import method_decorator
from ratelimit.decorators import ratelimit


class FriendshipViewSet(viewsets.GenericViewSet):
    # 希望POST /api/friendship/1/follow 是去 follow user_id=1 的用户
    # 因此这里的 queryset 需要时 User.objects.all()
    # 如果是 Friendship.objects.all() 会出现 404 Not Found
    # 因为 detail=True 的actions会默认先去调用 get_object() 也就是
    # queryset.filter(pk=1) 查询一下这个object在不在
    # 要follow的用户必须提前存在
    queryset = User.objects.all()
    serializer_class = FriendshipSerializerForCreate
    # 一般来说不同的views需要的pagination规则是不同的，因此一般都需要自定义
    pagination_class = FriendshipPagination

    @action(methods=['GET'], detail=True, permission_classes=[AllowAny])
    @method_decorator(ratelimit(key='user_or_ip', rate='3/s', method='GET', block=True))
    def followers(self, request, pk):
        # GET /api/friendships/1/followers/ 关注了User_id=1的用户
        friendships = Friendship.objects.filter(to_user_id=pk).order_by('-created_at')
        page = self.paginate_queryset(friendships)
        serializer = FollowerSerializer(page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(methods=['GET'], detail=True, permission_classes=[AllowAny])
    @method_decorator(ratelimit(key='user_or_ip', rate='3/s', method='GET', block=True))
    def followings(self, request, pk):
        friendships = Friendship.objects.filter(from_user_id=pk).order_by('-created_at')
        page = self.paginate_queryset(friendships)
        serializer = FollowingSerializer(page, many=True, context={'request': request})
        return self.get_paginated_response(serializer.data)

    @action(methods=['POST'], detail=True, permission_classes=[IsAuthenticated])
    @method_decorator(ratelimit(key='user', rate='10/s', method='POST', block=True))
    def follow(self, request, pk):
        # check if user with id=pk exists
        self.get_object()

        # /api/friendships/<pk>/follow/
        serializer = FriendshipSerializerForCreate(data={
            'from_user_id': request.user.id,
            'to_user_id': pk,
        })
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Please check input',
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)
        instance = serializer.save()
        return Response(
            FollowingSerializer(instance, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )

    @action(methods=['POST'], detail=True, permission_classes=[IsAuthenticated])
    @method_decorator(ratelimit(key='user', rate='10/s', method='POST', block=True))
    def unfollow(self, request, pk):
        # raise 404 if no user with id=pk
        unfollow_user = self.get_object()

        # 注意pk的类型是str，所以需要类型转换
        if request.user.id == unfollow_user.id:
            return Response({
                'success': False,
                'message': 'You cannot unfollow yourself'
            }, status=status.HTTP_400_BAD_REQUEST)
        # https://docs.djangoproject.com/en/3.1/ref/models/querysets/#delete
        # Queryset 的 delete 操作返回两个值，一个是删了多少数据，一个是具体每种类型删了多少
        # 为什么会出现多种类型数据的删除？因为可能因为 foreign key 设置了 cascade 出现级联
        # 删除，也就是比如 A model 的某个属性是 B model 的 foreign key，并且设置了
        # on_delete=models.CASCADE, 那么当 B 的某个数据被删除的时候，A 中的关联也会被删除。
        # 所以 CASCADE 是很危险的，我们一般最好不要用，而是用 on_delete=models.SET_NULL
        # 取而代之，这样至少可以避免误删除操作带来的多米诺效应。
        deleted, _ = Friendship.objects.filter(
            from_user=request.user,
            to_user=pk,
        ).delete()
        return Response({
            'success': True,
            'deleted': deleted,
        })

    # MySQL工程应用需要注意的
    # 1. 不要用JOIN，本质上JOIN将操作编程O(n^2)，量级很大，效率很低，因此在web实时响应请求的时候不要用
    # 2. 不要用CASCADE
    # 3. DROP FOREIGN KEY CONSTRAINT


    def list(self, request):
        return Response({'message': 'this is friendships home page'})

