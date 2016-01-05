#!/usr/bin/env python
#coding:utf8
import re
import hashlib
import datetime
import pytz
import time

from django.shortcuts import render_to_response
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, Http404

from conf import COMMAND_INFO
from models import AppItem, AppUser, Message

from utils import *

REPLY_DATA = '''
    <xml>
    <ToUserName><![CDATA[%s]]></ToUserName>
    <FromUserName><![CDATA[%s]]></FromUserName>
    <CreateTime>%s</CreateTime>
    <MsgType><![CDATA[%s]]></MsgType>
    %s
    </xml>
'''

TYPE_CONTENT_DICT = {
    'text': '<Content><![CDATA[%s]]></Content>',
    'news': '<ArticleCount>%s</ArticleCount><Articles>%s</Articles>',
    'voice': '<Voice><MediaId><![CDATA[%s]]></MediaId></Voice>',
}

ARTICLES = '''
    <item>
    <Title><![CDATA[%s]]></Title> 
    <Description><![CDATA[%s]]></Description>
    <PicUrl><![CDATA[%s]]></PicUrl>
    <Url><![CDATA[%s]]></Url>
    </item>
'''


KF_ZD_DATA = '''
    <xml>
    <ToUserName><![CDATA[%s]]></ToUserName>
    <FromUserName><![CDATA[%s]]></FromUserName>
    <CreateTime>%s</CreateTime>
    <MsgType><![CDATA[%s]]></MsgType>
    <TransInfo>
        <KfAccount>![CDATA[%s]]</KfAccount>
    </TransInfo>
    </xml>
'''

def gen_xml(instance):
    message = instance.message
    #客服
    if message.tag in ['kefu_gn',]:
        #yu 指定客服
        custom_server = message.custom_server_set.filter().first()
        kf_account = custom_server.kf_account
        if kf_account :
            params = (
                instance.from_user,
                instance.to_user,
                instance.message.get_create_time(),
                'transfer_customer_service',
                kf_account,
            )
            return KF_ZD_DATA % params
        else:
            params = (
                instance.from_user,
                instance.to_user,
                instance.message.get_create_time(),
                'transfer_customer_service',
                ''
            )
            return REPLY_DATA % params
    retype = message.retype

    type_content = TYPE_CONTENT_DICT.get(retype, '')
    #文本回复
    if retype == 'text':
        content = type_content % message.text
    #图文回复
    elif retype == 'news':
        atoms = message.atom_set.all()
        if not atoms:
            return ''
        articles_str = ''
        for atom in atoms:
            article = atom.article
            art_param = (
                article.title, 
                article.description, 
                article.get_image_url(), 
                article.get_url(),
            )
            articles_str += ARTICLES % art_param
        content = type_content % (atoms.count(), articles_str)
    #语音回复
    elif retype == 'voice':
        voice = message.voice
        if voice:
            content = type_content % voice.get_media_id()
        else:
            content = ''

    params = (
        instance.from_user,
        instance.to_user,
        instance.message.get_create_time(),
        retype,
        content,
    )
    return REPLY_DATA % params

class TempMessage():
    '''非数据库返回对象'''
    text = ''
    retype = ''
    create_time = datetime.datetime.utcnow()
    def get_create_time(self):
        time_stamp=time.mktime(self.create_time.timetuple())
        return long(time_stamp)


class ParseMessage():
    touser_re = r'<ToUserName><!\[CDATA\[(.+)\]\]></ToUserName>'
    fromuser_re = r'<FromUserName><!\[CDATA\[(.+)\]\]></FromUserName>'
    createtime_re = r'<CreateTime>(\d+)</CreateTime>'
    content_re = r'<Content><!\[CDATA\[(.+)\]\]></Content>'
    msgtype_re = r'<MsgType><!\[CDATA\[(.+)\]\]></MsgType>' 
    picurl_re = r'<PicUrl><!\[CDATA\[(.+)\]\]></PicUrl>'
    mediaid_re = r'<MediaId><!\[CDATA\[(.+)\]\]></MediaId>'
    msgid_re = r'<MsgId>(\d+)</MsgId>'        
    event_re = r'<Event><!\[CDATA\[(.+)\]\]></Event>'    
    eventkey_re = r'<EventKey><!\[CDATA\[(.+)\]\]></EventKey>'    
    latitude_re = r'<Latitude>(.+)</Latitude>'
    longitude_re = r'<Longitude>(.+)</Longitude>'
    precision = r'<Precision>(.+)</Precision>'
    expiredtime = r'<ExpiredTime>(\d+)</ExpiredTime>'
    failtime = r'<FailTime>(\d+)</FailTime>'
    failreason = r'<FailReason><!\[CDATA\[(.+)\]\]></FailReason>'

    message = None
    user = None
    event = ''
    now_time = ''

    def __init__(self, body, appitem):
        self.body = body
        self.appitem = appitem

    def parse_xml(self):     
        self.to_user = self.__re_find(self.touser_re)
        self.from_user = self.__re_find(self.fromuser_re)
        self.createtime = self.__re_find(self.createtime_re)
        self.msgtype = self.__re_find(self.msgtype_re)

        #语音
        if self.msgtype == 'voice' and self.appitem.command_set.filter\
            (tag='voice', status='start', openid=self.from_user).exists():
            self.media_id = self.__re_find(self.mediaid_re)
            self.appitem.voice_set.create(
                openid = self.from_user,
                update_time_str = self.createtime,
                media_id = self.media_id,
            )


        elif self.msgtype != 'event':
            self.content = self.__re_find(self.content_re)

            if self.content in COMMAND_INFO:
                #开启上传录音，关闭录音
                c_info = COMMAND_INFO.get(self.content)
                if c_info:
                    self.message = TempMessage()
                    if c_info[1] == 'start':
                        if not self.appitem.command_set.filter\
                            (tag=c_info[0], status='start', openid=self.from_user).exists():

                            self.appitem.command_set.create(
                                tag = c_info[0],
                                create_time_str = self.createtime,
                                status = 'start',
                                openid = self.from_user,
                            )
                            self.message.text = "开启录音上传"
                        else:
                            self.message.text = "已经开启"

                        self.message.retype = 'text'
                    elif c_info[1] == 'end':
                        commands = self.appitem.command_set.filter\
                        (tag=c_info[0], status='start', openid=self.from_user)
                        if commands:
                            commands.update(status='end')
                            self.message.text = "关闭录音上传"
                        else:
                            self.message.text = "没有开启录音上传"
                        self.message.retype = 'text'
            else:
                #客服功能
                gn = re.findall(r'^#(.+)#$', self.content)
                gn = gn and gn[0] or ''
                if gn:
                    self.message = self.appitem.messages.filter(keyword=gn, \
                        tag__in=['kefu_gn',]).first()
                else:
                    #关键字回复
                    self.message = self.appitem.messages.filter(keyword=self.content, \
                        tag__in=['keyword_recontent', 'qunfa']).first()
                    
                    #是否是关键字回复的子集
                    if self.message and self.message.is_son:
                        self.message = self.message.message

                    if self.msgtype == 'text' and self.appitem.is_receive:
                        self.appitem.receive_set.create(
                            appuser = self.__get_user(),
                            msg_type = self.msgtype,
                            text = self.content
                        )
        else:
            #菜单点击，关注，取消关注
            self.event = self.__re_find(self.event_re)
    
            if self.event == 'CLICK':
                #menu click事件
                self.eventkey = self.__re_find(self.eventkey_re)
                self.message = self.appitem.messages.filter(tag__in=['keyword_recontent', 'qunfa'], \
                    keyword=self.eventkey).first()
            elif self.event == 'subscribe':
                #关注,是否有EventKey，有的话，就是扫描带参数二维码事件
                self.message = self.appitem.messages.filter(tag=self.event).first()
                self.__subscribe_add_user()
            elif self.event == 'unsubscribe':
                #取消关注
                self.__unsubscribe_remove_user()
            elif self.event == 'LOCATION':
                #地理位置
                self.latitude = self.__re_find(self.latitude_re)
                self.longitude = self.__re_find(self.longitude_re)
                user = self.__get_user()
                if user and self.latitude and self.longitude:
                    user.latitude = self.latitude
                    user.longitude = self.longitude
                    user.save()


            elif self.event == 'SCAN':
                # 扫描带参数二维码事件，用户已关注时的事件推送
                pass

            elif self.event == 'qualification_verify_success':
                self.appitem.verifystatus_set.create(qualification_verify_type='qualification_verify_success', \
                    expiredtime=self.__re_find(self.expiredtime))
            elif self.event == 'qualification_verify_fail':
                self.appitem.verifystatus_set.create(failtime=self.__re_find(self.failtime), \
                    failreason=self.__re_find(self.failreason))
            elif self.event == 'naming_verify_success':
                self.appitem.verifystatus_set.create(expiredtime=self.__re_find(self.expiredtime))
            elif self.event == 'naming_verify_fail':
                self.appitem.verifystatus_set.create(failtime=self.__re_find(self.failtime), \
                    failreason=self.__re_find(self.failreason))
            elif self.event == 'annual_renew':
                self.appitem.verifystatus_set.create(expiredtime=self.__re_find(self.expiredtime))
            elif self.event == 'verify_expired':
                self.appitem.verifystatus_set.create(expiredtime=self.__re_find(self.expiredtime))


        #无匹配回复
        if not self.message and self.event not in ['LOCATION']:
            self.message = self.appitem.messages.filter(tag='keyword_default_recontent').first()  

        #记录用户最后一次操作微信的时间，用于判断是否有权限发客服信息
        if self.from_user:
            user = self.__get_user()
            if user:
                user.event_time = self.__get_now_time()
                user.save()


    def __re_find(self, re_str):
        data_result = re.findall(re_str, self.body)
        return data_result and data_result[0] or ''

    def __subscribe_add_user(self):
        #关注获取用户信息
        openid = self.from_user
        user_info = self.appitem.get_user_info(openid)
        user = self.__get_user()
        if not user:
            user = AppUser(openid=openid)
            user.save()
        try:
            user.nickname = user_info.get('nickname')
            user.sex = user_info.get('sex')
            user.language = user_info.get('language')
            user.city = user_info.get('city')
            user.province = user_info.get('province')
            user.country = user_info.get('country')
            user.headimgurl = user_info.get('headimgurl')
            user.unionid = user_info.get('unionid')
            user.save()
        except:
            pass
        if not self.appitem.app_users.filter(openid=openid).exists():
            self.appitem.app_users.add(user)
        else:
            user.is_guanzhu = True
            user.unionid = user_info.get('unionid')
            user.save()
            
    def __unsubscribe_remove_user(self):
        #取消关注移除用户
        user = self.__get_user()
        if user:
            self.appitem.app_users.remove(user)

    def __get_user(self):
        if not self.user:
            self.user = AppUser.objects.filter(openid=self.from_user).first()
        return self.user

    def __get_now_time(self):
        if not self.now_time:
            self.now_time = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
        return self.now_time

def check(params, token):
    signature = params.get('signature', '')
    timestamp = params.get('timestamp', '')
    nonce = params.get('nonce', '')

    tmp_str = ''.join(sorted([token, timestamp, nonce]))
    tmp_str = hashlib.sha1(tmp_str).hexdigest()
    if tmp_str == signature:
        return True
    else:
        return False        

@csrf_exempt
def weixin_api(request, token):
    appitem = AppItem.objects.filter(token=token, is_able=True).first()
    if not appitem or not check(request.GET, token):
        raise Http404
    
    #第一次验证开发者,如果失败，手动改is_valid为False,重新验证
    if not appitem.is_valid:
        echostr = request.GET.get('echostr', '')
        appitem.is_valid = True
        appitem.save()
        return HttpResponse(echostr)

    #解析接口请求
    try:
        msg = ParseMessage(request.body, appitem)
        msg.parse_xml()
        return_data = ''
    except Exception, data:
        print "parse body error ===>>"
        print Exception, ":", data

    #返回接口数据
    try:
        if msg.message:
            return_data = gen_xml(msg)
        else:
            return_data = ''   
    except Exception, data:
        print 'parse message error===>>'
        print Exception, ":", data

    return HttpResponse(return_data, content_type="application/xhtml+xml")