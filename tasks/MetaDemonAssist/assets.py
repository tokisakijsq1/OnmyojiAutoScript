from module.atom.image import RuleImage
from module.atom.click import RuleClick
from module.atom.long_click import RuleLongClick
from module.atom.swipe import RuleSwipe
from module.atom.ocr import RuleOcr
from module.atom.list import RuleList

# 本任务素材于 2026-11-11 从用户提供截图离线裁剪并验证:
# 全部模板对来源截图 1.0, 对其余截图最高误报 0.797(right_enter 对庭院横幅截图, 属同图标真实命中)
# 两页标题模板互判 0.62x(阈值0.8 可区分); OCR 标题关键词因竖排逐字兜底互相误报, 标题只用模板
class MetaDemonAssistAssets:

	# Image Rule Assets
	# 庭院右侧栏祸至无日活动图标(取两帧间稳定的核心子区24x24, 冰蓝核心光点会动画, 整图裁剪跨帧只0.79)
	I_MDA_RIGHT_ENTER = RuleImage(roi_front=(1187,230,24,24), roi_back=(1150,120,105,470), threshold=0.8, method="Template matching", file="./tasks/MetaDemonAssist/mda/mda_right_enter.png")
	# 祸至无日活动页的竖排"超鬼王"按钮(金边框内部)
	I_MDA_GOTO_HUOZHU = RuleImage(roi_front=(992,182,34,76), roi_back=(950,150,150,260), threshold=0.8, method="Template matching", file="./tasks/MetaDemonAssist/mda/mda_goto_huozhu.png")
	# 祸主降临页标题(与祸至无日标题同位, 靠模板区分)
	I_MDA_TITLE_HUOZHU = RuleImage(roi_front=(150,15,135,42), roi_back=(100,5,350,75), threshold=0.8, method="Template matching", file="./tasks/MetaDemonAssist/mda/mda_title_huozhu.png")
	# 祸至无日活动页标题
	I_MDA_TITLE_EVENT = RuleImage(roi_front=(150,15,132,42), roi_back=(100,5,350,75), threshold=0.8, method="Template matching", file="./tasks/MetaDemonAssist/mda/mda_title_event.png")
	# 左上角返回按钮(两个活动页同款同位)
	I_MDA_BACK = RuleImage(roi_front=(16,6,62,56), roi_back=(5,2,95,75), threshold=0.8, method="Template matching", file="./tasks/MetaDemonAssist/mda/mda_back.png")
	# 挑战按钮(右下大按钮, 有可挑战对象时显示)
	I_MDA_CHALLENGE = RuleImage(roi_front=(1130,566,124,124), roi_back=(1080,540,190,180), threshold=0.8, method="Template matching", file="./tasks/MetaDemonAssist/mda/mda_challenge.png")
	# 庭院邀请横幅上的"立即前往"圆按钮
	I_MDA_BANNER_GO = RuleImage(roi_front=(99,212,50,52), roi_back=(0,190,545,300), threshold=0.8, method="Template matching", file="./tasks/MetaDemonAssist/mda/mda_banner_go.png")
	# 2.5倍伤害勾选框 未勾选态(暗色空心圆, 来源截图2/4)
	I_MDA_BUFF_OFF = RuleImage(roi_front=(1115,514,23,24), roi_back=(1095,500,60,60), threshold=0.8, method="Template matching", file="./tasks/MetaDemonAssist/mda/mda_buff_off.png")
	# 2.5倍伤害勾选框 已勾选态(蓝色对勾圆, 来源用户特写裁剪图, 未实机验证, 代码以状态变化兜底)
	I_MDA_BUFF_ON = RuleImage(roi_front=(1113,512,29,29), roi_back=(1095,500,60,60), threshold=0.75, method="Template matching", file="./tasks/MetaDemonAssist/mda/mda_buff_on.png")

	# Click Rule Assets
	# 2.5倍伤害勾选圆圈中心
	C_MDA_BUFF = RuleClick(roi_front=(1115,514,24,24), roi_back=(1115,514,24,24), name="mda_buff")
	# 好友发现卡槽1/卡槽2 选择点击(头像区中心)
	C_MDA_CARD_1 = RuleClick(roi_front=(60,380,100,80), roi_back=(60,380,100,80), name="mda_card_1")
	C_MDA_CARD_2 = RuleClick(roi_front=(60,509,100,80), roi_back=(60,509,100,80), name="mda_card_2")

	# Ocr Rule Assets
	# 庭院邀请横幅触发检测(好友发现「N星」鬼王)
	O_MDA_BANNER = RuleOcr(roi=(0,190,545,300), area=(0,190,545,300), mode="Full", method="Default", keyword="鬼王", name="mda_banner")
	# 好友发现卡片区: 剩余时间=可挑战 / 击败奖励结算中=不可挑战(代码用 detect_and_ocr 逐行判)
	O_MDA_CARD = RuleOcr(roi=(140,368,175,265), area=(140,368,175,265), mode="Full", method="Default", keyword="剩余时间", name="mda_card")
	# 顶栏挑战资源 N/100 (挑战一次消耗10)
	O_MDA_RESOURCE = RuleOcr(roi=(1040,20,170,44), area=(1040,20,170,44), mode="DigitCounter", method="Default", keyword="", name="mda_resource")
