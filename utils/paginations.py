from rest_framework.pagination import BasePagination
from rest_framework.response import Response
from dateutil import parser
from django.conf import settings
from utils.time_constants import MAX_TIMESTAMP

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

    def paginate_hbase(self, hb_model, row_key_prefix, request):
        if 'created_at__gt' in request.query_params:
            # created_at__gt 用于下拉刷新的时候加载最新的内容进来
            # 为了简便起见，下拉刷新不做翻页机制，直接加载所有更新的数据
            # 因为如果数据很久没有更新的话，不会采用下拉的刷新的方式进行更新，而是重新加载最新的数据
            created_at__gt = request.query_params['created_at__gt']
            start = (*row_key_prefix, created_at__gt)
            stop = (*row_key_prefix, MAX_TIMESTAMP)
            # stop 不能直接给 None。因为字符串排序如下，如果给 None，则找不到最新的内容。需要找一个最大的
            # 时间戳。这里没有 reverse，需要保证 stop 的时间戳比 start 的都要大。因此选一个MAX_TIMESTAMP
            # (1, None) -> '1'
            # (1, 123123) -> '1:123123'
            # (1, 123124) -> '1:123124'
            # (1, .......)
            objects = hb_model.filter(start = start, stop = stop)
            if len(objects) and objects[0].created_at == int(created_at__gt):
                objects = objects[:0:-1]
            else:
                objects = objects[::-1]
            self.has_next_page = False
            return objects

        if 'created_at__lt' in request.query_params:
            # created_at__lt 用于向上滚屏（往下翻页）的时候加载下一页（更旧）的数据
            # 寻找 timestamp < created_at__lt 的 objects 里按照 timestamp 倒序的前 page_size + 1 个 objects
            # 比如目前的 timestamp 列表是 [1,2,3,4,5,6,7,8,9,10]如果 created_at__lt=5, page_size = 2
            # 则应该返回 [4,3,2]，多返回一个 object 的原因是为了判断是否还有下一页从而减少一次空加载。
            # 由于 hbase 只支持 <= 的查询而不支持 <，因此我们还需要再多取一个 item 保证 < 的 item 有 page_size + 1 个
            created_at__lt = request.query_params['created_at__lt']
            start = (*row_key_prefix, created_at__lt)
            stop = (*row_key_prefix, None)
            # hbase中的数据可能如下。如果直接设置 stop = None，则会将 1 的数据也添加到结果中。但是 1 的数据并不需要
            # 我们只需要 2 的数据。所以 stop 也需要添加一个 row_key_prefix 作为截止条件。这里有 reverse，因此 start
            # 的时间戳要大于 stop 的。
            # (1, ts1)
            # (1, ts2)
            # (1, ts3)
            # (1, ts4)
            # (2, ts1) ^
            # (2, ts2) ^
            # (2, ts3) -> start
            # (2, ts4)
            objects = hb_model.filter(start = start, stop = stop, limit = self.page_size + 2, reverse = True)
            if len(objects) and objects[0].created_at == int(created_at__lt):
                objects = objects[1:]
            if len(objects) > self.page_size:
                self.has_next_page = True
                objects = objects[:-1]
            else:
                self.has_next_page = False
            return objects

        # 没有任何参数，默认加载最新一页
        prefix = (*row_key_prefix, None)
        objects = hb_model.filter(prefix = prefix, limit = self.page_size + 1, reverse = True)
        if len(objects) > self.page_size:
            self.has_next_page = True
            objects = objects[:-1]
        else:
            self.has_next_page = False
        return objects

