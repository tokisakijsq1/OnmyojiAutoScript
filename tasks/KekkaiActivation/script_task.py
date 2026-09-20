# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import time

import random
import re
from cached_property import cached_property
from datetime import datetime, timedelta
from module.atom.click import RuleClick

from module.base.timer import Timer
from module.atom.image_grid import ImageGrid
from module.atom.image import RuleImage
from module.base.utils import point2str
from module.logger import logger
from module.exception import TaskEnd, GameStuckError

from tasks.KekkaiUtilize.script_task import ScriptTask as KU
from tasks.KekkaiUtilize.utils import CardClass
from tasks.KekkaiActivation.assets import KekkaiActivationAssets
from tasks.KekkaiActivation.utils import parse_rule, parse_card_sort_order
from tasks.KekkaiActivation.config import ActivationConfig
from tasks.Utils.config_enum import ShikigamiClass
from tasks.GameUi.page import page_main, page_guild
from tasks.KekkaiActivation.config import CardType

""" 结界挂卡 """
class ScriptTask(KU, KekkaiActivationAssets):

    def run(self):
        con = self.config.kekkai_activation.activation_config
        self.ui_get_current_page()
        self.ui_goto(page_guild)

        # 在寮的主界面 检查是否有收取体力或者是收取寮资金
        # self.check_guild_ap_or_assets()

        # 进入寮结界
        self.goto_realm()

        if con.exchange_before:
            self.check_max_lv(con.shikigami_class)
        # 收取经验
        self.harvest_card()
        # 开始挂卡
        self.run_activation(con)
        while 1:
            # 关闭到结界界面
            self.screenshot()
            if self.appear(self.I_REALM_SHIN):
                break
            if self.appear(self.I_SHI_GROWN):
                break
            if self.appear_then_click(self.I_UI_BACK_RED, interval=1):
                continue

        if con.exchange_max:
            self.check_max_lv(con.shikigami_class)
        # self.back_guild()
        self.ui_get_current_page()
        self.ui_goto(page_main)

        raise TaskEnd('KekkaiActivation')

    @cached_property
    def dict_card_image(self) -> dict:
        match_targets = {
            CardClass.TAIKO6: self.I_CARDS_KAIKO_6,
            CardClass.TAIKO5: self.I_CARDS_KAIKO_5,
            CardClass.TAIKO4: self.I_CARDS_KAIKO_4,
            CardClass.TAIKO3: self.I_CARDS_KAIKO_3,
            CardClass.FISH6: self.I_CARDS_FISH_6,
            CardClass.FISH5: self.I_CARDS_FISH_5,
            CardClass.FISH4: self.I_CARDS_FISH_4,
            CardClass.FISH3: self.I_CARDS_FISH_3,
            CardClass.MOON6: self.I_CARDS_MOON_6,
            CardClass.MOON5: self.I_CARDS_MOON_5,
            CardClass.MOON4: self.I_CARDS_MOON_4,
            CardClass.MOON3: self.I_CARDS_MOON_3,
            CardClass.MOON2: self.I_CARDS_MOON_2,
            CardClass.MOON1: self.I_CARDS_MOON_1
        }
        return match_targets

    @cached_property
    def dict_image_card(self) -> dict:
        return {v: k for k, v in self.dict_card_image.items()}

    @cached_property
    def order_targets(self) -> ImageGrid:
        rule = self.config.kekkai_activation.activation_config.card_type
        if rule == CardType.TAIKO:
            return ImageGrid([self.I_CARDS_KAIKO_6, self.I_CARDS_KAIKO_5])
        elif rule == CardType.FISH:
            return ImageGrid([self.I_CARDS_FISH_6, self.I_CARDS_FISH_5])
        else:
            logger.error('Unknown utilize rule')
            raise ValueError('Unknown utilize rule')

    def run_activation(self, _config: ActivationConfig) -> bool:
        """
        执行挂卡，要求在结界的界面
        顺便把下一次执行也设置了
        :return: 挂卡成功（）返回True，失败(时间没到提前来了)返回False
        退出的时候还是在挂卡界面而不是结界界面
        """
        self.goto_cards()
        # 太诡异了 为什么有这么长的动画, 那么长的动画先休息一会
        logger.hr('Start activation')
        time.sleep(0.5)
        while 1:
            self.screenshot()
            card_status = self.check_card_status()
            card_effect = self.check_card_effect()

            # 不稳定太，等待动画结束
            if not card_status and not card_effect:
                # 黄色的 ”激活“
                if self.appear(self.I_A_ACTIVATE_YELLOW, threshold=0.95):
                    continue
                if self.appear(self.I_A_DEMOUNT):
                    # 现在在动画里面
                    logger.info('Now in the animation')
                    logger.info('Now there is no card')
                    continue
            # 如果这张卡生效着，在使用中
            if card_status and card_effect:
                logger.info('Card is using')
                interval = self.ocr_time()
                self.set_next_run("KekkaiActivation", target=interval+datetime.now())
                return False
            # 如果已经选中这张卡了， 那就激活这张卡
            if card_status and not card_effect:
                logger.info('Card is selected but not using')
                while 1:
                    self.screenshot()
                    if self.appear(self.I_A_INVITE, threshold=0.8):
                        logger.info('Card is activated')
                        break
                    if self.appear_then_click(self.I_UI_CONFIRM, interval=0.6):
                        continue
                    if self.appear_then_click(self.I_A_ACTIVATE_YELLOW, interval=1):
                        continue
                interval = self.ocr_time(True)
                self.set_next_run("KekkaiActivation", target=interval + datetime.now())
                return True
            # 如果是什么都没有，那就是可以开始挂卡了
            if not card_status and not card_effect:
                logger.info('Card is not selected also not using')
                self.screening_card(_config.card_type)

    def goto_cards(self):
        """
        寮结界,前往挂卡界面
        :return:
        """
        while 1:
            self.screenshot()

            if self.appear(self.I_A_CHECK_CARD):
                break
            if self.appear(self.I_A_AUTO_INVITE):
                break
            if self.appear_then_click_multi_scale(self.I_SHI_CARD, interval=1):
                continue
        logger.info('Enter card page')

    def check_card_status(self, screenshot=False) -> bool:
        """
        判断使用有挂卡在上面了， 判断依据就是如果没看就可以显示背景图
        :param screenshot:
        :return: 如果有卡在上面了返回True，否则返回False
        """
        if screenshot:
            self.screenshot()
        return not self.appear(self.I_A_EMPTY)

    def check_card_effect(self, screenshot=False) -> bool:
        """
        检查这张卡是否生效了, 如果是出现的“邀请”那就是生效了， 如果是“激活”那就是还没生效
        :param screenshot:
        :return: 生效返回True
        """
        if screenshot:
            self.screenshot()
        if self.appear(self.I_A_INVITE, threshold=0.8):
            return True
        elif self.appear(self.I_A_ACTIVATE_YELLOW):
            return False
        logger.info('Unknown card effect')
        while 1:
            self.screenshot()
            if self.appear(self.I_A_INVITE, threshold=0.7):
                return True
            elif self.appear(self.I_A_ACTIVATE_YELLOW):
                return False
            elif self.appear(self.I_A_ACTIVATE_GRAY):
                return False

    def ocr_time(self, screenshot=False) -> timedelta or None:
        if screenshot:
            self.screenshot()
        delta = self.O_CARD_ALL_TIME.ocr_duration(self.device.image)
        if not isinstance(delta, timedelta):
            logger.warning('OCR error')
            return None
        if delta == timedelta(0):
            logger.error('The remaining time detected for this card is 0')
            logger.error('This may be due to the fact that the card has not yet been collected')
            raise GameStuckError
        return delta

    def screening_card(self, rule: str):
        """
        开始挑选卡
        :return:
        """

        if rule == CardType.TAIKO:
            card_class = CardClass.TAIKO
            target_class = self.I_A_CARD_KAIKO
        elif rule == CardType.FISH:
            card_class = CardClass.FISH
            target_class = self.I_A_CARD_FISH
        else:
            logger.warning('Unknown card rule')
            self.push_notify(content='Unknown card rule')
            return

        # 星级优先排序模式: 遍历卡列表找排序中最高优先级的卡
        # 找不到排序中的任何卡: 严格模式(开启不回退)则推送提醒人工挂卡后结束;
        # 否则回退默认挂卡模式(按每小时收益选最大)
        activation_config = self.config.kekkai_activation.activation_config
        order_str = activation_config.card_sort_order
        if order_str and order_str.strip():
            order = parse_card_sort_order(order_str)
            if order:
                target = self._select_card_by_order(order)
                if target is not None:
                    self._confirm_card(target, rule)
                    return
                if activation_config.card_sort_no_fallback:
                    self._card_sort_not_found()
                    return
                logger.info('No card matched the sort order, fallback to default activation')
            else:
                logger.warning('Card sort order can not be parsed, fallback to default activation')

        self._select_card_class(target_class)

        # 找最优卡
        while 1:
            self.screenshot()
            target = self.check_card_num()
            if target is None:
                # 未发现卡，处理逻辑
                self._card_not_found()
            self._confirm_card(target, rule)

    def _select_card_class(self, target_class: RuleImage):
        """
        在挂卡界面点击“切换卡的种类”下拉并选中目标卡类型
        :param target_class: 卡类型下拉项 RuleImage (I_A_CARD_KAIKO / I_A_CARD_FISH)
        :return:
        """
        while 1:
            self.screenshot()

            if self.appear(target_class):
                time.sleep(0.3)
                self.screenshot()
                if self.appear(target_class):
                    break
            if self.click(self.C_A_SELECT_CARD_LIST, interval=2.5):
                continue
        while 1:
            self.screenshot()
            if not self.appear(target_class):
                break
            if self.appear_then_click(target_class, interval=1):
                continue

    def _confirm_card(self, target: RuleClick, rule: str):
        """
        点击选中的卡并等待挂卡生效
        :param target: 目标卡的点击区域
        :param rule: 卡类型文案，用于成功推送
        :return:
        """
        while 1:
            self.screenshot()
            if self.appear(self.I_A_EMPTY):
                while 1:
                    self.screenshot()
                    if not self.appear(self.I_A_EMPTY):
                        self.config.kekkai_activation.activation_config.card_not_found_count = 0
                        self.config.save()
                        message = f'✅ 确认挂卡: {rule}'
                        self.save_image(content=message, push_flag=False, wait_time=0)
                        return
                    if self.click(target, interval=1):
                        continue

    def check_card_num(self):
        rule = self.config.kekkai_activation.activation_config.card_type
        if rule == CardType.TAIKO:
            min_card_num = self.config.kekkai_activation.activation_config.min_taiko_num
            check_card = "勾玉"
        elif rule == CardType.FISH:
            min_card_num = self.config.kekkai_activation.activation_config.min_fish_num
            check_card = "体力"
        else:
            logger.error('Unknown utilize rule')
            raise ValueError('Unknown utilize rule')

        ocr_count = 0
        while 1:
            self.screenshot()
            results = self.O_CHECK_CARD_NUMBER.detect_and_ocr(self.device.image)
            ocr_count += 1
            # 第一步：筛选出包含 "体力或者勾玉" 的结果
            filtered_results = [result for result in results if check_card in result.ocr_text]
            logger.info(f"识别到卡: {[result.ocr_text for result in filtered_results]}")

            # 第二步：提取数字并按数字排序
            numeric_results = []
            for result in filtered_results:
                # 使用正则表达式提取所有数字
                numbers = [int(num) for num in re.findall(r'\d+', result.ocr_text)]
                if numbers:  # 如果提取到数字
                    if numbers[0] < min_card_num:
                        continue
                    numeric_results.append((numbers[0], result))  # 按第一个数字排序

            if numeric_results:
                # 按数字大到小排序
                sorted_results = [result for _, result in sorted(numeric_results, key=lambda x: x[0], reverse=True)]
                max_result = sorted_results[0]  # 获取数字最大的结果对象

                box = max_result.box  # 获取边界框坐标
                x_min = self.O_CHECK_CARD_NUMBER.roi[0] + box[0][0]
                y_min = self.O_CHECK_CARD_NUMBER.roi[1] + box[0][1]
                width = box[1][0] - box[0][0]
                height = box[2][1] - box[1][1]
                roi = int(x_min), int(y_min), int(width), int(height)

                target = RuleClick(roi_front=roi, roi_back=roi, name="tmpclick")
                logger.info(f"选择挂卡: [{max_result.ocr_text}] {roi}")

                return target
            else:
                if ocr_count > 3:
                    logger.error('多次未找到符合条件的结果, 退出')
                    return None
                logger.warning("未找到符合条件的结果, 准备往上滑动")
                duration = 2
                safe_pos_x = random.randint(200, 400)
                safe_pos_y = random.randint(580, 600)
                p1 = (safe_pos_x, safe_pos_y)
                p2 = (safe_pos_x, safe_pos_y - 410)
                logger.info('Swipe %s -> %s, %sS ' % (point2str(*p1), point2str(*p2), duration))
                self.device.swipe_adb(p1, p2, duration=duration)
                time.sleep(1)
                continue

    def _swipe_up_card_list(self):
        """
        卡列表向上滑动一屏(向列表底部滚动)
        :return:
        """
        duration = 2
        safe_pos_x = random.randint(200, 400)
        safe_pos_y = random.randint(580, 600)
        p1 = (safe_pos_x, safe_pos_y)
        p2 = (safe_pos_x, safe_pos_y - 410)
        logger.info('Swipe %s -> %s, %sS ' % (point2str(*p1), point2str(*p2), duration))
        self.device.swipe_adb(p1, p2, duration=duration)
        time.sleep(1)

    def _swipe_card_list_to_top(self, swipes: int):
        """
        反向下滑把卡列表回滚到顶部
        :param swipes: 之前累计的上滑次数，多滑一次确保到顶(列表无法越过顶部，多滑无副作用)
        :return:
        """
        logger.info(f'Swipe back to top of card list after {swipes} swipes')
        duration = 2
        for _ in range(swipes + 1):
            safe_pos_x = random.randint(200, 400)
            safe_pos_y = random.randint(180, 200)
            p1 = (safe_pos_x, safe_pos_y)
            p2 = (safe_pos_x, safe_pos_y + 410)
            logger.info('Swipe %s -> %s, %sS ' % (point2str(*p1), point2str(*p2), duration))
            self.device.swipe_adb(p1, p2, duration=duration)
            time.sleep(1)

    def _select_card_by_order(self, order: list[CardClass]) -> RuleClick or None:
        """
        按星级优先级在卡列表中选卡: 优先级列表按连续同类型分组，逐组切换卡类型下拉，
        从顶部往下滑逐屏匹配组内各星级模板，命中组内最高优先级的卡记为候选;
        滑到底或达到滑动上限仍未命中则看下一组，全部组未命中返回 None
        :param order: 优先级从高到低的 CardClass 列表 (仅 TAIKO3~6 / FISH3~6)
        :return: 命中卡的 RuleClick，没有则 None
        """
        # 按连续同类型分组: [FISH4, FISH3, TAIKO5] -> [(FISH, [(0, FISH4), (1, FISH3)]), (TAIKO, [(2, TAIKO5)])]
        groups = []
        for idx, card in enumerate(order):
            card_type = CardType.TAIKO if card.name.startswith('TAIKO') else CardType.FISH
            if groups and groups[-1][0] == card_type:
                groups[-1][1].append((idx, card))
            else:
                groups.append((card_type, [(idx, card)]))

        type_targets = {
            CardType.TAIKO: self.I_A_CARD_KAIKO,
            CardType.FISH: self.I_A_CARD_FISH,
        }
        best_priority = len(order)  # 越小优先级越高
        best_box = None
        swipes = 0  # 当前卡列表自顶部起累计的上滑次数

        for card_type, pairs in groups:
            target_class = type_targets[card_type]
            logger.info(f'Searching card group: {card_type} {[c.name for _, c in pairs]}')
            self._select_card_class(target_class)
            if swipes:
                # 切换类型后列表可能停留在上次滚动的位置，先回滚到顶部
                self._swipe_card_list_to_top(swipes)
                swipes = 0

            found, used = self._search_cards_in_list(pairs)
            swipes = used
            if found is not None:
                priority, box = found
                if priority < best_priority:
                    best_priority = priority
                    best_box = box
                # 已经是全局最高优先级，无需继续找更低优先级的组
                if best_priority == 0:
                    break

        if best_box is not None:
            x, y, w, h = best_box
            roi = int(x), int(y), int(w), int(h)
            target = RuleClick(roi_front=roi, roi_back=roi, name="tmpclick")
            logger.info(f'选择挂卡(按优先级): order={order[best_priority].name} {roi}')
            return target

        # 没有任何排序中的卡: 回滚到顶部，交回默认挂卡模式
        if swipes:
            self._swipe_card_list_to_top(swipes)
        logger.info('No card matched the sort order in the whole list')
        return None

    def _search_cards_in_list(self, pairs: list[tuple]) -> tuple:
        """
        在当前卡类型列表中从顶部向下滑逐屏匹配目标星级模板
        :param pairs: (全局优先级下标, CardClass) 列表，下标越小优先级越高
        :return: ((优先级下标, 匹配框 (x, y, w, h)), 上滑次数)，未找到时第一项为 None
        """
        max_swipes = 20
        targets = [(idx, card, self.dict_card_image[card]) for idx, card in pairs]
        swipe_count = 0
        while 1:
            self.screenshot()
            image = self.device.image
            # 每屏按优先级顺序匹配，命中即返回
            for idx, card, target_image in targets:
                matches = target_image.match_all_any(image)
                if matches:
                    # 取匹配分数最高的一个
                    score, x, y, w, h = max(matches, key=lambda m: m[0])
                    logger.info(f'Found card {card.name} score={score:.3f} at ({x}, {y}, {w}, {h})')
                    return (idx, (x, y, w, h)), swipe_count
            if self.appear(self.I_AA_SWIPE_BLOCK):
                logger.info('Swipe to the end of card list')
                return None, swipe_count
            if swipe_count >= max_swipes:
                logger.warning('Max swipe count reached in card list')
                return None, swipe_count
            self._swipe_up_card_list()
            swipe_count += 1

    def _card_not_found(self):
        # 获取配置引用
        activation_config = self.config.kekkai_activation.activation_config
        # 多少分钟后重试
        retry_minutes = 180
        retry_count = 3
        # 递增未找到卡的计数器
        activation_config.card_not_found_count += 1

        if activation_config.card_not_found_count >= retry_count:
            # 达到重试上限时的处理
            log_msg = f"⚠️{activation_config.card_type}卡未检出（累计{retry_count}次），{retry_minutes}分钟后重试"
            activation_config.card_not_found_count = 0  # 重置计数器并延长下次执行时间
            next_run = datetime.now() + timedelta(minutes=retry_minutes)
        else:
            # # 未达上限切换卡类型
            new_type = (
                CardType.FISH
                if activation_config.card_type == CardType.TAIKO
                else CardType.TAIKO
            )
            log_msg = f"🔄{activation_config.card_type}卡未检出 → 切换{new_type}"
            activation_config.card_type = new_type
            next_run = datetime.now()

        # 统一记录日志和推送
        self.save_image(content=log_msg, push_flag=True)

        # 保存配置并设置下次执行
        self.config.save()
        self.set_next_run("KekkaiActivation", target=next_run)
        raise TaskEnd

    def _card_sort_not_found(self):
        """
        严格排序模式下遍历完整卡列表仍未找到排序中的卡:
        推送通知提醒人工挂卡，不挂卡不回退默认方式，
        按失败间隔(failure_interval, 默认10小时)后自动重试
        :return:
        """
        order_str = self.config.kekkai_activation.activation_config.card_sort_order
        content = f'❌ 结界挂卡失败: 卡列表中没有「{order_str}」中的任何卡, 本次未挂卡, 请人工挂卡' \
                  f'(或调整排序/关闭严格模式), 将按失败间隔自动重试'
        logger.warning(content)
        self.save_image(content=content, push_flag=True)
        # 真实推送: 走全局 Notifier (设置 -> 错误处理 -> 启用通知开关)
        self.config.notifier.push(title='结界挂卡失败', content=content)
        self.set_next_run("KekkaiActivation", target=datetime.now() + self.config.kekkai_activation.scheduler.failure_interval)
        raise TaskEnd

    def check_max_lv(self, shikigami_class: ShikigamiClass = ShikigamiClass.N):
        """
        在结界界面，进入式神育成，检查是否有满级的，如果有就换下一个
        退出的时候还是结界界面
        :return:
        """
        self.realm_goto_grown()
        if self.appear(self.I_RS_LEVEL_MAX):
            # 存在满级的式神
            logger.info('Exist max level shikigami and replace it')
            self.unset_shikigami_max_lv()
            self.switch_shikigami_class(shikigami_class)
            self.set_shikigami(shikigami_order=7, stop_image=self.I_RS_NO_ADD)
        else:
            logger.info('No max level shikigami')
        if self.detect_no_shikigami():
            logger.warning('There are no any shikigami grow room')
            self.switch_shikigami_class(shikigami_class)
            self.set_shikigami(shikigami_order=7, stop_image=self.I_RS_NO_ADD)

        # 回到结界界面
        while 1:
            self.screenshot()

            if self.appear(self.I_REALM_SHIN) and self.appear_multi_scale(self.I_SHI_GROWN):
                self.screenshot()
                if not self.appear(self.I_REALM_SHIN):
                    continue
                break
            if self.appear_then_click(self.I_UI_BACK_BLUE, interval=2.5):
                continue

    def harvest_card(self):
        """
        收卡的经验
        :return:
        """
        cards = [
            self.I_A_HARVEST_EXP,  # 如果到最后没有领的话有下面的一些图片
            self.I_A_HARVEST_FISH4,  # 斗鱼4/5区别不大 斗鱼的如果一直没有领的话
            self.I_A_HARVEST_KAIKO_4,  # 太鼓4
            self.I_A_HARVEST_KAIKO_3,   # 太鼓3
            self.I_A_HARVEST_KAIKO_6,  # 太鼓6
            self.I_A_HARVEST_FISH_6,  # 斗鱼6
            self.I_A_HARVEST_MOON_3,  # 太阴3
            self.I_A_HARVEST_FISH_3,  # 斗鱼三
        ]
        for i in range(5):
            self.screenshot()
            appear = [ self.appear_then_click_multi_scale(card, threshold=0.7) for card in cards ]
            if any(appear):
                break
        logger.info("")
        # self.appear_then_click(self.I_A_HARVEST_EXP)  # 如果到最后没有领的话有下面的一些图片
        # self.appear_then_click(self.I_A_HARVEST_FISH4)  # 斗鱼4/5区别不大 斗鱼的如果一直没有领的话
        # self.appear_then_click(self.I_A_HARVEST_KAIKO_4)  # 太鼓4
        # self.appear_then_click(self.I_A_HARVEST_KAIKO_3)  # 太鼓3
        # self.appear_then_click(self.I_A_HARVEST_KAIKO_6)  # 太鼓6
        # self.appear_then_click(self.I_A_HARVEST_FISH_6)  # 斗鱼6
        # self.appear_then_click(self.I_A_HARVEST_MOON_3)  # 太阴3
        # self.appear_then_click(self.I_A_HARVEST_FISH_3)  # 斗鱼三


if __name__ == "__main__":
    from module.config.config import Config
    from module.device.device import Device
    import cv2

    c = Config('oas1')
    d = Device(c)

    t = ScriptTask(c, d)
    t.run()
    # t.run_activation(t.config.kekkai_activation.activation_config)