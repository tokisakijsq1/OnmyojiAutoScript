# 新增配置字段的中文翻译添加指南

> 场景：在某个任务的 `config.py` 里新增了配置字段（`Field(description='xxx_help')`），
> 界面上却直接显示 `xxx` / `xxx_help` 这样的原始 key 而不是中文。
> 本文档解释原因，并给出必须遵守的添加步骤。

## 结论（先记这个）

**新增一个配置字段后，中文必须同时加到下面两个 JSON 文件里，缺一不可：**

| 文件 | 作用 | 谁在用 |
|---|---|---|
| `assets/i18n/zh-CN.json` | **附加翻译表**，新增字段的中文必须加在这里 | oasx 网页界面（`GET /home/additional_translate` 下发给前端）+ 后端 `config_model.py` 的 `_translate_text` |
| `module/config/i18n/zh-CN.json` | 全量翻译主表 | 桌面 QML 界面、`script.py` 的通知标题（`I18n.trans_zh_cn`）、oasx 翻译编辑器回写（`PUT /chinese_translate`） |

**为什么两个都要加：**

- 界面（oasx.exe）是打包好的前端，内部**内嵌了一份打包时的翻译快照**。
  老字段能显示中文，是因为快照里恰好有；新字段快照里没有，就会显示原始 key。
- `assets/i18n/zh-CN.json` 就是官方设计用来**不重新打包前端**、给新增字段补翻译的通道
  （见 `module/config/config_model.py` 中 `_load_zh_cn_translations` 的注释）。
- `module/config/i18n/zh-CN.json` 服务于 QML 桌面界面和运行日志/通知，
  不加的话换 QML 界面或通知时会显示 key。

## 添加步骤

假设在 `tasks/Hyakkiyakou/config.py` 新增了字段：

```python
hya_invite_friend_name: str = Field(default='', description='hya_invite_friend_name_help')
```

### 1. `assets/i18n/zh-CN.json`（关键，漏了界面就显示 key）

在文件末尾（最后一个键值对后面）追加，**key 用字段名本身，不带 description 后缀的那份也必须加**：

```json
{
  "...原有的...": "...",
  "hya_invite_friend_name": "指定好友名称",
  "hya_invite_friend_name_help": "开启邀请好友后优先邀请该好友"
}
```

注意：JSON 上一行末尾要补逗号，最后一对不能带逗号。

### 2. `module/config/i18n/zh-CN.json`

按字段在文件中已有的顺序位置插入同样的两条（`字段名` + `字段名_help`）。

### 3. 生效方式

- 后端 `_ZH_CN_TRANSLATIONS` 是进程级缓存（只加载一次），**需要重启 oasx / server 进程**。
- 前端每次加载页面都会重新拉取 `/home/additional_translate`，刷新网页即可。

## 踩坑记录

- 2026-09 百鬼夜行新增 `hya_invite_friend_name` 时只加了
  `module/config/i18n/zh-CN.json`，结果 oasx 界面显示原始 key。
  根因即上表：界面走的是 `assets/i18n/zh-CN.json` 附加表 + exe 内嵌快照。
- 后端 `script_task()` 接口返回的 `title` 是 pydantic 自动生成的
  Title Case（如 `Hya Invite Friend Name`），前端并不用它做展示，
  前端是拿**字段名 key** 自己查表翻译的，所以 key 必须写成字段名原样（全小写下划线）。
- 桌面 QML 界面的静态文案（菜单、按钮等）走的是 Qt 翻译系统
  （`module/config/i18n/zh_CN.ts/.qm`，需用 Qt Linguist 手动编译），
  与配置字段的 JSON 翻译是两套体系，新增配置字段不需要动 `.qm`。

## 检查清单

- [ ] `tasks/.../config.py`：字段 + `description='xxx_help'`
- [ ] `assets/i18n/zh-CN.json`：加 `xxx` 和 `xxx_help` 两条
- [ ] `module/config/i18n/zh-CN.json`：加同样的两条
- [ ] 重启 oasx / server 进程，刷新网页
