# This Python file uses the following encoding: utf-8
# @author runhey
# github https://github.com/runhey

import re

from module.logger import logger
from tasks.KekkaiUtilize.utils import CardClass
from module.atom.image_grid import ImageGrid


def parse_rule(rule: str) -> list[CardClass]:
    """
    反正不管用的是第一个
    :param rule:
    :return:
    """
    values = ['太鼓6', '太鼓5', '太鼓4', '太鼓3', '斗鱼6', '斗鱼5', '斗鱼4', '斗鱼3', '太阴6', '太阴5', '太阴4', '太阴3',
              '太阴2', '太阴1']
    match = {
        '太鼓6': CardClass.TAIKO6,
        '太鼓5': CardClass.TAIKO5,
        '太鼓4': CardClass.TAIKO4,
        '太鼓3': CardClass.TAIKO3,
        '斗鱼6': CardClass.FISH6,
        '斗鱼5': CardClass.FISH5,
        '斗鱼4': CardClass.FISH4,
        '斗鱼3': CardClass.FISH3,
        '太阴6': CardClass.MOON6,
        '太阴5': CardClass.MOON5,
        '太阴4': CardClass.MOON4,
        '太阴3': CardClass.MOON3,
        '太阴2': CardClass.MOON2,
        '太阴1': CardClass.MOON1,
    }
    rule = rule.replace(' ', '').replace('\n', '')
    # 正则表达式 分离 ">"
    rule = re.split(r'>', rule)
    rule = [item for item in rule if item in values]
    result = [match[item] for item in rule]
    return result


def parse_card_sort_order(rule: str) -> list[CardClass]:
    """
    解析挂卡星级优先级表达式，如 "斗鱼4星>太鼓5星>太鼓6"
    只支持斗鱼/太鼓的3~6星，按 ">" 分隔，越靠前优先级越高
    非法项丢弃并记录日志，解析结果为空返回 []
    :param rule:
    :return:
    """
    values = ['太鼓6', '太鼓5', '太鼓4', '太鼓3', '斗鱼6', '斗鱼5', '斗鱼4', '斗鱼3']
    match = {
        '太鼓6': CardClass.TAIKO6,
        '太鼓5': CardClass.TAIKO5,
        '太鼓4': CardClass.TAIKO4,
        '太鼓3': CardClass.TAIKO3,
        '斗鱼6': CardClass.FISH6,
        '斗鱼5': CardClass.FISH5,
        '斗鱼4': CardClass.FISH4,
        '斗鱼3': CardClass.FISH3,
    }
    rule = rule.replace(' ', '').replace('\n', '').replace('星', '')
    items = re.split(r'>', rule)
    result: list[CardClass] = []
    for item in items:
        if not item:
            continue
        if item not in values:
            logger.warning(f'Invalid card sort item: {item}')
            continue
        card = match[item]
        if card in result:
            logger.warning(f'Duplicated card sort item: {item}')
            continue
        result.append(card)
    return result

# def parse_targets(cards: list[CardClass]) -> ImageGrid:
#     """
#     从卡片列表中解析出目标
#     :param cards:
#     :return:
#     """
#     pass

# print(parse_rule("太鼓5 > 斗鱼5 > 太鼓4 > 斗鱼4 > 太鼓3 > 斗鱼3"))
