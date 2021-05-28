from django.db import models
from django.contrib.auth.models import User

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
    if hasattr(user, '_cached_user_profile'):
        return getattr(user, '_cached_user_profile')
    profile, _ = UserProfile.objects.get_or_create(user = user)
    # 使用user对象的属性进行缓存（cache），避免多次调用同一个user的profile时
    # 重复对数据库进行查询。这里用profile这个变量保存了从数据库读取的信息。
    setattr(user, '_cached_user_profile', profile)
    return profile

# 给User model增加一个profile的property方法用于快捷访问
User.profile = property(get_profile)