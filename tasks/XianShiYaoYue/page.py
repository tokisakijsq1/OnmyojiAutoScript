from tasks.XianShiYaoYue.assets import XianShiYaoYueAssets as xy
from tasks.GameUi.page import Page, page_main
from tasks.GameUi.assets import GameUiAssets as G

# ************************************* 现世妖约部分 *****************************************#

# 现世妖约活动页 xian_shi_yao_yue
page_xian_shi_yao_yue = Page(xy.I_XY_CHECK_ACTIVITY)
page_xian_shi_yao_yue.connect(page_main, G.I_BACK_YOLLOW, key="page_xian_shi_yao_yue->page_main")
# 入口图标位置随账号右侧图标数量浮动, 两种猫样式模板都挂上
page_main.connect(page_xian_shi_yao_yue, [xy.I_XY_OFFLINE_CELEBRATION, xy.I_XY_OFFLINE_CELEBRATION_2],
                  key="page_main->page_xian_shi_yao_yue")
# 现世商店页 xian_shi_yao_yue_shop
page_xian_shi_yao_yue_shop = Page(xy.I_XY_CHECK_SHOP)
# 商店页的活动灯笼是灰暗状态, 与活动页的金色状态不同, 两个模板都要挂
page_xian_shi_yao_yue_shop.connect(page_xian_shi_yao_yue, [xy.I_XY_GOTO_ACTIVITY, xy.I_XY_GOTO_ACTIVITY_2],
                                   key="page_xian_shi_yao_yue_shop->page_xian_shi_yao_yue")
page_xian_shi_yao_yue_shop.connect(page_main, G.I_BACK_YOLLOW, key="page_xian_shi_yao_yue_shop->page_main")
page_xian_shi_yao_yue.connect(page_xian_shi_yao_yue_shop, xy.I_XY_GOTO_SHOP,
                              key="page_xian_shi_yao_yue->page_xian_shi_yao_yue_shop")
