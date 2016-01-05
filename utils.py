#coding:utf8
import datetime
import hashlib
import os
import urllib
import urllib2
import json
import base64

from urllib import quote

from django.core.cache import cache
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from yimixk_beta.settings import SITE_USER_INFO_API, MEDIA_ROOT, DOMAIN
from django.conf import settings
from django.utils.timezone import localtime

try:
    from poster.encode import multipart_encode
    from poster.streaminghttp import register_openers
except:
    print 'please install poster'


def post_file(filename, url, media='media'):
    '''上传文件'''
    register_openers()
    datagen, headers = multipart_encode({media: open(filename, "rb")})
    request = urllib2.Request(url, datagen, headers)
    return urllib2.urlopen(request).read()

def post_file_get_media_id(filename, url):
    data = post_file(filename, url)
    dict_data = json.loads(data)
    if dict_data.get('type'):
       return dict_data

def get_dir(path):
    '''如果没有目录则创建'''
    if not os.path.isdir(path):
        os.makedirs(path)
    return path

def from_timestamp_get_datetime(ts, tzinfo=False, local=False):
    '''
    tzinfo 是否打开时区
    local 是否转换为本地时区
    '''
    if ts:
        ts = int(ts)
        utime = datetime.datetime.utcfromtimestamp(ts)
        if tzinfo:
            utime = utime.replace(tzinfo=pytz.utc)
            if local:
                utime = localtime(utime)
        return utime

def generate_code(plainText):
    return hashlib.sha1(plainText).hexdigest()

def getnowString():
    return datetime.datetime.now().strftime('%Y%m%d%H%M%s%f')

def generate_file_code():
    nowString = getnowString()
    key = "_upload_file_%s" % nowString
    return generate_code(key)

def upload_file_handler(instance,filename):
    date_str = datetime.datetime.now().strftime("%Y%m%d")
    path = date_str +"/"+instance.__class__.__name__.lower()
    suffix = filename.split(".")[-1] or "jpg"
    filename = generate_file_code()+"."+suffix
    return os.path.join(path, filename)

def gen_file_from_data(file_data):
    file_data = base64.b64decode(file_data)
    date_str = datetime.datetime.now().strftime("%Y%m%d")
    path = date_str +"/thumb"
    filename = generate_file_code()+".jpg"
    get_dir(settings.MEDIA_ROOT+'/'+path)
    name = os.path.join(path, filename)
    file(settings.MEDIA_ROOT+'/'+name, 'wb').write(file_data)
    return name

def set_image_instance_from_data(image_filed, request, name='file_data'):
    '''
    用法article.image = set_image_instance_from_data(article.image, request)
    '''
    file_data = request.POST.get(name)
    if file_data:
        image_filed = gen_file_from_data(file_data)
        return (image_filed, True)
    return (image_filed, False)

def method_get_api(url):
    response = urllib2.urlopen(url).read()
    dict_data = json.loads(response)
    return dict_data

def method_post_api(url, post_data):
    json_data = json.dumps(post_data, ensure_ascii=False).encode('utf8')
    req = urllib2.Request(url, json_data)
    req.add_header('Context-Type', 'application/json;charset=utf-8')
    return_json = urllib2.urlopen(req).read()
    return json.loads(return_json)

def get_entry_page(entry, count_per_page, page_number):
    '''分页返回page_number页的数据'''
    paginator = Paginator(entry, count_per_page)
    try:
        page_entry = paginator.page(page_number)
    except PageNotAnInteger:
        page_entry = paginator.page(1)
    except EmptyPage:
        page_entry = paginator.page(paginator.num_pages)
    return page_entry

def page_turning(list_obj, request, count=10):
    '''翻页函数''' 
    page = int(request.GET.get("p",1))
    matchs = get_entry_page(list_obj, count, page)
    show_pages = range(max(page-4,1),min(page+4, matchs.paginator.num_pages)+1)
    return (matchs, show_pages)

def convert_get_data(GET, key_list):
    '''翻页时用来继承get提交参数''' 
    get_data = ''
    for keyw in key_list:
        if GET.get(keyw):
            get_data += '%s=%s&'%(keyw, GET.get(keyw))
    return get_data

def convert_model_to_json(queryset, field_list):
    '''将model'''
    data_list = []
    for instance in queryset:
        data = {}
        for field in field_list:
            data[field] = getattr(instance, field)
        data_list.append(data)
    json_data = json.dumps(data_list)
    return json_data

def get_weixin_site_url(appitem, url):
    '''进入微网站的url'''
    return url
    # if not appitem.is_get_openid:
    #     return url
    # url = quote(url)
    # return SITE_USER_INFO_API % (appitem.appid, url)

def get_openid_api_url(appitem, url):
    if not appitem.is_get_openid:
        return url
    url = quote(url)
    return SITE_USER_INFO_API % (appitem.appid, url)


def get_qrcode_data(image_name):
    '''解析qrcode,需要安装zbar'''
    import zbar
    from PIL import Image
    scanner = zbar.ImageScanner()
    scanner.parse_config('enable')
    pil = Image.open(image_name).convert('L')
    width, height = pil.size
    raw = pil.tobytes()
    image = zbar.Image(width, height, 'Y800', raw)
    scanner.scan(image)
    data = ''
    for symbol in image:
        data += symbol.data
    del(image)
    return data


def delete_file(filepath):
    '''删除MEDIA_ROOT下文件'''
    if filepath and os.path.isfile(filepath) and MEDIA_ROOT in filepath:
        os.remove(filepath)
        return True

def delete_image(image):
    '''删除图片'''
    if image.name:
        filepath = MEDIA_ROOT+'/'+image.name
        return delete_file(filepath)

def get_absolute_path(file_url):
    '''多媒体url路径得到文件路径'''
    if file_url:
        filepath = settings.MEDIA_ROOT + '/' + file_url.split(settings.MEDIA_URL)[1]
        return filepath

def delete_media_root_file(file_url):
    if file_url:
        filepath = settings.MEDIA_ROOT + '/' + file_url.split(settings.MEDIA_URL)[1]
        if os.path.isfile(filepath):
            os.remove(filepath)
            return True

try:
    import qrcode
except:
    print 'please install qrcode'

def generate_qrcode(data, filepath):
    '''生成二维码'''
    try:
        img = qrcode.make(data)
        img.save(filepath)
        return True
    except:
        return False


def get_qrcode_url(instance):
    '''得到二维码'''
    date_str = datetime.datetime.now().strftime("%Y%m%d")
    son_path = '/qrcode/'+date_str+'/'
    get_dir(MEDIA_ROOT+son_path)
    class_name = instance.__class__.__name__.lower()
    suffix = '%s%s-%s.png'%(son_path, class_name, instance.id)
    filepath = MEDIA_ROOT+suffix
    url = instance.get_url()
    if url and instance.qrcode != filepath:
        generate_qrcode(url, filepath)
        instance.qrcode = filepath
        instance.save()
    son_url = filepath.lstrip(MEDIA_ROOT)
    # qrcode_url = 'http://%s/media/qrcode/%s-%s.png'%(DOMAIN, class_name, instance.id)
    qrcode_url = 'http://%s/media/%s'%(DOMAIN, son_url)
    return qrcode_url


def download_voice(url):
    response = urllib2.urlopen(url)
    headers = response.headers.dict
    ori_filename = headers.get('content-disposition', '')
    if 'filename=' in ori_filename:
        filename = ori_filename.split('filename=')[1].strip('"').strip("'")
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        url_dir = 'audio/%s/' % date_str
        get_dir(settings.MEDIA_ROOT + '/' + url_dir)
        url_path = url_dir + filename
        filename = settings.MEDIA_ROOT + '/' + url_path
        file(filename, 'wb').write(response.read())
        return settings.MEDIA_URL + url_path
    return ''

def create_tmp_data(token, filename, data):
    filedir = '%s/tmp/%s/' % (settings.MEDIA_ROOT, token)
    filedir = get_dir(filedir)

    filepath = filedir + filename
    file(filepath, 'wb').write(data)
    return filepath