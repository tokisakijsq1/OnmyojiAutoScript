## 这里是约定哪些是需要更新的     ./script_test.py 是对应的测试


## 2026-10 活动改版（拾此一瞬 / 磐长故地）

当期仅更新门票爬塔（磐长故地），100体/6体收益低未更新（`_run_ap`/`_run_boss` 仍是旧活动逻辑，勿用）。
新流程：活动主页点"磐长故地"(`I_TO_BATTLE_MAIN`) → 地图页 ocr 识别"战斗"牌(`O_BATTLE_PLAQUE`，位置不固定，竖排两字) → 战斗准备页(判据 `I_CHECK_BATTLE_MAIN`=右下挑战钻石文字区)。

- 门票与6体**不能**在界面内直接切换：`_run_pass` 已删除模式切换调用；`climb_mode_*` 三个素材已废弃
- 准备页判据不能用右上门票图标：地图页同位置有同一图标（0.82 也会过 0.8 阈值），改用右下挑战按钮文字区
- 准备页没有锁定阵容图标：`lock_team` 已加 3s 超时跳过
- `O_FIRE` 挑战 roi 改为 (1110,560,120,75)；`O_REMAIN_PASS` 门票数 roi 改为 (1138,15,60,45)
- `as_shi` 入口图标已换成当期图标(51x36)，但**没有整屏截图可验证 roi**，首次实机跑时注意
- 竖排"战斗"两字 OCR 检出率待实机确认，不行再换方案（如固定几个候选点击位）

## 2026-10-20 BOSS 模块更新（神眸垂世·首领）

`_run_boss` 已对接当期首领玩法，素材全部由用户 2026-10-20 截图裁剪并离线验证（7 图交叉矩阵：来源 1.0 / 负例远低于阈值）。

流程：活动主页点"神眸垂世·首领"(`I_TO_BATTLE_BOSS`) → BOSS页(判据 `I_CHECK_BATTLE_BOSS`=左上标题) → 循环：额外奖励检查 → lock_team → start_battle（点挑战→锁定直接开打/未锁走准备阶段→通用战斗框架→网格结算）→ 回BOSS页；结束走 `exit_activity()`（新增 `I_CHECK_BATTLE_BOSS` 分支点 `I_BOSS_BACK_ARROW`）。

- **结束条件**：右下"额外奖励 x/100"（`O_EXTRA_REWARD` DigitCounter）达到 **min(boss_limit, 100)** 即停；OCR 失败不误停，`put_status` 的 boss_limit 保留兜底。挑战按钮下的 x12 不消耗，不检测（用户确认）
- **战斗判活**：`boss_battle_appear()` = 顶部金圆图标内核(`I_BOSS_BATTLE_ICON`) 或 "特殊压制"狐狸图标(`I_BOSS_BATTLE_ICON_2`)。标准 `is_in_battle` 素材对 BOSS 战 UI 不匹配；用户标的两侧空白背景跨帧漂移（0.21~0.68）已弃用。金圆有动画，**内核裁剪**(29x18)三帧全 1.0，负例 max 0.73 故阈值 0.85
- **阵容锁**：BOSS 页开关位置与 pass 页相同但素材有差异（旧 `I_LOCK` 对新页仅 0.76），新增 `I_BOSS_LOCK`/`I_BOSS_UNLOCK`（同位 (897,640,39,44)，互斥 0.47），`lock_team` 按 climb_type 选素材对
- **式神录按钮复用** `I_BATTLE_MAIN_TO_RECORDS`（对 BOSS 页 0.972）；回退箭头与地图页不同，新增 `I_BOSS_BACK_ARROW`（与活动主页同款，由标题判据先门控）
- **网格结算**：复用 `_bw_success_activity`；门票网格锚点 1/2 对 BOSS 网格失配，锚点 3（点击屏幕继续）0.906 可用，另加 `I_GRID_ANCHOR_BOSS` 冗余；主循环另有 `reward_grid_appear→C_GRID_CONTINUE` 保险
- `O_FIRE_BOSS`(1115,585,120,75) 与 pass 的 `O_FIRE` 位置不同；`O_REMAIN_BOSS` 为旧活动遗留已停用
- 实机注意：改素材后须重启 OAS 实例进程；BOSS 准备阶段（未锁阵容）的预设/准备按钮素材未实机验证；金圆若实机漏检按战斗牌经验补多模板



## 关于页面导航（`./as/page.json`文件）

#### 图片 `shi` 表示进入到活动的主页面，截图的时候往上截图一点，因为快结束的时候图片下方会显示还有多少小时结束

![image-20251220103009134](https://runhey-img-stg1.oss-cn-chengdu.aliyuncs.com/img3/202512201030265.png)

#### 图片`to_battle_main` 和 `to_battle_boss` 分别表示进入默认的挑战界面和boss挑战界面

![image-20251220103500219](https://runhey-img-stg1.oss-cn-chengdu.aliyuncs.com/img3/202512201035354.png)

#### 图片`check_battle_main` 表示到达了这个默认战斗界面       |  `battle_main_to_records`表示从这里进入式神录来切换御魂

#### 图片`check_battle_boss`  和 `battle_boss_to_records` 类似的

![image-20251220104003594](https://runhey-img-stg1.oss-cn-chengdu.aliyuncs.com/img3/202512201040758.png)

#### 可能需要更新的如 `back_green`、 `red_exit` 和 `skip_button`  这些表示退出的时候碰到的时候会出现的

#### OAS 内部有一个专门的类来存放通用的图片。  路径在`./tasks/GlobalGame/ui`  有需要直接使用

![image-20251220104718877](https://runhey-img-stg1.oss-cn-chengdu.aliyuncs.com/img3/202512201047907.png)

## 关于活动切换（`./as/image.json`文件）

#### 图片 `climb_mode_pass` 门票爬塔标志 | `climb_mode_ap` 体力爬塔标志 | `climb_mode_switch` 切换门票爬塔和体力爬塔按钮

![climb_mode_pass](https://raw.githubusercontent.com/AzurTian/ImgBed/master/blog/climb_mode_pass.png)

![climb_mode_ap](https://raw.githubusercontent.com/AzurTian/ImgBed/master/blog/1.png)

![climb_mode_switch](https://raw.githubusercontent.com/AzurTian/ImgBed/master/blog/2.png)


## 关于战斗更新 （`./fire/ocr.json`文件）

#### OCR `remain_ap`  表示体力模式下剩余多少次数  `fire` 表示点击挑战

![image-20251220111306772](https://runhey-img-stg1.oss-cn-chengdu.aliyuncs.com/img3/202512201113931.png)

活动币模式下 `remain_pass`  和 boss 模式下也是类似

![image-20251220111505769](https://runhey-img-stg1.oss-cn-chengdu.aliyuncs.com/img3/202512201115927.png)

