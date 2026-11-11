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
