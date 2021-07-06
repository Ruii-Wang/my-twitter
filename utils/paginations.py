from rest_framework.pagination import BasePagination
from rest_framework.response import Response
from dateutil import parser
from django.conf import settings

class EndlessPagination(BasePagination):
    page_size = 20 if not settings.TESTING else 10

    def __init__(self):
        super(EndlessPagination, self).__init__()
        self.has_next_page = False

    def to_html(self):
        pass

    def paginate_ordered_list(self, reverse_ordered_list, request):
        if 'created_at__gt' in request.query_params:
            created_at__gt = parser.isoparse(request.query_params['created_at__gt'])
            objects = []
            for obj in reverse_ordered_list:
                if obj.created_at > created_at__gt:
                    objects.append(obj)
                else:
                    break
            self.has_next_page = False
            return objects

        index = 0
        if 'created_at__lt' in request.query_params:
            created_at__lt = parser.isoparse(request.query_params['created_at__lt'])
            for index, obj in enumerate(reverse_ordered_list):
                if obj.created_at < created_at__lt:
                    break
            else:
                # 没有找到任何满足条件的objects，返回空数组
                # 注意这个else对应的是for，参见python的for else用法
                reverse_ordered_list = []
        self.has_next_page = len(reverse_ordered_list) > index + self.page_size
        return reverse_ordered_list[index: index + self.page_size]

    def paginate_queryset(self, queryset, request, view=None):
        if 'created_at__gt' in request.query_params:
            created_at__gt = request.query_params['created_at__gt']
            queryset = queryset.filter(created_at__gt = created_at__gt)
            self.has_next_page = False
            return queryset.order_by('-created_at')

        if 'created_at__lt' in request.query_params:
            created_at__lt = request.query_params['created_at__lt']
            queryset = queryset.filter(created_at__lt = created_at__lt)

        # 多取一个数据，方便判断是否有下一页。小技巧。
        queryset = queryset.order_by('-created_at')[:self.page_size + 1]
        self.has_next_page = len(queryset) > self.page_size
        return queryset[:self.page_size]

    def paginate_cached_list(self, cached_list, request):
        paginated_list = self.paginate_ordered_list(cached_list, request)
        # 如果是上翻页，paginated_list 里面是所有最新的数据，直接返回
        if 'created_at__gt' in request.query_params:
            return paginated_list

        # 如果还有下一页，说明cached_list里的数据还没有取完，也直接返回
        if self.has_next_page:
            return paginated_list

        # 如果cached_list的长度不是最大限制，说明cached_list里已经是所有数据了
        if len(cached_list) < settings.REDIS_LIST_LENGTH_LIMIT:
            return paginated_list

        # 如果进入这里，说明可能存在在数据库里没有load在cache里的数据，需要直接去数据库查询
        return None

    def get_paginated_response(self, data):
        return Response({
            'has_next_page': self.has_next_page,
            'results': data,
        })