from module.atom.image import RuleImage
from module.atom.click import RuleClick
from module.atom.long_click import RuleLongClick
from module.atom.swipe import RuleSwipe
from module.atom.ocr import RuleOcr
from module.atom.list import RuleList

# 素材来源 2026-11-12 用户提供提供者截图(log/mdp_build_20261112/provider.png):
# 集结/邀请/召唤/空面具 4 个为 MetaDemon 与 GeneralInvite 现有 png 拷贝(0.996/1.0/1.0/0.905 实测),
# 选中金卡新裁自截图选中态(对未选中卡分离度 0.004)。验证记录见同目录 README 与 log/mdp_build_20261112
class MetaDemonProviderAssets:

	# Image Rule Assets
	# 自己发现卡右侧"集结"标记(点击弹好友邀请弹窗; MetaDemon 同款 png, 新截图 0.996)
	I_MDP_RALLY = RuleImage(roi_front=(247,146,47,52), roi_back=(200,100,140,200), threshold=0.8, method="Template matching", file="./tasks/MetaDemonProvider/mdp/mdp_rally.png")
	# 好友邀请弹窗底部"邀请"按钮(gi 同款 png, 对本弹窗 1.0000 像素级)
	I_MDP_INVITE = RuleImage(roi_front=(704,544,136,62), roi_back=(473,400,567,310), threshold=0.8, method="Template matching", file="./tasks/MetaDemonProvider/mdp/mdp_invite.png")
	# 召唤鬼王大圆按钮(右下角, 无鬼王时显示; MetaDemon 同款 png 1.0000)
	I_MDP_FIND = RuleImage(roi_front=(1140,582,86,81), roi_back=(1102,546,165,161), threshold=0.8, method="Template matching", file="./tasks/MetaDemonProvider/mdp/mdp_find.png")
	# 自己发现区空态面具(鬼王已消失判据之一; roiBack 限定自己发现区, 弹窗区有 0.787 误报勿放宽)
	I_MDP_EMPTY = RuleImage(roi_front=(44,134,88,85), roi_back=(30,110,270,160), threshold=0.85, method="Template matching", file="./tasks/MetaDemonProvider/mdp/mdp_empty.png")
	# 好友邀请弹窗内好友卡选中态金色底(裁自选中卡右上纯金底区, 避开名字头像)
	I_MDP_SELECTED = RuleImage(roi_front=(832,292,92,58), roi_back=(640,180,310,350), threshold=0.8, method="Template matching", file="./tasks/MetaDemonProvider/mdp/mdp_selected.png")

	# Swipe Rule Assets
	# 好友列表上滑(找下一屏; 起点低终点高表示手指上滑内容上移)
	S_MDP_LIST_UP = RuleSwipe(roi_front=(560,470,80,40), roi_back=(560,260,80,40), mode="default", name="mdp_list_up")

	# Ocr Rule Assets
	# 自己发现卡文本(鬼王在场判据)
	O_MDP_CARD = RuleOcr(roi=(140,158,120,55), area=(140,158,120,55), mode="Full", method="Default", keyword="剩余时间", name="mdp_card")
	# 好友邀请弹窗左/右列好友名(运行时注入 keyword, gi detect_select 模式)
	O_MDP_COLUMN_1 = RuleOcr(roi=(440,190,195,330), area=(440,190,195,330), mode="Full", method="Default", keyword="", name="mdp_column_1")
	O_MDP_COLUMN_2 = RuleOcr(roi=(730,190,200,330), area=(730,190,200,330), mode="Full", method="Default", keyword="", name="mdp_column_2")
	# 顶栏票数(仅日志参考)
	O_MDP_TICKET = RuleOcr(roi=(500,20,130,40), area=(500,20,130,40), mode="DigitCounter", method="Default", keyword="", name="mdp_ticket")
