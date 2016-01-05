#coding:utf8
from django.contrib import admin

from models import *

class AppItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_userprofile_show', 'get_weixin_api', 'is_able', 'is_valid', \
        'is_get_openid', 'start_time', 'expires_time', 
    ]
    raw_id_fields = ('user','app_groups', 'app_users', 'menus', 'messages', 'categories', 'articles')

    fieldsets = (
        ('1.基本信息',
            {'fields':('user', 'name', 'token', 'appid', 'app_secret', )}
        ),
        ('2.运营内容',
            {'fields':('is_able', 'is_valid', 'is_get_openid', 'is_receive', 'is_ueditor','messages', 'tag', 'start_time', 'expires_time')}
        ),
    )


class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'get_url']

class MessageAdmin(admin.ModelAdmin):
    list_display = ['get_tag_display', 'retype', 'keyword', 'get_appitem']

class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'name', 'licence_no', 'link_name', 'phone', 'province', 'city', \
        'get_head_image_show', 'get_licence_image_show', 'term'
    ]
    search_fields = ['id']
admin.site.register(Message, MessageAdmin)
admin.site.register(Article, ArticleAdmin)
admin.site.register(AppUser)
admin.site.register(AppGroup)
admin.site.register(AppItem, AppItemAdmin)
admin.site.register(Menu)
admin.site.register(SubMenu)
admin.site.register(Category)
admin.site.register(AtoM)
admin.site.register(Receive)
admin.site.register(Command)
admin.site.register(Voice) 
admin.site.register(VerifyStatus) 
admin.site.register(UserProfile, UserProfileAdmin)
