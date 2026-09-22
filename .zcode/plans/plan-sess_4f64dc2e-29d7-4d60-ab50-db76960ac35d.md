# 结界蹭卡「指定好友寄养」修改计划

## 功能行为（已确认）
- `UtilizeConfig` 新增 `friend_name: str`（默认空）。**留空 = 完全保持现有行为**；填了名字 = 优先蹭指定好友。
- 查找范围：**只在当前配置的 select_friend_list 列表内查找**（用户已确认），找不到不跨列表。
- 失败自动回退：指定好友没找到 / 该好友结界无空坑位 / 寄养失败 → 自动回退到现有常规蹭卡流程（当前列表继续找最优卡），保证每次运行必有产出。
- oasx UI：**无需改前端**。后端 pydantic 加字段后，oasx 通过 `GET /{script}/{task}/args`（`ConfigModel.script_task()` 动态导出 schema）自动渲染出文本输入框；保存走现有 `PUT .../value`（`types=string`）链路，均已支持。

## 修改文件

### 1. `tasks/KekkaiUtilize/config.py`
`UtilizeConfig` 增加两个字段：
```python
friend_name: str = Field(default='', description='utilize_friend_name_help')
utilize_target_friend: bool = Field(default=True, description='utilize_target_friend_help')
```
- `friend_name`：指定好友名称（OCR 精确匹配，需全称，不区分跨服同名）
- `utilize_target_friend`：是否启用指定好友优先（关闭后即使填了名字也不生效）

### 2. `tasks/KekkaiUtilize/utilize/ocr.json` + 重新生成 `assets.py`
新增 OCR 规则 `O_U_FRIEND_NAME`（Full 模式，`keyword=""` 运行时注入）：
```json
{"itemName": "u_friend_name", "roiFront": "228,155,930,400", "roiBack": "228,155,930,400", "mode": "Full", "method": "Default", "keyword": "", "description": "蹭卡好友列表中的好友名称区域"}
```
- roi 覆盖好友列表两列名字区（参考 GeneralInvite `O_FRIEND_NAME_1/2` 的 roi (434,185,189,345)/(729,184,196,346)，蹭卡列表更宽，先给大 roi，实测后可收窄）。
- 运行 `python dev_tools/assets_extract.py` 重新生成 `tasks/KekkaiUtilize/assets.py`（不能手改）。

### 3. `tasks/KekkaiUtilize/script_task.py`（核心）

**新增方法 `find_and_enter_friend_realm(name) -> bool`**（放在 `switch_friend_list` 附近）：
- 空名字直接 False。
- 用 `perform_swipe_action()` 风格的滑动循环（最多 ~8 屏，120s 超时）在**当前好友列表**内查找：
  - 每屏 `self.O_U_FRIEND_NAME.keyword = name` 后调 `self.ocr_appear_click(self.O_U_FRIEND_NAME, interval=1.5, exact=True)`（复用 GeneralInvite `detect_select` 的成熟模式，exact 精确匹配防误点）。
  - 点中后出现 `I_U_ENTER_REALM`（好友结界卡详情）即成功；若点击只是选中（未出现详情），再点一次该坐标。
- 找不到 → 滑回列表顶部（`S_U_END` + 反向滑动恢复原位），返回 False。

**新增方法 `try_target_friend(friend_name, shikigami_class, shikigami_order) -> bool`**：
- 调 `find_and_enter_friend_realm`；False 则返回 False（回退）。
- 复用 `run_utilize` L455-505 的「进入结界 + 判断坑位 + 换式神 + 上 N 卡」段落（提取为私有方法 `_enter_and_set_shikigami(...)` 供两处复用）。
- **坑位被占（无 stop_image）→ 返回 False**，由外层回退，不 return True。

**改造 `run_utilize(...)`**（L423）：新增参数 `friend_name: str = ''`，开头插入：
```python
if friend_name:
    logger.info(f'尝试指定好友寄养: {friend_name}')
    if self.try_target_friend(friend_name, shikigami_class, shikigami_order):
        self.utilize_add_count = 0
        return True
    logger.warning('指定好友寄养失败，回退到常规蹭卡')
    # 回到蹭卡列表，恢复常规流程
    self.back_realm(); self.realm_goto_grown(); self.grown_goto_utilize()
    self.switch_friend_list(friend)
```
失败回退后继续走现有 `_select_optimal_resource_card()` 流程。

**`check_utilize_add`**（L103）传参改为 `self.run_utilize(con.select_friend_list, con.shikigami_class, con.shikigami_order, con.friend_name)`。

### 4. `module/config/i18n/zh-CN.json`
新增帮助文案（GUI 描述显示）：
- `utilize_friend_name_help`：指定好友名称寄养（OCR 识别需全称，留空则常规蹭卡）；寄养位被占或失败时自动回退常规蹭卡
- `utilize_target_friend_help`：启用指定好友优先寄养

### 5. oasx UI（无需代码改动，验证步骤）
- oasx 前端是独立仓库（github.com/runhey/OASX），本仓库只有 exe；字段渲染完全由后端 schema 驱动：`type: "string"` → TextFormField，description 原样显示。
- 验证：重启 `python server.py`（端口 22288）→ oasx 重新进入 结界蹭卡 页面 → utilize_config 组出现「指定好友名称」输入框，可保存。

## 需要你提供的截图（实现时向我索取）
1. **蹭卡好友列表整屏截图**（含好友名字，用于校准 `O_U_FRIEND_NAME` 的 roi）——必需
2. 指定好友结界「坑位被占」的样子（右上角无 ADD_1/ADD_2 加号）——用于确认复用现有判断即可
3. （可选）跨区好友列表截图（若以后想支持跨区查找）

## 风险与对策
- OCR 同名/误识别：exact 精确匹配 + 点击后必须出现 `I_U_ENTER_REALM` 才算成功，否则视为未找到。
- 好友很多时查找耗时：滑动上限 8 屏 + 120s 超时，超时即回退。
- 回退路径状态错乱：复用现有 `back_realm()/realm_goto_grown()/grown_goto_utilize()` 导航原语，与现有 `check_utilize_add` 的往返模式一致。
- 用户配置兼容：新字段有默认值，旧 config json 无需迁移。