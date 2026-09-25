from tasks.XianShiYaoYue.assets import XianShiYaoYueAssets as xy
from tasks.GameUi.page import Page, page_main
from tasks.GameUi.assets import GameUiAssets as G

# ************************************* 现世妖约部分 *****************************************#

# 现世妖约活动页 xian_shi_yao_yue
page_xian_shi_yao_yue = Page(xy.I_XY_CHECK_ACTIVITY)
page_xian_shi_yao_yue.link(button=G.I_BACK_YOLLOW, destination=page_main)
# 入口图标位置随账号右侧图标数量浮动, 两种猫样式模板都挂上
page_main.link(button=[xy.I_XY_OFFLINE_CELEBRATION, xy.I_XY_OFFLINE_CELEBRATION_2], destination=page_xian_shi_yao_yue)
# 现世商店页 xian_shi_yao_yue_shop
page_xian_shi_yao_yue_shop = Page(xy.I_XY_CHECK_SHOP)
# 商店页的活动灯笼是灰暗状态, 与活动页的金色状态不同, 两个模板都要挂
page_xian_shi_yao_yue_shop.link(button=[xy.I_XY_GOTO_ACTIVITY, xy.I_XY_GOTO_ACTIVITY_2], destination=page_xian_shi_yao_yue)
page_xian_shi_yao_yue_shop.link(button=G.I_BACK_YOLLOW, destination=page_main)
page_xian_shi_yao_yue.link(button=xy.I_XY_GOTO_SHOP, destination=page_xian_shi_yao_yue_shop)
