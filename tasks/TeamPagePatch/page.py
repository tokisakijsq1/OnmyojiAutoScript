# 组队页面判据补丁(本地自有文件, 不改上游 GameUi/assets.py 与 default_pages.py 与各任务 script_task, 合并零冲突)
# 删除本目录(tasks/TeamPagePatch)并重启进程即完全回退。
#
# 背景: 上游 I_CHECK_TEAM(组队页左下 Q 版立绘 @32,585)是等级/功能解锁元素,
# 未解锁账号的组队页面没有它, 导致:
#   1) page_team 页面识别失败 -> goto_page(page_team) 抛 GamePageUnknownError
#   2) EvoZone/Orochi/FallenSun/EternitySea/BondlingFairyland/OtherWorldTwilight/Tako/
#      GeneralRoom 等 14 处 `appear(I_CHECK_TEAM)` 的"进入组队页面"确认永不命中 -> 空转卡死
# 修法(运行时替换资产实现, 语义="当前处于组队页面"):
#   I_CHECK_TEAM2 = 组队页左上角"组队"标题字样 (97,24,70,38), 全等级恒有,
#   来源 1.0 像素级, 对同风格金字标题页误报最高 0.532(阈 0.8)。
#   全部 14 处引用语义核对过均为"到达组队页面"确认, 无一处依赖立绘图案本身。
from tasks.GameUi.page import page_team
from tasks.GameUi.assets import GameUiAssets
from tasks.GameUi.matcher import any_of
from tasks.TeamPagePatch.assets import TeamPagePatchAssets

I_CHECK_TEAM2 = TeamPagePatchAssets.I_CHECK_TEAM2

# 1) 页面判据: page_team 追加并列(幂等)
if 'I_CHECK_TEAM2' not in repr(page_team.recognizer):
    page_team.recognizer = any_of(page_team.recognizer, I_CHECK_TEAM2)

# 2) 资产实现替换: 上游立绘(等级解锁) -> 标题字样(全等级恒有)
#    覆盖 EvoZone(run_leader 创建队伍循环)/Orochi/FallenSun/EternitySea/BondlingFairyland/
#    OtherWorldTwilight/Tako/GeneralRoom 全部 appear(I_CHECK_TEAM) 引用点
GameUiAssets.I_CHECK_TEAM = I_CHECK_TEAM2
