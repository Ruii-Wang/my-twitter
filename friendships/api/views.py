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
from utils.paginations import EndlessPagination
from django.utils.decorators import method_decorator
from ratelimit.decorators import ratelimit
from friendships.services import FriendshipService
from gatekeeper.models import GateKeeper
from friendships.hbase_models import HBaseFollower, HBaseFollowing


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
    pagination_class = EndlessPagination

    @action(methods=['GET'], detail=True, permission_classes=[AllowAny])
    @method_decorator(ratelimit(key='user_or_ip', rate='3/s', method='GET', block=True))
    def followers(self, request, pk):
        pk = int(pk)
        paginator = self.paginator
        if GateKeeper.is_switch_on('switch_friendship_to_hbase'):
            page = paginator.paginate_hbase(HBaseFollower, (pk,), request)
        else:
            # GET /api/friendships/1/followers/ 关注了User_id=1的用户
            friendships = Friendship.objects.filter(to_user_id = pk).order_by('-created_at')
            page = paginator.paginate_queryset(friendships)
        serializer = FollowerSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    @action(methods=['GET'], detail=True, permission_classes=[AllowAny])
    @method_decorator(ratelimit(key='user_or_ip', rate='3/s', method='GET', block=True))
    def followings(self, request, pk):
        paginator = self.paginator
        if GateKeeper.is_switch_on('switch_friendship_to_hbase'):
            page = paginator.paginate_hbase(HBaseFollowing, (pk,), request)
        else:
            friendships = Friendship.objects.filter(from_user_id = pk).order_by('-created_at')
            page = paginator.paginate_queryset(friendships)
        serializer = FollowingSerializer(page, many = True, context = {'request': request})
        return paginator.get_paginated_response(serializer.data)

    @action(methods=['POST'], detail=True, permission_classes=[IsAuthenticated])
    @method_decorator(ratelimit(key='user', rate='10/s', method='POST', block=True))
    def follow(self, request, pk):
        # check if user with id=pk exists
        to_follow_user = self.get_object()

        if FriendshipService.has_followed(request.user.id, to_follow_user.id):
            return Response({
                'success': False,
                'message': 'Please check input',
                'errors': [{'pk': f'You has followed user with id={pk}'}],
            }, status=status.HTTP_400_BAD_REQUEST)

        # /api/friendships/<pk>/follow/
        serializer = FriendshipSerializerForCreate(data={
            'from_user_id': request.user.id,
            'to_user_id': to_follow_user.id,
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

        deleted = FriendshipService.unfollow(request.user.id, unfollow_user.id)
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

