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
  道馆 `Dokan` 的 `dokan_battle_1` 与 `dokan_battle`（等准备按钮出现后调用）。
  斗技 `Duel.wait_battle` 保持 dev 原生的 `ui_click(O_D_HAND, O_D_AUTO)` 不动，
  不接入本模块，避免和上游 dev rebase 时冲突。
  新写战斗流程时直接调 `self.ensure_auto_battle()`，不要再复制一套 OCR 点击
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
