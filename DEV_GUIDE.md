# OAS 二次开发指南（开发要点与踩坑记录）

> 本文档沉淀实际开发中踩过的坑和验证过的做法。**开发新任务 / 改动现有任务前，先通读本文和
> [I18N_GUIDE.md](./I18N_GUIDE.md)，再看目标任务的 README.md**，避免重复踩坑。
> 每次开发结束后，把新的坑和结论补回本文对应章节。

## 目录

1. [新增一个任务的完整清单](#1-新增一个任务的完整清单)
2. [国际化：翻译必须写进两张表](#2-国际化翻译必须写进两张表)
3. [图片素材规范与验证](#3-图片素材规范与验证)
4. [页面注册与导航](#4-页面注册与导航)
5. [退出界面：粉色叉的检测和运用](#5-退出界面粉色叉的检测和运用)
6. [弹窗与原界面 UI 同时出现](#6-弹窗与原界面-ui-同时出现)
7. [长等待与设备卡死检测](#7-长等待与设备卡死检测)
8. [点击无响应的检测与重试](#8-点击无响应的检测与重试)
9. [战斗流程复用 GeneralBattle](#9-战斗流程复用-generalbattle)
10. [切换御魂](#10-切换御魂)
11. [调试技巧](#11-调试技巧)
12. [Git 工作流注意事项](#12-git-工作流注意事项)
14. [对弈竞猜：活动改版模板失效与防重启时间驱动设计](#14-对弈竞猜活动改版模板失效与防重启时间驱动设计2026-10-01)
15. [首领退治：未开启等待界面的无限空转与退避重进](#15-首领退治未开启等待界面的无限空转与退避重进2026-10-03)
16. [组队战后"继续邀请"弹窗：淡出动画二次匹配 + 无出口循环卡死](#16-组队战后继续邀请弹窗淡出动画二次匹配--无出口循环卡死2026-10-07)
17. [dev 基线迁移：重放自研修复到新版页面导航体系](#17-dev-基线迁移重放自研修复到新版页面导航体系2026-10-07)
18. [通用战斗：点准备可能落空，必须验证点击生效再认定进入战斗](#18-通用战斗点准备可能落空必须验证点击生效再认定进入战斗2026-10-09)
19. [结界蹭卡：经验酒壶满额格式带溢出加成，识别框裁掉开头会反复点提取](#19-结界蹭卡经验酒壶满额格式带溢出加成识别框裁掉开头会反复点提取2026-10-09)
20. [磐长故地爬塔：改素材必须重启进程，模块缓存在 sys.modules](#20-磐长故地爬塔改素材必须重启进程模块缓存在-sysmodules2026-10-10)
21. [转场与点击的等待约定：点完要等，认层要留轮数](#21-转场与点击的等待约定点完要等认层要留轮数2026-10-10)
25. [八岐大蛇队长邀请全灭：改版第二波与失败外传约定](#25-八岐大蛇队长邀请全灭改版第二波与失败外传约定2026-10-16)
26. [狭间暗域：集结正向等待、封印跳过与"当前区域扫完才算全封印"](#26-狭间暗域集结正向等待封印跳过与当前区域扫完才算全封印2026-10-16)
27. [悬赏封印 2026-10 大改版：卡片化主界面、圆圈大世界与新详情页](#27-悬赏封印-2026-10-大改版卡片化主界面圆圈大世界与新详情页2026-10-28)

---

## 1. 新增一个任务的完整清单

以 `tasks/XianShiYaoYue/` 为例，**缺一步就可能不生效**：

| 步骤 | 文件 | 说明 |
|---|---|---|
| 1 | `tasks/<TaskName>/config.py` | ConfigBase 子类，含 `scheduler: Scheduler` |
| 2 | `tasks/<TaskName>/script_task.py` | 必须含 `ScriptTask` 类，`script.py` 按 `tasks/<TaskName>/script_task.py` 动态加载 |
| 3 | `tasks/<TaskName>/assets.py` | 图片/OCR/点击资产（见第 3 节） |
| 4 | `tasks/<TaskName>/page.py` | 页面注册（可选，GameUi 会自动加载所有 page.py） |
| 5 | `module/config/config_model.py` | import + `Field(default_factory=...)` 注册 |
| 6 | `module/config/config_menu.py` | 加进 UI 分组（如 `Activity Task`） |
| 7 | **`module/config/config_manual.py` `SCHEDULER_PRIORITY`** | **最易漏！** 调度器按此表过滤待办队列，不在表里的任务 enable 后也会被直接丢弃（不进队列、不报错、不拉起） |
| 8 | `assets/i18n/zh-CN.json` + `module/config/i18n/zh-CN.json` | 两张翻译表（见第 2 节） |
| 9 | `tasks/<TaskName>/README.md` | 记录流程与特殊处理 |

验证调度是否生效（本地即可复现）：

```bash
./toolkit/python.exe -c "
from module.config.config import Config
c = Config('oas1')
c.update_scheduler()
print([f.command for f in c.pending_task])"
```

## 2. 国际化：翻译必须写进两张表

详见 [I18N_GUIDE.md](./I18N_GUIDE.md)。要点：

- `assets/i18n/zh-CN.json`：**附加翻译表**，oasx 界面显示中文的关键，不会被 GUI 回写覆盖
- `module/config/i18n/zh-CN.json`：全量主表，服务 QML 界面 / 通知标题 / 翻译编辑器回写
- **只加一张表是不够的**（百鬼夜行和现世妖约都踩过）
- 主表会被运行中的 GUI 回写覆盖（手工加的键会消失），这是正常现象，别在主表里找补——
  以附加表为准；后端 `_translate_text` 已改为按 mtime 热加载，改完无需重启后端
- 字段 label 由前端用「字段名 + 自己的翻译表」渲染，**后端下发的 title 前端不一定采用**；
  `config_model.py` 的 `merge_value` 里已加 pydantic 自动 title 的兜底翻译

## 3. 图片素材规范与验证

- 截图分辨率必须 1280x720；从用户提供的截图裁模板时，**必须避开截图上的标注框**
  （红圈/蓝框/绿框/白框），宁可裁小一点
- 模板匹配对缩放敏感：参考截图和实际截图的元素比例不同就不能用（如现世祝福卡片
  特写图与商店内尺寸不同，改用 OCR keyword）
- **同一元素在不同状态/账号下外观不同时，一个模板不够**，实测过的例子：
  - 左侧"活动"灯笼：活动页金色 / 商店页灰暗 → 两个模板都挂（page link 支持传 list）
  - 庭院"线下庆典"入口：动态立绘 + 位置随账号右栏图标数浮动 → 多个猫样式模板 +
    整个右栏做 roiBack（复用 FloatParade `fp_access` 的 `(1051,101,210,472)` 模式）
- **新模板必须验证**：对来源截图匹配得分应为 1.0；同时找一张"不该匹配"的截图测误报。
  注意测试时图片要转成 RGB（运行时设备截图是 RGB，`cv2.imread` 是 BGR，直接测会假阴性）
- OCR（RuleOcr）比模板更适合文字类检测，但**注意文案位置会随内容变化**
  （如排队横幅数字居中排版，固定 ROI 会读空），存在性检测优先用固定位置的元素
- **固定 roi（roi_back=roi_front）的文字横幅模板一碰就碎**：横幅是居中排版，
  随计时文字宽度/界面状态有 2~4px 漂移，固定 roi 下 matchTemplate 得分直接从 0.9+ 掉到 0.3x，
  运行时表现为"永远识别不到"。
  对策：roi_back 放宽为覆盖横幅整个区域的搜索区，让匹配自己定位；
  离线验证时先用宽区 matchTemplate 打印真实坐标与得分再定 roi。
  注意用户聊天转存的截图常被裁掉几个像素（1280x720 → 1276x718），对这类截图测"固定 roi 模板"必然假阴性，
  结论要以宽区得分为准；右栏按钮等静态元素不会漂移，可以继续用固定 roi

## 4. 页面注册与导航

- 页面定义在任务的 `page.py`，`Page(check)` + `page.link(button, destination)` 双向挂链接；
  `GameUi` 初始化时自动 import 所有 `tasks/**/page.py`
- `link` 的 button 支持传 list（同一跳转有多个外观时全部挂上）
- 从任意界面恢复到目标页：`self.ui_goto(page_xxx)`；页面未注册/识别不了时框架的
  `try_close_unknown_page` 会自动尝试关闭按钮（`ui_close` 列表）

## 5. 退出界面：粉色叉的检测和运用

- 十周年现世妖约的活动页/商店页**必须先点右上角粉色叉再点左上角黄色返回**，
  叉不点则返回按钮无效
- **粉叉可直接复用通用资产 `I_UI_BACK_RED`**（GlobalGame），无需新裁模板——
  遇到"疑似新按钮"先在现有资产里找（红色关闭、确认框、刷新键等通用样式大概率已有），
  找不到再裁新图
- 退出逻辑用循环直到 `I_CHECK_MAIN`：先叉后返回，参见 `XianShiYaoYue/script_task.py` 的 `_exit_to_main()`

## 6. 弹窗与原界面 UI 同时出现

**踩坑实例**：点"组队挑战"后弹出居中的"队伍公开权限"弹窗，弹窗**不遮挡**右下角的
组队挑战按钮。原写法"点组队挑战 → 等按钮消失 → 再处理弹窗"形成死循环：
按钮永远可见，弹窗处理代码永远执行不到，15 秒后误判卡死。

正确做法：**等待条件不能建立在"会被弹窗遮挡关系欺骗"的目标上**，改用状态机同时检测
多个目标，弹窗优先处理：

```python
while 1:
    self.screenshot()
    popup = self.appear(I_CREATE)          # 弹窗元素
    button = self.appear(I_TEAM_CHALLENGE) # 原界面元素
    if not popup and not button:
        break                              # 两者都消失才算完成
    if popup:
        ...                                # 弹窗优先
    elif button:
        ...                                # 无弹窗才点原按钮
```

同类问题：排队横幅出现在屏幕上方且带 X 按钮——**那个 X 是取消排队，绝不能点**；
把横幅 X 模板当作"排队中"的存在检测（位置固定，比 OCR 数字稳）。

**别假设"确认弹窗"一定有确定/取消**（2026-09-27 现世妖约买祝福踩坑）：点商品弹的
详情弹窗，购买交互是底部**金色价格按钮本身**（勾玉图标+价格），没有确定/取消对——
用 I_UI_CONFIRM 系列等确认会 6 秒零点击落空，随后二次 OCR 还会把"被弹窗挡住的
卡片"读空，误判成"已购买"。对策：拿到真实弹窗截图再裁模板；等不到预期按钮就
显式关闭弹窗重试，别让"读空"顺延成误判。

## 7. 长等待与设备卡死检测

- 设备层卡死检测：60 秒无点击动作 → `GameStuckError('Wait too long')` → 任务重启；
  `stuck_record_add('BATTLE_STATUS_S')` 可豁免短计时，但 300 秒长计时仍会触发
- **匹配/排队等长等待场景，循环每轮调用 `self.device.stuck_record_clear()`**，
  超时改由循环自己的 Timer 管理（参考 `_match_and_battle`）：
  - 检测到排队横幅 → 重置等待计时，继续等（人数 10 分钟无变化只告警不重启）
  - 横幅消失后才启用有限等待窗（180 秒）
- 战斗内长等待参考 `GeneralBattle.battle_wait`（stuck_record_add + 定期随机点击）
- **坑：任何点击/滑动都会经 `handle_control_check` 清空卡死白名单**（2026-10-07
  契灵之境长战斗反复 GameStuckError 的根因）：`random_click_swipt` 防封随机动作
  触发一次后，`BATTLE_STATUS_S` 豁免被 `stuck_record_clear()` 抹掉，只剩 60 秒
  普通计时器；只要战斗剩余时长 > 60 秒且期间没再触发下一次随机动作（约 0.8%/轮，
  期望间隔一两分钟），就必死——日志特征是 `Waiting for set()`（空集合）+ 随机点击
  后**正好 60 秒**报错，而错误截图里战斗正常进行。已修：恢复上游 62533827 注释掉的
  `random_click_swipt` 尾部重新 `stuck_record_add('BATTLE_STATUS_S')`（原注释为
  "重新设置为长战斗"）。自己写战斗循环时同理：凡循环内有点击动作，每轮点击后都要
  重新登记长等待豁免

## 8. 点击无响应的检测与重试

每个关键点击步骤都要回答三个问题：怎么确认点成功了？没成功多久重试？重试几次后怎么办？

- 跳转型点击：`ui_click(click, stop=目标页元素, interval=1.5, timeout=20)` 自带重试；
  返回 False 即失败
- 状态型点击（点了会消失的按钮）：循环 `appear(按钮)` + `click(interval=2)`，直到消失
- **坑：`appear(X, interval=…)` 命中后紧跟 `self.click(X, interval=…)` 会静默不点**
  （2026-10-04 oas3 手动模式切自动失效的根因）：`appear`/`click`/`ocr_appear` 按
  `target.name` **共用同一个 interval 计时器**，appear 命中就 reset，紧跟着的
  click 查同一计时器永远"没到时间"，直接 return False——日志特征是打了
  "click to switch auto" 却没有 `Click (x,y) @ X` 行。要用 `appear_then_click(X, interval=…)`
  （内部直接 `device.click`，不走 interval 拦截），或让 click 不传 interval。
  注意"状态型点击"那条的 appear+click 组合里两者间隔了截图/耗时操作，计时器
  自然到期才没踩坑；紧跟式调用必踩
- 重试耗尽的处置要区分场景：
  - **可能是正常业务结束**（如挑战次数用尽导致点击无响应）→ 先做业务检测
    （OCR 次数），用尽则抛业务异常（`BattleCountOut`）判定任务完成，正常收尾
  - 确实异常 → `raise GameStuckError`，由 script.py 统一走重启恢复
- 有次数限制的活动，**轮次开始前 + 点击无响应时**都要检查剩余次数
- **坑：判定"元素不存在"之前先等 UI 异步加载完**（2026-09-25 悬赏食梦貘被跳过的根因）：
  悬赏详情页的"追踪"按钮先渲染、"前往"目的地列表等服务器异步返回（同一次运行里
  有 1.4s+ 才就绪的实例），点开详情后立刻 `appear(I_GOTO_1)` 会误判成
  "未解锁的神秘任务"而跳过整个悬赏。已修：改用
  `wait_until_appear(I_GOTO_1, wait_time=3)`，超时才走跳过分支。
  任何"点开面板 → 立刻检查里面某个元素"的写法都要留 2~3 秒加载窗，
  尤其当"元素缺失"会触发跳过/放弃分支时
- **坑：清零 `click_record` 规避 `GameTooManyClickError` 时，计数必须按真实点击、且循环必须有 Timer 总上限**
  （2026-09-26 悬赏秘闻聊天循环的根因）：合法的连点场景（如秘闻长对话）确实需要绕开
  "同按钮 15 窗口内 ≥10 次即抛"的保护，但有两个前提——
  ① `self.click(btn, interval=x)` 被 interval 拦截时**返回 False 不实际点击**（不抛错），
  计数器必须用返回值判断，否则循环每 ~0.2s 迭代一次会把"6 次清零"变成"每 2 秒清零"，
  保护被整体废掉；② 连点会不断 `stuck_record_clear()` 重置 60 秒卡死计时，
  **点击无效目标时 GameStuckError 永远不会触发**，循环必须自带 Timer（参考
  `WantedQuests.secret()`：Timer(60) 超时 raise GameStuckError，6 次真实点击才清零一次）

## 9. 战斗流程复用 GeneralBattle

- 通用战斗一律 `self.run_general_battle(config=self.conf.general_battle)`：
  自动处理准备按钮、预设队伍、战斗等待、胜利/失败判定、结算点击（点一次确认跳转，
  不连点）
- 组队/协战战斗同样适用：进入战斗准备界面后与普通战斗一致
- `current_count` 由 run_general_battle 自增，第一场才会执行预设队伍切换
- 排队/邀请等组队前置流程需要自己写（参考 `_match_and_battle` 的状态机）
- **点准备后等正式开打的时长由 `_hook_battle_start_timeout()` 控制（默认 15s）**：
  组队本队友可能迟迟不点准备，齿轮不出现战斗就不开始（2026-10-16 现世妖约实测：
  点准备后 15s 就抛 `Battle is in manual mode and switch to auto failed` 重启）。
  需要更长等待的任务覆写该钩子（现世妖约 75s）；`ensure_auto_battle` 等待循环
  已每轮 `stuck_record_clear()`，长等待不会误触设备卡死重启
- **坑：切自动检测必须在"点准备"之后显式触发，不能指望 battle_before 循环自然走到**
  （2026-10-09 结界突破实测：切预设、点准备都正常，但点准备后一直没有切自动检测，
  卡在原地等游戏自己开打）：`battle_before` 只有 `is_in_real_battle`（战斗信息图标）
  命中才会调 `ensure_auto_battle`，而点完准备到正式开打的过渡期里
  `is_in_prepare` 和 `is_in_real_battle` 都不成立，循环只是空转 5 秒超时返回。
  注意 `switch_preset_team` 循环里的 `O_BATTLE_HAND`/`O_BATTLE_AUTO` 日志是"战斗是否
  已开打"的守卫检测（准备界面必然读空），不是切自动。
  已修：点到 `I_PREPARE_HIGHLIGHT` 后立即调 `ensure_auto_battle` 再返回；循环超时退出前
  再兜底调一次（锁定阵容由游戏自动点准备、或准备按钮没识别到时走这条）
- **切自动是一个模块，不要各写各的**（2026-10-09 全仓盘点后收拢）：
  `GeneralBattle.ensure_auto_battle()` = `wait_real_battle()`（等左下角齿轮出现，
  齿轮出现才算正式开打，返回 bool 不抛异常）+ 切换自动（识别"手动"后延迟 0.5s 复核再点，
  失败抛 `GameStuckError`）。全仓只有这一处实现。
  不走 `run_general_battle` 且自身没有切自动的自写战斗流程要显式调用，已接入的有：
  首领退治 `DemonRetreat`（点准备循环结束后调用）、
  道馆 `Dokan` 的 `dokan_battle_1` 与 `dokan_battle`（等准备按钮出现、点完准备后调用）。
  斗技 `Duel.wait_battle` 保持 dev 原生的 `ui_click(O_D_HAND, O_D_AUTO)` 不动，
  不接入本模块，避免和上游 dev rebase 时冲突。
  新写战斗流程时直接调 `self.ensure_auto_battle()`，不要再复制一套 OCR 点击
- **坑：调 `ensure_auto_battle` 前必须已有人点准备（自己点或锁定阵容游戏自动点）**
  （2026-10-13 道馆 oas1/oas2 双双卡死的根因，10-09 b6471ddc 引入）：齿轮只在正式开打后
  才渲染，`ensure_auto_battle` 内部 `wait_real_battle` 等 15 秒等不到齿轮就直接抛
  `GameStuckError`。道馆的 `dokan_battle` 在函数开头"等准备按钮出现"之后紧接
  `ensure_auto_battle`，但点准备动作在下方 while 循环的 `I_RYOU_DOKAN_IN_FIELD` 分支里——
  首场准备没人点，战斗永远不开始，日志表现为进 `In_Field` 后
  `BATTLE_AUTO/BATTLE_HAND: No text detected` 刷屏约 170 秒后卡死重启。
  已修：两处均在 `ensure_auto_battle` 前补
  `ui_click_until_disappear(self.I_PREPARE_HIGHLIGHT, interval=0.8)`（自带点击生效校验）。
  排查时注意：`wait_until_appear` 不传 `wait_time` 是无限等待，若准备按钮识别正常它会
  很快返回掩盖顺序问题，识别失效则换成另一种死法
- **坑：切自动必须等左下角齿轮出现（正式开打）再检测，且识别到"手动"后延迟复核再点**
  （2026-10-07 用户实机反馈"有时乱点反而切成手动"的根因）：开打瞬间界面仍在过渡，
  OCR 可能在一帧里读到"手动"，检测完立刻点击时游戏状态已变化（或点击落在过渡动画上），
  结果把本来就是"自动"的战斗反切成手动。已修 `ensure_auto_battle`：
  ① 循环里先等 `O_BATTLE_AUTO`/`O_BATTLE_HAND` 任一出现（齿轮出现=正式开始战斗），
  之前不做任何点击；② 识别到"手动"后 `time.sleep(0.5)` 重新截图，复核仍是"手动"
  才 `appear_then_click`，否则回循环重新判断
- **坑：挑战类战斗没有准备阶段，预设队伍流程必须能退出**（2026-09-26 悬赏卡死无限重启的根因）：
  式神挑战点"挑战"后直接开战，但战斗加载过渡期 `is_in_prepare` 会短暂命中，
  `switch_preset_team` 随之运行；战斗真正开始后左下角预设按钮的位置变成**手动/自动切换按钮**，
  OCR 循环点过去一下就把战斗切成手动（该状态账号级记忆，重启后依旧手动），
  而循环关键字是'预设'永远匹配不上、又没有超时 → 无点击死循环 60 秒 GameStuckError →
  重启 → 重跑同一悬赏 → 再卡死，无限循环。
  已修：循环加 15 秒 Timer 超时直接放弃预设；循环内检测 `O_BATTLE_HAND`/`O_BATTLE_AUTO`
  （战斗已开打）立即 return，让 `battle_before` 走到 `ensure_auto_battle` 切回自动。
  新写战斗前置流程时同样要回答"这个循环最坏情况怎么退出"

## 10. 切换御魂

- 复用 `SwitchSoul` 组件：`ui_goto(page_shikigami_records)` →
  `run_switch_soul('组,队')` 或 `run_switch_soul_by_name(组名, 队名)` → 回主界面
- 配置用 `tasks/Component/SwitchSoul/switch_soul_config.py` 的 `SwitchSoulConfig`
- 切换御魂后可能触发御魂不一致提示，`battle_before` 内已自动处理

## 11. 调试技巧

- **远端抓图**：`adb -s <serial> exec-out screencap -p > xxx.png`（MuMu 多开用
  adb connect 127.0.0.1:16xxx 对应端口），排查"卡在哪"先抓图再看日志
- **验证 i18n 下发**：`ConfigModel().script_task('TaskName')` 直接得到前端会收到的
  结构化数据，检查 title/description 是否已翻译
- **验证模板**：见第 3 节，注意 RGB/BGR
- **验证资产/导入**：`./toolkit/python.exe -m py_compile ...` +
  `import tasks.<TaskName>.script_task`
- 日志里的 `WARNING ui_click timeout` / `Failed recognize ...` 是定位卡点的重要线索，
  通常意味着模板在该页面失配（先怀疑状态差异，再怀疑坐标）
- dev_tools 下临时调试文件用完及时删除

## 12. Git 工作流注意事项

- 分支 `Tokisaki` 跟踪 `fork/Tokisaki`（origin 是作者的 gitcode，不要动）
- **`dev` 是上游作者的分支，绝不能往上面推任何东西**（2026-10-09 误推已强制撤回）：
  两个工作分支是 `fork/dev`（上游 dev 镜像，只 fetch 不 push）和
  `fork/Tokisaki-dev`（本地 `Tokisaki-dev` 的远程，跟踪关系已修正为
  `Tokisaki-dev -> fork/Tokisaki-dev`）。推送一律 `git push fork Tokisaki-dev`，
  写 `HEAD:dev` 是错的。本地已装 `.git/hooks/pre-push` 钩子：向任何远程的
  dev/master 推送都会被直接拒绝并提示正确命令，误推从机制上杜绝
  （注意：hooks 不随仓库同步，重装/换机后需按 `.git/hooks/pre-push` 重建）
- **改动必须先 commit**：`update_tokisaki.bat` 更新时要做 rebase，未提交的改动会挡住
- 用户手工改动过的文件（如 `tasks/Hyakkiyakou/*`）提交时注意区分，不要混入无关变更
- 推送报 `TLS connect error: unexpected eof`（schannel + 7890 代理）时加
  `-c http.sslBackend=openssl`；curl 正常而 git 报错即此症状

---

## 14. 对弈竞猜：活动改版模板失效与防重启时间驱动设计（2026-10-01）

- **活动 UI 改版后模板"集体失配"的特征**：任务进入页面后所有状态模板同时 miss、
  日志 `Waiting for set()` + 60 秒后 `GameStuckError` → 重启游戏 → next_run 已过又立刻
  重跑 → 反复重启。定位方法：拿报错截图对模板做**多尺度 matchTemplate**（0.7~1.4 步进 0.025），
  十周年对弈竞猜在 0.85 倍全中（0.99）→ 整套 UI 缩放了 15%，模板必须按新截图重裁。
  常见诱因：网易活动改版/换皮，旧 ROI 和旧阈值全部作废。
- **时间驱动型活动任务别依赖固定场次表**：用页面上的倒计时 OCR（注意 Duration 模式
  正则要求 H:MM:SS，"MM:SS" 会解析失败返回 None，改 Single 模式自己 parse）实推结算时刻，
  `set_next_run(task, target=绝对时刻)` 直接给调度器定目标；估错了下次到点会再校正，自愈。
- **休息/不可参与态要约到“下一个可操作窗口”而不是“下一场开场”**：2026-10-01 实测 8:33 休息
  被排到 10:03（下一场开场+3min），但下注窗口是 11:45（结算前 15 分钟），开场≠可操作；
  且场次表本身写错（首场实际 10:00 开）。改法：按结算时刻表推 `下一场结算 - before_end`，
  窗口已过就顺延到再下一场；开场+3min 只用于“进不了页面需要重试”的场景。
- **这类任务必须自带防重启**：主循环每轮 `stuck_record_clear()`（60 秒卡死保护交给任务自己的
  软超时 Timer 兜底，超时走 存截图+推送+改期 30 分钟，绝不 raise 卡死异常）；
  纯网络请求循环（如拉大神博主动态）同样要定期保活 + requests 全部带 timeout。
- **判"下注/购买类操作是否成功"要找不依赖新素材的判据**：如双鼓消失、页面离开原状态；
  弹窗内部按钮素材没到位时，宁可走失败路径推送通知，也不要盲点（涉及真实金币）。
- 相关文件：`tasks/FrogBoss/`（README 记录完整流程与待补素材清单）。

## 15. 首领退治：未开启等待界面的无限空转与退避重进（2026-10-03）

- **现场特征**：定时/寮活动监控拉起时退治还没开，进入后停在未开启的等待界面，
  日志每 ~23s 一条 `Enter demon_retreat false` 无限刷（10-03 现场 oas2/oas3 各空转
  350~440 轮、7 小时以上，整个调度器被这一个任务堵死，其他任务全部排不上）。
- **根因两个叠加**：① `goto_demon_retreat` 的 `I_RANK_LSIT`（"首领退治"标题）分支
  原实现只有 sleep 无计数无出口，循环唯一的退出条件 `goto_demon_retreat_num >= 5`
  只在点 `I_HUNT` 时递增，进了界面后就永远凑不够；② 该界面的返回箭头与
  `I_DEMON_BACK_CHECK` 模板不一致点不到，日志里 9 分钟一条返回点击都没有。
  设备 60s 卡死检测也不触发——没有 `stuck_record_add`，纯 sleep 循环不判卡死。
- **修法（退避重进，2026-10-03 已提交）**：等待界面不自动刷新开启状态，必须退回庭院
  重新进才会更新。`not_open_count` 计数，每轮回 `_exit_demon_retreat()`（依次尝试
  `I_DEMON_BACK_CHECK` → `I_UI_BACK_RED/YELLOW/BLUE` 通用返回链，60s 上限，识别到
  page_main/page_guild/page_town 任一已知页即设 `ui_current` 返回）→ `goto_main()`
  → 停 30s → 重进；第 2 次仍未开启（`NOT_OPEN_REENTER_COUNT`=2，用户指定）先退出再
  `return False`，交给 `run()` 既有失败路径 `set_next_run(success=False)` 推到第二天
  （failure_interval 配置 1 天），寮活动监控后续检测到开启通知仍可随时插队拉起。
- **等待界面截图（用户提供）离线验证**：`I_RANK_LSIT` 0.998 命中（就是它判定"未开启"
  等待态）；该界面左上是标准黄箭头，`I_UI_BACK_YELLOW` 0.985 命中 @(38,24)，通用返回链
  可退出。注意开启窗口为周六 10:00~23:00、由会长/副会长**手动开启**，定时 10:00 拉起时
  没开大概率是寮还没开，不是客户端状态过期——所以重进一次确认即放弃，别恋战。
  离线验证模板对截图时：RuleImage 按 RGB 加载，cv2 读图须先 BGR2RGB，命中判定要拿
  匹配坐标 (x+loc) 与 roi_front 求交，别只看分数。
- **通用教训**：任何"等某个状态出现"的 while 循环，计数器必须放在**循环内实际观察到的
  状态分支**里递增，不能只依赖某个点击动作；界面专属返回模板点不到时要有通用返回链
  （I_UI_BACK_RED/YELLOW/BLUE）兜底，超时宁可抛错走重启也不要无限空转。
- 相关文件：`tasks/DemonRetreat/script_task.py`（`goto_demon_retreat` / `_exit_demon_retreat`）。

## 16. 组队战后"继续邀请"弹窗：淡出动画二次匹配 + 无出口循环卡死（2026-10-07）

- **现场特征**：御魂/觉醒队长第一把正常打完、"是否继续邀请"弹窗正常点掉，队员接受
  邀请进了房间，但队长永远不点挑战；60 秒后 `GameStuckError: Wait too long` 重启游戏、
  房间解散。日志特征是相隔 ~1.7s 的两行 `Click default invite`（general_invite.py:0540），
  第二行之后零点击。错误截图画面是**无弹窗的组队房间**（队员已在位、挑战按钮可见）。
  10-03 起 oas3 每一次队长战斗收尾都中招（御魂+觉醒全灭），09-30 同代码还是单触发正常。
- **根因两个叠加**：① `check_and_invite` 开头只看单帧 `appear(I_GI_SURE)`，而点完确定后
  弹窗有淡出动画，过渡帧会让 I_GI_SURE（固定 roi 0.8）连同复选框模板再匹配上一次，
  函数被误触发第二次——09-30 单触发、10-03 起变双触发，代码与模板均未改过，是游戏端
  改了弹窗关闭表现；② 第二次进入后卡在勾选框循环：弹窗已消失，I_I_DEFAULT/I_I_NO_DEFAULT
  （固定小 roi）永不匹配，既不 break 也不点击，循环无超时无"弹窗消失"出口，只剩截图
  空转，60s 无点击被设备卡死检测击杀。`invite_again` 里有一模一样的循环（含无超时的
  外层等待），目前无调用点但同属一颗雷。
- **修法（最小改法，2026-10-07 已提交）**：勾选框循环每轮先判
  `if not self.appear(self.I_GI_SURE): return True`——弹窗没了就结束（误触发路径在此
  直接返回，顺带避免落进确认循环对着空画面补一枪确定）；成功路径照旧
  I_I_DEFAULT → break；再套 `Timer(10)` 兜底，超时告警后交给既有确认循环收尾。
  误触发本身无害（下一轮外层检查即 False），致命的只是无出口。
- **通用教训**：等弹窗内元素的 while 循环，出口必须包含"**弹窗整体已消失**"分支——
  弹窗动画（淡出/回弹）会让模板在关闭前后闪烁性命中，任何"单帧 appear 就认定弹窗在"
  的入口检查都可能被过渡帧骗进去；进去之后若只等弹窗内元素，就是必死循环。
  固定 roi + 阈值 0.8 的模板对动画中间帧尤其敏感。配套原则见第 6/7 节。
- 相关文件：`tasks/Component/GeneralInvite/general_invite.py`（`check_and_invite`，
  6 个调用点：御魂×2、觉醒、永生之海、朽木之海、羁绊）。

## 17. dev 基线迁移：重放自研修复到新版页面导航体系（2026-10-07）

背景：Tokisaki 分支整体切换到上游 dev（fork/dev `5bc3f6e2`）为新基线，重放本地保留项。
dev 自 09-18 起整替换了 `tasks/GameUi`（旧 `ui_goto/ui_goto_page/ui_get_current_page/
ui_page_appear` 已全部删除），本次按"dev 文件为底 + 三方应用本地补丁 / 整体搬文件 + 机械
换 API"两条路线完成 5 个提交（`1eb248a9..0f2c0739`，64 文件）。

- **新 API 速查**：`ui_goto/ui_goto_page(X)`→`goto_page(X)`；`ui_get_current_page()`→
  `get_current_page()`（失败返回 None 不抛错）；`ui_page_appear(p, skip_first_screenshot=False)`
  →`match_page_once(p)`（用当前帧，不再截图）；`self.ui_current = p` 直接删（goto_page 自带
  两帧识别+Dijkstra 寻路+未知页恢复，超时抛 `GamePageUnknownError`——旧 ui_goto 失败是静默
  返回，**语义差别要看调用点是否依赖"失败继续"**）。`ui_click/ui_click_until_disappear/
  ui_get_reward/ui_reward_appear_click` 仍在（移到 base_task.py），不用改。
- **任务本地页面**：`page.link(button=X, destination=Y)` → `page.connect(Y, X, key="a->b")`
  （连接方向=从本页出发；key 显式命名）。`Page.check`/`additional` 变为 recognizer 组合器
  （any_of/all_of）与 `add_enter_success_hooks`。registry 自动扫描 `tasks/*/page.py`，无需
  登记到门面（现世妖约 page.py 是现成范例）。
- **assets_extract 现已可安全重跑（2026-10-10，7e6ec531）**：全部任务（含 Component）的
  image/click/ocr/swipe/long_click JSON 已按 assets.py 真值反向重建补齐，dry-run 对比
  extractor 输出与现行 assets.py 完全一致（0 差异）。历史遗留的 OCR 字段混入 click、缺
  mode/threshold、同名重复副本、图像+OCR 字段混写等污染已清理。注意两点：① 以 assets.py
  为准手改时务必同步改 JSON（两边不一致时以 assets.py 为准，GUI 编辑则反向同步 assets.py）；
  ② 大规模改 JSON 后跑 extract 前，先用 extractor 的 dry-run 对比脚本验证一遍（临时把
  `AssetsExtractor.write_file` 置为 no-op 再对比解析结果）。
- **（历史）手写资产清单曾会被 assets_extract 洗掉**：`tasks/GameUi/assets.py` 尾部的
  `O_BATTLE_AUTO`/`O_BATTLE_HAND`（战斗自动/手动 OCR，9236651f 重写时曾丢失导致引用方
  AttributeError；ensure_auto_battle 与预设跳过依赖它们）——现已补入
  `tasks/GameUi/additional/ocr.json`，不再怕 extract；`tasks/Hyakkiyakou/slave/hya_slave.py:223-`
  的 5 条 `O_HYA_*` 是内联定义（跟文件走，不踩雷）。
- **三方应用补丁套路**：`git diff 37a884ef Tokisaki -- <file> | git apply --3way`，hunk 不
  重叠即干净通过（本次 general_battle/battle_wait/base_task 全干净）；冲突手工并集。本地
  fork/dev 引用名里的 `/dev:` 会被 MSYS 路径转换吃掉，需要时改用工作区文件或加引号。
- **验证清单（本次全过）**：迁移文件旧 API 残留 grep=0；资产引用 hasattr 静态核查；
  20 模块 import 冒烟（toolkit/python.exe，注意脚本要 `sys.path.insert(0, repo)`）；
  SCHEDULER_PRIORITY 无重复且新旧任务都在；PageRegistry 出边核对；31+10 项 pytest。
- **FrogBoss 决策**：本地重做版弃用，保留 dev 的 OAS 策略版（枚举 `Oas`，本地配置里的
  `frog_dashen_specific` 首跑回落默认，需在 GUI 重配）；本地 i18n 的 frog_* 键保留（dev
  策略枚举值 frog_majority/frog_dashen 正好复用）。
- 遗留实机验证项：ensure_auto_battle 的 roi 在当前 UI 表现；goto_page 超时抛异常的新语义
  在各任务的容错路径；对弈竞猜 dev 版全流程。

## 18. 通用战斗：点准备可能落空，必须验证点击生效再认定进入战斗（2026-10-09）

- **现象**：逢魔小怪（DemonEncounter `_battle` → `run_general_battle`）卡在准备界面，日志里
  BATTLE_AUTO/BATTLE_HAND OCR 空转 8 秒后报 "Battle is in manual mode and switch to auto failed"，
  卡死截图里右下角准备按钮（I_PREPARE_HIGHLIGHT 匹配 0.94）明明还在。
- **根因**：`battle_before` 里 `appear_then_click(I_PREPARE_HIGHLIGHT)` 命中后**不验证点击是否
  生效**，直接认为"已点过准备"并触发 `ensure_auto_battle`。点击被游戏吞掉（网络/动画落点偏移）
  时仍停在准备界面：左下角是预设按钮，OCR 读不到"手动/自动"，15 秒超时 → GameStuckError。
- **修复**：点准备后等最多 3 秒，`is_in_prepare` 持续为真且准备按钮重新可点则重试点击；
  离开准备界面（过渡动画/开打）才退出确认循环。c84da812。
- **通用教训**：任何 `appear_then_click` 之后如果后续状态机把"点过"当"生效"，都要补一次
  状态回读验证——准备按钮、确认弹窗、领奖按钮这类点击落空后无报错只留原界面的，尤其要验。

## 19. 结界蹭卡：经验酒壶满额格式带溢出加成，识别框裁掉开头会反复点提取（2026-10-09）

- **现象**：经验已领满（界面「今日已领取 48000/40000+8000」）时，`_check_exp_box` 仍连点
  `I_EXP_EXTRACT`，约 10 次后 `GameTooManyClickError` 触发重启。日志里 OCR 一直是
  `[BOX_EXP] [00/400008000]`。
- **根因两层**：
  1. `O_BOX_EXP` 的 roi `(654,538,179,39)` 是按「今日已领取xxxx/40000」标的，带溢出加成后
     整行变长且左移，框从 `48000` 中间才开始，只读到 `00/40000+8000`。
  2. `DigitCounter.after_process` 只保留数字和 `/`，加号被丢弃，`40000+8000` 粘成
     `400008000`。满额判断 `cur == total` 永远不成立（0 ≠ 4 亿），于是继续点提取。
- **修复**：roi 左移加宽到 `(600,538,260,39)`（`utilize/ocr.json` 与 `assets.py` 同步改）；
  满额判断改为直接对裁剪区域做 `model.ocr_single_line`，绕开 DigitCounter 后处理，
  用正则取 `/` 前的已领数与基础上限比较（溢出加成不计入上限）。已领满时先点
  `I_UI_BACK_RED` 关掉酒壶弹窗再 `_exit_to_realm`。
- **验证**：用 `log/error/1791558069766` 的报错截图实测，新 roi 原始识别为
  `48000/40000+8000`（得分 0.97），判定已领满。
- **注意**：`DigitCounter` 的后处理是所有计数 OCR 共用的，没有改它；以后再遇到
  `xxx/yyy+zzz` 这种带加成的计数，不要直接用 `O_xxx.ocr()` 的三元组，按原始文本解析。

## 20. 磐长故地爬塔：改素材必须重启进程，模块缓存在 sys.modules（2026-10-10）

**现象**：I_LOCK 素材与 roi 更新并提交后，实机 `wait_until_appear(AS_LOCK)` 仍然次次
2 秒超时；同一张截图离线 `RuleImage.match` 却是 1.0 命中。

**根因**：OAS 是常驻进程，任务模块（含 assets.py 的 RuleImage 对象、模板 png 的内存
副本）在首次 import 后缓存在 `sys.modules` 里，之后每次调度复用缓存。进程 01:47 启动、
16:06 首跑缓存了旧素材，17 点提交的新 roi/新 png 对它永远不可见。

**规则**：改动 assets.py / 模板 png / 任务逻辑后，**必须重启对应的 OAS 实例进程**再实测；
"离线验证通过但实机不生效"时先查进程启动时间是否早于改动时间（`head -1 log/日期_实例.txt`）。

**附**：本次同场修复——阵容锁开关两个状态各建一个模板（锁定=紫角挂锁 I_LOCK，解锁=
黑底金锁 I_UNLOCK），同位不同形互斥验证，交叉验证得分 1.0 / 0.52，阈值 0.8 余量充足；
lock_team 点击后用另一态出现做确认，3 次未确认则带警告放行。

## 21. 为崽而战（寝肥合战）：mixin 顺序坑与通用返回/按钮素材地图（2026-10-10）

- **组件 mixin 含 RightActivity 时必须放基类列表第一位**：`RightActivity(GameUi, ...)` 自身继承
  GameUi，写成 `(GameUi, ..., RightActivity, ...)` 会直接 `TypeError: Cannot create a consistent
  method resolution order (MRO)`。通用规则：组件类按"继承层次深的放前面"，RightActivity 这类
  已自带 GameUi 的组件放最前（FrogBoss 的 `class ScriptTask(RightActivity, ...)` 是现成范例）。
- **通用返回/按钮素材实测地图**（裁新模板前先对这张表）：
  - 深色圆底橙色 ↩ 返回箭头（集结/战斗等大地图场景左上角）= `I_UI_BACK_CIRCLE`，实测 0.94；
  - 活动页左上角屋顶形黄返回 = `I_UI_BACK_YELLOW`（0.98）；
  - 活动页左上角猫形回庭院小按钮 = `WeeklyTrifles` 摸鱼任务的
    `touch_fish_wt_tf_goto_main.png`（0.99，`ActivityShikigami.I_HOME_EXIT` 同款 0.92），
    直接复制 png 到本任务 res 目录即可，不必跨任务 import 别人的 Assets 类（避免 mixin
    属性名冲突静默覆盖）；
  - 弹窗粉叉 = `I_UI_BACK_RED`（寝肥合战·晚弹窗实测 0.918）。
- **全屏搜索模板（roi_back=0,0,1280,720）上线前必须做全截图互检**：对仓库现有各界面截图
  逐张跑 matchTemplate 记录最高误报分，阈值至少留 0.3 余量。本次"手动切换"扇子图标
  （55x50 特写、出现位置未知）全屏搜索最高误报 0.42，阈值定 0.75；注意金色的"阴阳术"
  扇形按钮是形状相近的高危误报源。
- **assets.py 手写与 extractor 输出 raw 顺序不同没关系**：extractor 按 rglob 顺序
  （click.json 在前）拼接，而现行各任务 assets.py 都是 Image 段在前——对比时按
  "规则行集合相等"判 0 差异即可（现世妖约基线同样如此）；GUI/extractor 重跑会自动归一。
- 任务实现：`tasks/NeiFeiHeZhan/`（为崽而战→寝肥合战自动参战，11:30/20:00 两场，
  倒计时 OCR 改期防干等，流程见其 README.md）。

## 21. 转场与点击的等待约定：点完要等，认层要留轮数（2026-10-10）

**现象**（磐长故地退出链实测）：`exit_activity` 认层循环里点完"回退箭头"后立刻继续
截图认层，界面还在 1~2 秒的转场/加载中，什么都匹配不上，8 轮循环在 2.2 秒内被空转
烧光，提前告警退出，最后靠 goto_page 兜底才回家（4f915489 修复：每次点击后 sleep(1)）。

### 约定

1. **点击触发转场/弹窗/页面跳转后，sleep(0.8~1.5s) 再继续下一轮识别**。
   转场期间的截图是加载帧，任何模板/OCR 都不会命中——空转轮数会按每轮 ~0.3s 烧掉。
2. **认层循环的轮数按"最坏点击次数 × 2 + 余量"给**（如三层退出链给 8 轮），
   并且每轮必须"有进展才算一轮"：要么点了东西，要么到终点；否则就是转场没等够。
3. **状态切换类点击必须验证生效**：点完等"对侧状态出现"再走（如阵容锁：点解锁后
   等 I_UNLOCK 出现，见 lock_team 双态互斥）；点了不验证 = 可能落空（与第 18 节
   "点准备落空"同源）。
4. **appear_then_click(interval=N) 只保证同名按钮不连点**，不保证点击生效、也不等待
   页面响应——需要生效确认的场合自己加验证。
5. **ui_click(click, stop=X) 的 stop 判据必须是目标层稳定可见的元素**，且沿途每一层
   都要有分支可走。反例：退出链 stop=I_TO_BATTLE_MAIN 只在活动主页出现，地图页没有
   任何判据 → "迷路"；正例：认层循环给每一层都配判据（I_CHECK_BATTLE_MAP /
   I_CHECK_ACT_MAIN / I_CHECK_MAIN），到哪层点哪层的返回。
6. 相关联的既有约定：弹窗淡出动画会造成二次匹配（第 16 节）；长等待循环每轮
   `stuck_record_clear()`（第 7 节）；OCR/模板识别前先确认页面已稳定（等判据元素
   出现再识别，不要在转场帧上 OCR）。
7. **卡死白名单会被任意点击清空**（2026-10-10 oas3 实测）：`stuck_record_add('BATTLE_STATUS_S')`
   给的是 300 秒长窗口，但每次点击都经 `handle_control_check -> stuck_record_clear()`
   把整个白名单连同记录一起清掉——登记后只要还有点击（点预设/点准备/绿标/随机滑动），
   战斗中实际只剩"最后一次点击后 60 秒"的预算，长战斗（爬塔可达 5 分钟）必误判
   GameStuckError。修法：battle_wait 主循环每轮守卫式补登
   `if 'BATTLE_STATUS_S' not in self.device.detect_record: detect_record.add(...)`，
   点完被洗掉 0.3 秒内自动补回（54b11854）。其他任务自己写的长战斗循环同理，
   要么循环里补登，要么参考 SixRealms 在关键点击后手动 re-add。

## 22. 弹窗按钮全面改版（2026-10-10）：确认/取消/勾选框模板批量失效（2026-10-10）

**现象**：组队战后"是否邀请队友继续进行战斗?"弹窗按钮从圆角深红描边改成扁平等宽+
两侧菱形新样式（确定文字也从"邀请"语义变为"确定"），`I_GI_SURE` 对新弹窗实测仅
0.043，队长续邀请链路（check_and_invite/invite_again）完全失灵。同批失效的还有
`I_GI_CANCEL`(0.153)、`I_I_DEFAULT`/`I_I_NO_DEFAULT` 勾选框两态（0.08~0.17，新样式
为深色圆形底+米色对勾）。

**修法**（用户裁新图替换，双边同步 roi）：
- `gi_gi_sure.png`→(664,407,180,65)、`gi_cancel.png`→(436,407,180,65)（新按钮统一
  180x65 规格，确定按钮与已更新的 `I_UI_CONFIRM` 同图源）；
- `gi_i_default.png`→(546,345,31,32)、`gi_i_no_default.png`→(545,345,32,32)；
- 验证口径：新图对全屏截图正向 ≥0.97，勾选两态互判 ≤0.63（0.8 阈值余量充足），
  对无关旧截图全屏搜误报 ≤0.67。

**教训**：
- 按钮样式改版是全局性的，"点按钮→等弹窗→点确定"链路里任何一环模板失效都会空转
  到 TooManyClick/GameStuck。再遇"点了按钮但确定没点到"先取最新报错截图离线跑
  匹配分定位，别急着改流程逻辑。
- 勾选框两态外形相近时裁剪尽量聚焦差异区（对勾本身），全圆裁剪互判 0.771 余量薄，
  内圈 31x32 裁剪互判降到 0.61。
- 尚未验证的同族嫌疑素材（改版全局扩散，实机报错再按同法换图）：~~`I_INVITE_ENSURE`~~
  （已于 2026-10-16 确认实锤并换图，见第 25 节）、队员端 `gi_i_accept*/gi_i_reject`（接受/拒绝弹窗）、以及
  各任务目录下残余的旧圆角式 *_confirm/*_ensure 模板（AbyssShadows/BondlingFairyland/
  DemonEncounter/Dokan×6/Exploration/FloatParade/Summon/HeroTest/RichMan/SixRealms/
  TalismanPass/TrueOrochi/WantedQuests/WeeklyTrifles/XianShiYaoYue 等均有）。

> **2026-10-14 合并后状态**：上游 10-11 起对同一批按钮做了"共享素材化"修复并已合并
> 进来——`I_UI_CONFIRM/I_UI_CANCEL/I_UI_CHECK/I_UI_UNCHECK` 换新图+加宽 roi_back、
> 新增 `*_OLD` 旧版保留；gi 专用 4 素材、`ss_sou_switch_sure`、12 套皮肤确定键、
> `gb_exit_ensure`、`res_fresh_ensure`、`res_get_reward`、Restart 登录/邮件弹窗素材
> 全部删除并改指共享素材。本地换图的 `I_INVITE_ENSURE`（上游漏改，旧 roi 实测 0.17）
> 与 `as_unlock.png`（上游未动）按"先他一步"原则保留本地新图新 roi。详见第 23 节。

## 23. fork/dev 合流：弹窗按钮收敛共享素材 + ActivityShikigami 归属拉锯（2026-10-14）

**背景**：fork/dev 5bc3f6e2→4c688865（45 提交，全部在 tasks/）合入 Tokisaki-dev，
合并基 ff594d1c，实测 49 个冲突。总策略：**弹窗按钮类与全部冲突整体取 dev**；
"本地先他一步更新且上游漏改"的素材保留本地；对本地更新的连带影响逐一同步修复。

**合流决策记录**：
- **ActivityShikigami：先取 dev 后回退，最终=本地重做版（ef9eadf7）**。dev 10-11 针对
  当期活动换了 8 张图+4 处 roi（remain_pass 791→1153 与本地 71341a03 同 bug 独立修复），
  也重做了 `_run_pass`，合并时按"有更新就取 dev"整体采用；同日用户决定**门票模式改回
  本地 Tokisaki-dev 版**（本地 15+ 提交重做：skip_story 剧情跳过链、确定性退出链、
  连战恢复、goto_page_safe 防准备页残留崩溃、双态阵容锁、网格结算 battle_activity.py），
  整任务目录从 backup/pre-merge-dev-20261014 恢复。恢复时顺带修两处：
  as/image.json 的 unlock 条目同步 assets.py 验证 roi（本地遗留未同步），以及
  battle_activity.py 补上缺失的 `import random`（2% 分支 NameError 隐患）。
  **dev 版后续若再更新此任务，需逐提交人工评估再合，不能整目录覆盖。**
- **GeneralBattle 结算兜底无需二选一**：本地网格结算改的是 success 钩子
  `_bw_success_activity`（后已搬去活动任务），上游 27241886 改的是 completion 钩子
  （本地零改动），时序互补（success"Get all reward"后才 enable completion）。
  自动合并后两边并存：上游 C_END_MASTER 大禁区、兜底 3s/最多 5 次强制 DONE 进来，
  本地 BATTLE_STATUS_S 守卫、切自动模块、battle_before 重试全部健在。
- **保留的本地资产（上游遗漏）**：`gi_invite_ensure.png`（好友列表邀请确定，上游仍是
  旧图旧 roi、实测 0.17 失效）与 `as_unlock.png`（黑底金锁解锁态）——保留本地新图，
  roi 补本地验证值并双边同步。`I_HOME_EXIT`/`I_BACK_ARROW`（navigator 未知页恢复用）
  定义随 dev 版 assets.py 被覆盖，**import 冒烟抓到 AttributeError 后补回**。

**同步修复清单**（合并后的连带影响）：
- 淡出误触发修复（原 0f2c0739）重移植到 dev 新版 `check_and_invite`：出口判据
  I_GI_SURE→I_UI_CONFIRM，保留 Timer(10) 超时。
- 删除孤儿文件 `battle_activity.py` + `as/as_grid_anchor_*.png`（dev 版 script_task
  不再引用；顺带消掉其缺 `import random` 的 NameError 隐患）。

**验证方法沉淀**（合并动素材后必做）：
1. `git grep` 被删素材名 → 无残留引用；
2. **全量悬空扫描**（比 grep 更强）：正则抽全部 assets.py 的 `^\t[IOCSL]_\w+ *=`
   定义集，再扫 tasks/、module/ 全部 .py 的 `self.X_…|xxxAssets.X_…` 引用求差——
   本次靠它+import 冒烟抓到 grep 抓不到的 I_HOME_EXIT；
3. `PYTHONPATH=. toolkit/python.exe -c "import …"` 对合并涉及模块做 import 冒烟；
4. 素材文件存在性扫描（引用的 file="./…" 逐个 os.path.exists）：本次 31 个缺失全部
   为上游历史遗留（fork/dev 同样缺），合并零引入。

**assets_extract 现状（重要）**：方向是 **JSON→assets.py**（不是反向）。上游自己的
assets.py↔JSON 存在漂移，合并后跑 extract 会删掉 4 个在用定义
（I_CONFIRM/I_CONFIRM_CLOSE_DIFF_SOUL/I_DISABLE_7DAYS_DIFF_SOUL/I_GREED_GHOST）、
复活死条目（C_GRID_* 等），**现阶段不要跑**；要恢复"extract 0 差异"需按 7e6ec531
的流程把全任务 JSON 重新按 assets.py 反向重建（独立 chore，待做）。

**实测回归清单**（合并后首跑观察点）：重启进程 → oas3 门票爬塔（本地重做版
`_run_pass`，即恢复后的原流程）→ 组队邀请链（淡出修复+共享勾选框）→ 探索
（UP 类型自适应滑屏）→ 斗技（ui_click 超时上限）→ 现世妖约（I_UI_CONFIRM 新
roi_back 回归）→ 获得奖励浮窗识别（dev 裁剪 y≈126 vs 本地旧裁剪 y≈239，理论可覆盖）。

## 24. 结界挂卡按序选卡：跨组坐标失配与低星窄条素材（2026-10-14）

**跨组坐标失配（已修）**：`_select_card_by_order` 按连续同类型分组搜索，命中最优卡后若
继续搜后面的组，卡类型下拉会把列表切走，点击却仍用命中时那套坐标 → 点到新列表同一
位置的其他卡。oas2 曾连续 4 天把"5星太鼓"挂成斗鱼列表同位置的低星卡（22:59→23:00→
14:59→06:59 四天 OCR 时长各不相同即为铁证），直到挂出 1 星斗鱼才被发现。修复：点击前
若类型被切走或列表滚动过（`last_type != best_type or best_swipes != swipes`），切回最优
卡类型并回顶重扫一次取新坐标；重扫不到按"整列无匹配"交回回退/严格提醒。

**素材全量重做（2026-10-14 完成）**：旧 8 个 `I_CARDS_*` 里 4 星是珠子窄条（TAIKO4
阈值 0.85 两周零命中，用户实锤列表里明明有 4 星太鼓；FISH4 阈值 0.7 靠 0.713 贴地飞），
3/5/6 星是含卡面大图。整卡面方案被数据否决：**美术区占面积太大导致相邻星级交叉得分
0.97+，模板原理上分不出星级**——旧 FISH5 对 4 星斗鱼打 0.966~0.981，"Found card FISH5"
点中的未必是 5 星。星级唯一可靠特征 = 珠子行（固定 6 槽，橙珠数=星级）。

新方案（窄条 + 双判据门）：
- 8 个模板全部重裁为**珠子行窄条**（89×18~21，x191-280，含珠行上下各 2px），
  `roi_back` 统一列表列 (150,145,170,520)，阈值统一 0.93。素材来源 = 用户提供的
  1280×720 整屏截图（log/template_review_20261014/ 有裁图脚本与验证脚本）。
- **注册必须两处手工同步**：`tasks/KekkaiActivation/assets.py` + `tasks/KekkaiActivation/cards/image.json`
  （assets_extract 现阶段不可跑，见第 23 节；漏改一边则未来重建 JSON 时回退）。
- 命中后走 `_match_gate_ok` 双判据门：框内**橙珠计数=目标星级**（cv2 连通域，
  面积≥40）+ 框上方 8px 卡面**暖色差 R-B 符号=目标类型**（太鼓 +77~+102，斗鱼
  -24~-35，间隙 120+，比任何模板分都稳）。门不过记 warning 丢弃，按未命中处理。
- 验证数据（4 截图 13 条目）：同星最低 0.9573（太鼓5跨屏，亚像素滚动），同类型相邻星
  最高 0.901，阈值 0.93 两侧各 ~0.03 余量；跨类型同星 0.950~0.953 靠类型判据拦
  （单阈值拉不开，间隙仅 0.004）。16 原始命中 → 门后 13 全对、0 误报。
- 教训：**整卡面模板在这个 UI 里根本分不出星级**，别再走"大图更稳"的直觉；窄条+
  程序化判据（颜色计数）比纯模板匹配抗老化得多。
- 实机生效需重启调度进程；上线后首周留意日志里的 `Gate mismatch`（素材老化前兆）
  与挂卡结果截图。

**首屏早退挂错星 + 阈值下调（2026-10-19）**：用户实锤"明明有 3/4 星却挂了 5 星"。
根因=卡列表按星级降序，高优先级的低星卡压在首屏折叠线以下（搜索列 roi_back 只盖前
3 行），而 `_search_cards_in_list` 逐屏"命中即返回"，首屏有 5 星就永不下滑 → 优先级
语义退化成"有几星挂几星"；此前几天 4星/3星"挂对"只是高星恰好耗尽，不是逻辑在工作。
修复（方案一全列扫描）：`_search_cards_in_list` 滑到列表底（I_AA_SWIPE_BLOCK）取整列
最优下标；组内最优卡命中即提前收工；前面组一旦有命中不再搜后面组（分组连续性保证
后面组下标必然更大）；点击前回顶对最优卡单独重扫一次取新坐标（扫完整列后停留位置
已变，旧坐标必点错卡——这是第 24 节开头跨组失配修复的一般化）。
阈值 0.93→0.90（TAIKO4 历史得分 0.939~0.956 贴线）：0.90 下 5 截图（10-14 四张 +
当晚实况一张）16/16 条目全命中、0 误报——0.90~0.93 区间新增的相邻星/跨类型/太阴
命中全部被双判据门拦下（橙珠数=星级、R-B 符号=类型，两判据都与阈值无关），同星
最低 0.9573、余量 0.027→0.057。教训：**肉眼数珠子不可靠**——实况截图里图标饰边
会被算进珠子行（裁图 band 起点混进 art blob），肉眼把 4星 数成 5星；星级以门判据
像素级命中的客观位置为准。离线回归 stub 三场景（多帧跨屏选 3星 / 实况单屏选 3星 /
纯斗鱼选 FISH5）全过，脚本在 `log/template_review_20261014/{validate_th.py,
regress_select.py}`，须 `toolkit\python.exe` 跑（系统 python 缺 ppocronnx）。


## 25. 八岐大蛇队长邀请全灭：改版第二波与失败外传约定（2026-10-16）

**现象**：oas2/oas3 清晨大蛇双卡死。oas3（队长）建房成功→好友列表 OCR 认出目标好友
并点击→`No appear invite ensure while invite friend`→确定没点上、列表没关→房间空位
被弹窗遮挡，开战判据 `not appear(I_ADD_1)` 误判"队友已进房"→对空房连点挑战 10 次
GameTooManyClickError→重启×3→人工接管。oas2（队员）等不到邀请，`BATTLE_STATUS_S`
卡死记录从未清除，恰好 5 分钟硬重启×3 同日陪葬。**oas3 用户肉眼看到的"卡在创建队伍"
实为建好的空房间**（两个"+"位+目标字样），创建步骤日志上每次都点到了。

**根因**：10-10 弹窗改版第二波，而且这次是**按钮文字换了**：好友列表确认按钮从
"确定"改成"**邀请**"（战后弹窗反过来从"邀请"改成"确定"，第 22 节正好记了反方向）。
旧图对新按钮仅 0.69（边框同款、文字不同），10-11 起全部账号日志再无一次
`GI_INVITE_ENSURE` 成功点击。第一版修复误判为"像素级换样式"，把素材换成
`ui_ui_confirm.png`（还是"确定"）——实机一轮即被 genre=invite_ensure_missing 诊断
截图证伪：弹窗里根本是个"邀请"按钮。**根因层面"文字换了"和"样式换了"从截图上一眼
分不出来，必须拿到真实弹窗截图看字，别拿互匹分数猜。**

**修法**：
- `gi_invite_ensure.png` 裁自实机邀请弹窗的"邀请"按钮 (704,544,136,62)；roi_back
  (630,495,290,155)→(520,400,520,310) 兜住弹窗布局漂移；assets.py 与 gi/image.json
  双边同步。验证：用户截图与两份 genre 诊断截图全 1.0000 命中，对"取消"0.66、对
  "确定(ui_ui_confirm)"0.18，297 张历史 error 截图零误报。
- 失败必须外传，不许静默假成功：`invite_friend` 确定按钮 8 秒不出现→存诊断截图
  （`log/screenshots`，genre=invite_ensure_missing，120s 节流）+`close_friend_list`
  兜底关列表（左上返回→确定，8 轮上限）→返回 False；`invite_friends` 返回"是否有
  邀请成功"；`run_invite` 首邀失败直接返回 False（原来忽略返回值照常点火）。
- `run_invite` 等待循环里见 `I_INVITE_ENSURE` 先点掉（列表残留遮挡空位判定的自愈）。
- `click_fire` 加 6 次上限并返回"是否真的开战"（以离开房间为准），空房连点不再
  冲到 10 次爆 TooManyClick。
- `Orochi.run_member` 等待循环每轮 `stuck_record_clear()`——等待邀请期间画面静止
  无点击，任何固定 stuck 记录都会在 wait_time 到点前先触发 5 分钟硬重启（第 7 节
  约定在本任务的具体化）。

**教训**：
- 改版嫌疑素材的"实机报错再换"不能拖：队长链路坏掉会以每天双账号 5+ 次硬重启的
  代价烧调度（10-11 至 10-16 共 6 天无人发现，因为重启链会自愈成人工接管退出，
  不看日志根本不知道）。
- "点了但没点上/没反应"的假成功（原 invite_friend 确定不出现仍返回 True）是比
  识别失效更危险的一层：它把素材问题放大成对空房开战→爆点击→连环重启。凡"点了
  确定"类操作，要么以弹窗消失为成功判据，要么失败必须外传。
- 弹窗开着会遮挡后续判据：开战判据依赖空位模板，好友列表弹窗一挡就误判。等待循
  环里对"可能残留的弹窗"先做自愈点击再评估状态。
- 验证素材时 error 目录的截图是"死亡现场"（弹窗已关），要找含目标按钮的活体截图
  得去其他任务的成功日志时段翻；新旧模板互匹分数（0.69）是判定"样式变了"的最快
  手段。

---

## 26. 狭间暗域：集结正向等待、封印跳过与"当前区域扫完才算全封印"（2026-10-16）

背景：当日按用户要求把狭间回退成 dev 原版（仅保留已封印检测），三台机器实机跑出一轮完整故障，
据此把两条经过验证的修复以最小形式加回，并顺带修掉阵容切换与点准备的冲突。

- **dev 原版的两个必崩场景（2026-10-16 三机实测）**：①集结期被寮活动监控拉起——
  `wait_until_disappear(集结中)` 的固定 roi 模板随倒计时文字漂移失配提前返回，集结期就开打，
  挑战连点 10 次全部无效（游戏弹"请勿频繁点击"）→ GameTooManyClickError 重启
  （error 截图里右上角横幅还挂着"集结"是最直接的证据）；②部分封印后切区域——
  `change_area`/`select_boss` 只认未封印样式的入口书，弹窗匹配不上就无限循环点"更换领域"
  或盲点封印书坐标，同款爆点击崩溃（即 2026-10-09 用户报过的 RES_CHANGE_AREA ×10）。
  结论：**回退到 dev 解决不了这两个场景，只会把崩溃加回来**；"dev 没问题"只在
  "进攻期中途手动去跑、场上怪还活着"的旧使用方式下成立。
- **集结等待必须用正向信号**（`wait_rally_finish`）：轮询顶部横幅出现"进攻中"（I_IS_ATTACK）
  才算集结结束，"集结中"（I_WAIT_TO_START）可见只作日志；两个横幅模板的 roi_back 都放宽为
  `(420,50,460,55)`（固定 roi 随倒计时文字 2~4px 漂移就失配，见第 3 节；双模板互匹 0.58/0.78
  均低于 0.8 阈值）。循环每轮 `stuck_record_clear()` 保活，15 分钟超时走失败排期——
  寮活动监控横幅还在时会再次拉起，无需自建重试。
- **"后续区域全封印"≠"任务结束"**：`switch_area` 改为返回 bool，False 只代表后三个区域封印，
  当前区域可能还有活目标——智能伤害分支靠 `find_enemy` 自然耗尽收尾（切区失败就留在当前区域
  继续清扫）；非智能分支在当前区域扫过一轮后才允许抛 `AbyssShadowsAllSealed`。当日实测：
  后三区封印+神龙首领存活，旧写法宣告"全封印"收工时次数是 1/2/0，一分钟后监控再次拉起
  照样能打进神龙首领——**提前宣告比崩溃更隐蔽，次数没打满就结束等于白丢奖励**。
- **阵容切换与点准备的冲突**：`switch_preset_team` 点完确认就返回，游戏穿魂还要几秒，
  `battle_before` 紧接着 0.35s 就点了准备（oas3 阴间门实测），没换完的阵容被带进战斗。
  对策：预设启用时确认后固定 `sleep(6)` 再进入点准备流程（每任务只发生一次，代价可接受）。
  `switch_soul_one` 3 次点击队伍全失败仍打 WARNING 后照常报成功——曾试改"报 ERROR+等穿魂"，
  用户裁决切换御魂实际没问题、保持原样（2026-10-16 回退）；第 25 节"失败外传"约定在此场景
  由实际使用经验让位，但"点了没点上还报成功"类改动在其他操作上仍应遵守该约定。
- **资产改动双表同步**：assets.py 与 `res/image.json` 必须同一提交内手工同步改
  （assets_extract 当前不可跑，JSON→assets 方向会洗掉活定义，见第 17 节与 memory）。
- **2026-10-17 首夜实测补丁（oas3 三连卡死）**：集结正向等待与扫尾语义本身正常
  （日志 `Rally finished, attack phase started`、`stay and sweep` 均出现），但扫尾后盲点
  (360,300) 关弹窗被书签飘动动画吃掉，弹窗残留挡住战报按钮 → `find_enemy` 无点击空转
  60 秒 → GameStuckError ×3 → **进程直接退出（三次失败保护）**。修法：①关弹窗改点底部
  空白 (640,680)；②`switch_area` 返回前以"战报按钮重新可见"确认弹窗真关了（书本模板在
  封印进度徽章/浮动动画下 0.37~0.74 不可靠，不能拿来做弹窗判据）；③`find_enemy` 加
  `stuck_record_clear()` 保活 + 战报按钮 30 秒不可见时点空白驱散的兜底自愈。
  附带发现：入口书模板对带进度徽章的书（孔雀 97%）只得 0.55，接近封印的区域会被误判
  已封印跳过——区域基本清空时损失可忽略，多状态模板待补。

## 27. 悬赏封印 2026-10 大改版：卡片化主界面、圆圈大世界与新详情页（2026-10-28）

改版内容：悬赏封印主界面从竖排列表变 4 张横排卡片（协作任务带"协"角标+"邀请好友"
小按钮，最多 4 张）；探索大世界左侧任务从文字条目变圆形头像圈（N/M 在圈内、
"悬赏封印"标签在圈下）；详情页整体右移下移（类型徽章 x646、信息 x717、行距 76px、
前往 x1053），新增"式神碎片""妖气"两种目的地类型（当前跳过不打）。

踩坑与对策（均有截图实测支撑）：

- **旧版"蓝对勾"追踪标志（I_TRACE_TRUE）随改版消失**：详情页和大世界都没有了，
  `execute_mission` 原来靠"点击条目直到蓝对勾出现"判详情打开会死循环。改用 OCR
  "悬赏目标"行（O_WQ_TARGET，FULL+keyword）做详情打开判定，点击循环自带 20s 上限。
- **Single 窄框 OCR 会裁字丢数字**：类型框 76px 宽时"秘闻"读成"闻"、"式神碎片"读成
  "神码"；信息框偶发把"数量:4"读成"数量:"导致整条目的地被正则丢弃。必须整区
  `detect_and_ocr`（O_WQ_DEST 628,262,340,300）后按行中心 y 归组、按 x<715 分
  徽章/信息，三张详情图 12 条目的地全部读对。
- **OCR 丢尾括号会让正则丢目的地**："第十八章(数量：24"无闭合括号，原正则要求
  `[)）]` 结尾直接失配。先 `re.sub(r'[)）]+$','',s)` 剥尾括号，闭合改可选。
- **菱形角标用矩形模板=四角全是背景**：一键/取消追踪角标是 45° 菱形，背景一变
  （主界面卡片内容不同）得分从 1.0 掉到 0.4；且"取消追踪 vs 一键追踪"纯模板分离度
  只有 0.771，贴着 0.8 阈值。改用 `Masked template matching` + 同目录 `_mask.png`
  （fillPoly 菱形掩码，非零参与匹配），分离度拉开到 0.490，背景免疫。
  注意：**详情页的"取消追踪"是另一种描边样式**（主界面是实底大金字），与主界面
  模板只有 0.17——上下文分离验证时"跨页面不命中"不一定是素材坏，可能本来就是
  两套美术；按实际调用场景分别裁模板即可。
- **FULL+keyword 的 `ocr()` 返回命中坐标框，不是文字**：取文字用 `detect_text()`
  （单行）或 `detect_and_ocr()`（多条）。
- **OCR filter 有竖排逐字兜底**：keyword 匹配不上时会按单字跨条目拼配，详情页竖排
  故事文本被读成"悬赏"也能命中 keyword"悬赏封印"（is_wq_remained 只在探索大世界
  主循环调用，与详情页不共存，故无害；但复用这条 OCR 到其他场景时要小心）。
- **协作类型识别新逻辑**：先认卡内"邀请好友"按钮（新模板 wq_invite_btn，4 卡位
  roiBack），再读卡片奖励图标判类型；勾玉/狗粮/猫粮/寿司物品图标本身没换皮，旧模板
  直接复用只改 roiBack；金币图标普通任务卡也有，所以"协卡上没有其他类型图标"才
  推定为金币协。槽位从 3 扩到 4。
- **好友邀请弹窗（别人邀请你）走 GlobalGame 全局 `_burst()`**：挂在 base_task
  `screenshot()` 上每帧自动检测，按 `global_game.emergency.friend_invitation`
  开关接受/拒绝/仅勾协，接受后自动把 WantedQuests next_run 拉到立刻——机制现成，
  本次只更新了 6 个素材（新弹窗的接受/拒绝/关闭X重裁，勾玉/猫粮/狗粮只改 roiBack）。
  弹窗 X 不在 I_UI_BACK_RED 的 roiBack 内，IGNORE 必须用自己的 X 模板。
- **庭院"封"字入口**随当前庭院皮肤微调，对旧模板只有 0.81 压线，已从新截图重裁；
  I_UI_BACK_RED 对新版主界面/详情页 X 均命中（0.92/0.95），关闭流程无感。

遗留（无截图/未实测，动前先补截图）：① 邀请好友对话框保留旧素材（用户确认暂不改，
匹配不到会走"找不到好友→取消"安全路径）；② 勾玉协作卡片未见过实例，类型模板系
复用旧图标待实机验证；③ 大世界宝箱（I_WQ_BOX）位置沿用旧 roiBack 未实测；
④ cooperation_only 的 trace_one 改为"点卡片→详情→追踪角标→关闭X"，未实机验证；
⑤ 妖气/式神碎片目的地目前跳过，要支持需扩展 name_funcs。
