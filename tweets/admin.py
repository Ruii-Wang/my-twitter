from django.contrib import admin
# Register your models here.
from tweets.models import Tweet


@admin.register(Tweet)
class TweetAdmin(admin.ModelAdmin):
    # 按照data_hierarchy进行筛选
    data_hierarchy = 'created_at'
    list_display = (
        'created_at',
        'user',
        'content',
    )