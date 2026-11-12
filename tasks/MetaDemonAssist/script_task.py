# 超鬼王协助: 庭院守候好友鬼王邀请横幅 -> 前往协助挑战(按星级决定2.5倍伤害) -> 通用战斗
# -> 处理好友发现列表内其余可挑战鬼王 -> 无可挑战返回庭院继续守候
# 调度: SCHEDULER_PRIORITY 最末(最低优先级); 守候/战斗间隙主动让位到点到点的其他任务,
# 其他任务结束后本任务 next_run 已过期被自动唤醒, 每次唤醒重新切御魂
import re
from cached_property import cached_property
from datetime import datetime, timedelta
from time import sleep

import cv2
import numpy as np

from module.base.timer import Timer
from module.config.config import Function
from module.exception import TaskEnd, GamePageUnknownError
from module.logger import logger

from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.Component.SwitchSoul.switch_soul import SwitchSoul
from tasks.GameUi.game_ui import GameUi
from tasks.GameUi.page import page_main, page_shikigami_records
from tasks.MetaDemonAssist.assets import MetaDemonAssistAssets
from tasks.MetaDemonAssist.config import MetaDemonAssist
from tasks.MetaDemonAssist.page import page_mda_huozhu

# 好友发现卡槽: 文本行"剩余时间"槽1 y406-446 / 槽2 y535-575; 珠子行槽1 y450 / 槽2 y579
CARD_SLOT_OFFSET = 129
# 珠子扫描窗(相对槽1珠子行), 亮珠颜色(228,114,35)已三截图标定
PEARL_X0, PEARL_W = 52, 76
PEARL_Y0, PEARL_H = 435, 70


class ScriptTask(GameUi, SwitchSoul, GeneralBattle, MetaDemonAssistAssets):
    # 战败判据任务内覆盖: 超鬼王败局美术在(410,95), 上游 I_FALSE 搜索区(413,124,100,100)
    # 不含该位置, 战败永不识别。I_MDA_FALSE=gb_false 同美术副本、搜索区(400,85,120,150)
    # 同时罩住超鬼王(410,95)与普通(413,124)两布局。类属性 shadowing 靠 MRO 最派生优先,
    # 只影响本任务实例的 self.I_FALSE, 不改共享资产(禁止重蹈 d5c0b823 全进程污染覆辙)。
    I_FALSE = MetaDemonAssistAssets.I_MDA_FALSE

    @cached_property
    def conf(self) -> MetaDemonAssist:
        return self.config.model.meta_demon_assist

    def run(self):
        # 每次唤醒先切御魂(用户要求: 其他任务跑完后唤起本任务, 重新切御魂再回庭院守候)
        self._switch_soul()
        self.goto_page(page_main)
        # 初始清扫: 处理本任务未运行期间(其他任务在跑时)好友共享的存量鬼王
        fatigue_full = False
        if self._goto_huozhu():
            fatigue_full = self._assist_loop() == 'fatigue_full'
            self._exit_to_main()
        # 疲劳满收工(2026-11-12 用户纠正: 顶栏是疲劳非资源, 满100不能打需等时间恢复;
        # 旧逻辑回庭院守候, 横幅还在就反复"前往->返回"往返)
        if fatigue_full:
            gap = self.conf.meta_demon_assist_config.mda_rerun_gap
            self.set_next_run(task='MetaDemonAssist', success=None, finish=False, server=False,
                              target=datetime.now() + timedelta(minutes=gap))
            logger.info(f'Fatigue full, skip waiting banner, retry in {gap} min')
            raise TaskEnd
        # 庭院守候邀请横幅
        self._wait_banner()
        gap = self.conf.meta_demon_assist_config.mda_rerun_gap
        self.set_next_run(task='MetaDemonAssist', success=None, finish=False, server=False,
                          target=datetime.now() + timedelta(minutes=gap))
        logger.info('MetaDemonAssist run finish')
        raise TaskEnd

    # ---------------- 让位 ----------------

    def _yield_to_scheduler(self) -> None:
        """其他任一启用的任务到点(next_run<=now)时主动让位:
        重排自己到 now + TaskEnd, 调度器按优先级必先跑对方, 对方结束后本任务自动被唤醒。"""
        now = datetime.now()
        for key, value in self.config.model.dict().items():
            if key == 'meta_demon_assist':
                continue
            func = Function(key, value)
            if not func.enable or not isinstance(func.next_run, datetime):
                continue
            if func.next_run <= now:
                logger.info(f'Yield to pending task: {func.command}')
                self.set_next_run(task='MetaDemonAssist', success=None, finish=False, server=False,
                                  target=now)
                raise TaskEnd('MetaDemonAssist yield')

    # ---------------- 切御魂 ----------------

    def _switch_soul(self) -> None:
        conf = self.conf.switch_soul_config
        if not conf.enable and not conf.enable_switch_by_name:
            return
        logger.hr('Switch soul', 2)
        if conf.enable:
            self.goto_page(page_shikigami_records)
            self.run_switch_soul(conf.switch_group_team)
        if conf.enable_switch_by_name:
            self.goto_page(page_shikigami_records)
            self.run_switch_soul_by_name(conf.group_name, conf.team_name)
        self.goto_page(page_main)

    # ---------------- 页面进出 ----------------

    def _goto_huozhu(self) -> bool:
        """经庭院右侧栏: 祸至无日页 -> 祸主降临页。活动未开/入口缺失返回 False。"""
        try:
            self.goto_page(page_mda_huozhu)
            return True
        except GamePageUnknownError:
            logger.warning('Goto page_mda_huozhu failed, activity may be closed')
            try:
                self.goto_page(page_main)
            except GamePageUnknownError:
                pass
            return False

    def _in_huozhu_page(self, is_screenshot: bool = True) -> bool:
        if is_screenshot:
            self.screenshot()
        return self.appear(self.I_MDA_TITLE_HUOZHU)

    def _exit_to_main(self) -> None:
        """认层退出: 祸主降临页 -> 祸至无日页 -> 庭院, 每层配判据, 点完等转场。"""
        for _ in range(10):
            self.screenshot()
            if self.appear(self.I_CHECK_MAIN):
                return
            clicked = False
            if (self.appear(self.I_MDA_TITLE_HUOZHU) or self.appear(self.I_MDA_CHALLENGE)
                    or self.appear(self.I_MDA_TITLE_EVENT) or self.appear(self.I_MDA_GOTO_HUOZHU)):
                self.click(self.I_MDA_BACK)
                clicked = True
            elif self.appear(self.I_UI_BACK_RED):
                self.appear_then_click(self.I_UI_BACK_RED, interval=1)
                clicked = True
            if clicked:
                sleep(1.2)
        try:
            self.goto_page(page_main)
        except GamePageUnknownError:
            logger.warning('Exit to main failed, leave it to recovery')

    # ---------------- 庭院守候 ----------------

    def _wait_banner(self) -> None:
        conf = self.conf.meta_demon_assist_config
        overall = Timer(conf.mda_max_duration * 60).start()
        stuck_keeper = Timer(280).start()
        recover_fail = 0
        self._keep_alive(stuck_keeper)
        while not overall.reached():
            self._yield_to_scheduler()
            self.screenshot()
            if stuck_keeper.reached():
                self._keep_alive(stuck_keeper)
            if not self.appear(self.I_CHECK_MAIN):
                # 庭院丢失(弹窗/被拉走): 导航自愈; 连续失败交给重启
                try:
                    self.goto_page(page_main)
                    recover_fail = 0
                except GamePageUnknownError:
                    recover_fail += 1
                    if recover_fail >= 3:
                        raise
                self._keep_alive(stuck_keeper)
                continue
            if self.appear(self.I_MDA_BANNER_GO) and self.ocr_appear(self.O_MDA_BANNER):
                star = self._banner_star()
                logger.info(f'Ghost king invitation detected, banner star: {star}')
                self.click(self.I_MDA_BANNER_GO)
                sleep(1)
                if not self.wait_until_appear(self.I_MDA_TITLE_HUOZHU, wait_time=8):
                    # 横幅过期/点击落空, 走右侧栏入口兜底
                    logger.info('Banner go click ineffective, fallback to right bar entry')
                    if not self._goto_huozhu():
                        self._keep_alive(stuck_keeper)
                        continue
                self._assist_loop(banner_star=star)
                self._exit_to_main()
                # 交互含点击会清卡死白名单, 重新登记长等待豁免
                self._keep_alive(stuck_keeper)
            sleep(conf.mda_monitor_interval)

    def _keep_alive(self, keeper: Timer) -> None:
        self.device.stuck_record_clear()
        self.device.stuck_record_add('PAUSE')
        keeper.reset()

    def _banner_star(self) -> int | None:
        """从横幅文字读星级: 发现「N星」鬼王"""
        for box in self.O_MDA_BANNER.detect_and_ocr(self.device.image):
            m = re.search(r'(\d)\s*星', box.ocr_text)
            if m:
                return int(m.group(1))
        return None

    # ---------------- 协助主循环 ----------------

    def _assist_loop(self, banner_star: int = None) -> None:
        """在祸主降临页: 扫好友发现卡片 -> 选卡 -> 按星级设2.5倍 -> 挑战 -> 通用战斗,
        直到无可挑战卡/资源不足/连败。返回时停在本页(或已离开), 退出交调用方。
        注意: 协助阶段不做让位检查(主动肝语义, 同 Provider/Orochi)——
        每场战斗结束后被到点任务打断 = 任务结束(2026-11-12 实机"战后即结束"根因), 让位只在守候循环。"""
        max_rounds = 30
        no_progress = 0
        lose_streak = 0
        sleep(2)  # 横幅跳转/战斗回页后, 好友发现卡数据服务器异步加载(悬赏教训: 1.4s+才就绪)
        for _ in range(max_rounds):
            self.screenshot()
            if not self._in_huozhu_page(False):
                # 弹窗/转场: 先尝试关弹窗
                if self.appear_then_click(self.I_UI_BACK_RED, interval=1):
                    sleep(1)
                    continue
                if self.wait_until_appear(self.I_MDA_TITLE_HUOZHU, wait_time=3):
                    continue
                logger.warning('Lost huozhu page in assist loop')
                return
            # 疲劳预检查: 顶栏 N/100 是疲劳度(随时间恢复), 满了才不能打(用户纠正 2026-11-12,
            # 之前误当"资源"用低值判耗尽导致疲劳剩8被拦)。读失败/低值一律继续打。
            try:
                cur, _, _total = self.O_MDA_RESOURCE.ocr(self.device.image)
                cur = int(cur)
            except (ValueError, TypeError):
                cur = None
            fatigue_max = self.conf.meta_demon_assist_config.mda_fatigue_max
            if cur is not None and cur >= fatigue_max:
                logger.info(f'Fatigue full: {cur}/{fatigue_max}, stop assisting and wait recovery')
                return 'fatigue_full'
            slot = self._find_challengeable_slot()
            if slot is None:
                # 单帧证据坑: 战斗结算浮层/页面数据异步加载会短暂让卡片区读空, 三帧都空才认定无可挑战
                for _f in range(2):
                    sleep(1.5)
                    self.screenshot()
                    slot = self._find_challengeable_slot()
                    if slot is not None:
                        break
                if slot is None:
                    logger.info('No challengeable ghost king in friend list (3 frames)')
                    return
            # 选卡(已选中则跳过)
            if not self.appear(self.I_MDA_CHALLENGE):
                self.click(self.C_MDA_CARD_1 if slot == 0 else self.C_MDA_CARD_2)
                sleep(0.8)
                if not self.wait_until_appear(self.I_MDA_CHALLENGE, wait_time=5):
                    no_progress += 1
                    logger.warning(f'Select card slot {slot} failed ({no_progress})')
                    if no_progress >= 3:
                        return
                    continue
            # 星级: 亮珠计数, 失败用横幅星级兜底
            star = self._count_pearls(slot)
            if not star:
                star = banner_star or 0
                logger.warning(f'Pearl count failed on slot {slot}, fallback banner star {star}')
            logger.info(f'Challenge ghost king: slot={slot} star={star}')
            # 2.5倍伤害: >=配置星级才勾选
            self._set_buff(star >= self.conf.meta_demon_assist_config.mda_buff_min_star)
            # 挑战
            self.ui_click_until_disappear(self.I_MDA_CHALLENGE, interval=1.8)
            if not self._wait_battle_enter():
                no_progress += 1
                logger.warning(f'Challenge click ineffective ({no_progress})')
                if no_progress >= 3:
                    return
                sleep(1)
                continue
            win = self.run_general_battle(config=self.conf.general_battle)
            if win:
                lose_streak = 0
                no_progress = 0
            else:
                lose_streak += 1
                if lose_streak >= 3:
                    logger.warning('Lose 3 battles in a row, stop assisting')
                    return
            sleep(1)  # 结算点击后的第一段转场
            # 等回到祸主降临页再进下一轮(消除转场中 OCR/页面判据的单帧误判)
            if not self.wait_until_appear(self.I_MDA_TITLE_HUOZHU, wait_time=5):
                logger.warning('Back to huozhu page not confirmed after battle')
        logger.info('Assist loop max rounds reached')

    def _find_challengeable_slot(self) -> int | None:
        """OCR 卡片区逐行判: 剩余时间=可挑战(按y分槽), 击败奖励结算中=跳过。"""
        try:
            results = self.O_MDA_CARD.detect_and_ocr(self.device.image)
        except Exception as e:
            logger.warning(f'Card panel ocr failed: {e}')
            return None
        for box in results:
            if '剩余时间' not in box.ocr_text:
                continue
            ys = [p[1] for p in box.box]
            y = self.O_MDA_CARD.roi[1] + min(ys)
            return 0 if y < 368 + 100 else 1
        return None

    def _count_pearls(self, slot: int) -> int:
        """数卡槽珠子行的亮珠数 = 星级(亮几颗是几星, 2026-11-11 三截图+合成5/6星离线标定)。"""
        y0 = PEARL_Y0 + CARD_SLOT_OFFSET * slot
        roi = self.device.image[y0:y0 + PEARL_H, PEARL_X0:PEARL_X0 + PEARL_W].astype(int)
        r, g, b = roi[:, :, 0], roi[:, :, 1], roi[:, :, 2]
        mask = ((r > 195) & (g > 55) & (g < 215) & (b < 140) & (r - b > 60)).astype(np.uint8)
        n, _, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
        count = 0
        for i in range(1, n):
            w, h, area = stats[i, 2], stats[i, 3], stats[i, 4]
            if 25 <= area <= 120 and 6 <= w <= 16 and 9 <= h <= 16:
                count += 1
        return count if 0 < count <= 6 else 0

    def _set_buff(self, enable: bool) -> None:
        """设置 2.5 倍伤害勾选。双态模板互斥; 状态不明时不盲点(反复盲点会来回翻转),
        仅在状态明确且与目标不符时点一次。"""
        for _ in range(2):
            self.screenshot()
            on = self.appear(self.I_MDA_BUFF_ON)
            off = self.appear(self.I_MDA_BUFF_OFF)
            if on == off:
                logger.warning(f'Buff checkbox state ambiguous (on={on}, off={off}), skip toggle')
                return
            if (enable and on) or (not enable and off):
                logger.info(f'2.5x damage buff already {"on" if enable else "off"}')
                return
            logger.info(f'Switch 2.5x damage buff to {"on" if enable else "off"}')
            self.click(self.C_MDA_BUFF)
            sleep(0.8)

    def _wait_battle_enter(self, timeout: int = 10) -> bool:
        """点完挑战后确认真的进了战斗(准备界面/正式战斗), 挑战按钮还在视为点击落空。"""
        timer = Timer(timeout).start()
        while not timer.reached():
            self.screenshot()
            if self.is_in_prepare(False) or self.is_in_real_battle(False):
                return True
            if self.appear(self.I_MDA_CHALLENGE):
                return False
        return self.is_in_prepare(False) or self.is_in_real_battle(False)


if __name__ == '__main__':
    from module.config.config import Config
    from module.device.device import Device

    c = Config('oas1')
    d = Device(c)
    t = ScriptTask(c, d)

    t.run()
