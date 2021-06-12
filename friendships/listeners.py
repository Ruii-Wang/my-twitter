def invalidate_following_cache(sender, instance, **kwargs):
    # 如果这个import放在函数外面，会出现循环引用的问题
    from friendships.services import FriendshipService
    FriendshipService.invalidate_following_cache(instance.from_user_id)