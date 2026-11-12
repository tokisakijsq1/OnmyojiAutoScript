# 组队页面判据补丁(本地自有文件, 不改上游 GameUi/assets.py 与 default_pages.py, 合并零冲突)
# 作用: 给 page_team 的识别条件追加并列第二判据 I_CHECK_TEAM2(左上角"组队"标题字样)。
# 背景: 上游唯一判据 I_CHECK_TEAM(左下Q版立绘)是等级解锁元素, 小号页面没有,
# 进组队界面后页面认不出任务卡死(2026-11-12 实机)。
# 加载: PageRegistry.load_all_pages() 自动扫描 tasks/*/page.py, 本文件随扫随生效。
from tasks.GameUi.page import page_team
from tasks.GameUi.matcher import any_of
from tasks.TeamPagePatch.assets import TeamPagePatchAssets

I_CHECK_TEAM2 = TeamPagePatchAssets.I_CHECK_TEAM2

# 幂等保护: 本模块只被 import 一次, 但防止未来加载机制变化导致重复包装
if 'I_CHECK_TEAM2' not in repr(page_team.recognizer):
    page_team.recognizer = any_of(page_team.recognizer, I_CHECK_TEAM2)
