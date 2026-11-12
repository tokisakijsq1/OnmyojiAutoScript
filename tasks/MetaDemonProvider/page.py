from tasks.MetaDemonProvider.assets import MetaDemonProviderAssets as mdp
from tasks.GameUi.page import Page, page_main
from tasks.GameUi.matcher import any_of
from tasks.Component.RightActivity.assets import RightActivityAssets as RAA

# 本任务自包含页面图(2026-11-12 重构: 此前跨任务引用超鬼王协助的 page_mda_huozhu,
# Provider 因此依赖协助任务模块存在; 现页面判据素材已拷贝为 mdp_ 副本, 页面 key
# 用 page_mdp_* 与协助的 page_mda_* 并存, 互不覆盖)。

# 祸至无日活动页(限时活动聚合页): 标题模板 + 超鬼王竖排按钮 并列判定
# 注: 标题OCR关键词("祸主降临"/"祸至无日")因竖排逐字兜底会互相误报, 页面判定只用模板
page_mdp_event = Page(any_of(mdp.I_MDP_TITLE_EVENT, mdp.I_MDP_GOTO_HUOZHU))

# 祸主降临页(超鬼王主界面): 标题模板 + 挑战按钮 并列判定
# (标题在无鬼王空态下也常驻, 页面判定不依赖挑战按钮)
page_mdp_huozhu = Page(any_of(mdp.I_MDP_TITLE_HUOZHU, mdp.I_MDP_CHALLENGE))

# 祸主降临页 -> 祸至无日页: 左上返回
page_mdp_huozhu.connect(page_mdp_event, mdp.I_MDP_BACK, key="page_mdp_huozhu->page_mdp_event")
# 祸至无日页 -> 祸主降临页: 超鬼王竖排按钮
page_mdp_event.connect(page_mdp_huozhu, mdp.I_MDP_GOTO_HUOZHU, key="page_mdp_event->page_mdp_huozhu")
# 祸至无日页 -> 庭院: 左上返回
page_mdp_event.connect(page_main, mdp.I_MDP_BACK, key="page_mdp_event->page_main")
# 庭院 -> 祸至无日页: 右侧栏活动图标(栏收起时先点展开钮)
page_main.connect(page_mdp_event, [mdp.I_MDP_RIGHT_ENTER, RAA.I_TOGGLE_BUTTON], key="page_main->page_mdp_event")
