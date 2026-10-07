# This Python file uses the following encoding: utf-8
# @author Tokisaki
# github https://github.com/runhey
from pydantic import BaseModel, Field

from tasks.Component.config_scheduler import Scheduler
from tasks.Component.config_base import ConfigBase
from tasks.Component.SwitchSoul.switch_soul_config import SwitchSoulConfig
from tasks.Component.GeneralBattle.config_general_battle import GeneralBattleConfig


class XianShiYaoYueConfig(BaseModel):
    # 战斗次数
    battle_count: int = Field(default=40, description='xy_battle_count_help', ge=1, le=99)
    # 购买现世祝福
    buy_blessing: bool = Field(default=True, description='xy_buy_blessing_help')
    # 直接组队挑战(需虚拟定位)
    direct_challenge: bool = Field(default=False, description='xy_direct_challenge_help')


class XianShiYaoYue(ConfigBase):
    scheduler: Scheduler = Field(default_factory=Scheduler)
    switch_soul_config: SwitchSoulConfig = Field(default_factory=SwitchSoulConfig)
    general_battle: GeneralBattleConfig = Field(default_factory=GeneralBattleConfig)
    xian_shi_yao_yue_config: XianShiYaoYueConfig = Field(default_factory=XianShiYaoYueConfig)
