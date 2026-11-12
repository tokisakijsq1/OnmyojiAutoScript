from tasks.MetaDemonAssist.assets import MetaDemonAssistAssets as mda
from tasks.GameUi.page import Page, page_main
from tasks.GameUi.assets import GameUiAssets as G
from tasks.GameUi.matcher import any_of
from tasks.Component.RightActivity.assets import RightActivityAssets as RAA

# 祸至无日活动页(限时活动聚合页): 标题模板 + 超鬼王竖排按钮 并列判定
# 注: 标题OCR关键词("祸主降临"/"祸至无日")因竖排逐字兜底会互相误报, 页面判定只用模板
page_mda_event = Page(any_of(mda.I_MDA_TITLE_EVENT, mda.I_MDA_GOTO_HUOZHU))

# 祸主降临页(超鬼王主界面): 标题模板 + 挑战按钮 并列判定
# (标题在无鬼王空态下也常驻, 页面判定不依赖挑战按钮)
page_mda_huozhu = Page(any_of(mda.I_MDA_TITLE_HUOZHU, mda.I_MDA_CHALLENGE))

# 祸主降临页 -> 祸至无日页: 左上返回
page_mda_huozhu.connect(page_mda_event, mda.I_MDA_BACK, key="page_mda_huozhu->page_mda_event")
# 祸至无日页 -> 祸主降临页: 超鬼王竖排按钮
page_mda_event.connect(page_mda_huozhu, mda.I_MDA_GOTO_HUOZHU, key="page_mda_event->page_mda_huozhu")
# 祸至无日页 -> 庭院: 左上返回
page_mda_event.connect(page_main, mda.I_MDA_BACK, key="page_mda_event->page_main")
# 庭院 -> 祸至无日页: 右侧栏活动图标(栏收起时先点展开钮)
page_main.connect(page_mda_event, [mda.I_MDA_RIGHT_ENTER, RAA.I_TOGGLE_BUTTON], key="page_main->page_mda_event")

# 超鬼王战败结算"失败"字样位置(410,95)在上游 I_FALSE 搜索区(413,124,100,100)之外,
# battle_wait 战败钩子永不触发(普通副本失败字样在区内故上游无感)。扩大搜索区覆盖两种布局:
# 普通副本原位置(413,124 附近)仍在区内、命中点不变, 仅允许超鬼王的新位置被找到。
# 运行时改资产属性, 零上游文件改动; 删除以下两行即回退。
from tasks.Component.GeneralBattle.assets import GeneralBattleAssets as _GBA
_GBA.I_FALSE.roi_back = (380, 78, 180, 130)
