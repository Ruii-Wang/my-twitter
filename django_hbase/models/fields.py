class HBaseField:
    field_type = None

    def __init__(self, reverse = False, column_family = None):
        self.reverse = reverse
        self.column_family = column_family
        # 增加 is_required 属性，默认为true和default属性，默认为None
        # 并在HBaseModel中做相应的处理，抛出相应的异常信息

class IntegerField(HBaseField):
    field_type = 'int'


class TimestampField(HBaseField):
    field_type = 'timestamp'
