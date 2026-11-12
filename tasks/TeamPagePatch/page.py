# 组队页面判据补丁(本地自有文件, 不改上游 GameUi/assets.py 与 default_pages.py, 合并零冲突)
# 作用: 给 page_team 的识别条件追加并列第二判据 I_CHECK_TEAM2。
# I_CHECK_TEAM2 与上游 I_CHECK_TEAM 同图案同 roi 的独立副本, 专供本地用标注工具换图
# (任务选 TeamPagePatch, 红框裁新图案保存即重生成 assets.py), 上游素材老化/换皮时不再动上游文件。
# 加载: PageRegistry.load_all_pages() 自动扫描 tasks/*/page.py, 本文件随扫随生效。
from tasks.GameUi.page import page_team
from tasks.GameUi.matcher import any_of
from tasks.TeamPagePatch.assets import TeamPagePatchAssets

I_CHECK_TEAM2 = TeamPagePatchAssets.I_CHECK_TEAM2

# 幂等保护: 本模块只被 import 一次, 但防止未来加载机制变化导致重复包装
if 'I_CHECK_TEAM2' not in repr(page_team.recognizer):
    page_team.recognizer = any_of(page_team.recognizer, I_CHECK_TEAM2)
