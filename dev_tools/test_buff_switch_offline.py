# -*- encoding: utf-8 -*-
"""
离线仿真: 2026-10-29 加成界面改版后的开关判定逻辑
对两张实机截图的每一行验证: OFF模板判定 / 发光占比判定 / 点击落点
"""
import sys
sys.path.insert(0, '.')

import cv2
import numpy as np
from numpy import fromfile, uint8

from tasks.Component.GeneralBuff.assets import GeneralBuffAssets as A

SWITCH_ON_GLOW_RATIO = 0.06


def load_rgb(path):
    img = cv2.imdecode(fromfile(path, dtype=uint8), -1)
    if img.ndim == 3 and img.shape[2] == 4:
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2RGB)
    else:
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    return img


def switch_is_on(image, area):
    x, y, w, h = area
    region = image[y:y + h, x:x + w]
    r = region[:, :, 0].astype(np.int32)
    g = region[:, :, 1].astype(np.int32)
    b = region[:, :, 2].astype(np.int32)
    glow = ((r >= 225) & (g >= 210) & (b >= 150) & (b <= 230)).mean()
    return glow, glow > SWITCH_ON_GLOW_RATIO


def off_detected(image, area):
    old = A.I_CLOSE_RED.roi_back
    A.I_CLOSE_RED.roi_back = list(area)
    ok = A.I_CLOSE_RED.match(image)
    score = A.I_CLOSE_RED.last_score
    A.I_CLOSE_RED.roi_back = old
    return ok, score


# (行名, 文字y(OCR基准), 期望状态) — err截图: gold50=ON 其余OFF; user截图: 全OFF
# exp50 是面板最末行, 被底部渐隐遮罩 → 两种判定都不可见属预期(触发 exp_50/100 的上滑循环)
ROWS = [('awake 觉醒', 143, 'OFF'), ('soul 御魂', 210, 'OFF'),
        ('gold100 金币100%', 277, 'OFF'), ('gold50 金币50%', 346, 'OFF'),
        ('exp100 经验100%', 413, 'OFF'), ('exp50 经验50%', 480, 'SWIPE')]

CASES = {
    'err_0646(实机错误截图, gold50=开)': (
        load_rgb(r'D:\YYS\log\error\1793227598573\2026-10-29_06-46-38-314187.png'),
        {'gold50 金币50%': 'ON'}),
    'user_0840(用户提供截图, 全关)': (
        load_rgb(r'C:\Users\Tokisaki\.zcode\cli\image-cache\session_b62b2825e7ed05c52ef5c545ae46b492\image-779b04dab7c763f289b5fe0bd13e8b48.png'),
        {}),
}

all_ok = True
for case_name, (img, override) in CASES.items():
    print(f'\n===== {case_name} =====')
    for row_name, text_y, default_state in ROWS:
        expected = override.get(row_name, default_state)
        area = (848, text_y - 10, 48, 40)
        glow, on = switch_is_on(img, area)
        off, score = off_detected(img, area)
        detected = 'ON' if on else ('OFF' if off else '??')
        if expected == 'SWIPE':
            ok = (detected == '??')  # 遮罩行两种判定都不可见 → 触发上滑
        else:
            ok = (detected == expected)
        all_ok &= ok
        mark = 'OK ' if ok else 'FAIL'
        print(f'  [{mark}] {row_name:<18} 期望={str(expected):<4} 判定={detected:<4} '
              f'glow={glow:.3f} off模板分={score:.3f} 点击中心=({area[0] + 24},{area[1] + 20})')

# awake/soul 走 get_area_image 路径: 模板定位行图标y
print('\n===== get_area_image 路径 (awake/soul 行定位) =====')
for case_name, (img, _) in CASES.items():
    for rule in [A.I_AWAKE, A.I_SOUL]:
        ok_match = rule.match(img)
        y = rule.roi_front[1]
        area = (848, int(y), 48, int(rule.roi_front[3]))
        glow, on = switch_is_on(img, area)
        off, score = off_detected(img, area)
        detected = 'ON' if on else ('OFF' if off else '??')
        ok = (detected == 'OFF')
        all_ok &= (ok and ok_match)
        print(f'  [{"OK " if ok and ok_match else "FAIL"}] {case_name[:9]} {rule.name:<10} '
              f'匹配={ok_match} 行y={y} 判定={detected} glow={glow:.3f} off分={score:.3f}')

print('\n全部通过' if all_ok else '\n存在失败项!')
