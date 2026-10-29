# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey
import time

import cv2
import numpy as np

from module.base.timer import Timer
from tasks.Component.GeneralBuff.assets import GeneralBuffAssets
from module.atom.ocr import RuleOcr
from module.atom.image import RuleImage
from tasks.base_task import BaseTask
from module.logger import logger


# 2026-10-29 加成界面改版: 每行开关变为行尾圆形巴纹按钮(开启=发光且旋转, 关闭=暗色静止),
# 按钮列固定在 x≈852-892, 与描述文字之间隔着剩余时间进度条, 不能再按"文字右缘+10"定位开关
SWITCH_AREA_X = 848
SWITCH_AREA_W = 48
# 按钮发光色(淡黄 ≈243,239,195)占行内按钮区的比例: 实测开启态任意旋转角 >=0.126, 关闭态 <=0.019
SWITCH_ON_GLOW_RATIO = 0.06


class GeneralBuff(BaseTask, GeneralBuffAssets):

    def open_buff(self):
        """
        打开buff的总界面
        :return:
        """
        logger.info('Open buff')
        while 1:
            self.screenshot()
            if self.appear(self.I_CLOUD):
                break
            if self.appear_then_click(self.I_BUFF_1, interval=2):
                continue

        check_image = self.I_AWAKE
        while 1:
            self.screenshot()
            if self.appear(check_image):
                break

            self.swipe(self.S_BUFF_UP, interval=2)

    def close_buff(self):
        """
        关闭buff的总界面, 但是要确保buff界面已经打开了
        :return:
        """
        logger.info('Close buff')
        while 1:
            self.screenshot()
            if not self.appear(self.I_CLOUD):
                break
            if self.appear_then_click(self.I_BUFF_1, interval=2):
                continue

    def get_area(self, buff: RuleOcr) -> tuple:
        """
        获取要点击的开关buff的区域
        :param cls:
        :param image:
        :param buff:
        :return:  如果没有就返回None
        """
        # 防止邀请框挡住BUFF框架
        self.reject_invite()
        self.screenshot()
        area = buff.ocr(self.device.image)
        if area == tuple([432.0, 143.0, 325.0, 21.0]):
            logger.info(f'No {buff.name} buff')
            return None

        # 开关是行尾固定列的圆形按钮(x见SWITCH_AREA_X), OCR只提供行的y
        start_x = SWITCH_AREA_X
        start_y = area[1] - 10
        width = SWITCH_AREA_W
        height = area[3] + 20
        return int(start_x), int(start_y), int(width), int(height)

    def set_switch_area(self, area):
        """
        设置开关的区域
        :param area:
        :return:
        """
        self.I_CLOSE_RED.roi_back = list(area)  # 动态设置roi

    def switch_is_on(self) -> bool:
        """
        当前行(需先 set_switch_area)的圆形按钮是否为开启态
        开启态按钮发光且旋转, 固定模板无法匹配, 用发光色像素占比判定(旋转不变)
        """
        x, y, w, h = self.I_CLOSE_RED.roi_back
        region = self.device.image[y:y + h, x:x + w]
        r = region[:, :, 0].astype(np.int32)
        g = region[:, :, 1].astype(np.int32)
        b = region[:, :, 2].astype(np.int32)
        glow = ((r >= 225) & (g >= 210) & (b >= 150) & (b <= 230)).mean()
        return glow > SWITCH_ON_GLOW_RATIO

    def switch_set(self, is_open: bool, timeout: int = 10) -> bool:
        """
        把当前行的开关切到目标状态, 点击行尾圆形按钮直到状态一致
        :param is_open: 目标状态 True=开启
        :param timeout: 超时秒数
        :return: 是否达到目标状态
        """
        timer = Timer(timeout).start()
        while 1:
            self.screenshot()
            if self.switch_is_on() == is_open:
                return True
            if timer.reached():
                return False
            x, y, w, h = self.I_CLOSE_RED.roi_back
            self.device.click(x + w // 2, y + h // 2, control_name='GB_SWITCH')
            time.sleep(1)

    def gold_50(self, is_open: bool = True):
        """
        金币50buff
        :param is_open: 是否打开
        :return:
        """
        logger.info(f'{"Open" if is_open else "Close"} gold 50 buff')
        self.screenshot()
        area = self.get_area(self.O_GOLD_50)
        if not area:
            logger.warning('No gold 50 buff')
            return None
        self.set_switch_area(area)
        if not self.switch_set(is_open):
            logger.warning(f'{"Open" if is_open else "Close"} gold 50 buff failed')

    def gold_100(self, is_open: bool = True):
        """
        金币100buff
        :param is_open: 是否打开
        :return:
        """
        logger.info(f'{"Open" if is_open else "Close"} gold 100 buff')
        self.screenshot()
        area = self.get_area(self.O_GOLD_100)
        if not area:
            logger.warning('No gold 100 buff')
            return None
        self.set_switch_area(area)
        if not self.switch_set(is_open):
            logger.warning(f'{"Open" if is_open else "Close"} gold 100 buff failed')

    def exp_50(self, is_open: bool = True):
        """
        经验50buff
        :param is_open: 是否打开
        :return:
        """
        logger.info(f'{"Open" if is_open else "Close"} exp 50 buff')
        while 1:
            self.screenshot()
            area = self.get_area(self.O_EXP_50)
            if not area:
                logger.warning('No exp 50 buff')
                continue
            self.set_switch_area(area)

            if not self.appear(self.I_CLOSE_RED) and not self.switch_is_on():
                self.device.swipe(p2=(530, 240), p1=(580, 320))
                time.sleep(1)
            else:
                break

        if not self.switch_set(is_open):
            logger.warning(f'{"Open" if is_open else "Close"} exp 50 buff failed')

    def exp_100(self, is_open: bool = True):
        """
        经验100buff
        :param is_open: 是否打开
        :return:
        """
        logger.info(f'{"Open" if is_open else "Close"} exp 100 buff')
        while 1:
            self.screenshot()
            area = self.get_area(self.O_EXP_100)
            if not area:
                logger.warning('No exp 100 buff')
                continue
            self.set_switch_area(area)

            if not self.appear(self.I_CLOSE_RED) and not self.switch_is_on():
                self.device.swipe(p2=(530, 240), p1=(580, 320))
                time.sleep(1)
            else:
                break

        if not self.switch_set(is_open):
            logger.warning(f'{"Open" if is_open else "Close"} exp 100 buff failed')

    def get_area_image(self, target: RuleImage) -> list:
        """
        获取觉醒加成或者是御魂加成所要点击的区域
        因为实在的图片比ocr快
        :param image:
        :param target:
        :return:
        """
        self.reject_invite()
        self.screenshot()

        if not target.match(self.device.image):
            logger.warning(f'No {target.name} buff')
            return None
            # logger.info(f'front area: {target.roi_front}')
            # logger.info(f'front center: {target.front_center()}')
        start_x = SWITCH_AREA_X
        start_y = int(target.roi_front[1])
        width = SWITCH_AREA_W
        height = int(target.roi_front[3])
        return [start_x, start_y, width, height]

    def awake(self, is_open: bool = True):
        """
        觉醒buff
        :param is_open: 是否打开
        :return:
        """
        logger.info(f'{"Open" if is_open else "Close"} awake buff')
        self.screenshot()
        area = self.get_area_image(self.I_AWAKE)
        if not area:
            logger.warning('No awake buff')
            return None
        self.set_switch_area(area)
        if not self.switch_set(is_open):
            logger.warning(f'{"Open" if is_open else "Close"} awake buff failed')

    def soul(self, is_open: bool = True):
        """
        御魂buff
        :param is_open: 是否打开
        :return:
        """
        logger.info(f'{"Open" if is_open else "Close"} soul buff')
        self.screenshot()
        area = self.get_area_image(self.I_SOUL)
        if not area:
            logger.warning('No soul buff')
            return None
        self.set_switch_area(area)
        if not self.switch_set(is_open):
            logger.warning(f'{"Open" if is_open else "Close"} soul buff failed')

    def reject_invite(self):
        from tasks.Component.GeneralInvite.assets import GeneralInviteAssets as gia
        while 1:
            self.screenshot()
            if not (self.appear(gia.I_I_REJECT_1) or self.appear(gia.I_I_REJECT_2) or self.appear(gia.I_I_REJECT_3)):
                break
            if self.appear(gia.I_I_REJECT_3):
                self.click(gia.I_I_REJECT_3, 6)
                continue
            if self.appear(gia.I_I_REJECT_2):
                self.click(gia.I_I_REJECT_2, 6)
                continue
            if self.appear(gia.I_I_REJECT_1):
                self.click(gia.I_I_REJECT_1, 6)
                continue


if __name__ == '__main__':
    from module.config.config import Config
    from module.device.device import Device

    c = Config('oas1')
    d = Device(c)
    t = GeneralBuff(c, d)

    t.open_buff()
    # t.screenshot()
    #
    t.awake(is_open=True)
    t.soul(is_open=True)
    t.gold_50(is_open=False)
    t.gold_100(is_open=False)
    t.exp_50(is_open=True)
    t.exp_100(is_open=True)
