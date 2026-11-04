# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
from datetime import timedelta, datetime

import random

from module.base.timer import Timer
from module.server.i18n import I18n
from tasks.BondlingFairyland.config import BondlingMode
from tasks.Component.GeneralBattle.general_battle import GeneralBattle
from tasks.BondlingFairyland.assets import BondlingFairylandAssets
from tasks.BondlingFairyland.config_battle import BattleConfig

from module.logger import logger




class BondlingBattle(GeneralBattle, BondlingFairylandAssets):

    def run_battle(self, battle_config: BattleConfig, limit_count: int = None) -> bool:
        """
        :return: 如果结契成功返回True，否则返回False
        """
        logger.hr("General battle start", 2)
        self.current_count += 1
        logger.info(f'Current tasks: {I18n.trans_zh_cn(self.config.task.command)}')
        logger.info(f'Current count: {self.current_count} / {limit_count}')

        task_run_time = datetime.now() - self.start_time
        # 格式化时间，只保留整数部分的秒
        task_run_time_seconds = timedelta(seconds=int(task_run_time.total_seconds()))
        logger.info(f'Current times: {task_run_time_seconds} / {self.limit_time}')

        if self.check_load():
            # 首先要判断进入战斗的界面
            self.green_mark(battle_config.green_enable, battle_config.green_mark)

        # 进入战斗过程
        return self.catch_battle_wait(battle_config.random_click_swipt_enable)


    def check_load(self) -> bool:
        """
        检查战斗时候的加载动画
        如何是还在加载种，有那个要准备的按钮，就返回True
        如果已经进入战斗了，就返回False
        :return:
        """
        while 1:
            self.screenshot()
            if self.appear(self.I_BUFF):
                return True
            if self.appear(self.I_EXIT):
                return False

    def catch_battle_wait(self, random_click_swipt_enable: bool) -> bool:
        """
        重写一个 战斗等待
        :return: 如果捕获成功返回True，否则返回False
        """
        self.device.stuck_record_add('BATTLE_STATUS_S')
        self.device.click_record_clear()
        # 有时候 只会点击 获得奖励和开始战斗
        # 战斗过程 随机点击和滑动 防封
        logger.info("Start battle process")
        win: bool = False
        bondling_mode = self.config.bondling_fairyland.bondling_config.bondling_mode
        cap_again = bondling_mode in [BondlingMode.MODE3, BondlingMode.MODE4]
        cap_cnt, max_cap = 0, 10
        catch_ui_timer = None  # 结契页(挑战按钮)连续可见计时
        while 1:
            # 捕获次数超过最大次数限制, 则不再进行捕获
            if cap_cnt >= max_cap:
                cap_again = False
            self.screenshot()
            # 如果捕获成功
            if self.appear_then_click(self.I_CAP_SUCCESS, action=self.C_CAP_SUCCESS,  interval=1):
                win = True
                catch_ui_timer = None
            # 连续结契捕获失败
            if self.appear_then_click(self.I_CAP_FAILURE, action=self.C_CAP_SUCCESS, interval=1):
                win = False
                catch_ui_timer = None
            # 非连续结契且单次抓捕失败
            if not cap_again and self.appear_then_click(self.I_BATTLE_FAIL_ABANDON, interval=1):
                win = False
                catch_ui_timer = None
            # 连续结契则继续结契
            if cap_again and self.appear_then_click(self.I_CAP_AGAIN, interval=1):
                self.device.click_record_clear()  # 需要10次结契因此清空点击记录
                cap_cnt += 1
                catch_ui_timer = None
                continue
            # 如果领奖励
            if self.appear(self.I_REWARD, threshold=0.6):
                break
            if self.appear_then_click(self.I_WIN, threshold=0.6):
                catch_ui_timer = None
                continue
            if self.appear_then_click(self.I_BATTLE_SUCCESS, threshold=0.6, interval=1):
                catch_ui_timer = None
                continue
            if self.appear_then_click(self.I_BATTLE_FAIL, threshold=0.6, interval=1):
                catch_ui_timer = None
                continue
            # 普通胜利有时点掉胜利横幅后直接回到结契界面, 没有任何弹窗(获得奖励/结契成功/失败),
            # 本循环原本只认 I_REWARD, 会困在这里随机点击空转直到 GameTooManyClickError。
            # 出口: 没有任何结算弹窗且挑战按钮连续可见 2 秒, 视为战斗已结束
            if self.appear(self.I_BALL_FIRE):
                if catch_ui_timer is None:
                    catch_ui_timer = Timer(2).start()
                    continue
                if catch_ui_timer.reached():
                    logger.info('Back to catch ui without reward popup, battle is over')
                    break
            else:
                catch_ui_timer = None
            # 如果开启战斗过程随机滑动
            if random_click_swipt_enable:
                self.random_click_swipt()

        # 确定获得奖励 无论是胜利还是失败
        if win:
            logger.info("Catch success")
        else:
            logger.info("Catch failure")
        while 1:
            self.screenshot()
            # 如果出现领奖励
            action_click = random.choice([self.C_REWARD_1, self.C_REWARD_2, self.C_REWARD_3])
            if self.appear_then_click(self.I_REWARD, action=action_click, interval=1.5):
                continue
            if self.appear_then_click(self.I_WIN, threshold=0.6):
                continue
            if self.appear_then_click(self.I_BATTLE_SUCCESS, threshold=0.6, interval=1):
                continue
            if self.appear_then_click(self.I_BATTLE_FAIL_ABANDON, interval=1):
                continue
            if self.appear_then_click(self.I_BATTLE_FAIL, threshold=0.6, interval=1):
                continue
            if not self.appear(self.I_REWARD):
                break
        logger.info("Get reward")
        return win
