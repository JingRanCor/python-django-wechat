#coding:utf8


MESSAGE_TAG = (
    ('keyword_recontent', '关键字回复'),
    ('keyword_default_recontent', '无匹配回复'),
    ('subscribe', '关注'),
    ('qunfa', '四次群发'),
)

MESSAGE_TYPE_LIST = (
    ('text', '文本回复'),
    ('news', '图文回复'),
    ('voice', '语音回复'),
    ('kefu_gn', '客服功能'),
)

MENU_CHOICES = (
    ('click', '关键字回复'),
    ('view', '跳转'),
    ('sub_menu', '子按键'),
)

SUB_MENU_CHOICES = (
    ('click', '单击动作'),
    ('view', '跳转'),
)

ARTICLE_TAG = (
    ('article', '文章'),
    ('album', '相册'),
)

CATEGORY_TAG_CHOICES = (
    ('article', '文章'),
    ('album', '相册'),
    # ('navigation', '导航'),
    ('article_and_album', '文章和相册'),
)

MESSAGE_STATUS = (
    ('create', '创建中'),
    ('sending', '发送中'),
    ('success', '发送成功'),
)

APPITEM_TAG = (
    ('dingyue', '订阅号'),
    ('fuwu', '服务号'),
    ('unknown', '未认证'),
)


MESSAGE_TYPESTR = (
    ('create', '创建'),
    ('import', '导入'),
)

VERIFY_TYPE = (
    ('qualification_verify_success', '资质认证成功'),
    ('qualification_verify_fail', '资质认证失败'),
    ('naming_verify_success', '命名成功'),
    ('naming_verify_fail', '名称认证失败'),
    ('annual_renew', '年审通知'),
    ('verify_expired', '认证过期失效通知'),
)