# 超鬼王提供者: 召唤鬼王 -> 点集结邀请指定好友(=开超鬼王协助的账号) -> 等好友击杀
# -> 鬼王消失5s后再召唤, 循环直到无法召唤; 票尽收工次日再跑(success_interval 语义)
# 击杀等待超时(mdp_kill_timeout)重邀一次, 第二次仍超时收工(用户拍板 2026-11-12)
#
# 2026-11-12 重构(自包含): 页面图/页判据素材拷贝为本任务 mdp_ 副本(此前跨任务引用
# 超鬼王协助的 page_mda_huozhu, 协助模块不在就导航不了); 页面 key 用 page_mdp_* 与
# 协助的 page_mda_* 并存, 两任务互不依赖, 仅共享可复用组件(GameUi/RightActivity)。
#
# 邀请链路时序对齐百鬼夜行范式(tasks/Hyakkiyakou/slave/hya_slave.py _invite_specific_friend):
#   弹窗框出现 != 列表内容就绪 -> 列表就绪等待(OCR 轮询到非空名单, 修 2026-11-12 实机
#   "点完集结后给 OCR 的时间太短"读空误判); 滑动翻页校验有效性(前后名单对比, 吞滑重试,
#   到底即停, 修盲滑两次就放弃); 点中好友留确认间隔再查选中态(修 0.4s 连点无间隔)。
#
# 其他既有语义(保持不变):
#   1) 让位误伤已修: Provider 是主动肝任务(同 Orochi 语义), 全程占用调度器直到票尽
#   2) 游戏截断长好友名(丶永…夜) -> _name_hit 前缀+difflib 容错匹配(单测11例)
#   3) 鬼王消失双帧确认(弹窗关闭动画/结算浮层遮挡的单帧假消失, 契灵假0同源坑)
import difflib
from cached_property import cached_property
from time import sleep

from module.base.timer import Timer
from module.exception import TaskEnd, GamePageUnknownError
from module.logger import logger

from tasks.GameUi.game_ui import GameUi
from tasks.GameUi.page import page_main
from tasks.MetaDemonProvider.assets import MetaDemonProviderAssets
from tasks.MetaDemonProvider.config import MetaDemonProvider
from tasks.MetaDemonProvider.page import page_mdp_huozhu

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
# 邀请弹窗列表就绪: 首个沉降等待(秒) / 就绪轮询上限(秒) / 就绪判据=名字最少字符数
LIST_SETTLE = 1.0
LIST_READY_TIMEOUT = 6
LIST_READY_MIN_CHARS = 2
# 选好友最多向下翻屏数(首屏 + MAX_SWIPES 次滑动; 已观察列表规模两屏内, 留余量)
MAX_SWIPES = 4
# 选中标记确认轮数(每轮间隔确认, 给选中动画留渲染时间)
SELECT_CONFIRM_RETRY = 3

# ---------------- 召唤队列卡识别(与排序无关, 数星标) ----------------
# 弹窗卡按"拥有的星级种类"压缩排列(缺的星级不留空位), 固定坐标不可用(2026-11-12 用户实测);
# 排序下拉(高到低/低到高)只影响位置顺序, 识别与它无关。
# 锚点=卡上星标(橙色小星): 实测单颗宽5-6px 间距9.3px, 星级行 y 370-380, 卡间距约99px。
# 色带列游程计数(同 MetaDemonAssist 亮珠范式): 游程=单颗星, x聚类=卡, 簇内颗数=星级。
STAR_BAND = (340, 358, 620, 36)  # 星标检索带 x,y,w,h(全6卡 x348-937, 弹窗固定布局)
STAR_PIP_MIN_W = 3               # 单颗星标最小像素宽(滤金框/眼睛红边的1px毛边)
STAR_CLUSTER_GAP = 40            # x聚类阈值: 星间距9px归同卡, 卡间距99px分卡
EYE_CLICK_Y = 340                # 卡上眼睛图标中心y(点击选中)


def find_eye_cards(image):
    """识别召唤队列弹窗里的裂变之眼卡(纯函数, 便于离线验证同一份逻辑)。
    星标橙色带 -> 列游程=单颗星 -> 按x聚类=卡, 簇内颗数=星级。
    返回 [(star, cx, cy), ...] 按屏幕从左到右。
    注意: 星标分"点亮(橙)/未点亮(灰)"两态(如持有3颗的4星眼显示3橙2灰),
    橙色掩膜天然只数点亮的 = 当前有效星级, 灰星被正确忽略(2026-11-12 部分卡截图人眼核对)。"""
    x0, y0, w, h = STAR_BAND
    band = image[y0:y0 + h, x0:x0 + w]
    r = band[:, :, 0].astype(int)
    g = band[:, :, 1].astype(int)
    b = band[:, :, 2].astype(int)
    colsum = ((r > 180) & (g > 90) & (g < 190) & (b < 90)).sum(axis=0)
    pips = []
    start = None
    for x in range(w + 1):
        on = x < w and colsum[x] > 3
        if on and start is None:
            start = x
        elif not on and start is not None:
            if x - start >= STAR_PIP_MIN_W:
                pips.append(x0 + (start + x) // 2)
            start = None
    cards = []
    for p in pips:
        if cards and p - cards[-1][-1] <= STAR_CLUSTER_GAP:
            cards[-1].append(p)
        else:
            cards.append([p])
    return [(len(c), sum(c) // len(c), EYE_CLICK_Y) for c in cards]


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
        """进祸主降临页(本任务自包含页面图, 不再依赖超鬼王协助模块)。"""
        try:
            self.goto_page(page_mdp_huozhu)
            return True
        except GamePageUnknownError:
            logger.warning('Goto page_mdp_huozhu failed, activity may be closed')
            try:
                self.goto_page(page_main)
            except GamePageUnknownError:
                pass
            return False

    def _exit_to_main(self) -> None:
        """认层退回庭院; 中间层判据用通用返回键+页面自愈, 终点以庭院判据为准。"""
        for _ in range(10):
            self.device.stuck_record_clear()
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
            # 单轮可达 16s 无点击(模板不匹配时 ui_click/wait_until_appear 干等), 每轮清卡死记录
            self.device.stuck_record_clear()
            self.screenshot()
            if self.ocr_appear(self.O_MDP_CARD) or self.appear(self.I_MDP_RALLY):
                return True
            ticket = self._read_ticket()
            logger.info(f'Summon ghost king (attempt {attempt}), ticket={ticket}, target_star={star or "default"}')
            if star:
                res = self._summon_by_queue(star)
                if res == 'depleted':
                    # 目标星级及更高的眼卡都没有: 票尽语义, 直接收工(不再空重试)
                    logger.warning('No summonable eye card (target star and higher all absent), stop this run')
                    return False
                if not res:
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

    def _summon_by_queue(self, star: int):
        """指定星级召唤: 全部队列弹窗内按星标识别各眼卡(与排序无关), 点精确星级的卡;
        没有该星则点星级更高里最接近的; 再没有 = 无可召唤卡, 返回 'depleted' 收工。
        返回 True=已召唤 / False=弹窗链路失败(调用方可重试) / 'depleted'=无卡可召(调用方结束任务)。"""
        self.ui_click(self.I_MDP_QUEUE, stop=self.I_MDP_SUMMON_NOW, interval=2, timeout=10)
        if not self.wait_until_appear(self.I_MDP_SUMMON_NOW, wait_time=4):
            logger.warning('Summon queue popup did not open')
            return False
        cards = find_eye_cards(self.device.image)
        if not cards:
            # 防弹窗渲染中误判: 稍候复核一次再下结论
            sleep(1.5)
            self.screenshot()
            cards = find_eye_cards(self.device.image)
        if not cards:
            logger.warning('No eye card in queue popup at all')
            self._close_summon_popup()
            return 'depleted'
        usable = [c for c in cards if c[0] >= star]
        if not usable:
            logger.warning(f'No eye card star>={star} (owned stars={sorted(c[0] for c in cards)}), stop summon')
            self._close_summon_popup()
            return 'depleted'
        # 精确星级优先, 没有则在更高星里取最接近的(min); 不往低星兜底(用户指定)
        picked = min(usable, key=lambda c: c[0])
        star_n, cx, cy = picked
        logger.info(f'Click eye card star={star_n} at ({cx},{cy}), owned stars={sorted(c[0] for c in cards)}')
        self.device.click(x=cx, y=cy, control_name='mdp_eye_card')
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
        self._close_summon_popup()
        return False

    def _close_summon_popup(self) -> bool:
        """关召唤队列弹窗: 粉叉(I_UI_BACK_RED), 以立即召唤按钮消失为出口。"""
        timer = Timer(10).start()
        while not timer.reached():
            self.screenshot()
            if not self.appear(self.I_MDP_SUMMON_NOW):
                return True
            self.appear_then_click(self.I_UI_BACK_RED, interval=1.5)
            sleep(1)
        logger.warning('Close summon popup failed')
        return False

    def _read_ticket(self):
        # 顶栏票数是单独数字(如 37), 不是 cur/total 格式, 用 Digit 模式直接返回 int
        try:
            return int(self.O_MDP_TICKET.ocr(self.device.image))
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
        """点集结 -> 弹窗内选好友 -> 点邀请 -> 等弹窗关闭。失败返回 False(调用方收工)。
        时序对齐百鬼夜行范式: 弹窗开 -> 列表就绪等待 -> 逐屏查找(滑动有效性校验)
        -> 点中后留间隔确认选中态 -> 点邀请等弹窗消失。"""
        logger.info(f'Rally invite round {round_no}, friend={friend}')
        self.ui_click(self.I_MDP_RALLY, stop=self.I_MDP_INVITE, interval=2, timeout=12)
        if not self.wait_until_appear(self.I_MDP_INVITE, wait_time=4):
            logger.warning('Friend invite popup did not open')
            return False
        # 逐屏查找: 首屏 -> 滑动翻页(校验真的翻了页, 吞滑补滑, 到底即停)
        found = False
        for screen in range(MAX_SWIPES + 1):
            self.screenshot()
            self._wait_list_ready()
            if self._select_friend(friend):
                found = True
                break
            if screen >= MAX_SWIPES:
                break
            logger.info(f'Friend not on screen {screen + 1}/{MAX_SWIPES + 1}, scroll list')
            if not self._scroll_friend_list():
                logger.info('Friend list scroll has no effect, reached bottom')
                break
        if not found:
            logger.warning(f'Friend {friend} not found in invite list')
            self.device.save_screenshot('mdp_friend_not_found', interval=120)
            self._close_invite_popup()
            return False
        # 选中标记确认(点中后先留间隔给选中动画渲染, 再复查; 没选中就重新点名字)
        selected = False
        for attempt in range(SELECT_CONFIRM_RETRY):
            sleep(1)
            self.screenshot()
            if self.appear(self.I_MDP_SELECTED):
                selected = True
                break
            logger.info(f'Selected mark not visible (attempt {attempt + 1}/{SELECT_CONFIRM_RETRY}), re-click name')
            if self._select_friend(friend):
                continue
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

    def _list_names(self) -> list:
        """读邀请弹窗双列当前可见名字(用于列表就绪判据与滑动有效性对比)。"""
        names = []
        for rule in (self.O_MDP_COLUMN_1, self.O_MDP_COLUMN_2):
            for result in rule.detect_and_ocr(self.device.image):
                text = (result.ocr_text or '').replace(' ', '')
                if text:
                    names.append(text)
        return names

    def _wait_list_ready(self) -> bool:
        """等邀请弹窗的好友列表渲染完成(弹窗框出现 != 内容就绪, 2026-11-12 实机读空教训)。
        仿百鬼夜行进面板后的列表加载等待, 但用实际 OCR 读取代替盲等:
        LIST_SETTLE 首沉降后轮询, 任一列读到名字即就绪; 超时返回 False(调用方继续走选好友,
        选不到自然走失败链路, 不额外分支)。"""
        sleep(LIST_SETTLE)
        timer = Timer(LIST_READY_TIMEOUT).start()
        while not timer.reached():
            self.screenshot()
            if any(len(n) >= LIST_READY_MIN_CHARS for n in self._list_names()):
                return True
            sleep(0.5)
        return False

    def _scroll_friend_list(self) -> bool:
        """滑动好友列表并确认真的翻页。游戏偶尔吞滑动, 盲滑会一路空翻到底
        (百鬼夜行 _scroll_friend_list 同源坑); 滑动前后对比双列 OCR 名单判定。
        返回 True=列表内容变化(翻页成功) / False=没变化(吞滑或已到底, 调用方停止翻页)。"""
        before = self._list_names()
        self.swipe(self.S_MDP_LIST_UP, 2)
        sleep(1.2)
        self.screenshot()
        after = self._list_names()
        return after != before

    def _close_invite_popup(self) -> None:
        """找不到好友/确认失败时退出弹窗: 点粉叉, 出口=邀请按钮消失; 超时导航自愈。"""
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
