#coding:utf8
import os
import urllib2
import json


from yimixk_beta.settings import MEDIA_ROOT


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

try:
    # from PIL import Image
    import Image
except:
    print 'please install PIL'

def gen_thumb_filename(filename):
    '''生成缩略图的路径'''
    path, name = os.path.split(filename)
    new_path = path.replace('/upload/', '/upload/thumb/')
    if not os.path.isdir(new_path):
        os.makedirs(new_path)
    new_name = os.path.join(new_path, name)
    return new_name

#改变图片大小
def resize_img(img_path, size=64,style='jpg', ch_width=200):
    try:
        img = Image.open(img_path)
        (width,height) = img.size
        new_width = ch_width
        new_height = height * new_width / width
        out = img.resize((new_width, new_height), Image.ANTIALIAS)
        thumb_filename = gen_thumb_filename(img_path)
        filename, ext = os.path.splitext(thumb_filename)
        new_file_name = '%s.%s' % (filename, style)

        #得到压缩率
        filesize = os.path.getsize(img_path)/1024
        if filesize > size:
            quality = int(float(size) / float(filesize) * 100) - 1
        else:
            quality = 100
        out.save(new_file_name, quality=quality)
        return new_file_name
    except Exception,e:
        print Exception,':',e
 
def post_thumb_get_thumb_media_id(filename, url):
    '''提交缩略图到微信服务器得到id'''
    # filename = resize_img(filename) #生成缩略图
    if filename:
       data = post_file(filename, url)
       dict_data = json.loads(data)
       # thumb_media_id = dict_data.get('thumb_media_id')
       thumb_media_id = dict_data.get('media_id')
       return thumb_media_id and thumb_media_id or None



def gen_news_data(query_list, upload_url, fieldname='image'):
    '''根据输入的article list 生成图文素材数据'''
    articles = []
    for query in query_list:
        query_filename = getattr(query, fieldname).name
        if not query_filename:
            return {}
        else:
            filename = MEDIA_ROOT + '/' + query_filename
            thumb_media_id = post_thumb_get_thumb_media_id(filename, upload_url)
            if not thumb_media_id:
                return {}
            article = {
                'thumb_media_id': thumb_media_id,
                'author': query.author,
                'title': query.title,
                "content_source_url": query.url,
                'content': query.content,
                'digest': query.description
            }
            articles.append(article)

    data = {'articles': articles}
    return data

def gen_group_qunfa_data(group_id, content, msgtype):
    '''生成群发的数据'''
    if group_id =='0':
        data = {
            "filter":{"is_to_all":True},
            "msgtype": msgtype,
        }
    else:
        data = {
            "filter":{"group_id": group_id},
            "msgtype": msgtype,
        }
    if msgtype == 'mpnews':
        data[msgtype] = {"media_id": content}
    elif msgtype == 'text':
        data[msgtype] = {'content': content}
    return data


def gen_yulan_qunfa_data(content, msgtype, touser=None, towxname=None):

    '''生成预览的数据'''
    if touser:
        data = {
            "touser": touser,
            "msgtype": msgtype,
        }
    else:
        data = {
            "towxname": towxname,
            "msgtype": msgtype,
        } 
    if msgtype == 'mpnews':
        data[msgtype] = {"media_id": content}
    elif msgtype == 'text':
        data[msgtype] = {'content': content}
    return data 