from pydantic import BaseModel, Field

from tasks.Component.config_scheduler import Scheduler
from tasks.Component.config_base import ConfigBase
from tasks.Component.SwitchSoul.switch_soul_config import SwitchSoulConfig
from tasks.Component.GeneralBattle.config_general_battle import GeneralBattleConfig


class MetaDemonAssistConfig(BaseModel):
    # 庭院守候轮询间隔(秒)
    mda_monitor_interval: float = Field(default=1.0, description='mda_monitor_interval_help', ge=0.5, le=5)
    # 单次运行庭院守候时长上限(分钟)
    mda_max_duration: int = Field(default=120, description='mda_max_duration_help', ge=10, le=1440)
    # 自然结束(守候时长到点)后下次运行间隔(分钟)
    mda_rerun_gap: int = Field(default=10, description='mda_rerun_gap_help', ge=1, le=720)
    # 勾选2.5倍伤害的最低鬼王星级(5/6星勾选, 1-4星不勾)
    mda_buff_min_star: int = Field(default=5, description='mda_buff_min_star_help', ge=2, le=6)
    # 疲劳判定上限: 顶栏疲劳读数达到此值视为疲劳满不能打, 收工等恢复后再跑(满值100)
    mda_fatigue_max: int = Field(default=100, description='mda_fatigue_max_help', ge=1, le=200)


class MetaDemonAssist(ConfigBase):
    scheduler: Scheduler = Field(default_factory=Scheduler)
    switch_soul_config: SwitchSoulConfig = Field(default_factory=SwitchSoulConfig)
    general_battle: GeneralBattleConfig = Field(default_factory=GeneralBattleConfig)
    meta_demon_assist_config: MetaDemonAssistConfig = Field(default_factory=MetaDemonAssistConfig)
