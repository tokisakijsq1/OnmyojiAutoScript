from pydantic import BaseModel, Field

from tasks.Component.config_scheduler import Scheduler
from tasks.Component.config_base import ConfigBase
from tasks.Component.GeneralBattle.config_general_battle import GeneralBattleConfig


class MainStoryConfig(BaseModel):
    # 剧情界面连续多少秒没有任何可识别按钮后, 点左上角返回退出当前剧情(退路)
    ms_idle_timeout: float = Field(default=15, description='ms_idle_timeout_help', ge=5, le=60)
    # 单次运行中点返回退出剧情的次数上限, 达到即结束任务
    ms_escape_limit: int = Field(default=3, description='ms_escape_limit_help', ge=1, le=10)
    # 单次运行最多进入多少段剧情
    ms_max_count: int = Field(default=30, description='ms_max_count_help', ge=1, le=200)


class MainStory(ConfigBase):
    scheduler: Scheduler = Field(default_factory=Scheduler)
    general_battle: GeneralBattleConfig = Field(default_factory=GeneralBattleConfig)
    main_story_config: MainStoryConfig = Field(default_factory=MainStoryConfig)
