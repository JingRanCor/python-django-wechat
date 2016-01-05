#coding:utf8

import time
import datetime
import urllib2
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.core.cache import cache
from urllib import quote
from django.core.urlresolvers import reverse
from django.conf import settings

from utils import upload_file_handler, method_get_api, method_post_api, \
    get_weixin_site_url, get_openid_api_url, get_qrcode_url, download_voice,\
    from_timestamp_get_datetime, post_file_get_media_id, get_absolute_path

from choice_lib import MESSAGE_TAG, MESSAGE_TYPE_LIST, MENU_CHOICES, \
    SUB_MENU_CHOICES, ARTICLE_TAG, CATEGORY_TAG_CHOICES, MESSAGE_STATUS, APPITEM_TAG,\
    MESSAGE_TYPESTR, VERIFY_TYPE

from yimixk_beta.settings import DOMAIN, TOKEN_CACHE_PRE, SITE_USER_INFO_API ,JSAPI_TICKET


#客户注册信息
class UserProfile(models.Model):
    user = models.OneToOneField(User, blank=True, null=True,verbose_name="用户")
    name = models.CharField(
        max_length=128, blank=True, null=True, verbose_name="公司名称")
    licence_no = models.CharField(
        max_length=32, blank=True, verbose_name='营业执照ID')
    link_name = models.CharField(
        max_length=128, blank=True, null=True, verbose_name="联系人姓名")
    phone = models.CharField(
        max_length=48, blank=True, null=True, verbose_name="电话")
    province = models.CharField(
        max_length=96, blank=True, null=True, verbose_name="省份")
    city = models.CharField(
        max_length=128, blank=True, null=True, verbose_name="城市")
    licence_image = models.FileField(
        max_length=128, blank=True, null=True, upload_to=upload_file_handler, verbose_name="营业执照副本 电子版（1M内）")
    head_image = models.FileField(
        max_length=128, blank=True, null=True, upload_to=upload_file_handler, verbose_name="头像")
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    term = models.CharField(
        max_length=128, blank=True, null=True, verbose_name="期限")

    def get_image(self, field):
        if field:
            url_prefix = 'http://%s/media/' % DOMAIN
            return url_prefix + field.name
        else:
            return ''

    def get_head_image_url(self):
        return self.get_image(self.head_image)

    def get_licence_image_url(self):
        return self.get_image(self.licence_image)

    def get_image_show(self, field):
        url = self.get_image(field)
        label = "<img src='%s' style='width:40px;height:40px;'/>" % url
        return label
    def get_head_image_show(self):
        return self.get_image_show(self.head_image)
    def get_licence_image_show(self): 
        return self.get_image_show(self.licence_image)

    get_head_image_show.allow_tags = True
    get_head_image_show.short_description = "头像"
    get_licence_image_show.allow_tags = True
    get_licence_image_show.short_description = "营业执照副本"


class VerifyStatus(models.Model):
    appitem = models.ForeignKey('AppItem', blank=True, null=True, verbose_name='AppItem')
    qualification_verify_type = models.CharField(max_length=128, blank=True, \
        null=True, verbose_name='认证资质状态', choices=VERIFY_TYPE)
    expiredtime = models.DateTimeField(blank=True, null=True, verbose_name='认证过期时间')
    failtime = models.DateTimeField(blank=True, null=True, verbose_name='失败发生时间')
    failreason = models.CharField(max_length=128, blank=True, null=True, verbose_name='认证失败原因')


class AppItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, verbose_name='用户', blank=True, null=True)
    name = models.CharField(max_length=128, blank=True, null=True, verbose_name='名称')
    token = models.CharField(max_length=128,  unique=True, blank=True, null=True, verbose_name='token', db_index=True)
    appid = models.CharField(max_length=128, blank=True, null=True, verbose_name='APPID')
    app_secret = models.CharField(max_length=128, blank=True, null=True, verbose_name='APP_SECRET')
    app_groups = models.ManyToManyField('AppGroup', verbose_name='app内的组') 
    app_users = models.ManyToManyField('AppUser', verbose_name='app内用户') 
    menus = models.ManyToManyField('Menu', verbose_name='一级菜单') 
    messages = models.ManyToManyField('Message', verbose_name='app内的处理事件') 
    categories = models.ManyToManyField('Category', verbose_name='分类') 
    articles = models.ManyToManyField('Article', verbose_name='元素材') 
    is_able = models.BooleanField(default=False, verbose_name="是否可用")
    is_valid = models.BooleanField(default=False, verbose_name="mp是否验证")
    is_get_openid = models.BooleanField(default=False, verbose_name="网站是否可获取用户openid")
    is_receive = models.BooleanField(default=False, verbose_name="网站是否储存用户发的文本信息")
    start_time = models.DateTimeField(blank=True, null=True, verbose_name='开始时间')
    expires_time = models.DateTimeField(blank=True, null=True, verbose_name='到期时间')
    tag = models.CharField(max_length=20, blank=True, null=True, default="fuwu", verbose_name='账号类型', choices=APPITEM_TAG)
    is_ueditor = models.BooleanField(default=False, verbose_name="是否百度编辑器")



    class Meta:
        verbose_name_plural = '微信账号'
        verbose_name = '微信账号'
        ordering = ['-id']

    def __unicode__(self):
        return self.name

    def get_url_by_name(self, name, args=(), query_string={}, openid=False):
        try:
            url = reverse(name, args=args)
            if query_string:
                string = ''
                for key in query_string:
                    string += key+'='+str(query_string[key]) + '&'
                url = url + '?' + string.rstrip('&')
        except:
            url = ''
        url = 'http://'+settings.DOMAIN+url
        if openid:
            return get_openid_api_url(self, url) #得到用户openid
        else:
            return get_weixin_site_url(self, url)

    def get_userprofile_show(self):
        try:
            url = '/admin/yimi_admin/userprofile/?q=%s' % self.user.userprofile.id
        except:
            url = ''
        label = "<a href='%s'>%s</a>" % (url, self.user.username)
        return label
    get_userprofile_show.allow_tags = True
    get_userprofile_show.short_description = "账号"

    #获取全部客服
    def get_getkflist(self):
        url = 'https://api.weixin.qq.com/cgi-bin/customservice/getkflist?access_token=%s' %self.get_token()
        dict_data = method_get_api(url)
        return dict_data    

    #获取客服接待信息
    def get_getonlinekflist(self):
        url = 'https://api.weixin.qq.com/cgi-bin/customservice/getonlinekflist?access_token=%s' %self.get_token()
        dict_data = method_get_api(url)
        return dict_data    

    #添加客服信息
    def kfaccount_add(self, account, nickname, password):
        post_data = {"kf_account" : account,"nickname" : nickname,"password" : password,}
        return self.post_kfaccount(post_data)

    #修改客服信息
    def kfaccount_update(self, account, nickname, password):
        post_data = {"kf_account" : account,"nickname" : nickname,"password" : password,}
        return self.post_kfaccount_update(post_data)


    #发送添加客服信息
    def post_kfaccount(self, post_data):
        '''创建分组'''
        url = 'https://api.weixin.qq.com/customservice/kfaccount/add?access_token=' + self.get_token()
        return_data = method_post_api(url, post_data)
        return self.successed(return_data)    

    def get_kfaccount_uploadheadimg_url(self, kf_account):
        return "http://api.weixin.qq.com/customservice/kfaccount/uploadheadimg?access_token=%s&kf_account=%s" % (self.token,kf_account) 


    def post_kfaccount_update(self, post_data):
        url = 'https://api.weixin.qq.com/customservice/kfaccount/update?access_token=%s&kf_account=%s' % (self.token,kf_account) 
        dict_data = method_post_api(url, post_data)
        return self.successed(dict_data)   


    def kfaccount_del(self, kf_account):
        url = 'https://api.weixin.qq.com/customservice/kfaccount/del?access_token=%s&kf_account=%s' % (self.token,kf_account) 
        dict_data = method_get_api(url)
        return self.successed(dict_data)    

    #获取客服聊天记录
    def getrecord(self,starttime, endtime, openid, pagesize, pageindex):
        url = 'https://api.weixin.qq.com/cgi-bin/customservice/getrecord?access_token=%s' % (self.token,kf_account) 
        dict_data = method_get_api(url)
        return dict_data


    def get_site_url(self):
        '''电商微站首页'''
        url = 'http://%s/appsite/%s/home/' % (DOMAIN, self.token)
        return get_weixin_site_url(self, url)


    def get_kefu_url(self):
        '''微站客服页面'''
        url = 'http://%s/appsite/%s/kefu/' % (DOMAIN, self.token)
        return get_openid_api_url(self, url)

    def get_vote_url(self):
        '''投票'''
        url = reverse('appsite:vote', args=(self.token,))
        url = 'http://%s%s' % (DOMAIN, url)
        return get_openid_api_url(self, url)


    def get_weixin_api(self):
        return 'http://%s/api/%s/' % (DOMAIN, self.token)
    get_weixin_api.short_description = '微信接口'


    def get_token(self):
        token_cache_key = TOKEN_CACHE_PRE+'_'+self.token #对不同的app指定不同的缓存
        token = cache.get(token_cache_key)
        if token:
            return token
        else:
            url = 'https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid=%s&secret=%s' % (self.appid, self.app_secret)
            dict_data = method_get_api(url)
            token = dict_data.get('access_token')
            expires_in = dict_data.get('expires_in')
            if token and expires_in:
                cache.set(token_cache_key, token, expires_in-60)
            return token or ''


    def get_jsapi_ticket(self):
        jsapi_ticket_key = JSAPI_TICKET+'_'+self.token
        jsapi_ticket = cache.get(jsapi_ticket_key)
        if jsapi_ticket:
            return jsapi_ticket
        else:
            url = 'https://api.weixin.qq.com/cgi-bin/ticket/getticket?access_token=%s&type=jsapi' % (self.get_token())
            dict_data = method_get_api(url)
            jsapi_ticket = dict_data.get('ticket')
            expires_in = dict_data.get('expires_in')
            if jsapi_ticket and expires_in:
                cache.set(jsapi_ticket_key, jsapi_ticket, expires_in-60)
            return jsapi_ticket or ''


    def getcallbackip(self):
        '''获取服务器地址'''
        url = 'https://api.weixin.qq.com/cgi-bin/getcallbackip?access_token=%s' %self.get_token()
        dict_data = method_get_api(url)
        ip_list = dict_data.get('ip_list')
        if ip_list:
            return ip_list



    def successed(self, data):
        if data.get('errcode') == 0 and data.get('errmsg') == 'ok':
            return True
        else:
            return False

    def get_user_info(self, openid):
        '''得到用户的详细信息''' 
        url = 'https://api.weixin.qq.com/cgi-bin/user/info?access_token=%s&openid=%s&lang=zh_CN' % (self.get_token(), openid)
        return method_get_api(url)

    def get_all_user(self, next_id=None):
        '''得到所有用户列表''' 
        suffix = ''
        if next_id:
            suffix = '&next_openid=' + next_id
        return method_get_api('https://api.weixin.qq.com/cgi-bin/user/get?access_token='+self.get_token()+suffix)

    def create_menu(self, post_data):
        '''创建菜单，成功返回True'''
        url = 'https://api.weixin.qq.com/cgi-bin/menu/create?access_token='+self.get_token()
        return_data = method_post_api(url, post_data)
        return self.successed(return_data)

    def select_menu(self):
        '''查询menu'''
        url = 'https://api.weixin.qq.com/cgi-bin/menu/get?access_token=' + self.get_token()
        return method_get_api(url)

    def delete_menu(self):
        '''删除menu'''
        url = 'https://api.weixin.qq.com/cgi-bin/menu/delete?access_token='+self.get_token()
        return self.successed(method_get_api(url))

    def send_create_menu(self):
        '''发送创建menu''' 
        menus = self.menus.exclude(name=None).exclude(name="")
        button_data = []
        for menu in menus:
            menu_name = menu.name
            if menu.style == 'click':
                data = {
                    'type': 'click',
                    'name': menu_name,
                    'key': menu.key
                }
            elif menu.style == 'view':
                data = {
                    'type': 'view',
                    'name': menu_name,
                    'url': menu.url,
                }

            #扫码推事件
            elif menu.style == 'scancode_push':
                data['type'] = 'scancode_push'
                data['key'] = 'scancode_push'
                data['sub_button']=[]

            #扫码推事件且弹出“消息接收中”提示框
            elif menu.style == 'scancode_waitmsg':
                data['type'] = 'scancode_waitmsg'
                data['key'] = 'scancode_waitmsg'
                data['sub_button']=[]

            #弹出系统拍照发图
            elif menu.style == 'pic_sysphoto':
                data['type'] = 'pic_sysphoto'
                data['key'] = 'pic_sysphoto'
                data['sub_button']=[]
    
            #弹出拍照或者相册发图
            elif menu.style == 'pic_photo_or_album':
                data['type'] = 'pic_photo_or_album'
                data['key'] = 'pic_photo_or_album'
                data['sub_button']=[]

            #弹出微信相册发图器
            elif menu.style == 'pic_weixin':
                data['type'] = 'pic_weixin'
                data['key'] = 'pic_weixin'
                data['sub_button']=[]

            #弹出地理位置选择器
            elif menu.style == 'location_select':
                data['type'] = 'location_select'
                data['key'] = 'location_select'


            elif menu.style == 'sub_menu':
                sub_data = []
                
                for submenu in menu.submenu_set.exclude(name=None).exclude(name="") :
                    submenu_name = submenu.name
                    if submenu.style == 'click':
                        son_data = {
                            'type': 'click',
                            'name': submenu_name,
                            'key': submenu.key
                        }
                    elif submenu.style == 'view':
                        son_data = {
                            'type': 'view',
                            'name': submenu_name,
                            'url': submenu.url,
                        }
                    sub_data.append(son_data)
                data = {
                    'name': menu_name,
                    'sub_button': sub_data
                }
            button_data.append(data)
        if button_data:
            post_data = {'button':button_data}
            return self.create_menu(post_data)
        else:
            return self.delete_menu()

    def get_user_openid(self, request):
        '''微网站获取用户openid'''
        code = request.GET.get("code", '') 
        if code:
            url = 'https://api.weixin.qq.com/sns/oauth2/access_token?appid=%s&secret=%s&code=%s&grant_type=authorization_code' % (self.appid, self.app_secret, code)
            data = method_get_api(url)
            openid = data.get("openid", '')
            return openid
        else:
            return ''

    def post_process(self, post_data):
        '''发送客服数据过程'''
        url = 'https://api.weixin.qq.com/cgi-bin/message/custom/send?access_token=' + self.get_token()
        return_data = method_post_api(url, post_data)
        return self.successed(return_data)        

    def post_text_to_user(self, openid, content):
        '''发送文本'''
        post_data = {
            "touser": openid,
            "msgtype": "text",
            "text":{
                "content": content
            }
        }
        return self.post_process(post_data)

    def post_pic_to_user(self, openid, media_id):
        '''发送图片'''
        post_data = {
            "touser": openid,
            "msgtype": "image",
            "image":{
                "media_id": media_id
            }
        }
        return self.post_process(post_data)

    def post_voice_to_user(self, openid, media_id):
        '''发送语音'''
        post_data = {
            "touser": openid,
            "msgtype": "voice",
            "voice":{
                "media_id": media_id
            }
        }
        return self.post_process(post_data)


    def post_video_to_user(self, openid, media_id, thumb_media_id, title, description):
        '''发送视频'''
        post_data = {
            "touser": openid,
            "msgtype": "video",
            "video":{
                "media_id": media_id,
                'thumb_media_id':thumb_media_id,
                'title':title,
                'description':description,

            }
        }
        return self.post_process(post_data)


    def post_news_to_user(self, openid, msg):
        '''发送图文(点击跳转到外链)'''
        atoms = msg.get_atoms()
        article_list = []
        for atom in atoms:
            article_list.append(atom.article.convert_to_dict())
        post_data = {
            "touser": openid,
            "msgtype": "news",
            "news":{
                "articles": article_list
            }
        }
        return self.post_process(post_data)

    def post_mpnews_to_user(self, openid, media_id):
        '''发送图文(点击跳转到图文消息页面)'''
        post_data = {
            "touser": openid,
            "msgtype": "mpnews",
            "mpnews":{
                "media_id": media_id,
            }
        }
        return self.post_process(post_data)


    def post_wxcard_to_user(self, openid, card_id, card_ext):
        '''发送卡券'''
        post_data = {
            "touser": openid,
            "msgtype": "wxcard",
            "wxcard":{
                "card_id": card_id,
                'card_ext':card_ext
            }
        }
        return self.post_process(post_data)



    def create_qrcode(self, scene_id, permanent=False, expire_seconds=1800):
        '''创建带参数二维码,永久的要permanent=True'''
        scene_id = str(scene_id)
        url = 'https://api.weixin.qq.com/cgi-bin/qrcode/create?access_token=%s' % self.get_token()
        if permanent:
            post_data = {"action_name": "QR_LIMIT_SCENE", "action_info": {"scene": {"scene_id": scene_id}}}
            expire_seconds = 0
        else:
            post_data = {
                "expire_seconds": expire_seconds, 
                "action_name": "QR_SCENE", 
                "action_info": {"scene": {"scene_id": scene_id}},
            }

        return_data = method_post_api(url, post_data)
        if return_data.get('ticket'):
            return 'https://mp.weixin.qq.com/cgi-bin/showqrcode?ticket='+return_data.get('ticket')

    def get_weixin_upload_api(self, style):
        return "http://file.api.weixin.qq.com/cgi-bin/media/upload?access_token=%s&type=%s" % (self.get_token(), style)

    def get_material_add_news_api(self):
        '''新增永久图文素材接口'''
        return "https://api.weixin.qq.com/cgi-bin/material/add_news?access_token=%s" %self.get_token()

    def get_material_update_news_api(self):
        '''修改永久素材接口'''
        return "https://api.weixin.qq.com/cgi-bin/material/update_news?access_token=%s" %self.get_token()

    def get_material_add_material_api(self, media, type):
        '''新增其他类型素材'''
        post_data = {
            'media':media,
            'type':type,
        }
        url = "https://api.weixin.qq.com/cgi-bin/material/add_material?access_token=%s" % self.get_token()
        return_data = method_post_api(url, post_data)
        return return_data

    def get_material(self, media_id):
        '''获取永久素材'''
        post_data = {
            'media_id':media_id,
        }
        url = "https://api.weixin.qq.com/cgi-bin/material/get_material?access_token=%s" % self.get_token()
        return_data = method_post_api(url, post_data)
        return return_data.get('media_id')

    def get_materialcount(self):
        '''获取素材总数'''
        url = "https://api.weixin.qq.com/cgi-bin/material/get_materialcount?access_token=%s" % self.get_token()
        return method_get_api(url)


    def get_batchget_material(self, type, offset=0, count=20):
        '''获取素材列表'''
        post_data = {
            'type':type,
            'offset':offset,
            'count':count,
        }
        url = "https://api.weixin.qq.com/cgi-bin/material/batchget_material?access_token=%s" %self.get_token()
        return_data = method_post_api(url, post_data)
        return return_data


    def del_material(self, media_id):
        '''删除永久素材'''
        post_data = {
            'media_id':media_id,
        }
        url = "https://api.weixin.qq.com/cgi-bin/material/del_material?access_token=%s" % self.get_token()
        return_data = method_post_api(url, post_data)
        return return_data.get('errcode')


    def get_weixin_upload_thumb_api(self):
        '''上传多媒体接口'''
        return self.get_weixin_upload_api('thumb')
    def get_weixin_qunfa_news_api(self):
        '''上传图文素材到微信'''
        return "https://api.weixin.qq.com/cgi-bin/media/uploadnews?access_token=%s" % self.get_token()
    def get_weixin_all_group_api(self):
        '''微信用户组api'''
        return "https://api.weixin.qq.com/cgi-bin/groups/get?access_token=%s" % self.get_token()
    def get_weixin_all_group(self):
        '''获取微信全部用户组信息'''
        return method_get_api(self.get_weixin_all_group_api())

    def get_weixin_group_qunfa_api(self):
        '''微信按组群发api'''
        return 'https://api.weixin.qq.com/cgi-bin/message/mass/sendall?access_token=%s' % self.get_token()


    def get_weixin_yulan_qunfa_api(self):
        '''微信预览api'''
        return 'https://api.weixin.qq.com/cgi-bin/message/mass/preview?access_token=%s' % self.get_token()


    def get_weixin_uploadimg_api(self):
        '''微信图片上传接口'''
        url = 'https://api.weixin.qq.com/cgi-bin/media/uploadimg?access_token=%s' % self.get_token()
        return url


    def group_successed(self, data):
        group = data.get('group')
        id = group.get('id')
        name = group.get('name')
        if id and name:
            return (id ,name)
        else:
            return (False, False)

    def post_group(self, post_data):
        '''创建分组'''
        url = 'https://api.weixin.qq.com/cgi-bin/groups/create?access_token=' + self.get_token()
        return_data = method_post_api(url, post_data)
        return self.group_successed(return_data)        

    def post_group_name(self, name):
        '''发送分组数据'''
        post_data = {"group":{"name":name}}
        return self.post_group(post_data)

   


    def group_fasong_successed(self, data):
        errcode = data.get('errcode')
        msg_id = data.get('msg_id')
        if errcode==0  and msg_id:
            return msg_id
        else:
            return ''

    def post_group_msg(self, post_data):
        '''发送分组消息'''
        url = 'https://api.weixin.qq.com/cgi-bin/message/mass/sendall?access_token=' + self.get_token()
        return_data = method_post_api(url, post_data)
        return self.group_fasong_successed(return_data)        

    def post_group_shuju(self, group_id, text):
        '''发送文本分组消息'''
        post_data = {
        "filter":{
        "is_to_all":False,
        "group_id":group_id,
        },
        "text":{
        "content":text
        },
        "msgtype":"text"
        }
        return self.post_group_msg(post_data)



    def post_user_group(self, post_data):
        '''移动分组'''
        url = 'https://api.weixin.qq.com/cgi-bin/groups/members/update?access_token=' + self.get_token()
        return_data = method_post_api(url, post_data)
        return self.successed(return_data)        

    def move_user_group(self, openid, to_groupid):
        '''发送移动分组消息'''
        post_data = {"openid":openid,"to_groupid":to_groupid}
        return self.post_user_group(post_data)


    def post_rename_user(self, post_data):
        '''移动分组'''
        url = 'https://api.weixin.qq.com/cgi-bin/user/info/updateremark?access_token=' + self.get_token()
        return_data = method_post_api(url, post_data)
        return self.successed(return_data)        

    def groups_members_batchupdate(self, openid_list, to_groupid):
        '''批量移动用户分组'''
        post_data = {
            'openid_list':openid_list,
            'to_groupid':to_groupid,
        }
        return_data = method_post_api(url, post_data)
        return return_data.get('errcode')


    def rename_user(self, openid, name):
        post_data = {"openid":openid,"remark":name}
        return self.post_rename_user(post_data)

    def search_user_group(self, appuser):
        post_data = {"openid":appuser.openid}
        url = 'https://api.weixin.qq.com/cgi-bin/groups/getid?access_token='+ self.get_token()
        return_data = method_post_api(url, post_data)
        group_id = return_data.get('groupid')
        if group_id:
            return group_id
        else:
            return ''


    def get_niming_user_info_url(self, url):
        url = 'https://open.weixin.qq.com/connect/oauth2/authorize?appid=%s&redirect_uri=%s&response_type=code&scope=snsapi_userinfo&state=STATE#wechat_redirect'\
        %(self.appid, quote(url))
        return url


    def code_to_access_token(self, code):
        url = 'https://api.weixin.qq.com/sns/oauth2/access_token?appid=%s&secret=%s&code=%s&grant_type=authorization_code'%(self.appid,self.app_secret,code)
        return_data = method_get_api(url)
        if return_data.get('access_token'):
            url = 'https://api.weixin.qq.com/sns/userinfo?access_token=%s&openid=%s&lang=zh_CN'%(return_data.get('access_token'), return_data.get('openid'))
            return_data = method_get_api(url)
            return (return_data.get('openid'), return_data.get('nickname'), return_data.get('sex'),return_data.get('province'),\
                return_data.get('city'), return_data.get('country'), return_data.get('headimgurl'))

    def send_template_msg(self, post_data):
        '''发送模板消息'''
        url_api = 'https://api.weixin.qq.com/cgi-bin/message/template/send?access_token=%s' % self.get_token()
        return_data = method_post_api(url_api, post_data)
        return self.successed(return_data)



    def get_batchget_user_info(self, openid_list):
        post_data = {}
        user_list = []
        for openid in openid_list:
            user_list.append({'openid':openid, 'lang':'zh-CN'})
        post_data['user_list'] = user_list
        url = 'https://api.weixin.qq.com/cgi-bin/user/info/batchget?access_token=%s'%(self.get_token())
        return_data = method_post_api(url, post_data)
        return return_data.get('user_info_list')

    def get_current_autoreply_info(self):
        url = 'https://api.weixin.qq.com/cgi-bin/get_current_autoreply_info?access_token=%s' %self.get_token()
        return method_get_api(url)

    def get_current_selfmenu_info(self):
        url = 'https://api.weixin.qq.com/cgi-bin/get_current_selfmenu_info?access_token=%s' %self.get_token()
        return method_get_api(url)



class Receive(models.Model):
    appuser = models.ForeignKey('AppUser', on_delete=models.SET_NULL, blank=True, null=True, verbose_name="提问人")
    appitem = models.ForeignKey('AppItem', on_delete=models.SET_NULL, blank=True, null=True, verbose_name="appitem")
    msg_type = models.CharField(max_length=100, verbose_name='信息类型', default='text')
    text = models.TextField(blank=True, null=True, verbose_name='文本内容')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    class Meta:
        ordering = ['-id']



class Message(models.Model):
    keyword = models.CharField(max_length=100, blank=True, null=True, verbose_name='关键字', db_index=True)
    tag = models.CharField(max_length=100, default='keyword_recontent',verbose_name='标示', choices=MESSAGE_TAG)
    retype = models.CharField(max_length=100, verbose_name='返回信息类型', default='text', choices=MESSAGE_TYPE_LIST)
    text = models.TextField(blank=True, null=True, verbose_name='文本内容')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    status = models.CharField(max_length=100,blank=True, null=True, verbose_name='状态', choices=MESSAGE_STATUS)
    message = models.ForeignKey('Message', related_name="sons",blank=True, null=True, verbose_name="父集")
    is_son = models.BooleanField(default=False, verbose_name="是否子集")
    voice = models.ForeignKey('Voice', on_delete=models.SET_NULL, blank=True, null=True, verbose_name="语音")
    typestr = models.CharField(max_length=20, verbose_name='形成方式', default='create',choices=MESSAGE_TYPESTR)
    

    class Meta:
        ordering = ['-id']

    def __unicode__(self):
        return self.keyword or self.text or self.retype

    def get_create_time(self):
        time_stamp=time.mktime(self.create_time.timetuple())
        return long(time_stamp)

    def get_atoms(self):
        if self.retype == 'news':
            return self.atom_set.all()

    def get_appitem(self):
        return self.appitem_set.first()


class AtoM(models.Model):
    message = models.ForeignKey('Message', on_delete=models.SET_NULL, blank=True, null=True, verbose_name="信息事件")
    article = models.ForeignKey('Article', on_delete=models.SET_NULL, blank=True, null=True, verbose_name="文章")
    sequence = models.IntegerField(
        blank=True, null=True, default=1, verbose_name="排序")
    class Meta:
        ordering = ['-sequence']


class Article(models.Model):
    tag = models.CharField(max_length=100, default='article',verbose_name='图文回复类型', choices=ARTICLE_TAG)
    title = models.CharField(max_length=200, blank=True, null=True, verbose_name='标题')
    author = models.CharField(max_length=100, blank=True, null=True, verbose_name='作者')
    description = models.TextField(blank=True, null=True, verbose_name='描述')
    picurl = models.CharField(max_length=500, blank=True, null=True, verbose_name='图片链接')
    url = models.CharField(max_length=500, blank=True, null=True, verbose_name='原文链接')
    image = models.FileField(
        max_length=128, blank=True, null=True, upload_to=upload_file_handler, verbose_name="本地上传")
    content = models.TextField(blank=True, null=True, verbose_name='正文')
    create_time = models.DateTimeField(auto_now_add=True,  blank=True, null=True,verbose_name='创建时间')
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, blank=True, null=True, verbose_name="分类")
    qrcode = models.CharField(max_length=500, blank=True, null=True, verbose_name='二维码地址')
    navigation = models.ForeignKey('Navigation', blank=True, null=True, verbose_name='导航')
    muban_id = models.IntegerField(blank=True, null=True, verbose_name='模板样式id')

    class Meta:
        verbose_name_plural = '文章'
        verbose_name = '文章'
        ordering = ['-id']

    def __unicode__(self):
        return self.title

    def get_appitem(self):
        return self.appitem_set.first()

    def get_image_url(self):
        if self.picurl:
            return self.picurl
        elif self.image:
            url_prefix = 'http://%s/media/' % DOMAIN
            return url_prefix + self.image.name
        else:
            return ''

    def get_qrcode_url(self):
        '''得到二维码'''
        return get_qrcode_url(self)

    def get_url(self):
        appitem = self.get_appitem()
        if appitem:
            if not self.content and self.url:
                return self.url

            if self.tag == 'article':
                url = 'http://%s/appsite/%s/article-detail/%s/' % (DOMAIN, appitem.token, self.id)
                return get_weixin_site_url(appitem, url)
            else:
                return self.url
        else:
            return ''

    def convert_to_dict(self):
        data = {
            'title': self.title, 
            'description': self.description, 
            'url': self.get_url(),
            'picurl': self.get_image_url(), 
        }
        return data



class Category(models.Model):
    name = models.CharField(max_length=100, blank=True, null=True, verbose_name='名称')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    is_single = models.BooleanField(default=False, verbose_name="内容为一时是否跳转到详情页")
    is_show = models.BooleanField(default=False, verbose_name="是否首页展示")
    image = models.FileField(
        max_length=128, blank=True, null=True, upload_to=upload_file_handler, verbose_name="本地上传")
    sequence = models.IntegerField(
        blank=True, null=True, default=1, verbose_name="排序")
    tag = models.CharField(max_length=100, default='article',verbose_name='类型', choices=CATEGORY_TAG_CHOICES)
    summery = models.CharField(max_length=50, blank=True, null=True, verbose_name='摘要')

    class Meta:
        ordering = ['-sequence',]

    def get_url(self):
        appitem = self.appitem_set.first()
        if appitem:
            if self.tag == 'navigation':
                url = 'http://%s/appsite/%s/navigation-list/%s/' % (DOMAIN, appitem.token, self.id)
                return get_weixin_site_url(appitem, url)

            if not self.is_single:
                url = 'http://%s/appsite/%s/article-list/%s/' % (DOMAIN, appitem.token, self.id)
            else:
                articles = self.article_set.all()
                article_count = articles.count()
                albums = self.album_set.all()
                album_count = albums.count()
                if article_count == 1 and album_count == 0:
                    article = articles[0]
                    url = article.get_url()
                elif article_count == 0 and album_count == 1:
                    album = albums[0]
                    url = album.get_url()
                else:
                    url = 'http://%s/appsite/%s/article-list/%s/' % (DOMAIN, appitem.token, self.id)

            return get_weixin_site_url(appitem, url)
        else:
            return ''

    def get_image_url(self):
        if self.image:
            url_prefix = 'http://%s/media/' % DOMAIN
            return url_prefix + self.image.name
        else:
            url_prefix = 'http://%s/' %DOMAIN
            return url_prefix + 'static/yimi_admin/images/category_default.jpg'

 
class AppUser(models.Model):
    
    openid = models.CharField(max_length=128, blank=True, null=True, verbose_name='用户标识', db_index=True)
    nickname = models.CharField(max_length=128, blank=True, null=True, verbose_name='昵称')
    beizhu = models.CharField(max_length=128, blank=True, null=True, verbose_name='备注')
    sex = models.IntegerField(verbose_name="性别", blank=True, null=True)
    city = models.CharField(max_length=128, blank=True, null=True, verbose_name='城市')
    province = models.CharField(max_length=128, blank=True, null=True, verbose_name='省份')
    country = models.CharField(max_length=128, blank=True, null=True, verbose_name='国家')
    language = models.CharField(max_length=128, blank=True, null=True, verbose_name='用户语言')
    headimgurl = models.CharField(max_length=500, blank=True, null=True, verbose_name='头像')
    event_time = models.DateTimeField(blank=True, null=True,verbose_name='最后一次操作微信时间')
    latitude = models.CharField(max_length=128, blank=True, null=True, verbose_name='纬度')
    longitude = models.CharField(max_length=128, blank=True, null=True, verbose_name='经度')
    is_guanzhu = models.BooleanField(default=True, verbose_name='是否关注,true为关注，false未关注')
    unionid = models.CharField(max_length=128, blank=True, null=True, verbose_name='唯一id')
    
    class Meta:
        ordering=['-event_time']

    def __unicode__(self):
        return self.nickname and self.nickname or self.openid

    def can_send_message(self):
        '''是否可以发送客服信息'''
        day2 = datetime.timedelta(2)
        day2_later = self.event_time + day2

        if day2_later.replace(tzinfo=None) > datetime.datetime.utcnow():
            return True
        else:
            return False

    def set_beizhu(self, appitem , post_data):
        '''设置备注名字'''
        url = 'https://api.weixin.qq.com/cgi-bin/user/info/updateremark?access_token=' + appitem.get_token()
        return_data = method_post_api(url, post_data)
        return self.successed(return_data)   
     

    def get_muban_shuju(self, appitem, remark):
        '''设置备注名'''
        post_data = {
            "openid": self.openid,
            'remark':remark,
                    }
        return self.set_beizhu(appitem, post_data)


    def successed(self, data):
        if data.get('errcode') == 0 and data.get('errmsg') == 'ok':
            return True
        else:
            return False


class AppGroup(models.Model):
    name = models.CharField(max_length=128, blank=True, null=True, verbose_name='组名称')
    app_users = models.ManyToManyField('AppUser', verbose_name='组成员')
    group_id = models.IntegerField(blank=True, null = True,verbose_name ='组id')
    flag = models.BooleanField(default = False, verbose_name='是否在微信分组')

class Menu(models.Model):
    style = models.CharField(max_length=100, default='click',verbose_name='标示', choices=MENU_CHOICES)
    name = models.CharField(max_length=128, blank=True, null=True, verbose_name='名称')
    key = models.CharField(max_length=128, blank=True, null=True, verbose_name='关键字')
    url = models.CharField(max_length=500, blank=True, null=True, verbose_name='跳转链接')
    group_id = models.CharField(max_length=128, blank=True, null=True, verbose_name='用户分组id')
    sex = models.CharField(max_length=128, blank=True, null=True, verbose_name='男（1）女（2），不填则不做匹配')
    country = models.CharField(max_length=128, blank=True, null=True, verbose_name='国家信息')
    province = models.CharField(max_length=128, blank=True, null=True, verbose_name='省份信息')
    city = models.CharField(max_length=128, blank=True, null=True, verbose_name='city')
    client_platform_type = models.CharField(max_length=128, blank=True, null=True, \
        verbose_name='IOS(1), Android(2),Others(3)，不填则不做匹配')


class SubMenu(models.Model):
    menu = models.ForeignKey('Menu', blank=True, null=True, verbose_name="菜单")
    style = models.CharField(max_length=100, default='click',verbose_name='标示', choices=SUB_MENU_CHOICES)
    name = models.CharField(max_length=128, blank=True, null=True, verbose_name='名称')
    key = models.CharField(max_length=128, blank=True, null=True, verbose_name='关键字')
    url = models.CharField(max_length=500, blank=True, null=True, verbose_name='跳转链接')
    group_id = models.CharField(max_length=128, blank=True, null=True, verbose_name='用户分组id')
    sex = models.CharField(max_length=128, blank=True, null=True, verbose_name='男（1）女（2），不填则不做匹配')
    country = models.CharField(max_length=128, blank=True, null=True, verbose_name='国家信息')
    province = models.CharField(max_length=128, blank=True, null=True, verbose_name='省份信息')
    city = models.CharField(max_length=128, blank=True, null=True, verbose_name='city')
    client_platform_type = models.CharField(max_length=128, blank=True, null=True, \
        verbose_name='IOS(1), Android(2),Others(3)，不填则不做匹配')

class Album(models.Model):
    '''相册'''
    appitem = models.ForeignKey('AppItem', on_delete=models.SET_NULL, blank=True, null=True, verbose_name="appitem")
    name = models.CharField(max_length=128, blank=True, null=True, verbose_name='名称')
    image = models.FileField(
        max_length=128, upload_to=upload_file_handler, blank=True, null=True, verbose_name="图片")
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, blank=True, null=True, verbose_name="分类")
    create_time = models.DateTimeField(auto_now_add=True,  blank=True, null=True,verbose_name='创建时间')


    def get_image_url(self):
        if self.image:
            url_prefix = 'http://%s/media/' % DOMAIN
            return url_prefix + self.image.name
        else:
            return '/'

    def get_url(self):
        appitem = self.appitem
        if appitem:
            url = 'http://%s/appsite/%s/album-detail/%s/' % (DOMAIN, appitem.token, self.id)
            return get_weixin_site_url(appitem, url)
        else:
            return ''


class ImageItem(models.Model):
    album = models.ForeignKey('Album', on_delete=models.SET_NULL, blank=True, null=True, verbose_name="相册")
    name = models.CharField(max_length=128, blank=True, null=True, verbose_name='名称')
    image = models.FileField(
        max_length=128, upload_to=upload_file_handler, blank=True, null=True, verbose_name="图片")
    sequence = models.IntegerField(
        blank=True, null=True, default=1, verbose_name="排序")
    information = models.TextField(verbose_name='信息', blank=True, null=True)

    class Meta:
        ordering = ['-sequence']

    def get_image_url(self):
        if self.image:
            url_prefix = 'http://%s/media/' % DOMAIN
            return url_prefix + self.image.name
        else:
            return '/'

class Navigation(models.Model):
    '''导航'''
    appitem = models.ForeignKey('AppItem', on_delete=models.SET_NULL, blank=True, null=True, verbose_name="appitem")
    name = models.CharField(max_length=128, blank=True, null=True, verbose_name='名称')
    addr = models.CharField(max_length=128, blank=True, null=True, verbose_name='地址')
    tel = models.CharField(max_length=28, blank=True, null=True, verbose_name='电话')
    latitude = models.CharField(max_length=128, blank=True, null=True, verbose_name='纬度')
    longitude = models.CharField(max_length=128, blank=True, null=True, verbose_name='经度')

    class Meta:
        ordering = ['-id']

    def get_transfer_url(self):
        url = 'http://%s/appsite/%s/navigation-detail/%s/transfer/' % (DOMAIN, self.appitem.token, self.id)
        return get_openid_api_url(self.appitem, url)
        
    def get_driving_url(self):
        url = 'http://%s/appsite/%s/navigation-detail/%s/driving/' % (DOMAIN, self.appitem.token, self.id)
        return get_openid_api_url(self.appitem, url)



class CarouselFigure(models.Model):
    '''轮播图'''
    appitem = models.ForeignKey('AppItem', on_delete=models.SET_NULL, blank=True, null=True, verbose_name="appitem")
    image = models.FileField(
        max_length=128, upload_to=upload_file_handler, blank=True, null=True, verbose_name="图片")
    url = models.CharField(max_length=512, verbose_name="链接", blank=True, null=True)
    sequence = models.IntegerField(
        blank=True, null=True, default=1, verbose_name="排序")
    name = models.CharField(max_length=128, verbose_name='名称')
    information = models.TextField(verbose_name='信息', blank=True, null=True)
    class Meta:
        verbose_name = '轮播图'
        verbose_name_plural = '轮播图'
        ordering = ['-sequence']

    def __unicode__(self):
        return self.name

    def get_url(self):
        if 'http://' in self.url:
            return self.url
        else:
            return 'http://' + self.url

    def get_image_url(self):
        if self.image:
            url_prefix = 'http://%s/media/' % DOMAIN
            return url_prefix + self.image.name
        else:
            return '/'

COMMAND_TAG = (
    ('voice', '语音上传'),
)
COMMAND_STATUS = (
    ('start', '启动'),
    ('end', '结束'),
)

class Command(models.Model):
    tag = models.CharField(max_length=10, default='voice',verbose_name='命令类型',choices=COMMAND_TAG, db_index=True)
    create_time_str = models.CharField(max_length=64, blank=True, null=True, verbose_name='创建时间')
    status = models.CharField(max_length=10,blank=True, null=True, verbose_name='状态', choices=COMMAND_STATUS)
    openid = models.CharField(max_length=128, blank=True, null=True, verbose_name='用户标识', db_index=True)
    appitem = models.ForeignKey('AppItem', blank=True, null=True, verbose_name="appitem")


class Voice(models.Model):
    openid = models.CharField(max_length=128, blank=True, null=True, verbose_name='用户标识', db_index=True)
    create_time = models.DateTimeField(auto_now_add=True,  blank=True, null=True,verbose_name='创建时间')
    update_time_str = models.CharField(max_length=64, blank=True, null=True, verbose_name='创建时间戳')
    media_id = models.CharField(max_length=128, blank=True, null=True, verbose_name='media_id')
    file_url = models.CharField(max_length=200, verbose_name="链接", blank=True, null=True)
    appitem = models.ForeignKey('AppItem', blank=True, null=True, verbose_name="appitem")
    is_done = models.BooleanField(default=False, verbose_name="是否已下载")

    class Meta:
        ordering = ['-id']

    def get_nickname(self):
        appuser = self.appitem.app_users.filter(openid=self.openid).first()
        if appuser:
            return appuser.nickname
        else:
            return ''

    def get_update_time(self):
        return from_timestamp_get_datetime(self.update_time_str)

    def get_status(self):
        if self.is_done:
            return True
        else:
            delta = datetime.datetime.utcnow() - self.get_update_time()
            if delta.days < 3:
                return True
        return False

    def get_status_icon(self):
        if self.get_status():
            return '/static/admin/img/icon-yes.gif'
        else:
            return '/static/admin/img/icon-no.gif'

    def get_is_done_icon(self):
        if self.is_done:
            return '/static/admin/img/icon-yes.gif'
        else:
            return '/static/admin/img/icon-no.gif'

    def get_file_url(self, down=False):
        if not self.is_done and down:
            url = 'http://file.api.weixin.qq.com/cgi-bin/media/get?access_token=%s&media_id=%s' % (self.appitem.get_token(), self.media_id)
            file_url = download_voice(url)
            if file_url:
                self.file_url = file_url
                self.is_done = True
                self.save()
                return file_url
        else:
            return  self.file_url

    def get_media_id(self):
        delta = datetime.datetime.utcnow() - self.get_update_time()
        if delta.days >= 3:
            url = self.appitem.get_weixin_upload_api('voice')
            if self.is_done and self.file_url:
                filename = get_absolute_path(self.file_url)
                dict_data = post_file_get_media_id(filename, url)
                if dict_data:
                    self.media_id = dict_data.get('media_id')
                    self.update_time_str = dict_data.get('created_at')
                    self.save()
        return self.media_id



#----------微站首页设置

class WeiSite(models.Model):
    appitem = models.ForeignKey('AppItem', on_delete=models.SET_NULL, blank=True, null=True, verbose_name="appitem")
    image = models.FileField(
        max_length=128, upload_to=upload_file_handler, blank=True, null=True, verbose_name="图片")
    image_url = models.CharField(max_length=256, verbose_name="链接", blank=True, null=True)

    article_header = models.TextField(blank=True, null=True, verbose_name='文章开始')
    article_mark = models.TextField(blank=True, null=True, verbose_name='文章末尾')
    shouye_id = models.IntegerField(default=1,blank=True, null= True, verbose_name='首页模板id')
    liebiao_id = models.IntegerField(default=1, blank=True, null=True, verbose_name='列表页模板id')
    xiangqingye_id = models.IntegerField(default=1, blank=True, null=True, verbose_name='详情页模板id')
    def get_image_url(self):
        if self.image:
            url_prefix = 'http://%s/media/' % DOMAIN
            return url_prefix + self.image.name
        else:
            return '/'


class VoteOption(models.Model):
    slug = models.CharField(max_length=3, verbose_name="标示符", blank=True, null=True)
    title = models.CharField(max_length=512, verbose_name="投票项", blank=True, null=True)
    appitem = models.ForeignKey('AppItem', on_delete=models.SET_NULL, blank=True, null=True, verbose_name="appitem")
    is_show = models.BooleanField(default=True, verbose_name="是否可用")


class Vote(models.Model):
    appitem = models.ForeignKey('AppItem', on_delete=models.SET_NULL, blank=True, null=True, verbose_name="appitem")
    appuser = models.ForeignKey('AppUser', on_delete=models.SET_NULL, blank=True, null=True, verbose_name="投票人")
    options = models.ManyToManyField('VoteOption', blank=True, null=True, verbose_name="选项")
    content = models.TextField(blank=True, null=True, verbose_name='内容')
    create_time = models.DateTimeField(auto_now_add=True,  blank=True, null=True,verbose_name='创建时间')

    class Meta:
        ordering = ['-id']

# def new_appitem_handler(sender, instance, created, **kwargs):
#     '''注：在admin后台操作无效，在代码中创建appitem。新建appitem时自动创建关注回复和无匹配回复'''
#     if created:
#         if not instance.messages.filter(tag='keyword_default_recontent').exists():
#             instance.messages.create(tag='keyword_default_recontent')
#         if not instance.messages.filter(tag='subscribe').exists():
#             instance.messages.create(tag='subscribe')


# post_save.connect(new_appitem_handler,sender=AppItem)


class Custom_server(models.Model):
    appitem = models.ForeignKey('AppItem', on_delete=models.SET_NULL, blank=True, null=True, verbose_name="appitem")
    kf_account = models.CharField(max_length=32, blank=True, null=True, verbose_name='客服账号,最大为10汉字')
    kf_nick = models.CharField(max_length=32,blank=True, null=True, verbose_name='客服昵称，最大为12汉字')
    kf_id = models.CharField(max_length=16, blank=True, null=True, verbose_name='客服id')
    kf_headimgurl = models.CharField(max_length=128, blank=True, null=True, verbose_name='客服头像')
    kf_password = models.CharField(max_length=16, blank=True, null=True, verbose_name='客服密码最大12')
    message = models.ForeignKey(Message, blank=True, null=True, verbose_name='消息')
    def get_kf_headimgurl(self):
        if self.kf_headimgurl:
            url_prefix = 'http://%s/media/' % DOMAIN
            return url_prefix + self.kf_headimgurl.name
        else:
            return ''