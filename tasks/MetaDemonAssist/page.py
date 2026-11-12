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
# battle_wait 战败钩子永不触发。此前(2026-11-12 d5c0b823)曾在此用运行时改
# _GBA.I_FALSE.roi_back 修复——但 PageRegistry.load_all_pages() 会扫描导入所有
# tasks/*/page.py, 该 mutation 因此进入每个进程, 且扩宽区(380,78,180,130)纵向
# 罩不住普通败局美术(413,124~224), 普通副本败局匹配掉到 0.3x, 御魂/结界突破/
# 逢魔等同进程流程全部战败失察卡死(绘卷专用 RealmRaid 四连/oas1 DemonEncounter)。
# 现改任务内副本判据 I_MDA_FALSE + ScriptTask 类内 shadowing(见 script_task.py),
# 不再触碰任何共享资产。
