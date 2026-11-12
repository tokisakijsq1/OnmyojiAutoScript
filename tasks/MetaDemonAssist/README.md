# MetaDemonAssist 超鬼王协助

超鬼王活动「祸至无日/祸主降临」期间的守候型协助任务：在庭院实时监测好友的鬼王邀请横幅，
自动前往协助挑战，按星级决定是否勾选 2.5 倍伤害，打完列表内所有可挑战的好友鬼王后回庭院继续守候。

**与 MetaDemon（超鬼王主任务）的关系**：MetaDemon 是主动玩法（自己召唤/自己发现的鬼王）；
本任务只处理**好友发现**的鬼王（协助），两者可同时启用。UI 布局与 MetaDemon 同源（卡槽/按钮位置基本一致），
但素材均按 2026-11 当前活动重新裁剪验证（MetaDemon 的 `md_battle_demon` 对当前挑战按钮仅 0.52，不可复用）。

**自包含（2026-11-12 重构）**：页面图/素材/战斗判据全部任务内闭环，零跨任务依赖（AST 级检查
`log/mda_fix_20261112/check_imports.py` 护航），与 MetaDemonProvider 互不依赖，仅共享可复用组件
（GameUi/SwitchSoul/GeneralBattle/RightActivity）。战败判据以类属性 shadowing 任务内覆盖
（`ScriptTask.I_FALSE = I_MDA_FALSE`，详见 script_task.py 头注释），不触碰任何共享资产。

## 流程

1. **run()**：切御魂（两种开关，同现世妖约）→ 回庭院 → 经右侧栏进活动**初始清扫**一遍存量好友鬼王
   （覆盖任务未运行期间漏掉的横幅）→ 回庭院守候。
2. **庭院守候 `_wait_banner`**：
   - 每轮截图检测邀请横幅：`I_MDA_BANNER_GO`（立即前往圆钮模板）+ `O_MDA_BANNER`（keyword「鬼王」）双判据；
   - 命中 → 读横幅「N星」→ 点立即前往 → 进祸主降临页（8 秒不达则走右侧栏入口兜底）→ 协助循环 → 认层退回庭院；
   - 庭院丢失（弹窗/被拉走）→ `goto_page(page_main)` 自愈，连续 3 次失败交给重启；
   - 长等待保活：280s 周期 `stuck_record_clear + stuck_record_add('PAUSE')`；**每次交互回来后必须重新登记**
     （点击会清掉卡死白名单，见 DEV_GUIDE 第 7/21 节）；
   - 守候 `mda_max_duration`（默认 120 分钟）到点自然结束 → `set_next_run(target=now+mda_rerun_gap)`。
3. **协助循环 `_assist_loop`**（祸主降临页）：
   - 资源检查：顶栏 N/100（`O_MDA_RESOURCE` DigitCounter，单次挑战消耗 10），`0 < N < 10` 判耗尽退出；
   - 扫好友发现卡片区（`O_MDA_CARD.detect_and_ocr`）：文本行「剩余时间」=可挑战（按 y 分槽 1/2），
     「击败奖励结算中」=不可挑战（已打过/正在结算），无则返回庭院（用户规则）；
   - 选卡（卡槽未选中时点头像区，等挑战按钮出现）→ **亮珠计数判星级**（卡底一排 6 珠，亮几颗=几星，
     程序化颜色连通域计数；失败用横幅「N星」兜底）→ 星级 ≥ `mda_buff_min_star`（默认5）勾选 2.5 倍伤害
     （双态模板，状态不明不盲点，防止来回翻转）→ 点挑战 → `run_general_battle`（通用战斗含点准备/切自动/胜负结算）；
   - 胜负：通用 `I_WIN`/`I_FALSE` 对本活动结算界面离线实测 0.995/0.991，开箱即用；
     失败按用户规则再挑战，连败 3 场退出。
4. **让位 `_yield_to_scheduler`**（本任务在 `SCHEDULER_PRIORITY` 最末=最低优先级）：
   守候循环每轮 + 协助循环每场战斗结束间隙，检查任一其他启用任务 `next_run <= now`，
   有则 `set_next_run(self, target=now)` + `raise TaskEnd`；调度器必先跑对方，对方结束后本任务自动唤醒
   （唤醒后重新走 run()：重新切御魂 → 初始清扫 → 守候，符合需求）。**战斗中不让位**（打完当前场再让）。

## 页面图（page.py）

- `page_mda_event` 祸至无日页（标题模板+超鬼王竖排按钮 any_of）
- `page_mda_huozhu` 祸主降临页（标题模板+挑战按钮 any_of；标题在无鬼王空态也常驻）
- `page_main ⇄ page_mda_event`（右侧栏图标+I_TOGGLE_BUTTON）`⇄ page_mda_huozhu`（超鬼王竖排按钮）
- 注：两页标题几乎同位同风格（祸至无日/祸主降临），**OCR keyword 会因竖排逐字兜底互相误报，只能用模板判页**
  （交叉得分 0.62 vs 阈值 0.8，实测可区分）。

## 素材与验证（2026-11-11，13 张用户截图离线标定）

| 素材 | 说明 | 验证 |
|---|---|---|
| mda_right_enter | 右侧栏图标**核心稳定区** 24x24 | 整图标有动画（光点），跨帧 0.797；核心区跨帧 0.994、误报≤0.56 |
| mda_goto_huozhu | 超鬼王竖排按钮内部（避开黄框标注线） | 1.0 / 误报 ≤0.64 |
| mda_title_huozhu / mda_title_event | 两页标题 | 1.0，互判 0.62x |
| mda_back | 左上返回（两页同款同位，一个模板通吃） | 1.0 |
| mda_challenge | 挑战按钮（MetaDemon 旧素材 0.52 已失效） | 1.0 / 无 >0.6 误报 |
| mda_banner_go | 横幅立即前往圆钮 | 1.0 / 零误报 |
| mda_buff_off / mda_buff_on | 2.5 倍勾选双态 | OFF 1.0；**ON 来自用户特写裁剪，未实机验证** |
| 珠子计数 | 亮珠 RGB(228,114,35)，8x12，间距 11px，槽1珠行 y450/槽2 y579 | 4星卡=4、结算卡=3、空=0、合成 5/6 星=5/6 全对 |

## 已知风险 / 待实机验证

1. **mda_buff_on 未实机验证**：勾选态模板来自用户 179x51 特写图，实机若 ON 态不识别，代码走"状态不明不盲点"
   分支（保持现状并告警），拿到实机勾选态截图后重裁。
2. **横幅多样性**：只见过 4 星横幅样本；星级数字 OCR（发现「N星」）实测 0.97 可靠，但好友名/星数位置漂移需观察。
3. **卡槽 2**：所有截图都只有槽 1（单卡），槽 2 坐标按 MetaDemon 槽间距 129px 推算，实机多卡场景待验证。
4. **战斗结算回页**：胜利结算点按后是否直接回祸主降临页（用户描述会），若中间有奖励浮窗，
   `_assist_loop` 顶部的弹窗自愈（I_UI_BACK_RED）+ 页面等待兜底。
5. **资源计数 OCR**：roi (1040,20,170,44)，读 0 视为识别失败不当耗尽（防止 DigitCounter 裁边误判）。
6. 实机首跑观察：让位/唤醒是否按预期工作（next_run 语义）、初始清扫入口（右侧栏图标浮动）、守候期 CPU（轮询 1s）。

## 注册清单

config_model.py（import + `meta_demon_assist` 字段）、config_menu.py（Activity Task）、
config_manual.py（SCHEDULER_PRIORITY **最末**）、i18n 两张表（assets/i18n + module/config/i18n，键前缀 mda_）。
改素材后须**重启 OAS 进程**（sys.modules 缓存）。
