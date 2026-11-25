# 主线剧情自动推进: 庭院三点入口 -> 剧情循环(跳过/对话/探查/战斗) -> 回庭院 -> 下一段,
# 直到庭院不再出现入口图标。
#
# 剧情循环每轮重新识别画面, 按优先级只处理一件事:
#   确认跳过 -> 动画跳过 -> 对话跳过 -> 探查 -> 战斗 -> 剧情对话三点 -> 问号推进 -> 通用奖励浮窗 -> 战斗流程 -> 庭院
# 跳过链最优先是用户规则: 对话和动画播放中左上角返回键无效, 必须先走完跳过。
# 退路: 连续 ms_idle_timeout 秒没有任何可识别按钮且画面静止时, 直接沿用返回键(I_UI_BACK_CIRCLE)退出本段剧情;
# 连退几轮都退不出去也不抛卡死异常(原地重试会连撞三次杀进程), 而是先按失败排期再让导航兜底回庭院。
# 战斗复用 GeneralBattle(点准备/切自动/胜负判定/结算点击), 战败即结束任务。
import os
import time
from datetime import datetime

import cv2
import numpy as np
from cached_property import cached_property

from module.base.timer import Timer
from module.exception import TaskEnd
from module.logger import logger

from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.GameUi.game_ui import GameUi
from tasks.GameUi.page import page_main
from tasks.MainStory.assets import MainStoryAssets
from tasks.MainStory.config import MainStory

# ---------------- 常量 ----------------
# 庭院入口图标需连续可见多久才点击(回庭院的转场帧里图标可能一闪而过)
ENTRY_STABLE = 1.5
# 庭院连续多久不出现入口图标才认定剧情全部做完(下一段入口可能延迟弹出)
NO_ENTRY_STABLE = 5.0
# 进入剧情后的宽限期: 点完入口庭院画面还会停留一会, 这段时间不判"已回庭院"
ENTRY_GRACE = 3.0
# 剧情结束后庭院需连续可见多久才认定本段结束
COURTYARD_STABLE = 2.5
# 入口点了没反应(进剧情后零点击就回了庭院)连续几次后结束任务
ENTRY_FAIL_LIMIT = 3
# 点返回后多久内允许点退出确认弹窗
ESCAPE_CONFIRM_WINDOW = 5.0
# 连续多少轮"画面静止且无按钮"后判定这段剧情退不出去(每轮 = ms_idle_timeout 秒)
IDLE_LIMIT = 4
# 单段剧情总时长上限(秒): 兜底防"界面来回变但剧情不推进"的死循环
STORY_MAX_DURATION = 1800
# 点战斗按钮后等准备页/战斗界面出现的窗口(秒)。剧情->战斗的转场实测约 7 秒, 而
# battle_before 只等 5 秒: 转场没走完就进去会在准备页上超时, 超时兜底的切自动又被
# 准备页左下角的"预设"按钮骗过齿轮 OCR(wait_real_battle 误判已开打), 最终
# GameStuckError 重启游戏(2026-11-24 小号5 实机)。先等界面真正出现再交给通用流程。
STORY_BATTLE_ENTER_WAIT = 20
# 同一剧情按钮的点击冷却(秒)
STORY_CLICK_INTERVAL = 1.2
# 每次点击后的短暂等待(秒): 给游戏时间消化这次点击, 下一轮再重新识别, 避免在旧画面上重复点击
CLICK_SETTLE = 0.5
# 同一按钮在同一画面状态下的容错次数: 连点 3 次画面仍没变 = 点击没生效, 拉黑该按钮组合
# (交给空等 / 返回退路处理), 防止无限硬点直到触发连点保护
CLICK_RETRY_LIMIT = 3
# 按钮可见但仍在冷却 / 空转时的轮询间隔
COOLDOWN_SLEEP = 0.3
# 连点保护放行阈值。device.click_record 是最近 15 次点击的队列, 同名 >=10 或两名各 >=6 即抛
# GameTooManyClickError。主线里"点三点 -> 点跳过 -> 回场景 -> 再点三点"是合法的连续点击,
# 所以相邻两次点击间界面状态变了(= 点击生效)就允许清记录; 状态没变的重复点击不清, 保护照常生效
CLICK_RECORD_LIMIT = 9
# 状态签名里按钮坐标的量化步长(像素): 小于它的抖动不算状态变化
SIGNATURE_CELL = 8
# 空等时判"画面是否还在变"的帧差阈值(0~255 灰度均值差)。标定: 同一剧情场景两个对话节拍之间 1.02,
# 历史语料里同画面截图对的 75 分位 1.42, 而镜头/人物在动的画面通常 >=4
SCENE_MOVING_DIFF = 2.5
# 顶部的跑马灯横幅和帧率标签一直在变, 不参与帧差比较
SCENE_DIFF_TOP = 120
SCENE_DIFF_SIZE = (160, 75)
# 顶部聊天播报横幅的禁点区(2026-11-25 用户截图红框, 实测 435,61 ~ 1083,108): 从庭院进入剧情后,
# 命中框碰到这个区域的按钮一律不点——播报浮在按钮上层, 点下去只会误触播报; 被它压住的按钮
# 按"没看见"处理, 交给空等 / 返回退路。coord() 是命中框内的随机点, 所以按"框相交"判断
CHAT_BANNER_BOX = (435, 61, 648, 47)
# 诊断截图目录
DIAGNOSIS_DIR = './log/screenshots/MainStory'


class _Stable:
    """条件连续成立满 duration 秒才返回 True, 中途一断重新计时。"""

    def __init__(self, duration: float) -> None:
        self.duration = duration
        self.since = None

    def update(self, flag: bool, now: float = None) -> bool:
        if not flag:
            self.since = None
            return False
        now = time.time() if now is None else now
        if self.since is None:
            self.since = now
        return now - self.since >= self.duration

    def reset(self) -> None:
        self.since = None


def _shrink(image: np.ndarray) -> np.ndarray:
    """判"画面是否还在变"用的缩略灰度图"""
    small = cv2.resize(image[SCENE_DIFF_TOP:], SCENE_DIFF_SIZE, interpolation=cv2.INTER_AREA)
    return small.astype(np.float32).mean(axis=2)


class ScriptTask(GameUi, GeneralBattle, MainStoryAssets):
    @cached_property
    def conf(self) -> MainStory:
        return self.config.model.main_story

    @cached_property
    def skip_buttons(self) -> list:
        """对话/动画的跳过链, 任何画面下都最优先处理(可以叠在庭院画面上)"""
        return [self.I_MS_CONFIRM_SKIP, self.I_MS_SKIP_ANIM, self.I_MS_SKIP_DIALOG]

    @cached_property
    def story_buttons(self) -> list:
        """剧情场景内每轮按此优先级找按钮"""
        return self.skip_buttons + [self.I_MS_INVESTIGATE, self.I_MS_BATTLE, self.I_MS_STORY_DIALOG,
                                    self.I_MS_STORY_QUESTION]

    @cached_property
    def story_markers(self) -> list:
        """剧情启动判据; 三点和问号须同时满足剧情 HUD 双条件。"""
        return self.skip_buttons

    def run(self):
        self._advance()
        raise TaskEnd

    def _advance(self) -> None:
        conf = self.conf.main_story_config
        logger.hr('Main story start', 1)
        state = {'story': 0, 'escape': 0, 'stuck': False, 'entry_fail': 0}

        def finish() -> None:
            """按本次运行的情况排期收尾"""
            if state['stuck']:
                self._finish(False, 'Story stuck on unrecognized screen, screenshot in log/screenshots/MainStory',
                             push=True)
            elif state['escape'] >= conf.ms_escape_limit:
                self._finish(False, 'Story exited by back button too many times, '
                                    'screenshot in log/screenshots/MainStory', push=True)
            else:
                self._finish(True, f"No more story, advanced {state['story']}")

        def after_story(outcome: str, clicks: int, entered: bool) -> bool:
            """一段剧情结束后的处置, 返回 False = 任务已排期结束"""
            if outcome == 'battle_failed':
                self._finish(False, 'Story battle failed', push=True)
                return False
            if outcome == 'stuck':
                # 退不出去: 先按失败排期, 万一下面导航也失败(抛 GamePageUnknownError 走标准重启),
                # 重启后不会原地重试连撞三次; 再让导航兜底回庭院
                state['stuck'] = True
                self.set_next_run(task='MainStory', success=False, server=True)
                self._back_to_courtyard()
                outcome = 'escaped'
            state['escape'] += outcome == 'escaped'
            if state['escape'] >= conf.ms_escape_limit:
                finish()
                return False
            if entered:
                # 进了剧情却一下都没点就回到庭院 = 入口点击没生效
                state['entry_fail'] = state['entry_fail'] + 1 if (outcome == 'done' and clicks == 0) else 0
                if state['entry_fail'] >= ENTRY_FAIL_LIMIT:
                    self._finish(False, 'Story entry not responding', push=True)
                    return False
                if state['story'] >= conf.ms_max_count:
                    self._finish(False, 'Story count limit reached', push=True)
                    return False
            return True

        outcome, clicks, entered = None, 0, False
        # 启动时已身处剧情(上次异常中断/手动点了入口): 先把这一段走完再回庭院找入口。
        # 庭院判定放宽到 0.8: 庭院被弹窗压暗时仍算庭院, 交给导航处理, 不进剧情循环
        self.screenshot()
        if not self.appear(self.I_CHECK_MAIN, threshold=0.8) and (
                self._any_visible(self.story_markers) or self._story_hud_visible()):
            logger.info('Already in a story scene, continue it first')
            outcome, clicks = self._story_loop()

        entry_stable, no_entry_stable = _Stable(ENTRY_STABLE), _Stable(NO_ENTRY_STABLE)
        while 1:
            if outcome is not None:
                if not after_story(outcome, clicks, entered):
                    return
                outcome = None
            self.screenshot()
            if not self.appear(self.I_CHECK_MAIN):
                # 剧情收尾可能落在别的界面: 回庭院再找入口
                self._back_to_courtyard()
                entry_stable.reset()
                no_entry_stable.reset()
                self.screenshot()
            # 庭院对话: 跳过按钮叠在庭院画面上, 入口图标仍在, 交给剧情循环而不能去点入口
            if self._any_visible(self.skip_buttons):
                entry_stable.reset()
                no_entry_stable.reset()
                outcome, clicks = self._story_loop()
                entered = False
            elif self.appear(self.I_MS_COURTYARD_ENTRY):
                no_entry_stable.reset()
                if not entry_stable.update(True):
                    time.sleep(COOLDOWN_SLEEP)
                    continue
                state['story'] += 1
                logger.info(f"Click story entry ({state['story']}/{conf.ms_max_count})")
                self.appear_then_click(self.I_MS_COURTYARD_ENTRY)
                entry_stable.reset()
                outcome, clicks = self._story_loop()
                entered = True
            else:
                entry_stable.reset()
                if no_entry_stable.update(True):
                    finish()
                    return
                time.sleep(COOLDOWN_SLEEP)

    # ---------------- 剧情循环 ----------------

    def _story_loop(self) -> tuple[str, int]:
        """推进当前这段剧情直到回到庭院。

        :return: (结果, 按钮点击数)。结果 'done' 剧情走完回到庭院 / 'escaped' 点返回退回庭院 /
                 'battle_failed' 剧情战斗失败 / 'stuck' 没有可识别按钮且退不出去(或时长到顶)。
        """
        logger.hr('Story loop', 2)
        conf = self.conf.main_story_config
        idle = Timer(conf.ms_idle_timeout).start()
        total = Timer(STORY_MAX_DURATION).start()
        grace = Timer(ENTRY_GRACE).start()
        courtyard = _Stable(COURTYARD_STABLE)
        last_sig = None       # 上一次点击时的界面状态签名
        escaped = False       # 最后一个动作是否为"点返回"
        idle_rounds = 0       # 连续"画面静止且无按钮"的轮数
        diagnosed = False     # 本段空等是否已存过现场截图
        idle_seen = False     # 是否已进入"无按钮"的空等状态
        ineffective = 0       # 同一画面状态下同一按钮的连续点击次数(状态没变 = 点击没生效)
        blocked_sig = None    # 连点 3 次无效后被拉黑的按钮组合, 不再硬点
        clicks = 0
        ref = None            # 判"画面是否还在变"的参考帧(进入空等时记, 之后每轮更新)

        def progressed() -> None:
            nonlocal last_sig, escaped, idle_rounds, diagnosed, idle_seen, ref
            nonlocal ineffective, blocked_sig
            idle.reset()
            idle_rounds = 0
            escaped = False
            last_sig = None
            diagnosed = False
            idle_seen = False
            ineffective = 0
            blocked_sig = None
            ref = None

        escape_confirm = None  # 点了返回后的退出确认窗口(Timer), None = 没点过
        while 1:
            if total.reached():
                logger.warning(f'Story lasts over {STORY_MAX_DURATION}s, it may not be progressing')
                self._save_diagnosis('timeout')
                return 'stuck', clicks
            # 卡死检测交给本循环自己的计时器(idle / total)
            self.device.stuck_record_clear()
            self.screenshot()

            in_courtyard = self.appear(self.I_CHECK_MAIN)
            # 庭院画面上的三点是入口图标(由外层负责), 不当剧情对话按钮点
            buttons = self.skip_buttons if in_courtyard else self.story_buttons
            visible = []
            for t in buttons:
                if not (self._story_icon_visible(t) if t in
                        (self.I_MS_STORY_DIALOG, self.I_MS_STORY_QUESTION) else self.appear(t)):
                    continue
                if self._in_chat_banner(t):
                    # 聊天播报压住的按钮点了会误触播报: 当作没看见, 让空等/返回退路接手
                    logger.info(f'Story button {t.name} covered by chat banner, ignore it')
                    continue
                visible.append(t)
            sig = tuple((t.name, t.roi_front[0] // SIGNATURE_CELL, t.roi_front[1] // SIGNATURE_CELL)
                        for t in visible)
            # 拉黑的按钮组合当作没看见: 让下面的奖励/战斗/庭院/空等/返回退路正常接手,
            # 否则永远跳过其他分支, 只能等 30 分钟总时长超时
            if blocked_sig is not None and sig == blocked_sig:
                visible = []
                sig = ()
            skipping = bool(visible and visible[0] in self.skip_buttons)

            # 刚点过返回时先检查跳过按钮, 避免把剧情确认当成退出确认。
            if not skipping and escape_confirm is not None and not escape_confirm.reached():
                if self._click_exit_confirm():
                    courtyard.reset()
                    continue

            # 1) 剧情按钮: 按优先级点第一个, 仍在冷却则等一会再看
            if visible:
                courtyard.reset()
                if self.appear_then_click(visible[0], interval=STORY_CLICK_INTERVAL):
                    clicks += 1
                    time.sleep(CLICK_SETTLE)
                    if sig != last_sig:
                        # 界面相对上一次点击变了 = 点击生效, 连点记录攒多了放行一次
                        last_sig = sig
                        ineffective = 1
                        blocked_sig = None
                        if len(self.device.click_record) >= CLICK_RECORD_LIMIT:
                            self.device.click_record_clear()
                    else:
                        # 状态没变 = 这次点击很可能没生效(被弹窗吞了/点了没反应), 容错 3 次
                        ineffective += 1
                        if ineffective >= CLICK_RETRY_LIMIT:
                            blocked_sig = sig
                            logger.warning(f'Story button {visible[0].name} clicked {ineffective} times '
                                           f'without visible effect, block it and fall back')
                    idle.reset()
                    idle_rounds = 0
                    escaped = False
                    diagnosed = False
                    idle_seen = False
                else:
                    time.sleep(COOLDOWN_SLEEP)
                continue

            # 2) 通用奖励浮窗
            if self.ui_reward_appear_click():
                progressed()
                continue

            # 3) 战斗: 点了战斗按钮后转场进准备页; 任务中断后恢复时可能已在战斗中/结算
            if self.is_in_prepare(False) or self.is_in_battle(False):
                if not self._battle():
                    return 'battle_failed', clicks
                progressed()
                continue

            # 4) 庭院 = 本段剧情结束
            if in_courtyard:
                idle_seen = False
                if grace.reached() and courtyard.update(True):
                    if blocked_sig is not None and self._any_visible(buttons):
                        # 拉黑的按钮(点不动的庭院对话/弹窗)还叠在庭院上: 按 done 返回会让外层
                        # 无限"重进剧情循环 -> 3 次无效点击", 这里按 stuck 交给导航兜底
                        logger.warning('Blocked story buttons still on courtyard, treat as stuck')
                        return 'stuck', clicks
                    blocked_sig = None
                    outcome = 'escaped' if escaped else 'done'
                    logger.info(f'Story loop end: {outcome}, clicks {clicks}')
                    return outcome, clicks
                time.sleep(COOLDOWN_SLEEP)
                continue
            courtyard.reset()

            # 5) 没有任何可识别按钮: 空等 -> 退路
            if not idle_seen:
                # 刚进入空等: 从此刻起计时, 并记下此刻的画面, 之后每轮比"相邻两次空等之间变了多少"。
                # 不能拿点击那一刻当基准: 点击本身就是用来改变画面的, 15 秒后去比必然判成"在播"
                idle_seen = True
                idle.reset()
                ref = _shrink(self.device.image)
                time.sleep(COOLDOWN_SLEEP)
                continue
            if not idle.reached():
                time.sleep(COOLDOWN_SLEEP)
                continue
            idle.reset()
            moving, ref = self._scene_changed(ref)
            if moving:
                # 画面还在变 = 过场/转场在播: 不计入空等轮数(长过场不会被误判卡死),
                # 也不点返回(用户规则: 动画播放中返回键无效)
                idle_rounds = 0
                logger.info('Story scene is still changing, keep waiting')
                continue
            idle_rounds += 1
            logger.warning(f'Story idle {conf.ms_idle_timeout:.0f}s without recognizable buttons '
                           f'(round {idle_rounds}/{IDLE_LIMIT})')
            if not diagnosed:
                self._save_diagnosis('idle')
                diagnosed = True
            if self.appear(self.I_UI_BACK_CIRCLE):
                # 退路: 左上角返回。对话/动画播放中它点不动, 而那些画面必有跳过按钮、走不到这里,
                # 所以此时点它不会打断对话或动画
                self.appear_then_click(self.I_UI_BACK_CIRCLE)
                escaped = True
                escape_confirm = Timer(ESCAPE_CONFIRM_WINDOW).start()
            if idle_rounds >= IDLE_LIMIT:
                return 'stuck', clicks

    def _scene_changed(self, ref) -> tuple[bool, np.ndarray]:
        """判断相邻两次空等之间画面有没有明显变化(过场/转场在播)。

        参考帧每轮都换成当前画面: 比的是"这 15 秒变了多少"。若一直拿旧帧当基准, 缓慢漂移的画面
        (飘云、计时节拍)差值会逐轮累加, 总有一轮被误判成"在播"而清零轮数, 永远判不出退不出。

        :return: (是否在变, 新的参考帧 = 当前画面的缩略图)
        """
        small = _shrink(self.device.image)
        changed = ref is None or float(np.abs(small - ref).mean()) >= SCENE_MOVING_DIFF
        return changed, small

    def _click_exit_confirm(self) -> bool:
        """点了返回之后, 若弹出退出确认则点确认(新旧两版确定按钮并列识别)。"""
        for confirm in (self.I_UI_CONFIRM, self.I_UI_CONFIRM_SAMLL, self.I_UI_CONFIRM_OLD):
            if self.appear_then_click(confirm, interval=1.5):
                logger.info(f'Click {confirm.name} to confirm exiting story')
                return True
        return False

    def _battle(self) -> bool:
        """剧情战斗: 走通用战斗(点准备 -> 切自动 -> 等胜负 -> 结算点击)。"""
        logger.hr('Story battle', 2)
        config = self.conf.general_battle
        # 等转场落地(见 STORY_BATTLE_ENTER_WAIT 注释); 已在战斗中/结算时立即通过
        timer = Timer(STORY_BATTLE_ENTER_WAIT).start()
        while not timer.reached():
            self.device.stuck_record_clear()
            self.screenshot()
            if self.is_in_prepare(False) or self.is_in_real_battle(False) \
                    or self.appear(self.I_WIN) or self.appear(self.I_FALSE, threshold=0.6) \
                    or self.appear(self.I_REWARD, threshold=0.6):
                break
            time.sleep(COOLDOWN_SLEEP)
        if self.is_in_real_battle(False) or self.appear(self.I_WIN) \
                or self.appear(self.I_FALSE, threshold=0.6) or self.appear(self.I_REWARD, threshold=0.6):
            # 已经开打或已到结算(任务中断后恢复): 跳过战前流程, 确保自动后直接等结算
            if self.is_in_real_battle(False):
                self.ensure_auto_battle(timeout=self._hook_battle_start_timeout())
            return self.battle_wait(random_click_swipt_enable=config.random_click_swipt_enable)
        return self.run_general_battle(config=config)

    # ---------------- 收尾 ----------------

    def _back_to_courtyard(self) -> None:
        logger.hr('Back to courtyard', 2)
        self.goto_page(page_main)

    def _story_hud_visible(self) -> bool:
        """剧情专用 HUD 双判据, 避免把庭院入口或普通界面三点误认成剧情内图标。"""
        return self.appear(self.I_UI_BACK_CIRCLE, threshold=0.85) and self.appear(self.I_MS_STORY_HUD_CHAT)

    def _story_icon_visible(self, target) -> bool:
        """半透明图标以原始 RGB 模板评分; 附加 HUD 判据过滤跨场景误命中。"""
        return self.appear(target) and self._story_hud_visible()

    @staticmethod
    def _in_chat_banner(target) -> bool:
        """按钮命中框是否碰到顶部聊天播报禁点区(coord() 是框内随机点, 相交即可能点进播报)。"""
        x, y, w, h = target.roi_front
        bx, by, bw, bh = CHAT_BANNER_BOX
        return x < bx + bw and x + w > bx and y < by + bh and y + h > by

    def _any_visible(self, targets) -> bool:
        return any(self.appear(t) for t in targets)

    def _save_diagnosis(self, tag: str) -> None:
        """存一张现场截图, 遇到没见过的剧情界面时据此补素材。"""
        try:
            os.makedirs(DIAGNOSIS_DIR, exist_ok=True)
            from module.base.utils import save_image
            save_image(self.device.image, f'{DIAGNOSIS_DIR}/{datetime.now():%Y-%m-%d_%H-%M-%S}_{tag}.png')
        except Exception as e:
            logger.warning(f'Save diagnosis screenshot failed: {e}')

    def _finish(self, success: bool, note: str, push: bool = False) -> None:
        logger.info(f'Main story finish: {note}')
        if push:
            self.config.notifier.push(title='主线剧情', content=f'<{self.config.config_name}> {note}')
        self.set_next_run(task='MainStory', success=success, server=True)
