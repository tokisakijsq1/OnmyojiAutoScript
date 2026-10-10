# This Python file uses the following encoding: utf-8
# 当期爬塔(磐长故地)专用的战斗结算扩展。
# 只挂在本任务 ScriptTask 上, 通过 MRO 覆盖共享 Battle 的 _bw_success_activity,
# 不改动 tasks/Component/GeneralBattle 共享文件; 下次活动改版时本文件随素材一起更新/废弃。
from cached_property import cached_property

from module.base.timer import Timer
from module.logger import logger
from module.atom.click import RuleClickExclude

from tasks.Component.GeneralBattle.battle import Battle
from tasks.Component.GeneralBattle.battle_wait import BattleResult, HookSignal, runtime


class ActivityBattle:

    @cached_property
    def _grid_templates(self) -> list:
        return [self.I_GRID_ANCHOR_1, self.I_GRID_ANCHOR_2, self.I_GRID_ANCHOR_3]

    def reward_grid_appear(self) -> bool:
        """活动大奖励网格结算页: 三模板命中任一"""
        return any(self.appear(t) for t in self._grid_templates)

    @cached_property
    def _exclude_click_grid(self) -> RuleClickExclude:
        """随机点击兜底: 排除奖励网格禁区(蓝框区域)"""
        return RuleClickExclude([self.C_GRID_REWARD_AREA], name='exclude_click_grid',
                                strategy='rejection', distribution='uniform')

    def _bw_success_activity(self, pub, pri) -> HookSignal:
        """
        活动结算: 在共享 activity 结算之上兼容大奖励网格页(无"获得奖励"标题)。
        - 网格页与奖励浮窗都不在 -> 直接走共享逻辑
        - 三模板命中网格页 -> 点底部"点击屏幕继续"安全位翻页
        - 模板全失配但6s内见过网格页 -> 随机点击兜底(排除奖励网格禁区)
        - 误点奖励的详情弹窗 -> 点左侧空白关闭
        """
        if not (self.appear(self.I_UI_REWARD) or self.reward_grid_appear()):
            return Battle._bw_success_activity(self, pub, pri)
        self.screenshot()
        if not (self.appear(self.I_UI_REWARD) or self.reward_grid_appear()):
            return Battle._bw_success_activity(self, pub, pri)

        logger.info('Win battle (activity reward)')
        timer = Timer(20).start()
        grid_seen_timer = None  # 网格页最近一次被识别的时间源, 兜底随机点击只在6s内生效
        while 1:
            self.screenshot()

            # 胜利结算界面(若出现)先点掉
            if self.appear_then_click(self.I_WIN, interval=1):
                continue

            # 不小心点到了具体的奖励, 会弹出物品详情(内含"获取途径"), 点左侧空白关闭
            if self.appear(self.I_END_FIX_1) or self.appear(self.I_END_FIX_2) or self.appear(self.I_END_FIX_3):
                self.screenshot()
                if self.appear(self.I_END_FIX_1) or self.appear(self.I_END_FIX_2) or self.appear(self.I_END_FIX_3):
                    self.click(self.C_REWARD_2, interval=2.5)
                continue

            if self.reward_grid_appear():
                grid_seen_timer = Timer(6).start()
                self.click(self.C_GRID_CONTINUE, interval=2)
                continue

            if self.appear(self.I_UI_REWARD):
                # 奖励浮窗(小窗): 随机点击, 复用更大的网格禁区更安全
                grid_seen_timer = grid_seen_timer or Timer(6).start()
                if random.random() < 0.02:
                    x, y = self._exclude_click_grid.coord()
                    self.device.click(x=x, y=y, control_name='reward_grid_click')
                    continue
                self.click(self._exclude_click_grid, interval=2.5)
                continue

            if grid_seen_timer is not None and not grid_seen_timer.reached():
                # 模板全失配但网格页刚出现过: 随机点击兜底, 排除奖励网格禁区
                self.click(self._exclude_click_grid, interval=2.5)
                continue

            if not self.appear(self.I_END_FIX_2):
                self.screenshot()
                if any([self.appear(self.I_UI_REWARD), self.appear(self.I_END_FIX_1),
                        self.appear(self.I_END_FIX_2), self.appear(self.I_END_FIX_3)]):
                    continue
                if self.reward_grid_appear():
                    continue
                logger.info('Get all reward')
                pub.per_battle.success = BattleResult.SUCCESS
                return runtime.hook_enabled_update(
                    enable=('completion',),
                    disable=('success', 'failure'),
                )

            if timer.reached_and_reset():
                logger.warning('Activity reward handling timeout')
                break
        return HookSignal.CONTINUE
