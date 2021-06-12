from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class FriendshipPagination(PageNumberPagination):
    # 默认的page_size，也就是page没有在url参数里面的时候
    page_size = 20
    # 默认的page_size_query_param是None表示不允许客户端指定每一页的大小
    # 如果加上这个配置，就表示客户端可以通过size = 10来制定一个特定大小的用于不同的场景
    # 如手机和web端访问同一个api但是需要的size大小不同
    page_size_query_param = 'size'
    # 允许客户端指定的最大page_size是多少
    max_page_size = 20

    def get_paginated_response(self, data):
        # 完成翻页之后返回给前端的数据需要进行包装
        # 具体定义哪些key需要与前端商量决定
        return Response({
            'total_results': self.page.paginator.count,
            'total_pages': self.page.paginator.num_pages,
            'page_number': self.page.number,
            'has_next_page': self.page.has_next(),
            'results': data,
        })