from pydantic import BaseModel, Field

from tasks.Component.config_scheduler import Scheduler
from tasks.Component.config_base import ConfigBase


class MetaDemonProviderConfig(BaseModel):
    # 集结邀请的指定好友名(=开超鬼王协助的账号在游戏内的好友名, 须与游戏显示一致)
    provider_friend_name: str = Field(default='', description='provider_friend_name_help')
    # 指定召唤的鬼王星级(0=默认队列不指定; 4/5/6=召唤队列弹窗中点击对应星级裂变之眼后立即召唤)
    mdp_target_star: int = Field(default=0, description='mdp_target_star_help', ge=0, le=6)
    # 等待好友击杀的超时(分钟), 超时重新集结邀请一次, 第二次仍超时收工
    mdp_kill_timeout: int = Field(default=10, description='mdp_kill_timeout_help', ge=1, le=60)
    # 单次运行时长兜底(分钟)
    mdp_max_duration: int = Field(default=120, description='mdp_max_duration_help', ge=10, le=1440)


class MetaDemonProvider(ConfigBase):
    scheduler: Scheduler = Field(default_factory=Scheduler)
    meta_demon_provider_config: MetaDemonProviderConfig = Field(default_factory=MetaDemonProviderConfig)
