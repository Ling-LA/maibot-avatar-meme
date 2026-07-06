"""QQ头像表情包插件 v3.0

通过 /表情 命令，输入QQ号或@某人，调用 apix.iqfk.top 聚合SV2接口生成搞笑表情包。
支持 307 种效果，/表情列表 生成图片菜单。
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import math
import os
import random
import re
import time
from pathlib import Path
from typing import Any

import aiohttp
from maibot_sdk import Command, Field, MaiBotPlugin, PluginConfigBase

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    Image = None  # type: ignore

API_URL = "https://apix.iqfk.top/api/sv1"
MEME_JS_URL = "https://meme.iqfk.top/js/meme-generator.js"
CACHE_FILE = "effects_cache.json"  # relative to plugin dir
AUTO_UPDATE_COOLDOWN = 3600  # 1 hour between auto checks

EFFECTS: dict[str, str] = {}
PAGE_SIZE = 42

# Auto-update state (module-level to survive between command invocations)
_last_update_check: float = 0
_daily_cache_date: str = ""  # YYYY-MM-DD of last fetch
_update_lock = asyncio.Lock()
_plugin_dir: Path | None = None


class PluginSectionConfig(PluginConfigBase):
    __ui_label__ = "插件"
    __ui_icon__ = "package"
    __ui_order__ = 0

    enabled: bool = Field(default=True, description="启用插件")
    config_version: str = Field(default="3.0.0", description="配置版本")
    api_key: str = Field(default="", description="SV1 API Key")
    api_key_v2: str = Field(default="", description="SV2 API Key")


class MemeConfig(PluginConfigBase):
    plugin: PluginSectionConfig = Field(default_factory=PluginSectionConfig)


# ─── effects data ───────────────────────────────────────────────

EFFECTS = {
    "kurogames_verina_group_photo": "和维里奈合影",
    "family_know": "家人们谁懂啊",
    "kurogames_cartethyia_feetup": "卡提希娅抬脚",
    "what_he_wants": "最想要的东西",
    "beat_head": "怎么说话的你",
    "fill_head": "满脑子都是它",
    "kurogames_jinhsi_steamed_buns": "今汐小龙包",
    "mihoyo_senior_phone": "米学长手机",
    "kurogames_rover_head": "漂泊头像框",
    "out": "out",
    "distracted": "注意力涣散",
    "acg_entrance": "二次元入口",
    "decent_kiss": "像样的亲亲",
    "cat_scratch": "猫抓猫猫抓",
    "atri_like": "亚托莉喜欢",
    "caused_by_this": "这个引起的",
    "feizhaiking": "肥仔网络皇帝",
    "zhiyexuanshou": "职业选手",
    "erciyuan": "你是二次元",
    "back_to_work": "继续干活",
    "kurogames_rover_lick": "漂泊者舔",
    "always": "一直一直",
    "divorce": "离婚协议",
    "potato_mines": "土豆地雷",
    "sphere_rotate": "球面旋转",
    "painter": "格蕾修画",
    "let_me_in": "让我进去",
    "capoo_love": "咖波爱心",
    "rotate_3d": "三维旋转",
    "walnut_pad": "胡桃平板",
    "seal": "源石封印",
    "sekaiichi_kawaii": "第一可爱",
    "fade_away": "灰飞烟灭",
    "dont_go_near": "不要靠近",
    "tomb_yeah": "坟前比耶",
    "tightly": "紧紧贴着",
    "jiji_king": "急急国王",
    "paint": "这像画吗",
    "kurogames_yangyang_lover": "秧秧老公",
    "dont_get": "你不懂啦",
    "baby": "宝宝是我",
    "zzdd": "指指点点",
    "ikun_durian_head": "榴莲坤头",
    "ikun_like": "坤坤喜欢",
    "ikun_why_are_you": "你干嘛哟",
    "mixue": "蜜雪冰城",
    "kurogames_rover_cards": "荣耀之丘",
    "kurogames_changli_finger": "抽卡非酋",
    "whisper": "窃窃私语",
    "cinderella_eat": "灰姑娘吃",
    "atri_finger": "亚托莉指",
    "addiction": "毒瘾发作",
    "kurogames_orang": "飞廉之猩",
    "azur_lane_cheshire_thumbs_up": "柴郡点赞",
    "peas": "我勒个豆",
    "something": "什么东西",
    "yuzu_soft_ayachi_nene": "宁宁困惑",
    "mihoyo_yelan_phone": "夜兰手机",
    "pay_to_watch": "付费观看",
    "capoo_smash_egg": "咖波砸蛋",
    "kurogames_phrolova_eat": "弗洛洛吃",
    "ignite": "燃起来了",
    "jiubingfufa": "旧病复发",
    "left_right_jump": "左右横跳",
    "learn": "偷学基础",
    "plana_eat": "普拉娜吃",
    "luotianyi_need": "洛天依要",
    "konata_watch": "泉此方看",
    "onepunch": "给你一拳",
    "qilongwang": "骑龙王",
    "keliplay": "可莉打",
    "wolaile": "我来了",
    "daomaoyan": "导冒烟",
    "wudizhen": "无敌帧",
    "play_together": "一起玩",
    "shuaiqunwu": "甩群舞",
    "shuainiuzi": "甩牛子",
    "mihoyo": "米哈游",
    "little_angel": "小天使",
    "karyl_point": "凯露指",
    "lim_x_0": "无穷小",
    "kurogames_jinhsi_sit": "今汐坐",
    "happy_new_year": "新年好",
    "buyaolian": "不要脸",
    "sold_out": "卖掉了",
    "capooplay": "咖波打",
    "kurogames_lupa_eat": "露帕吃",
    "nahida_bite": "草神啃",
    "pyramid": "金字塔",
    "stew": "炖群友",
    "play_game": "玩游戏",
    "tom_tease": "汤姆笑",
    "swirl_turn": "回旋转",
    "subject3": "科目三",
    "thermometer_gun": "体温枪",
    "this_chicken": "鸡符咒",
    "washer": "洗衣机",
    "windmill_turn": "风车转",
    "you_dont_get": "你不懂",
    "hug_leg": "抱大腿",
    "funny_mirror": "哈哈镜",
    "lick_candy": "棒棒糖",
    "ice_tea_head": "冰红茶",
    "klee_eat": "可莉吃",
    "chase_train": "追火车",
    "capoo_rub": "咖波贴",
    "charpic": "字符画",
    "stare_at_you": "盯着你",
    "pixelate": "像素化",
    "play_baseball": "打棒球",
    "sit_still": "坐得住",
    "kurogames_camellya_photo": "大傻椿",
    "ikun_head": "小黑子",
    "contract": "卖身契",
    "huochailu": "火柴鹿",
    "garbage": "垃圾桶",
    "kurogames_iuno_hug": "尤诺抱",
    "read_love_letters": "看情书",
    "chillet_deer": "疾风鹿",
    "mihoyo_qiqi_suck": "七七舔",
    "kurogames_jinhsi_eat": "今汐吃",
    "pregnancy_test": "验孕棒",
    "widow": "未亡人",
    "coupon": "兑换券",
    "backflip": "后空翻",
    "play_basketball": "打篮球",
    "listen_music": "听音乐",
    "no_response": "无响应",
    "myplay": "笨死了",
    "caosini": "爆炒你",
    "electrify_you": "电死你",
    "payment_code": "付款码",
    "yesirmiao": "敬礼喵",
    "zhuishamiao": "追杀你",
    "sikete": "斯科特",
    "dieluohan": "叠罗汉",
    "nizaishuo": "你再说",
    "orange_head": "橘子头",
    "fireworks_head": "看烟花",
    "miss_in_my_sleep": "睡梦中",
    "kurogames_lupa_photo": "露帕指",
    "scissor_seven_head": "伍六七",
    "kurogames_zhezhi_draw": "折枝画",
    "kurogames_abby_weeping": "阿布哭",
    "look_leg": "看看腿",
    "blood_pressure": "高血压",
    "capoo_draw": "咖波画",
    "capoo_rip": "咖波撕",
    "capoo_point": "咖波指",
    "kaleidoscope": "万花筒",
    "capoo_fished_out": "咖波掏",
    "look_this_icon": "看图标",
    "my_wife": "我老婆",
    "safe_sense": "安全感",
    "maomaochong": "毛毛虫",
    "chuosini": "戳死你",
    "sunflower": "太阳花",
    "yuzu_soft_ciallo": "Ciallo",
    "doroya": "doro鸭",
    "doro": "doro点赞",
    "doro_dear": "doro 爱",
    "doro_lick": "doro 舔",
    "dorowaimai": "doro 外卖",
    "chuangfei": "创飞",
    "mix_dog": "小狗",
    "police_car": "警车",
    "wanhuo": "玩火",
    "lashi": "拉石",
    "daobao": "导爆",
    "aichuai": "挨踹",
    "wanju": "玩具",
    "fangpi": "放屁",
    "trolley": "推车",
    "tease": "拿捏",
    "symmetric": "对称",
    "printing": "打印",
    "police": "出警",
    "police1": "警察",
    "perfect": "完美",
    "pass_the_buck": "甩锅",
    "overtime": "加班",
    "name_generator": "亚名",
    "mahiro_readbook": "看书",
    "love_you": "爱你",
    "loop": "循环",
    "look_flat": "看扁",
    "keep_away": "远离",
    "fogging": "回南",
    "confuse": "迷惑",
    "jiujiu": "啾啾",
    "cover_face": "捂脸",
    "china_flag": "国庆",
    "throwing_poop": "扔石",
    "fishing": "钓鱼",
    "rune": "符咒",
    "fart": "放屁2",
    "think_what": "在想",
    "wooden_fish": "木鱼",
    "you_should_call": "致电",
    "flush": "红温",
    "flick": "弹你",
    "flash_blind": "闪瞎",
    "taunt": "嘲笑",
    "time_to_go": "抓走",
    "spider": "蜘蛛",
    "mourning": "上香",
    "loading": "加载",
    "kick_ball": "踢球",
    "hold_tight": "抱哭",
    "follow": "关注",
    "thump_wildly": "爆捶",
    "rip_angrily": "怒撕",
    "applaud": "鼓掌",
    "behead": "斩首",
    "shock": "震惊",
    "adoption": "收养",
    "anyliew_people_i_like": "挚爱",
    "anyliew_struggling": "挣扎",
    "begged_me": "求我",
    "xile": "洗了",
    "pinailong": "奶龙",
    "chuini": "捶你",
    "cockroaches": "小强",
    "dinosaur_head": "迷你",
    "duidi": "怼地",
    "fever": "发烧",
    "ikun_basketball": "篮球",
    "mihoyo_genshin_impact_players": "原批",
    "need": "需要",
    "dont_touch": "别碰",
    "why_at_me": "艾特",
    "scratch_head": "挠头",
    "support": "支柱",
    "clown_mask": "小丑",
    "mahiro_fuck": "鄙视",
    "kurogames_good_night": "晚安",
    "clownish": "滑稽",
    "small_hands": "小手",
    "alike": "一样",
    "add_chaos": "添乱",
    "cyan": "群青",
    "wallpaper": "墙纸",
    "wave": "波纹",
    "vibrate": "震动",
    "upside_down": "反了",
    "teach": "讲课",
    "stickman_dancing": "跳舞",
    "speechless": "无语",
    "smash": "砸碎",
    "read_book": "看书2",
    "shake_head": "晃脑",
    "punch": "打拳",
    "potato": "土豆",
    "rip_clothes": "撕开",
    "kurogames_mp": "鸣批",
    "saimin_app": "催眠",
    "rise_dead": "诈尸",
    "run_away": "快逃",
    "diucat": "丢猫",
    "penshe": "喷射",
    "zuini": "嘴你",
    "heike": "嘿壳",
    "richu": "日出",
    "liedui": "列队",
    "durian": "榴莲",
    "downban": "下班",
    "ikun_need_tv": "坤坤",
    "dragon_hand": "龙手",
    "mihoyo_funina_death_penalty": "死刑",
    "mihoyo_ineffa_droid": "人机",
    "zhongcheng": "忠诚",
    "slacking_off": "摸鱼",
    "horse_riding": "骑马",
    "laydown_do": "躺撅",
    "sitdown_do": "坐撅",
    "dinosaur": "恐龙",
    "remote_control": "遥控",
    "jibao": "挤爆",
    "huanying": "欢迎",
    "huanying2": "欢迎2",
    "huanying3": "欢迎3",
    "bite": "啃",
    "suck": "吸",
    "turn": "转",
    "eat": "吃",
    "shuai": "甩",
    "throw_gif": "抛",
    "crawl": "爬",
    "pound": "捣",
    "play": "顶",
    "petpet": "摸",
    "pat": "拍",
    "knock": "敲",
    "hammer": "锤",
    "thump": "捶",
    "throw": "扔",
    "step_on": "踩",
    "rip": "撕",
    "capoo_stew": "炖",
    "jerry_stare": "盯",
    "roll": "滚",
    "capoo_strike": "撞",
    "worship": "拜",
    "shiroko_pero": "舔",
    "pinch": "捏",
    "masturbate": "导",
    "jump": "跳",
    "raise_image": "举",
    "pao": "跑",
    "yao": "摇",
    "ok": "ok",
    "ly01": "LY-1舰载激光武器",
    "little_do": "小掘",
    "do": "超市",
    "can_can_need": "看看你的",
    "oral_sex": "口",
    "lash": "鞭打",
    "fencing": "击剑",
    "hug": "抱抱",
    "beat_up": "揍",
    "rub": "贴贴",
    "pigcar": "猪猪车",
    "dorochui": "doro锤",
    "chiikawa": "吉伊卡哇",
    "qi": "骑",
    "nantongjue": "男铜",
    "nvtongjue": "女铜",
    "mixue_stick_beaten_fresh_orange": "棒打鲜橙",
    "mixue_jasmine_milk_green": "茉莉奶绿",
}

# V2 效果（需要两个QQ号，调用 sv2 接口）
V2_EFFECTS: dict[str, str] = {
    "ly01": "LY-1舰载激光武器",
    "little_do": "小掘",
    "do": "超市",
    "can_can_need": "看看你的",
    "oral_sex": "口",
    "lash": "鞭打",
    "fencing": "击剑",
    "hug": "抱抱",
    "beat_up": "揍",
    "rub": "贴贴",
    "pigcar": "猪猪车",
    "dorochui": "doro锤",
    "chiikawa": "吉伊卡哇",
    "qi": "骑",
    "nantongjue": "男铜",
    "nvtongjue": "女铜",
    "mixue_stick_beaten_fresh_orange": "棒打鲜橙",
    "mixue_jasmine_milk_green": "茉莉奶绿",
}


def _get_effects_list(v2: bool = False) -> list[tuple[str, str]]:
    """Return effects list for menu."""
    src = V2_EFFECTS if v2 else EFFECTS
    return [(k, v) for k, v in src.items()]


def _find_effect_v1(keyword: str) -> str | None:
    """Find v1 effect by index, exact value, exact name, or substring."""
    kw = keyword.strip()
    v1_list = [(k, v) for k, v in EFFECTS.items()]
    if kw.isdigit():
        idx = int(kw)
        if 1 <= idx <= len(v1_list):
            return v1_list[idx - 1][0]
    kw_lower = kw.lower()
    if kw_lower in {k.lower(): k for k in EFFECTS}:
        return {k.lower(): k for k in EFFECTS}[kw_lower]
    for value, name in EFFECTS.items():
        if name == kw or kw_lower in value.lower() or kw_lower in name:
            return value
    return None


def _find_effect_v2(keyword: str) -> str | None:
    """Find v2 effect by index, exact value, exact name, or substring."""
    kw = keyword.strip()
    v2_list = [(k, v) for k, v in V2_EFFECTS.items()]
    if kw.isdigit():
        idx = int(kw)
        if 1 <= idx <= len(v2_list):
            return v2_list[idx - 1][0]
    kw_lower = kw.lower()
    if kw_lower in {k.lower(): k for k in V2_EFFECTS}:
        return {k.lower(): k for k in V2_EFFECTS}[kw_lower]
    for value, name in V2_EFFECTS.items():
        if name == kw or kw_lower in value.lower() or kw_lower in name:
            return value
    return None


def _build_menu_image(page: int, v2: bool = False) -> bytes | None:
    """Generate paginated menu image. v2=True for v2 two-person effects."""
    if Image is None:
        return None

    effects = _get_effects_list(v2=v2)
    total = len(effects)
    total_pages = math.ceil(total / PAGE_SIZE) if total else 1

    if page < 1 or page > total_pages:
        return None

    # Layout
    col_widths = [32, 180, 130]
    header_h = 52
    footer_h = 28
    pad_x, pad_y = 12, 8
    cell_h = 28

    img_w = sum(col_widths) + pad_x * 2
    rows_per_page = PAGE_SIZE
    img_h = header_h + rows_per_page * cell_h + footer_h + pad_y

    # Colors
    bg = (255, 245, 250)  # light pink
    header_bg = (255, 126, 182)  # primary pink
    cell_bg_a = (255, 255, 255)
    cell_bg_b = (255, 240, 245)
    text_dark = (80, 60, 70)
    text_mid = (150, 120, 140)
    text_light = (255, 255, 255)

    img = Image.new("RGB", (img_w, img_h), bg)
    draw = ImageDraw.Draw(img)

    # Try to load font
    font_paths = [
        "C:/Windows/Fonts/msyh.ttc",  # Microsoft YaHei
        "C:/Windows/Fonts/simhei.ttf",  # SimHei
        "C:/Windows/Fonts/simsun.ttc",
    ]
    font = font_sm = font_xs = None
    for fp in font_paths:
        try:
            font = ImageFont.truetype(fp, 14)
            font_sm = ImageFont.truetype(fp, 12)
            font_xs = ImageFont.truetype(fp, 10)
            break
        except (OSError, IOError):
            continue
    if font is None:
        font = font_sm = font_xs = ImageFont.load_default()

    # Header
    draw.rectangle([(0, 0), (img_w, header_h)], fill=header_bg)
    title = "🎭 表情包效果菜单" if not v2 else "👥 V2双人效果菜单"
    subtitle = "V1效果 | 每日自动更新" if not v2 else "需传入两个QQ | /表情2列表 查看"
    draw.text((pad_x + 4, 8), title, fill=text_light, font=font)
    page_info = f"{page}/{total_pages}  (共{total}种)"
    dw = draw.textlength(page_info, font=font_sm) if hasattr(draw, "textlength") else len(page_info) * 8
    draw.text((img_w - pad_x - dw - 4, 8), page_info, fill=text_light, font=font_sm)
    draw.text((pad_x + 4, 28), subtitle, fill=(255, 220, 230), font=font_xs)

    # Column headers
    col_x = pad_x
    headers = ["#", "value (命令参数)", "效果名"]
    for i, (hdr, cw) in enumerate(zip(headers, col_widths)):
        draw.text((col_x + 2, header_h + 2), hdr, fill=text_mid, font=font_xs)
        col_x += cw

    # Divider line after header
    draw.line([(pad_x, header_h + 16), (img_w - pad_x, header_h + 16)], fill=(220, 190, 200))

    # Rows
    start_idx = (page - 1) * PAGE_SIZE
    end_idx = min(start_idx + PAGE_SIZE, total)
    for i, idx in enumerate(range(start_idx, end_idx)):
        value, name = effects[idx]
        y = header_h + 18 + i * cell_h
        bg_c = cell_bg_a if i % 2 == 0 else cell_bg_b

        # Row background
        draw.rectangle([(pad_x, y), (img_w - pad_x, y + cell_h)], fill=bg_c)

        # Sequence number
        seq = str(idx + 1)
        sw = draw.textlength(seq, font=font_xs) if hasattr(draw, "textlength") else len(seq) * 6
        draw.text((pad_x + (col_widths[0] - sw) / 2, y + 4), seq, fill=text_mid, font=font_xs)

        # Value
        draw.text((pad_x + col_widths[0] + 2, y + 4), value, fill=text_dark, font=font_sm)

        # Name
        draw.text((pad_x + col_widths[0] + col_widths[1] + 2, y + 4), name, fill=text_dark, font=font_sm)

    # Footer
    fy = header_h + 18 + rows_per_page * cell_h + 4
    draw.line([(pad_x, fy - 2), (img_w - pad_x, fy - 2)], fill=(220, 190, 200))
    footer_text = f"第 {page}/{total_pages} 页 | 发送 /表情列表 {page+1 if page < total_pages else 1} 翻页"
    draw.text((pad_x + 4, fy), footer_text, fill=text_mid, font=font_xs)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# ─── cache & auto-update ────────────────────────────────────

def _cache_path() -> Path:
    """Return absolute path to the effects cache file."""
    if _plugin_dir:
        return _plugin_dir / CACHE_FILE
    return Path(__file__).parent / CACHE_FILE


def _load_cached_effects() -> dict[str, str]:
    """Load effects from local cache file. Returns {} on failure."""
    path = _cache_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _save_cached_effects(effects: dict[str, str]) -> None:
    """Save effects dict to local cache file."""
    try:
        _cache_path().write_text(
            json.dumps(effects, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except Exception:
        pass


async def _fetch_online_effects(logger=None) -> dict[str, str] | None:
    """Fetch and parse effects from meme.iqfk.top JS source.

    Returns dict {value: name} or None on failure.
    """
    try:
        async with aiohttp.ClientSession() as session:
            headers = {"User-Agent": "Mozilla/5.0"}
            async with session.get(MEME_JS_URL, headers=headers,
                                   timeout=aiohttp.ClientTimeout(total=20)) as resp:
                if resp.status != 200:
                    if logger:
                        logger.warning(f"获取效果列表失败 HTTP {resp.status}")
                    return None
                text = await resp.text()
    except Exception as e:
        if logger:
            logger.warning(f"获取效果列表异常: {e}")
        return None

    match = re.search(r"const memeData = (\[.*?\]);", text, re.DOTALL)
    if not match:
        return None

    pairs = re.findall(r"{ name: '([^']*)', value: '([^']*)' }", match.group(1))
    if not pairs:
        return None

    return {value: name for name, value in pairs}


async def _sync_effects(logger=None, force: bool = False) -> tuple[int, int]:
    """Check for new effects online and merge into EFFECTS dict.

    Daily cache: only fetches once per calendar day unless force=True.
    Returns (new_count, total_count).
    """
    global _last_update_check, _daily_cache_date
    _last_update_check = time.time()

    today = time.strftime("%Y-%m-%d")
    if not force and _daily_cache_date == today:
        return 0, len(EFFECTS)

    online = await _fetch_online_effects(logger)
    if online is None:
        return 0, len(EFFECTS)

    # Merge: online effects overwrite by value, keep local extras
    merged = dict(online)
    for value, name in EFFECTS.items():
        if value not in merged:
            merged[value] = name

    new_count = len(merged) - len(EFFECTS)
    if new_count > 0 or force:
        EFFECTS.clear()
        EFFECTS.update(merged)
        _save_cached_effects(dict(EFFECTS))
        _daily_cache_date = today
        if logger:
            logger.info(f"🎭 发现 {new_count} 个新效果，共 {len(EFFECTS)} 种（今日已缓存）")
    else:
        _daily_cache_date = today  # mark as checked even if no new effects

    return new_count, len(EFFECTS)


class AvatarMemePlugin(MaiBotPlugin):
    """QQ头像表情包插件 v3.1"""

    config_model = MemeConfig

    async def on_load(self) -> None:
        global _plugin_dir
        _plugin_dir = Path(__file__).parent

        cached = _load_cached_effects()
        if cached:
            for value, name in cached.items():
                EFFECTS[value] = name

        self.ctx.logger.info(f"QQ表情包插件 v3.3 加载 | V1:{len(EFFECTS)}种 V2:{len(V2_EFFECTS)}种")

    async def on_unload(self) -> None:
        pass

    async def on_config_update(self, scope: str, config_data: dict[str, object], version: str) -> None:
        del scope, config_data, version

    # ── helpers ──────────────────────────────────────────────

    async def _extract_all_qqs(self, target: str, raw_text: str, message: Any = None) -> list[str]:
        """Extract ALL QQ numbers from message segments and target text.
        
        Order: @mentions first (from message dict), then plain numbers from text.
        Deduplicated while preserving order.
        """
        qqs: list[str] = []
        seen: set[str] = set()

        def add_from_segment(qq: Any) -> None:
            """Add from message segment — trust the source, minimal validation."""
            qq = str(qq).strip()
            if qq and qq not in seen:
                qqs.append(qq)
                seen.add(qq)

        def add_from_text(qq: str) -> None:
            """Add from text — only accept valid QQ numbers."""
            qq = str(qq).strip()
            if qq.isdigit() and qq not in seen and 5 <= len(qq) <= 12:
                qqs.append(qq)
                seen.add(qq)

        # 1. @mentions from message dict's raw_message segments
        if isinstance(message, dict):
            segments = message.get("raw_message")
            if isinstance(segments, list):
                for seg in segments:
                    if not isinstance(seg, dict):
                        continue
                    if str(seg.get("type") or "").lower() == "at":
                        data = seg.get("data")
                        if isinstance(data, dict):
                            add_from_segment(data.get("target_user_id") or data.get("qq") or data.get("user_id"))

        # 2. CQ codes in text (safety: coerce to str)
        for src in (str(raw_text), str(target)):
            for m in re.finditer(r"\[CQ:at,qq=(\d+)\]", src):
                add_from_text(m.group(1))

        # 3. Plain QQ numbers from target text
        for m in re.finditer(r"(\d{5,12})", str(target)):
            add_from_text(m.group(1))

        # 4. Resolve @display_name mentions via group member list
        if isinstance(message, dict):
            resolved = await self._resolve_at_mentions(target, message)
            for qq in resolved:
                add_from_segment(qq)

        return qqs

    # ── API call ─────────────────────────────────────────────

    async def _call_api(self, meme: str, qq: str, qq2: str = "", v2: bool = False) -> bytes | None:
        """Call apix API to generate a meme image.

        Args:
            meme: effect value
            qq: primary QQ number
            qq2: secondary QQ number (for v2 dual-person effects)
            v2: if True, use sv2 endpoint with pic1/pic2 params
        """
        key = self.config.plugin.api_key
        if not key:
            self.ctx.logger.error("API Key 未配置")
            return None

        if v2:
            v2key = self.config.plugin.api_key_v2 or key
            params = f"key={v2key}&meme={meme}&pic1={qq}&pic2={qq2 or qq}"
            url = f"https://apix.iqfk.top/api/sv2?{params}"
            headers = {}
        else:
            params = f"key={key}&meme={meme}&pic={qq}"
            url = f"{API_URL}?{params}"
            headers = {}

        async with aiohttp.ClientSession() as session:
            data = await self._fetch_image(session, url, headers if headers else None)
            if data:
                return data

        return None

    async def _fetch_image(
        self, session: aiohttp.ClientSession, url: str, headers: dict | None = None
    ) -> bytes | None:
        try:
            kw = {"timeout": aiohttp.ClientTimeout(total=30)}
            if headers:
                kw["headers"] = headers
            async with session.get(url, **kw) as resp:
                if resp.status != 200:
                    return None
                ct = resp.headers.get("Content-Type", "")
                data = await resp.read()
                if "image" in ct:
                    return data
                # Debug log non-image responses
                if data[:1] == b"{":
                    text = data[:200].decode("utf-8", errors="replace")
                    if '"error"' in text or '"msg"' in text:
                        self.ctx.logger.warning(f"API: {text}")
        except Exception as e:
            self.ctx.logger.warning(f"API请求失败: {e}")
        return None

    # ── @mention resolution ─────────────────────────────────

    async def _resolve_at_mentions(self, target: str, message: dict) -> list[str]:
        """Resolve @display_name to QQ. Only @self works (sender match)."""
        mentions: list[str] = re.findall(r"@(\S+)", target)
        if not mentions:
            return []

        qqs: list[str] = []
        seen: set[str] = set()

        user_info = (message.get("message_info") or {}).get("user_info", {})
        sender_qq = str(user_info.get("user_id", ""))
        sender_nick = user_info.get("user_nickname", "")
        sender_card = user_info.get("user_cardname") or ""

        for name in mentions:
            if name in (sender_nick, sender_card) and sender_qq and sender_qq not in seen:
                qqs.append(sender_qq)
                seen.add(sender_qq)

        return qqs

    # ── commands ─────────────────────────────────────────────

    @Command(
        "avatar_meme",
        description="用QQ号头像制作表情包",
        pattern=r"^[/／]表情\s*(?P<target>.+)?$",
    )
    async def handle_meme(self, stream_id: str = "", **kwargs: Any) -> tuple[bool, str, bool]:
        matched_groups: dict = kwargs.get("matched_groups") or {}
        raw_text: str = str(kwargs.get("text") or "")
        message: Any = kwargs.get("message")

        target = (matched_groups.get("target") or "").strip()

        if not self.config.plugin.enabled:
            return False, "插件未启用", True

        if not target:
            await self.ctx.send.text(_help_text(), stream_id)
            return True, "显示帮助", True

        # Extract ALL QQs (mentions first, then plain numbers)
        all_qqs = await self._extract_all_qqs(target, raw_text, message)
        if not all_qqs:
            await self.ctx.send.text("❓ 请提供QQ号或@某人", stream_id)
            return True, "未找到QQ号", True

        # Find effect keyword from remaining text
        cleaned = re.sub(r"\[CQ:at[^\]]*\]", "", target).strip()
        cleaned = re.sub(r"\d{5,12}", "", cleaned).strip()
        cleaned = re.sub(r"@\S+\s*", "", cleaned).strip()
        # Determine v1/v2 based on QQ count
        if len(all_qqs) >= 2:
            # 2+ QQs → V2 only
            qq1, qq2 = all_qqs[0], all_qqs[1]
            effect = _find_effect_v2(cleaned) if cleaned else None
            if not effect:
                choices = [(v, n) for v, n in V2_EFFECTS.items()]
                v, n = random.choice(choices)
                effect = v
            name = V2_EFFECTS.get(effect, effect)
            self.ctx.logger.info(f"V2表情包 qq1={qq1} qq2={qq2} meme={effect} ({name})")
            result = await self._call_api(effect, qq1, qq2, v2=True)
            if result is None:
                await self.ctx.send.text(f"❌ [{name}] 生成失败", stream_id)
                return True, "V2 API失败", True
            b64 = base64.b64encode(result).decode("utf-8")
            await self.ctx.send.image(b64, stream_id)
            return True, f"V2 qq1={qq1} qq2={qq2} meme={effect}", True

        # 1 QQ → V1 only (no V2 solo)
        qq = all_qqs[0]
        effect = _find_effect_v1(cleaned) if cleaned else None
        if not effect:
            effect = random.choice(list(EFFECTS.keys()))
        name = EFFECTS.get(effect, effect)
        self.ctx.logger.info(f"表情包 qq={qq} meme={effect} ({name})")
        result = await self._call_api(effect, qq)
        if result is None:
            await self.ctx.send.text(f"❌ [{name}] 生成失败", stream_id)
            return True, "API失败", True

        b64 = base64.b64encode(result).decode("utf-8")
        await self.ctx.send.image(b64, stream_id)
        return True, f"ok qq={qq} meme={effect}", True

    @Command(
        "meme_list",
        description="表情包效果菜单",
        pattern=r"^[/／]表情(?:包)?列表\s*(?P<page>\d+)?$",
    )
    async def handle_list(self, stream_id: str = "", **kwargs: Any) -> tuple[bool, str, bool]:
        global _last_update_check
        matched_groups: dict = kwargs.get("matched_groups") or {}
        page_str = (matched_groups.get("page") or "").strip()
        page = int(page_str) if page_str.isdigit() else 1

        # Auto-check for new effects (once per day, non-blocking)
        today = time.strftime("%Y-%m-%d")
        if _daily_cache_date != today:
            asyncio.create_task(self._auto_update())

        total = len(EFFECTS)
        total_pages = math.ceil(total / PAGE_SIZE)

        if page < 1 or page > total_pages:
            await self.ctx.send.text(f"❌ 页码范围: 1-{total_pages}", stream_id)
            return True, "页码无效", True

        img_bytes = await asyncio.to_thread(_build_menu_image, page, False)
        if img_bytes is None:
            await self.ctx.send.text("❌ 生成菜单图片失败", stream_id)
            return True, "菜单生成失败", True

        b64 = base64.b64encode(img_bytes).decode("utf-8")
        await self.ctx.send.image(b64, stream_id)
        return True, f"菜单 p{page}/{total_pages}", True

    async def _auto_update(self) -> None:
        """Background auto-update: check for new effects, log result."""
        async with _update_lock:
            new, total = await _sync_effects(self.ctx.logger)
            if new > 0:
                self.ctx.logger.info(f"自动更新: +{new}新效果, 共{total}种")

    @Command(
        "meme_update",
        description="手动更新表情包效果列表",
        pattern=r"^[/／]表情(?:包)?更新$",
    )
    async def handle_update(self, stream_id: str = "", **kwargs: Any) -> tuple[bool, str, bool]:
        del kwargs
        await self.ctx.send.text("🔍 正在检查新效果...", stream_id)

        async with _update_lock:
            new, total = await _sync_effects(self.ctx.logger, force=True)

        if new > 0:
            await self.ctx.send.text(f"✅ 更新完成！新增 {new} 种，共 {total} 种效果\n发送 /表情列表 查看", stream_id)
        elif new == 0:
            await self.ctx.send.text(f"👌 已是最新，共 {total} 种效果", stream_id)
        else:
            await self.ctx.send.text("❌ 检查更新失败，请稍后再试", stream_id)

        return True, f"更新 new={new} total={total}", True

    @Command(
        "meme2_list",
        description="V2双人表情包效果菜单",
        pattern=r"^[/／]表情2列表\s*(?P<page>\d+)?$",
    )
    async def handle_list2(self, stream_id: str = "", **kwargs: Any) -> tuple[bool, str, bool]:
        matched_groups: dict = kwargs.get("matched_groups") or {}
        page_str = (matched_groups.get("page") or "").strip()
        page = int(page_str) if page_str.isdigit() else 1

        total = len(V2_EFFECTS)
        total_pages = math.ceil(total / PAGE_SIZE) if total else 1

        if page < 1 or page > total_pages:
            await self.ctx.send.text(f"❌ 页码范围: 1-{total_pages}", stream_id)
            return True, "页码无效", True

        img_bytes = await asyncio.to_thread(_build_menu_image, page, True)
        if img_bytes is None:
            await self.ctx.send.text("❌ 生成菜单图片失败", stream_id)
            return True, "菜单生成失败", True

        b64 = base64.b64encode(img_bytes).decode("utf-8")
        await self.ctx.send.image(b64, stream_id)
        return True, f"V2菜单 p{page}/{total_pages}", True

    @Command(
        "meme_help",
        description="表情包帮助",
        pattern=r"^[/／]表情(?:包)?帮助$",
    )
    async def handle_help(self, stream_id: str = "", **kwargs: Any) -> tuple[bool, str, bool]:
        await self.ctx.send.text(_help_text(), stream_id)
        return True, "帮助", True


def _help_text() -> str:
    total = len(EFFECTS)
    total2 = len(V2_EFFECTS)
    return (
        f"🎭 QQ头像表情包 | V1:{total}种 V2:{total2}种\n"
        "━━━━━━━━━━━━━━━━━\n"
        "# V1 单人效果 (1个QQ)\n"
        "  /表情 QQ号             随机V1\n"
        "  /表情 @某人            随机V1\n"
        "  /表情 QQ号 效果名      指定效果\n"
        "  /表情 QQ号 42          按序号指定\n"
        "  /表情列表              第1页\n"
        "\n"
        "# V2 双人效果 (2个QQ)\n"
        "  /表情 QQ1 QQ2           随机V2\n"
        "  /表情 @A @B             随机V2\n"
        "  /表情 QQ1 QQ2 击剑      指定V2效果\n"
        "  /表情2列表              第1页\n"
        "\n"
        "  /表情更新               手动刷新效果\n"
        "  /表情帮助               看这个"
    )


def create_plugin() -> AvatarMemePlugin:
    return AvatarMemePlugin()
