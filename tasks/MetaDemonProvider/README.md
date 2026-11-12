# MetaDemonProvider 超鬼王提供者

超鬼王活动的"供体"账号任务：召唤鬼王 → 点**集结**弹好友邀请弹窗 → 邀请指定好友（= 开
[MetaDemonAssist](../MetaDemonAssist/README.md) 超鬼王协助的账号）→ 等好友击杀 → 鬼王消失 5s 后再召唤，
循环直到无法召唤（票尽）。收工后 `set_next_run(success=True)` 走 success_interval（默认 1 天，GUI 可改）。

**与 MetaDemon（自己打超鬼王）/ MetaDemonAssist（协助打好友鬼王）的分工**：本任务不打架（无战斗/切魂配置），
只负责"生产鬼王给好友打"。两个账号分别启用 Provider 与 Assist 即可联动。

## 流程

1. `goto_page(page_mda_huozhu)`（**复用** MetaDemonAssist 的页面图，跨任务引用 page 对象）。
2. 主循环（`mdp_max_duration` 兜底）。**全程不让位**（2026-11-12 实机教训：Provider 是主动肝任务，
   同 Orochi 语义，等待击杀期间被到点任务打断 = 主号失去集结目标，任务被拆散；Assist 是守候型
   才让位，两类任务语义不同）：
   - **鬼王在场检测**：自己发现卡 OCR「剩余时间」（O_MDP_CARD）或集结标记（I_MDP_RALLY）可见；
   - 无鬼王 → 点召唤鬼王（I_MDP_FIND）→ 等 10s 鬼王出现；重试 2 次仍失败 = **无法召唤，收工**；
   - 有鬼王 → 点集结标记 → 等好友邀请弹窗（I_MDP_INVITE 出现）；
   - **选好友**：双列 OCR `detect_and_ocr` + 容错匹配（`_name_hit`：清洗省略号/空格后
     全等 / 短前缀 / difflib≥0.75 三级）——**游戏把长名缩略显示（丶永…夜），exact 永不命中**
     （魂十三→魂干三同源的截断坑，2026-11-12 实机确认）；0.75 的取值=3 字名误读 1 字要拦
     （误邀别人代价高），4 字名误读 1 字起放行；单测 11 例全过（log/mdp_build_20261112）。
     首屏没有 → 列表上滑一屏再找（S_MDP_LIST_UP）；两屏仍无 → 整轮重试 1 次 → 仍失败：
     存诊断截图 `mdp_friend_not_found` + 关弹窗 + **收工**（失败外传，不静默）；
   - 点中后等选中金卡（I_MDP_SELECTED，裁自选中卡右上纯金底区，避开名字头像）确认，最多重试 3 次；
   - 点「邀请」→ 以**弹窗消失**为成功判据（Timer 8s 兜底，失败存 `mdp_invite_ensure_missing` + 收工）；
   - **等好友击杀**：轮询自己发现区（每轮 280s 周期 `stuck_record_clear + add('PAUSE')` 保活 +
     `ui_reward_appear_click` 顺手清结算弹窗）；鬼王消失判据 = 卡片 OCR 读空 **且** 空面具出现，
     **连续 2 帧确认**（防邀请弹窗关闭动画/结算浮层遮挡造成单帧假消失，契灵假 0 同源坑）；
     `mdp_kill_timeout`（默认 10 分钟）超时 → **重新集结邀请一次**；第二次仍超时 → 收工（鬼王留着，
     下次运行时仍在场可直接集结；鬼王约 37 分钟自然逃跑）；
   - 鬼王消失 → `sleep(5)`（用户指定）→ `_clear_settlement` 清奖励/结算弹窗 → 回到鬼王检测。
3. 收工：认层退回庭院（通用返回键 + `goto_page(page_main)` 兜底）→ 排期 → `raise TaskEnd`。

### 指定星级召唤（2026-11-12 识别化改版，用户指定规则）

`mdp_target_star`≠0 时点「全部队列」开召唤队列弹窗选卡：`find_eye_cards` 数每张卡**点亮的星标（橙）**
得星级与点击位置——**与排序下拉（高到低/低到高）无关**：弹窗按"拥有的星级种类"压缩排列，缺的星级
不留空位、卡位会漂移，固定坐标不可用（用户实测）。锚点=卡上星标小橙星（单颗宽 5-6px、间距 9.3px、
y 370-380），列游程=单颗星、x 聚类（阈值 40px）=卡；星标有**点亮(橙)/未点亮(灰)两态**，只数橙色
=当前有效星级。选卡：**精确星级优先 → 没有则点星级更高里最接近的 → 再没有 = depleted 直接收工**
（不往低星兜底，不再空重试）。关弹窗用 `_close_summon_popup`（粉叉，以立即召唤按钮消失为出口）。

## 素材（2026-11-12，log/mdp_build_20261112/ 有验证脚本）

| 素材 | 来源 | 验证 |
|---|---|---|
| mdp_rally 集结标记 | **拷贝** MetaDemon `md_boss_convene.png` | 对提供者新截图 0.996 @(247,154)，零误报 |
| mdp_invite 弹窗邀请钮 | **拷贝** GeneralInvite `gi_invite_ensure.png` | **1.0000 @(704,544) 像素级**（两种弹窗邀请按钮完全同款），零误报 |
| mdp_find 召唤鬼王钮 | **拷贝** MetaDemon `md_find_demon.png` | 1.0000（noKing 召唤钮） |
| mdp_empty 自己发现空面具 | **拷贝** MetaDemon `md_boss_empty.png` | 0.905；**roiBack 限定自己发现区**（弹窗选中金卡区有 0.787 误报，勿放宽） |
| mdp_selected 选中金卡 | **新裁**自截图选中卡右上纯金底区 (832,292,92,58)（避开名字头像，通用） | 来源 1.0，对未选中卡同位区 **0.004** |
| O_MDP_CARD | 自己发现卡「剩余时间」(140,158,120,55) | 1.00 |
| O_MDP_COLUMN_1/2 | 弹窗双列好友名 (440,190,195,330)/(730,190,200,330)，行距 95px | 8 个好友名全读出 0.80~1.00 |
| O_MDP_TICKET | 顶栏票数 (500,20,130,40)，**Digit 模式**（裸数字非 cur/total，DigitCounter 会解析成 0+刷 WARNING） | "37" 正确返回 int（仅日志，不做判断依据） |
| mdp_queue 全部队列钮 | 2026-11-12 事故截图重裁 (1058,492,184,40)——16:16 标注重裁框画到按钮上方空隙致 0.55 分三连卡死（DEV_GUIDE 34 节） | 事故截图 1.000，54 张无关截图零误报 |
| mdp_summon_now 立即召唤钮 / mdp_selected 蓝勾 | 2026-11-12 标注重裁自弹窗样本 | 弹窗样本仅一份离线验不了，**待实机** |
| （无模板）召唤队列卡识别 | `find_eye_cards` 星标橙色列游程计数 (340,358,620,36)，x聚类阈值 40px | 三张弹窗样本 [6,5,4,3,2,1] / [1,2,3,4,5,6] / [2,3,5] 全过 + 选卡断言（log/mdp3_build） |

## 已知风险 / 待实机验证

1. **集结点击后的弹窗交互只有一张截图样本**：弹窗关闭方式（无 X 按钮，找不到好友时 `_close_invite_popup`
   先点通用粉叉再导航自愈，路径未实测）；邀请过快的游戏限制（gi 经验是 sleep 3，本任务单好友无连邀）。
2. **选中金卡在弹窗刚打开时是否有默认预选**未确认——若打开即有金色选中，首轮流 `_select_friend`
   点名字前可能已选中别人：点名字成功即覆盖选中，风险低；但"点名字失败(OCR 没命中)且已有默认选中"
   会误确认别人，实机首跑注意日志。
3. 召唤鬼王的消耗与"无法召唤"的具体形态（票尽按钮变灰？弹提示？）未实测——当前以"点击后鬼王 10s
   未出现"重试 2 次判收工。
4. 提供者端的击杀结算弹窗形态未实测（`_clear_settlement` 用通用奖励浮窗+粉叉兜底）。
5. 好友列表滚动到底检测未做（好友极多时两屏找不到即收工，实机按需加 SwitchSoul 式到底检测）。
6. 协作联动验证：Provider 邀请后 Assist 端（庭院横幅）是否稳定收到、打完 Provider 端鬼王消失的时机。

## 注册清单

config_model.py（import + `meta_demon_provider`）、config_menu.py（Activity Task）、
config_manual.py（SCHEDULER_PRIORITY：`MemoryScrolls > MetaDemonProvider > MetaDemonAssist`）、
i18n 附加表（assets/i18n/zh-CN.json，键前缀 provider_friend_name / mdp_；主表会被 oasx 回写洗掉属正常）。
改素材后须**重启 OAS 进程**。GUI 里"限时活动"分组启用；`provider_friend_name` 必填（留空 run() 直接抛错）。
