# 组队页面判据补丁(本地自有文件, 不改上游 GameUi/assets.py 与 default_pages.py, 合并零冲突)
# 作用: 给 page_team 的识别条件追加并列第二判据 I_CHECK_TEAM2。
# I_CHECK_TEAM2 与上游 I_CHECK_TEAM 同图案同 roi 的独立副本, 专供本地用标注工具换图
# (红框裁新图案保存即生效), 上游 page_check_team.png 老化/换皮时不再动上游文件。
# 加载: PageRegistry.load_all_pages() 自动扫描 tasks/*/page.py, 本文件随扫随生效。
from tasks.GameUi.page import page_team
from tasks.GameUi.matcher import any_of
from module.atom.image import RuleImage

I_CHECK_TEAM2 = RuleImage(roi_front=(32,585,82,65), roi_back=(0,563,148,139), threshold=0.8, method="Template matching", file="./tasks/GameUi/page/page_check_team2.png")

# 幂等保护: 本模块只被 import 一次, 但防止未来加载机制变化导致重复包装
if 'page_check_team2' not in repr(page_team.recognizer):
    page_team.recognizer = any_of(page_team.recognizer, I_CHECK_TEAM2)
