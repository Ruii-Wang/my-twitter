from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_delete
from accounts.listeners import profile_changed
from utils.listeners import invalidate_object_cache

class UserProfile(models.Model):
    # OneToOne field会创建一个unique index，确保不会有多个UserProfile指向同一个user
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True)
    # 用Django fileField可以起到imageField同样的效果
    avatar = models.FileField(null=True)
    # 当一个user被创建之后，需要创建一个user profile的object
    # 此用户还来不及去设置nickname等信息，因此设置null=True
    nickname = models.CharField(null=True, max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return '{} {}'.format(self.user, self.nickname)

# 定义一个profile的property方法，植入到User这个model中
# 这样当我们通过user的一个实例化对象访问profile的时候，即user_instance.profile
# 就会在UserProfile中进行get_or_create来获得对应的profile的object
# 这种写法利用了Python的灵活性进行hack的方法，这样会方便我们通过user快速访问到对应的profile信息
def get_profile(user):
    from accounts.services import UserService
    if hasattr(user, '_cached_user_profile'):
        return getattr(user, '_cached_user_profile')
    profile = UserService.get_profile_through_cache(user.id)
    # 使用user对象的属性进行缓存（cache），避免多次调用同一个user的profile时
    # 重复对数据库进行查询。这里用profile这个变量保存了从数据库读取的信息。
    setattr(user, '_cached_user_profile', profile)
    return profile

# 给User model增加一个profile的property方法用于快捷访问
User.profile = property(get_profile)

# hook up listeners to invalidate cache
# user出现删除的时候发的信号
pre_delete.connect(invalidate_object_cache, sender = User)
# user出现修改的时候发的信号
post_save.connect(invalidate_object_cache, sender = User)

pre_delete.connect(profile_changed, sender = UserProfile)
post_save.connect(profile_changed, sender = UserProfile)