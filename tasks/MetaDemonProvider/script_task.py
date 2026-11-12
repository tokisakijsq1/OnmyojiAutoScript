# 超鬼王提供者: 召唤鬼王 -> 点集结邀请指定好友(=开超鬼王协助的账号) -> 等好友击杀
# -> 鬼王消失5s后再召唤, 循环直到无法召唤; 票尽收工次日再跑(success_interval 语义)
# 击杀等待超时(mdp_kill_timeout)重邀一次, 第二次仍超时收工(用户拍板 2026-11-12)
# 2026-11-12 实机反馈: 邀请完任务就结束 -> 两根因已修:
#   1) 让位误伤: Provider 是主动肝任务(同 Orochi 语义), 全程占用调度器直到票尽, 不做守候式让位
#   2) 游戏截断长好友名(丶永…夜)致 exact 匹配永不命中 -> 前缀+difflib 容错匹配
import difflib
from cached_property import cached_property
from time import sleep

from module.base.timer import Timer
from module.exception import TaskEnd, GamePageUnknownError
from module.logger import logger

from tasks.GameUi.game_ui import GameUi
from tasks.GameUi.page import page_main
from tasks.MetaDemonAssist.page import page_mda_huozhu
from tasks.MetaDemonProvider.assets import MetaDemonProviderAssets
from tasks.MetaDemonProvider.config import MetaDemonProvider

# 选好友失败的整体重试轮数
SELECT_RETRY = 2
# 召唤失败重试次数(超过=无法召唤, 收工)
SUMMON_RETRY = 2
# 鬼王消失后等结算再召唤的间隔(秒, 用户指定)
RESUMMON_DELAY = 5
# 鬼王消失判据需连续确认的帧数(防弹窗关闭动画/结算浮层遮挡造成单帧假消失, 契灵假0同源坑)
GONE_CONFIRM_FRAMES = 2
# 好友名容错匹配: 截断名前缀长度 与 difflib 相似度阈值
# 0.75 的取值: 3字名误读1字(0.667)要拦(误邀别人代价高), 4字名误读1字(0.75)起放行
NAME_PREFIX_LEN = 3
NAME_RATIO = 0.75


class ScriptTask(GameUi, MetaDemonProviderAssets):

    @cached_property
    def conf(self) -> MetaDemonProvider:
        return self.config.model.meta_demon_provider

    def run(self):
        friend = self.conf.meta_demon_provider_config.provider_friend_name.strip()
        if not friend:
            raise ValueError('MetaDemonProvider: provider_friend_name 未配置, 无法集结邀请')
        overall = Timer(self.conf.meta_demon_provider_config.mdp_max_duration * 60).start()
        if not self._goto_provider_page():
            logger.warning('Goto provider page failed, activity may be closed')
            self.set_next_run(task='MetaDemonProvider', success=True)
            raise TaskEnd
        while not overall.reached():
            # 注意: 本任务全程不让位(主动肝任务, 同 Orochi 语义)——
            # 等待击杀期间被到点任务打断 = 主号失去集结目标, 任务被拆散(2026-11-12 实机教训)
            # 鬼王在场检测: 自己发现卡 OCR 或 集结标记可见
            self.screenshot()
            king_here = self.ocr_appear(self.O_MDP_CARD) or self.appear(self.I_MDP_RALLY)
            if not king_here:
                if not self._summon():
                    break  # 无法召唤, 收工
                continue
            # 集结邀请
            killed = self._rally_and_wait(friend)
            if killed is None:
                break  # 邀请链路失败, 收工
            if killed:
                logger.info(f'Ghost king killed, resummon in {RESUMMON_DELAY}s')
                sleep(RESUMMON_DELAY)
                self._clear_settlement()
                continue
            # 两次超时未被击杀 -> 收工(鬼王留着, 下次再跑时仍在场可先集结)
            logger.warning('Ghost king not killed after re-invite, stop this run')
            break
        self._exit_to_main()
        self.set_next_run(task='MetaDemonProvider', success=True)
        logger.info('MetaDemonProvider run finish')
        raise TaskEnd

    # ---------------- 页面 ----------------

    def _goto_provider_page(self) -> bool:
        """进祸主降临页(复用超鬼王协助的页面图, 跨任务引用 page 对象是既有惯例)。"""
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

    def _exit_to_main(self) -> None:
        """认层退回庭院; 中间层判据用通用返回键+页面自愈, 终点以庭院判据为准。"""
        for _ in range(10):
            self.screenshot()
            if self.appear(self.I_CHECK_MAIN):
                return
            if self.appear(self.I_MDP_INVITE):
                # 好友弹窗残留: 点弹窗外空白关不掉就跳过(下一轮 _clear 系列兜底)
                sleep(1)
                continue
            if (self.appear(self.I_MDP_RALLY) or self.appear(self.I_MDP_FIND)
                    or self.appear(self.I_MDP_SELECTED) or self.ui_reward_appear_click()):
                self.appear_then_click(self.I_UI_BACK_RED, interval=1)
                sleep(1.2)
                continue
            # 未知层: 点通用返回
            self.appear_then_click(self.I_UI_BACK_YELLOW, interval=1.5)
            sleep(1.2)
        try:
            self.goto_page(page_main)
        except GamePageUnknownError:
            logger.warning('Exit to main failed, leave it to recovery')

    # ---------------- 召唤 ----------------

    def _summon(self) -> bool:
        """召唤鬼王并等待出现在自己发现区; SUMMON_RETRY 次失败=无法召唤(票尽等), 返回 False。"""
        star = self.conf.meta_demon_provider_config.mdp_target_star
        for attempt in range(1, SUMMON_RETRY + 2):
            self.screenshot()
            if self.ocr_appear(self.O_MDP_CARD) or self.appear(self.I_MDP_RALLY):
                return True
            ticket = self._read_ticket()
            logger.info(f'Summon ghost king (attempt {attempt}), ticket={ticket}, target_star={star or "default"}')
            if star:
                if not self._summon_by_queue(star):
                    sleep(2)
                    continue
            else:
                self.ui_click_until_disappear(self.I_MDP_FIND, interval=2.5)
            if self.wait_until_appear(self.I_MDP_RALLY, wait_time=10):
                logger.info('Ghost king summoned')
                return True
            sleep(2)
        logger.warning('Summon failed repeatedly, no more summonable ghost king')
        return False

    def _summon_by_queue(self, star: int) -> bool:
        """指定星级召唤: 全部队列 -> 召唤队列弹窗点对应星级裂变之眼 -> 立即召唤 -> 等2s回召唤界面。
        排序下拉保持默认'星级从高到低': 槽位0=6星, 槽位1=5星, ... 槽位5=1星 (眼行x: 393+97*i)。"""
        self.ui_click(self.I_MDP_QUEUE, stop=self.I_MDP_SUMMON_NOW, interval=2, timeout=10)
        if not self.wait_until_appear(self.I_MDP_SUMMON_NOW, wait_time=4):
            logger.warning('Summon queue popup did not open')
            return False
        slot = 6 - star
        xs = [393, 493, 592, 690, 790, 882]
        if not (0 <= slot < len(xs)):
            logger.warning(f'Star {star} has no queue slot')
            return False
        logger.info(f'Click eye slot {slot} (star {star}) at ({xs[slot]},355)')
        self.device.click(x=xs[slot], y=355, control_name=f'mdp_eye_slot{slot}')
        sleep(0.6)
        ensured = False
        timer = Timer(8).start()
        while not timer.reached():
            self.screenshot()
            if self.appear_then_click(self.I_MDP_SUMMON_NOW, interval=1.5):
                ensured = True
                continue
            if ensured and not self.appear(self.I_MDP_SUMMON_NOW):
                logger.info('Summon by queue done, wait 2s back to summon page')
                sleep(2)
                return True
        logger.warning('Summon-now popup never closed')
        self._close_invite_popup()
        return False

    def _read_ticket(self):
        try:
            cur, _, _t = self.O_MDP_TICKET.ocr(self.device.image)
            return int(cur)
        except (ValueError, TypeError):
            return None

    # ---------------- 集结邀请 + 等击杀 ----------------

    def _rally_and_wait(self, friend: str) -> bool | None:
        """集结邀请指定好友并等待击杀。
        返回 True=被击杀(鬼王消失) / False=两轮等待超时 / None=邀请链路失败(收工)。"""
        timeout = self.conf.meta_demon_provider_config.mdp_kill_timeout * 60
        for round_no in (1, 2):
            if not self._invite_friend(friend, round_no):
                return None
            # 等好友击杀(鬼王消失): 空面具出现 且 卡片OCR读空, 连续 GONE_CONFIRM_FRAMES 帧一致才算
            # (单帧证据坑: 邀请弹窗关闭动画/结算浮层会短暂遮挡卡片区造成假消失)
            timer = Timer(timeout).start()
            keep_alive = Timer(280).start()
            log_timer = Timer(30).start()
            gone_frames = 0
            while not timer.reached():
                self.screenshot()
                if log_timer.reached():
                    logger.info(f'Waiting kill (round {round_no}): '
                                f'remain={int(timer.remain())}s card_ocr={self.ocr_appear(self.O_MDP_CARD)} '
                                f'empty={self.appear(self.I_MDP_EMPTY)}')
                    log_timer.reset()
                if keep_alive.reached():
                    self.device.stuck_record_clear()
                    self.device.stuck_record_add('PAUSE')
                    keep_alive.reset()
                if self.ui_reward_appear_click():
                    keep_alive.reset()
                    gone_frames = 0
                    continue
                if not self.appear(self.I_MDP_INVITE):
                    gone = (not self.ocr_appear(self.O_MDP_CARD)) and self.appear(self.I_MDP_EMPTY)
                    gone_frames = gone_frames + 1 if gone else 0
                    if gone_frames >= GONE_CONFIRM_FRAMES:
                        logger.info('Ghost king is killed and gone')
                        return True
                else:
                    gone_frames = 0
                sleep(2)
            logger.warning(f'Kill wait timeout (round {round_no}), re-invite')
        return False

    def _invite_friend(self, friend: str, round_no: int) -> bool:
        """点集结 -> 弹窗内选好友 -> 点邀请 -> 等弹窗关闭。失败返回 False(调用方收工)。"""
        logger.info(f'Rally invite round {round_no}, friend={friend}')
        self.ui_click(self.I_MDP_RALLY, stop=self.I_MDP_INVITE, interval=2, timeout=12)
        if not self.wait_until_appear(self.I_MDP_INVITE, wait_time=4):
            logger.warning('Friend invite popup did not open')
            return False
        # 选好友: 双列 OCR 注入 keyword, 首屏 -> 滑一屏 -> 重试整轮
        for attempt in range(SELECT_RETRY):
            if self._select_friend(friend):
                break
            logger.info(f'Friend not on current screen ({attempt + 1}/{SELECT_RETRY}), scroll list')
            self.swipe(self.S_MDP_LIST_UP, 2)
            sleep(1.5)
            if self._select_friend(friend):
                break
            sleep(1)
        else:
            logger.warning(f'Friend {friend} not found in invite list')
            self.device.save_screenshot('mdp_friend_not_found', interval=120)
            self._close_invite_popup()
            return False
        # 选中金卡确认(点了名字没选中就再点, 仿 gi detect_select)
        selected = False
        for _ in range(3):
            self.screenshot()
            if self.appear(self.I_MDP_SELECTED):
                selected = True
                break
            if self._select_friend(friend):
                continue
            sleep(1)
        if not selected:
            logger.warning('Friend selected mark never appeared')
            self.device.save_screenshot('mdp_select_missing', interval=120)
            self._close_invite_popup()
            return False
        # 点邀请, 以弹窗消失为成功判据(失败外传约定)
        ensured = False
        timer = Timer(8).start()
        while 1:
            self.screenshot()
            if self.appear_then_click(self.I_MDP_INVITE, interval=1.5):
                ensured = True
                continue
            if ensured and not self.appear(self.I_MDP_INVITE):
                logger.info('Invite sent, popup closed')
                return True
            if timer.reached():
                self.device.save_screenshot('mdp_invite_ensure_missing', interval=120)
                logger.warning('Invite popup never closed')
                self._close_invite_popup()
                return False

    @staticmethod
    def _name_hit(friend: str, text: str) -> bool:
        """好友名容错匹配:
        游戏把长名缩略显示(如 丶永…夜), exact 永不命中(魂十三→魂干三同源的截断坑);
        OCR 也可能形近误读。三级判据: 清洗后全等 / 任一方为另一方的短前缀(截断) / difflib 相似度。"""
        clean = lambda s: s.replace(' ', '').replace('…', '').replace('···', '').replace('...', '')
        f, t = clean(friend), clean(text)
        if not f or not t:
            return False
        if f == t:
            return True
        # 截断: OCR 文本(去掉省略号)是配置名的前缀, 或配置名以 OCR 文本开头
        if len(t) <= len(f) and f.startswith(t[:NAME_PREFIX_LEN]):
            return True
        if len(f) <= len(t) and t.startswith(f[:NAME_PREFIX_LEN]):
            return True
        return difflib.SequenceMatcher(None, f, t).ratio() >= NAME_RATIO

    def _select_friend(self, friend: str) -> bool:
        """当前屏双列 OCR 容错匹配好友名并点击其卡片(不验证选中, 选中由调用方确认)。"""
        for rule in (self.O_MDP_COLUMN_1, self.O_MDP_COLUMN_2):
            rx, ry, rw, rh = rule.roi
            for result in rule.detect_and_ocr(self.device.image):
                text = result.ocr_text
                if not self._name_hit(friend, text):
                    continue
                box = result.box
                xs = [p[0] for p in box]
                ys = [p[1] for p in box]
                cx = rx + int((min(xs) + max(xs)) / 2)
                cy = ry + int((min(ys) + max(ys)) / 2)
                logger.info(f'Friend name hit: "{text}" -> click ({cx},{cy})')
                self.device.click(x=cx, y=cy, control_name=rule.name)
                return True
        return False

    def _close_invite_popup(self) -> None:
        """找不到好友/确认失败时退出弹窗: 依次尝试点公开(取消选中语义)与返回键, 最后导航自愈。"""
        logger.info('Close invite popup')
        timer = Timer(12).start()
        while not timer.reached():
            self.screenshot()
            if not self.appear(self.I_MDP_INVITE):
                return
            self.appear_then_click(self.I_UI_BACK_RED, interval=1.5)
            sleep(1)
        try:
            self.goto_page(page_main)
        except GamePageUnknownError:
            pass

    def _clear_settlement(self) -> None:
        """好友击杀后的结算/奖励弹窗清理(提供者端可能弹协战奖励)。"""
        timer = Timer(10).start()
        while not timer.reached():
            self.screenshot()
            if self.ui_reward_appear_click():
                timer.reset()
                continue
            if self.appear_then_click(self.I_UI_BACK_RED, interval=1):
                timer.reset()
                sleep(1)
                continue
            break


if __name__ == '__main__':
    from module.config.config import Config
    from module.device.device import Device

    c = Config('oas1')
    d = Device(c)
    t = ScriptTask(c, d)

    t.run()
