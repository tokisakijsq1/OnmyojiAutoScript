# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from datetime import timedelta, time, datetime
from time import sleep
from typing import List

import re
import cv2
from cached_property import cached_property

from module.atom.image import RuleImage
from module.atom.ocr import RuleOcr
from module.base.timer import Timer
from module.exception import TaskEnd, GameStuckError
from module.logger import logger
from tasks.Component.Costume.config import MainType
from tasks.Component.GeneralBattle.config_general_battle import GeneralBattleConfig
from tasks.GameUi.page import page_main, page_exploration, page_shikigami_records
from tasks.Secret.script_task import ScriptTask as SecretScriptTask
from tasks.WantedQuests.assets import WantedQuestsAssets
from tasks.WantedQuests.config import CooperationType, CooperationSelectMask
from tasks.WantedQuests.explore import WQExplore, ExploreWantedBoss


class ScriptTask(WQExplore, SecretScriptTask, WantedQuestsAssets):
    want_strategy_excluding: list[list] = []  # 不需要执行的
    # 追踪界面(显示"前往"按钮的界面,左上角位置,神秘任务不好使)显示以下名称时,任务不再执行
    unwanted_boss_name_list: list = []

    @cached_property
    def battle_config(self) -> GeneralBattleConfig:
        return self.config.model.wanted_quests.general_battle

    def run(self):
        con = self.config.model.wanted_quests
        unwanted_boss_names = con.wanted_quests_config.unwanted_boss_names
        if unwanted_boss_names is not None and unwanted_boss_names != '':
            import re
            self.unwanted_boss_name_list = re.split(r"[，,]", unwanted_boss_names)

        # 自动换御魂
        if con.switch_soul_config.enable:
            self.goto_page(page_shikigami_records)
            self.run_switch_soul(con.switch_soul_config.switch_group_team)
        if con.switch_soul_config.enable_switch_by_name:
            self.goto_page(page_shikigami_records)
            self.run_switch_soul_by_name(con.switch_soul_config.group_name, con.switch_soul_config.team_name)

        preSuc = False
        if (self.get_config()).cooperation_only:
            preSuc = self.pre_work_cooperation_only()
        else:
            preSuc = self.pre_work()
        if not preSuc:
            # 无法完成预处理 很有可能你已经完成了悬赏任务
            logger.warning('Cannot pre-work')
            logger.warning('You may have completed the reward task')
            self.next_run()
            raise TaskEnd('WantedQuests')

        error_count = 0
        while 1:
            self.screenshot()
            if not self.is_wq_remained():
                logger.info("no more wq remained")
                break
            if self.appear(self.I_WQ_BOX):
                logger.info("get reward")
                self.ui_get_reward(self.I_WQ_BOX)
                continue
            if self.appear(self.I_TREASURE_BOX_CLICK):
                logger.info("get treasure")
                self.ui_get_reward(self.I_TREASURE_BOX_CLICK)
                continue
            if error_count > 3:
                logger.warning('failed too many times, exit')
                break
            if self.current_count >= 30:
                logger.error(f'current count {self.current_count} >= 20, exit')
                raise Exception('current count >= 20, exit')
            cu, re, total, area = self.find_wq(self.device.image)
            logger.info(f"find_wq result: current {cu} remain {re} total {total} area {area}")
            if re == -2:
                logger.info("only completed wanted quests remained")
                break
            if re == -1:
                error_count += 1
                # 没找到任务 尝试上滑
                self.swipe(self.S_WQ_LIST_UP, interval=1)
                sleep(1)
                continue
            # 找到任务,执行
            self.O_WQ_TEXT_ALL.area = area
            if self.execute_mission(self.O_WQ_TEXT_ALL, total - cu) is False:
                # 该任务无法执行(无可打目的地/怪名被排除等): 计入失败,
                # 否则会永远找到同一个任务反复进详情页形成无点击死循环
                error_count += 1
            else:
                error_count = 0
            sleep(1.5)

        self.next_run()
        raise TaskEnd('WantedQuests')

    def next_run(self):
        before_end: time = self.get_config().before_end
        if before_end == time(hour=0, minute=0, second=0):
            self.set_next_run(task='WantedQuests', success=True, finish=True)
            return
        time_delta = timedelta(hours=-before_end.hour, minutes=-before_end.minute, seconds=-before_end.second)
        now_datetime = datetime.now()
        now_time = now_datetime.time()
        if time(hour=5) <= now_time < time(hour=18):
            # 如果是在5点到18点之间，那就设定下一次运行的时间为第二天的5点 + before_end
            next_run_datetime = datetime.combine(now_datetime.date() + timedelta(days=1), time(hour=5))
            next_run_datetime = next_run_datetime + time_delta
        elif time(hour=18) <= now_time < time(hour=23, minute=59, second=59):
            # 如果是在18点到23点59分59秒之间，那就设定下一次运行的时间为第二天的18点 + before_end
            next_run_datetime = datetime.combine(now_datetime.date() + timedelta(days=1), time(hour=18))
            next_run_datetime = next_run_datetime + time_delta
        else:
            # 如果是在0点到5点之间，那就设定下一次运行的时间为今天的18点 + before_end
            next_run_datetime = datetime.combine(now_datetime.date(), time(hour=18))
            next_run_datetime = next_run_datetime + time_delta
        self.set_next_run(task='WantedQuests', target=next_run_datetime)

    def pre_work(self):
        """
        前置工作，
        :return:
        """
        self.goto_page(page_main)
        done_timer = Timer(5)
        while 1:
            self.screenshot()
            if self.appear(self.I_TRACE_DISABLE):
                break
            if self.appear_then_click(self.I_WQ_SEAL, interval=1):
                continue
            if self.appear_then_click(self.I_TRACE_ENABLE, interval=1):
                continue
            if self.special_main and self.click(self.C_SPECIAL_MAIN, interval=3):
                logger.info('Click special main left to find wanted quests')
                continue
            if self.appear(self.I_UI_BACK_RED):
                if not done_timer.started():
                    done_timer.start()
            if done_timer.started() and done_timer.reached():
                self.ui_click_until_disappear(self.I_UI_BACK_RED)
                return False
        # 已追踪所有任务
        logger.info('All wanted quests are traced')

        # 存在协作任务则邀请
        self.screenshot()
        if self.appear(self.I_WQ_INVITE_1) or self.appear(self.I_WQ_INVITE_2) \
                or self.appear(self.I_WQ_INVITE_3) or self.appear(self.I_WQ_INVITE_4):
            if self.need_invite_vip():
                self.all_cooperation_invite()
            else:
                self.invite_five()
        self.ui_click_until_disappear(self.I_UI_BACK_RED)
        self.goto_page(page_exploration)
        return True

    def pre_work_cooperation_only(self):
        #
        if self.get_current_page() != page_main:
            self.goto_page(page_main)
        # 打开悬赏封印 界面
        done_timer = Timer(5)
        while 1:
            self.screenshot()
            if self.appear(self.I_TRACE_ENABLE) or self.appear(self.I_TRACE_DISABLE):
                break
            if self.appear_then_click(self.I_WQ_SEAL, interval=1):
                continue
            if self.special_main and self.click(self.C_SPECIAL_MAIN, interval=3):
                logger.info('Click special main left to find wanted quests')
                continue
            if self.appear(self.I_UI_BACK_RED):
                if not done_timer.started():
                    done_timer.start()
            if done_timer.started() and done_timer.reached():
                self.ui_click_until_disappear(self.I_UI_BACK_RED)
                return False
        #
        if not (self.appear(self.I_WQ_INVITE_1) or self.appear(self.I_WQ_INVITE_2)
                or self.appear(self.I_WQ_INVITE_3) or self.appear(self.I_WQ_INVITE_4)):
            logger.info("there is no cooperation quest")
            return False

        # if self.appear(self.I_WQ_INVITE_1):
        #     self.trace_one(self.I_WQ_INVITE_1)
        # if self.appear(self.I_WQ_INVITE_2):
        #     self.trace_one(self.I_WQ_INVITE_2)
        # if self.appear(self.I_WQ_INVITE_3):
        #     self.trace_one(self.I_WQ_INVITE_3)

        # 追踪任务 并邀请
        self.all_cooperation_invite()

        self.ui_click_until_disappear(self.I_UI_BACK_RED)
        self.goto_page(page_exploration)
        return True

    def _wq_detail_open(self) -> bool:
        """
            悬赏详情页打开判定：
            普通任务标题是"悬赏目标：击败N个XX"，协作任务标题是"自己击败XX"没有"悬赏"字样
            （协作详情页为实机发现 2026-10-28：只认"悬赏目标"会让协作任务在详情页判定处
            20s 超时，主循环反复重进形成无点击死循环卡死）
        """
        return self.appear(self.O_WQ_TARGET) or self.appear(self.O_WQ_TARGET_COOP)

    def trace_one(self, card_index: int):
        """
            追踪单个协作任务：点击协作卡片打开详情页 -> 点右下角"追踪"角标 -> 关闭详情页
            (旧版"点邀请按钮附近打开单任务追踪界面"的交互已随 2026-10 悬赏改版消失)
        @param card_index: 协作卡片序号 1..4
        """
        self.screenshot()
        # 点击卡片立绘区域(避开右上角协角标与中部邀请好友按钮)
        x = 220 + (card_index - 1) * 280
        self.device.click(x, 250, control_name=f'wq_coop_card_{card_index}')
        open_timer = Timer(6).start()
        while 1:
            self.screenshot()
            if self._wq_detail_open():
                break
            if open_timer.reached():
                logger.warning('trace_one: coop quest detail not opened')
                return
        for _ in range(3):
            self.screenshot()
            if not self._wq_detail_open():
                break
            if not self.appear(self.I_WQ_DETAIL_TRACE):
                # 角标消失说明已变为"取消追踪"，追踪成功
                break
            if self.appear_then_click(self.I_WQ_DETAIL_TRACE, interval=1.5):
                continue
            break
        self.close_wq_detail()

    def close_wq_detail(self):
        """
            关闭悬赏详情页：点右上角X直到详情标题行消失
            NOTE 右下角的"取消追踪"绝对不能点，会把任务取消追踪
        """
        timer = Timer(15).start()
        while 1:
            self.screenshot()
            if not self._wq_detail_open():
                break
            if timer.reached():
                logger.warning('WQ detail close timeout')
                break
            self.click(self.C_WQ_DETAIL_CLOSE, interval=1)

    @staticmethod
    def extract_monster_name(text: str) -> str:
        """
            从"悬赏目标：击败10个山童"或协作标题"自己击败山兔"提取怪名
            NOTE OCR偶发错字(实测"涂壁"被读成"涂障")，排除名单匹配不到就算了，与旧竖排OCR同样的局限
        """
        if not text:
            return ''
        match = re.search(r'(?:击败\d+\s*[个只]|自己击败)(.+)$', text)
        return match.group(1).strip() if match else ''

    def execute_mission(self, ocr, num_want: int):
        """

        :param ocr: 要点击的 文字
        :param num_want: 一共要打败的怪物数量
        :return:
        """
        GOTO_BUTTON = [self.I_GOTO_1, self.I_GOTO_2, self.I_GOTO_3, self.I_GOTO_4]
        name_funcs: dict = {
            '式神': self.challenge,
            '探索': self.explore,
            '秘闻': self.secret
        }

        def detect_destination_rows(img) -> list:
            """
                目的地区域一次 detect_and_ocr，按行分组成 [(类型徽章文字, 目的地信息), ...x4]
                NOTE 不能用逐行 Single 窄框：实测首字被裁("秘闻"读成"闻")、数字偶发丢失
                ("数量:4"读成"数量:")导致整条目的地被误丢；整区检测 + 按y归行全部读对
            """
            row_ys = [301, 377, 452, 528]  # 四行文字的y中心(1280x720)
            rows = [[] for _ in range(4)]
            for r in self.O_WQ_DEST.detect_and_ocr(img):
                yc = (r.box[0][1] + r.box[2][1]) / 2 + self.O_WQ_DEST.roi[1]
                x0 = r.box[0][0] + self.O_WQ_DEST.roi[0]
                ri = min(range(4), key=lambda k: abs(yc - row_ys[k]))
                rows[ri].append((x0, r.ocr_text))
            out = []
            for items in rows:
                items.sort()
                # x<715 是类型徽章区，x>=715 是目的地信息
                badge = ''.join(t for x, t in items if x < 715)
                info = ''.join(t for x, t in items if x >= 715)
                out.append((badge, info))
            return out

        def extract_info(index: int, rows: list) -> tuple or None:
            """
            提取每一个地点的信息
            :param index: 从零开始
            :param rows: detect_destination_rows 的结果
            :return:
            (type, destination, number, goto_button, func)
            (类型, 地点层级，可以打败的数量，前往按钮, func)
            类型： 挑战0, 秘闻1， 探索2
            """
            # 获取用户设置的值
            user_limit = self.config.model.wanted_quests.wanted_quests_config.layer_limit.value
            # 定义完整的层数后缀顺序
            all_layers = ["壹", "贰", "叁", "肆", "伍", "陆", "柒", "捌", "玖", "拾", "番外"]
            # 根据用户选择进行截取，生成 layer_limit 集合
            if user_limit == "无限制":
                layer_limit = set()
            else:
                start_idx = all_layers.index(user_limit) if user_limit in all_layers else 6
                # 截取该层及之后的所有层
                layer_limit = set(all_layers[start_idx:])

            # ,荒川之怒·壹，4，前往按钮，function
            result = [-1, '', -1, GOTO_BUTTON[index], self.challenge, '']
            type_wq, info_raw = rows[index]
            info_wq_1 = info_raw.replace('：', ':').replace('（', '(').replace('）', ')')
            # OCR偶发丢尾括号/多出尾括号，统一剥掉再匹配(闭合括号改为可选)
            info_wq_1 = re.sub(r'[)）]+$', '', info_wq_1)
            match = re.match(r"^(.*?)[（(]?数量[：:]\s*(\d+)$", info_wq_1)
            if not match:
                return None
            wq_destination = match.group(1)
            wq_number = int(match.group(2))
            # 秘闻层数超限：不直接丢弃，记入兜底候选——当某悬赏全部目的地都超限时
            # execute_mission 会选层数最低的一个执行，保证悬赏总能推进
            over_limit_layer = -1
            if wq_destination[-1] in layer_limit:
                logger.warning('This secret layer is too high')
                over_limit_layer = all_layers.index(wq_destination[-1])
            result[1] = wq_destination
            result[2] = wq_number
            order_list = self.config.model.wanted_quests.wanted_quests_config.battle_priority
            order_list = order_list.replace(' ', '').replace('\n', '')
            order_list: list = re.split(r'>', order_list)
            # OCR识别"式神"但用户配置用"挑战"，做映射
            type_wq_for_order = '挑战' if type_wq == '式神' else type_wq
            result[0] = order_list.index(type_wq_for_order) if type_wq_for_order in order_list else -1
            result[4] = name_funcs.get(type_wq, lambda: logger.warning('No task can be challenged'))
            result[5] = type_wq
            logger.info(f'[Wanted Quests] type: {type_wq} destination: {wq_destination} number: {wq_number} ')
            if result[0] == -1:
                return None
            if over_limit_layer >= 0:
                over_limit_wq_list.append((over_limit_layer, tuple(result)))
                return None
            return tuple(result)

        logger.hr('Start wanted quests')
        # 点击左侧圆圈打开详情，以详情标题行出现为打开标志（普通/协作两种标题都认）
        # (旧版蓝对勾 I_TRACE_TRUE 已随 2026-10 悬赏改版消失；自带20s上限防无限点击)
        open_timer = Timer(20).start()
        while 1:
            self.screenshot()
            if self._wq_detail_open():
                break
            if open_timer.reached():
                logger.warning('WQ detail not opened in 20s, skip this quest')
                return False
            if self.click(ocr, interval=1):
                continue
        # 详情页的'前往'按钮可能比页面晚加载（服务器异步返回目的地列表），
        # 不等待就判定会把正常任务误认为未解锁的神秘任务而跳过（2026-09-25 食梦貘悬赏被跳过的根因）
        if not self.wait_until_appear(self.I_GOTO_1, wait_time=3):
            # 等待后仍没有 '前往'按钮，那这个可能是神秘任务但是没有解锁
            logger.warning('This is a secret mission but not unlock')
            self.close_wq_detail()
            return False
        # 跳过不想打的：从"悬赏目标：击败N个XX"横排提取怪名(旧竖排OCR区域已随改版失效)
        # NOTE detect_text 返回文本；ocr() 在 FULL+keyword 下返回的是命中坐标框，不能用来取文字
        monster_name = self.extract_monster_name(self.O_WQ_TARGET.detect_text(self.device.image))
        if monster_name and monster_name in self.unwanted_boss_name_list:
            #
            logger.warning(f'unwanted {monster_name}')
            self.close_wq_detail()
            return False

        info_wq_list = []
        over_limit_wq_list = []
        dest_rows = detect_destination_rows(self.device.image)
        for i in range(4):
            info_wq = extract_info(i, dest_rows)
            if info_wq:
                info_wq_list.append(info_wq)
        info_wq_list = [item for item in info_wq_list if item not in self.want_strategy_excluding]
        if not info_wq_list and over_limit_wq_list:
            # 全部目的地都因层号超限被过滤：选层数最低的超层秘闻兜底
            logger.warning('All destinations are over layer limit, fallback to the lowest over-limit secret')
            info_wq_list.append(min(over_limit_wq_list, key=lambda x: x[0])[1])
        if not info_wq_list:
            logger.warning('No wanted quests can be challenged')
            self.close_wq_detail()
            return False
        # sort
        info_wq_list.sort(key=lambda x: x[0])
        filtered = list(filter(lambda x: (x[5] == '秘闻' or x[5] == '式神') and x[2] >= 3, info_wq_list))
        if filtered:
            info_wq_list = filtered
        best_type, destination, once_number, goto_button, func, _ = info_wq_list[0]
        do_number = 1 if once_number >= num_want else num_want // once_number + (1 if num_want % once_number > 0 else 0)
        try:
            func(goto_button, do_number)
        except ExploreWantedBoss:
            logger.warning('The extreme case. The quest only needs to challenge one final boss, so skip it')
            self.want_strategy_excluding.append(info_wq_list[0])
            # 详情页还开着，关掉再返回，否则主循环会在详情页上找任务列表
            self.close_wq_detail()

    def challenge(self, goto_btn, num):
        self.ui_click(goto_btn, self.I_WQC_FIRE)
        self.ui_click(self.I_WQC_UNLOCK, self.I_WQC_LOCK)
        self.ui_click_until_disappear(self.I_WQC_FIRE)
        # 进入战斗
        self.run_general_battle(config=self.battle_config)
        self.wait_until_appear(self.I_WQC_FIRE, wait_time=4)
        # 关闭 挑战界面
        while 1:
            self.screenshot()
            if self.appear(self.I_CHECK_EXPLORATION):
                break
            if self.appear_then_click(self.I_UI_BACK_YELLOW, interval=1.5):
                continue

    def secret(self, goto, num=1):
        self.ui_click(goto, self.I_WQSE_FIRE)
        for i in range(num):
            self.wait_until_appear(self.I_WQSE_FIRE)
            # self.ui_click_until_disappear(self.I_WQSE_FIRE)
            # 又臭又长的对话针的是服了这个网易
            click_count = 0
            # 对话点击每次都会重置设备卡死计时（handle_control_check → stuck_record_clear），
            # 若点击无效对话永远关不掉，卡死检测永远不会触发，必须自带总上限
            # （实测合法长对话约 15 秒/12 连点，60 秒为 4 倍余量）
            chat_timer = Timer(60).start()
            while 1:
                self.screenshot()
                if not self.appear(self.I_UI_BACK_RED, threshold=0.7):
                    break
                if chat_timer.reached():
                    logger.error('Secret mission chat not closed in 60s')
                    raise GameStuckError('Secret mission chat not closed in 60s')
                if self.appear_then_click(self.I_WQSE_FIRE, interval=1):
                    continue
                if self.appear(self.I_UI_BACK_RED, threshold=0.7) and not self.appear(self.I_WQSE_FIRE):
                    # click 返回 False 表示被 interval 拦截未实际点击，不计入；
                    # 按真实点击计数，6 次（约 4.8s）清零一次，保证合法长对话
                    # 不撞 GameTooManyClickError（同按钮 15 窗口内 ≥10 次即抛）
                    if self.click(self.C_SECRET_CHAT, interval=0.8):
                        click_count += 1
                    if click_count >= 6:
                        logger.warning('Secret mission chat too long, force to close')
                        click_count = 0
                        self.device.click_record_clear()
                    continue
            success = self.run_general_battle(self.battle_config)
        while 1:
            self.screenshot()
            if self.appear(self.I_CHECK_SECRET_ZONES):
                break
            if self.appear_then_click(self.I_UI_BACK_RED, interval=1):
                continue
            if self.appear_then_click(self.I_UI_BACK_BLUE, interval=1.5):
                continue
        self.goto_page(page_exploration)
        self.wait_until_stable(self.I_CHECK_EXPLORATION)
        logger.info('Secret mission finished')

    def invite_random(self, add_button: RuleImage):
        self.screenshot()
        if not self.appear(add_button):
            return False
        self.ui_click(add_button, self.I_WQ_INVITE_ENSURE, interval=2.5)
        logger.info('enter invite form')
        sleep(1)
        self.click(self.I_WQ_FRIEND_1)
        sleep(0.4)
        self.click(self.I_WQ_FRIEND_2)
        sleep(0.4)
        self.click(self.I_WQ_FRIEND_3)
        sleep(0.4)
        self.click(self.I_WQ_FRIEND_4)
        sleep(0.4)
        self.click(self.I_WQ_FRIEND_5)
        sleep(0.2)
        self.screenshot()
        if not self.appear(self.I_WQ_INVITE_SELECTED):
            logger.warning('No friend selected')
            return False
        self.ui_click_until_disappear(self.I_INVITE_ENSURE)
        sleep(0.5)

    def invite_five(self):
        """
        邀请好友，默认点五个
        :return:
        """

        logger.hr('Invite friends')
        self.invite_random(self.I_WQ_INVITE_1)
        self.invite_random(self.I_WQ_INVITE_2)
        self.invite_random(self.I_WQ_INVITE_3)
        self.invite_random(self.I_WQ_INVITE_4)

    def all_cooperation_invite(self, name_all: str = None):
        """
            所有的协作任务依次邀请
            如果配置了只完成协作任务 还会将该任务设置为追踪
        @return:

        """
        self.screenshot()
        ret = self.get_cooperation_info()
        if len(ret) == 0:
            logger.info("no Cooperation found")
            return False
        typeMask = 15
        typeMask = CooperationSelectMask[(self.get_config()).cooperation_type.value]
        for item in ret:
            # 该任务是需要邀请的任务类型
            if not (item['type'] & typeMask):
                # BUG 存在多个协作任务时,邀请完第一个协作任务对方接受后,未邀请的任务位置无法确定(缺少信息)
                # 例如 按顺序存在 abc 3个协作任务,邀请完a,好友接受后,这三个任务在界面上的顺序变化,abc 还是bca
                # 如果顺序不变 则应该没有问题
                logger.info("cooperationType %s But needed Type %s ,Skipped", item['type'], typeMask)
                break
            '''
               尝试5次 如果邀请失败 等待20s 重新尝试
               阴阳师BUG: 好友明明在线 但邀请界面找不到该好友(好友未接受任何协作任务的情况下)
           '''
            index = 0
            item['inviteResult'] = False
            if name_all is None:
                name = self.get_invite_vip_name(item['type'])
            else:
                name = name_all
            logger.warning("find cooperationType %s ,start invite %s", item['type'], name)
            while index < 5:
                if self.cooperation_invite(item['inviteBtn'], name):
                    item['inviteResult'] = True
                    index = 5
                    continue
                logger.info("%s not found,Wait 20s,%d invitations left", name, 5 - index - 1)
                index += 1
                sleep(20) if index < 5 else sleep(0)
                # NOTE 等待过程如果出现协作邀请 将会卡住 为了防止卡住
                self.screenshot()
            # 邀请追踪一起吧,只有邀请成功才追踪
            if item['inviteResult']:
                self.invite_success_callback(item['type'], name)
                if (self.get_config()).cooperation_only:
                    logger.info("start trace_one")
                    self.trace_one(item['card'])
        return ret

    def cooperation_invite(self, btn: RuleImage, name: str):
        """
            单个协作任务邀请
        @param btn:
        @param name:
        @return:
        """
        self.ui_click(btn, stop=self.I_WQ_INVITE_ENSURE, interval=2.5)

        # 选人
        self.O_WQ_INVITE_COLUMN_1.keyword = name
        self.O_WQ_INVITE_COLUMN_2.keyword = name

        find = False
        for i in range(2):
            self.wait_until_appear(self.I_WQ_INVITE_FRIEND_LIST_APPEAR, wait_time=4)
            self.screenshot()
            in_col_1 = self.ocr_appear_click(self.O_WQ_INVITE_COLUMN_1)
            in_col_2 = self.ocr_appear_click(self.O_WQ_INVITE_COLUMN_2)
            find = in_col_2 or in_col_1
            if find:
                self.wait_until_appear(self.I_WQ_INVITE_SELECTED, wait_time=2)
                self.screenshot()
                if self.appear(self.I_WQ_INVITE_SELECTED):
                    logger.info("friend found and selected")
                    break
                # TODO OCR识别到文字 但是没有选中 尝试重新选择  (选择好友时,弹出协作邀请导致选择好友失败)
            # 检测跨服好友按钮是否高亮
            while 1:
                self.screenshot()
                if not self.appear_highlight(self.I_WQ_INVITE_DIFF_SVR_HIGHLIGHT):
                    self.click(self.I_WQ_INVITE_DIFF_SVR)
                    continue
                break
            # 等待好友列表加载
            self.wait_until_appear(self.I_WQ_INVITE_DIFF_SVR_HIGHLIGHT, wait_time=4)
        # 没有找到需要邀请的人,点击取消 返回悬赏封印界面
        if not find:
            self.screenshot()
            self.ui_click_until_disappear(self.I_WQ_INVITE_CANCEL, interval=1.5)
            return False
        #
        self.ui_click_until_disappear(self.I_WQ_INVITE_ENSURE, interval=1)
        return True

    def get_cooperation_info(self) -> List:
        """
            获取协作任务详情（2026-10 改版：协作任务是带"协"角标的卡片，
            卡内有"邀请好友"按钮；金币协作卡上没有专属图标，由无其他类型图标推定）
        @return: 协作任务类型与邀请按钮、卡片序号
        """
        self.screenshot()
        retList = []
        for index in range(4):
            btn = self.__getattribute__("I_WQ_INVITE_" + str(index + 1))
            if not self.appear(btn):
                continue
            # NOTE 因为食物协作里面也有金币奖励,所以判断金币协作放在最后面:
            #      卡上找不到勾玉/食粮/体力图标时按金币协作处理
            for tname, ctype in [("JADE", CooperationType.Jade),
                                 ("DOG_FOOD", CooperationType.Food),
                                 ("CAT_FOOD", CooperationType.Food),
                                 ("SUSHI", CooperationType.Sushi)]:
                if self.appear(self.__getattribute__("I_WQ_COOPERATION_TYPE_" + tname + "_" + str(index + 1))):
                    retList.append({'type': ctype, 'inviteBtn': btn, 'card': index + 1})
                    break
            else:
                retList.append({'type': CooperationType.Gold, 'inviteBtn': btn, 'card': index + 1})
        logger.info(f"get cooperation size {len(retList)}")
        return retList

    # 使用平均亮度检测是否一致
    def appear_highlight(self, rule_image: RuleImage):
        def compute_region_brightness(img, top_left, width, height):
            """
            计算目标区域的平均亮度 (灰度图的平均值)
            :param img: 目标图像
            :param top_left: 匹配区域的左上角坐标
            :param width: 模板宽度
            :param height: 模板高度
            :return: 区域亮度均值
            """
            # 裁剪出匹配区域
            region = img[top_left[1]:top_left[1] + height, top_left[0]:top_left[0] + width]
            # 转为灰度图
            gray_region = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
            # 计算灰度均值
            return gray_region.mean()

        src = rule_image.corp(self.device.image)
        template = rule_image.image
        result = cv2.matchTemplate(src, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)

        brightness_src = compute_region_brightness(src, max_loc, template.shape[1], template.shape[0])
        brightness_template = compute_region_brightness(template, (0, 0), template.shape[1], template.shape[0])

        if max_val > rule_image.threshold and (brightness_src >= brightness_template * rule_image.threshold) and (
                brightness_src <= brightness_template * (2 - rule_image.threshold)):
            rule_image.roi_front[0] = max_loc[0] + rule_image.roi_back[0]
            rule_image.roi_front[1] = max_loc[1] + rule_image.roi_back[1]
            return True
        return False

    @cached_property
    def special_main(self) -> bool:
        # 特殊的庭院需要点一下，左边然后才能找到图标
        main_type = self.config.global_game.costume_config.costume_main_type
        if main_type == MainType.COSTUME_MAIN_3:
            return True
        return False

    def get_config(self):
        return self.config.wanted_quests.wanted_quests_config

    def need_invite_vip(self):
        return bool(self.get_config().invite_friend_name)

    def get_invite_vip_name(self, ctype: CooperationType):
        return self.get_config().invite_friend_name

    def invite_success_callback(self, ctype: CooperationType, name):
        """
           邀请成功回调
        @param ctype:
        @type ctype:
        @param name:
        @type name:
        """

        return True

    def process_ocr(self, txt):
        def detect_spliter(txt):
            index = txt.find('/')
            if index != -1:
                return index
            # 由于斜杠'/'经常被误识别为'7',且悬赏封印悬赏怪物总数没有与‘7’相关的数字
            reg = re.compile(r'^(\d+)([7/])(\d+)$')
            match = reg.match(txt)
            if match:
                return match.start(2)
            return -1

        index = detect_spliter(txt)
        if index < 0:
            return 0, 0, 0
        return int(txt[:index]), 1, int(txt[index + 1:])

    def txt_ocr_appear(self, ocr_item: RuleOcr, reg, img):
        res = ocr_item.ocr(img)
        regex = re.compile(reg)
        ismatch = regex.match(res)
        return ismatch is not None

    def find_wq(self, img):
        def calc_xywh(box):
            rec_x, rec_y, rec_w, rec_h = box[0, 0], box[0, 1], box[1, 0] - box[0, 0], box[2, 1] - box[0, 1]
            x = rec_x + self.O_WQ_TEXT_ALL.roi[0]
            y = rec_y + self.O_WQ_TEXT_ALL.roi[1]
            w = rec_w
            h = rec_h
            return [x, y, w, h]

        res_list = self.O_WQ_TEXT_ALL.detect_and_ocr(img)
        import re
        reg_time = re.compile(r'^([01]?[0-9]|2[0-3]):([0-5]?[0-9]):?([0-5]?[0-9])?$')
        reg_fengyin = re.compile(r'.*[封|野]印.*')
        # 由于斜杠'/'经常被误识别为'7',且悬赏封印悬赏怪物总数没有与‘7’相关的数字
        reg_progress = re.compile(r'^(\d+)([7/])(\d+)$')
        # 没有检测到斜杠，符合格式：前N位与后N位相同,表示已完成
        reg_XX = re.compile(r'^(\d+)\1$')
        # 过滤掉协或者未知悬赏等其他无用字符
        reg_other = re.compile(r'[?？协边]')
        completed_only = False
        for index, res in enumerate(res_list):
            if reg_fengyin.match(res.ocr_text):
                continue
            if reg_time.match(res.ocr_text):
                continue
            if reg_other.search(res.ocr_text):
                continue
            if (match := reg_progress.match(res.ocr_text)):
                spliter_index = match.start(2)
                xywh = calc_xywh(res.box)
                self.O_WQ_TEXT_ALL.area = xywh
                cu, re, total = int(res.ocr_text[:spliter_index]), 1, int(res.ocr_text[spliter_index + 1:])
                logger.info(f'Matched: {res.ocr_text}')
                # 识别结果规范性检查
                if total > 14:
                    logger.warning("Total number of wanted quests is greater than 14")
                    total = total % 10
                if cu > total:
                    logger.warning('Current number of wanted quests is greater than total number')
                    cu = cu // 10
                if cu == total:
                    # 该任务已完成，一般是悬赏任务，邀请人没有做导致的
                    completed_only = True
                    continue
                return cu, re, total, xywh
            # 例如：1414 66 1212
            if reg_XX.match(res.ocr_text):
                continue
            # 什么都没匹配上，判断上一个识别结果如果为悬赏封印，那么认为该识别结果错误，尝试执行一次
            last_index = (index - 1) if index > 0 else 0
            if reg_fengyin.match(res_list[last_index].ocr_text):
                return 0, 1, 3, calc_xywh(res_list[last_index].box)

        if completed_only:
            return -2, -2, -2, [0, 0, 0, 0]
        return -1, -1, -1, [0, 0, 0, 0]

    def is_wq_remained(self):
        # 检测是否还存在任务
        return self.appear(self.O_WQ_WANTED)



if __name__ == '__main__':
    from module.config.config import Config
    from module.device.device import Device
    import re

    c = Config('oas1')
    d = Device(c)
    t = ScriptTask(c, d)
    # import cv2
    #
    # img = cv2.imread(r'E:\2.png')
    # img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    #
    # res = t.find_wq(img)

    t.run()
