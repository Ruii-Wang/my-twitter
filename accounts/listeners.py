def user_changed(sender, instance, **kwargs):
    # import写在函数内避免循环调用
    from accounts.services import UserService
    UserService.invalidate_user(instance.id)

def profile_changed(sender, instance, **kwargs):
    from accounts.services import UserService
    UserService.invalidate_profile(instance.user_id)