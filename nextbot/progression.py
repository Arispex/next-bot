from __future__ import annotations

PROGRESSION_TIERS: list[tuple[str, str]] = [
    ("kingSlime", "史莱姆王"),
    ("eyeOfCthulhu", "克苏鲁之眼"),
    ("eaterOfWorldsOrBrainOfCthulhu", "世界吞噬者/克苏鲁之脑"),
    ("queenBee", "蜂后"),
    ("skeletron", "骷髅王"),
    ("deerclops", "独眼鹿怪"),
    ("wallOfFlesh", "血肉墙"),
    ("queenSlime", "史莱姆王后"),
    ("theTwins", "双子魔眼"),
    ("theDestroyer", "毁灭者"),
    ("skeletronPrime", "机械骷髅王"),
    ("plantera", "世纪之花"),
    ("golem", "石巨人"),
    ("dukeFishron", "猪龙鱼公爵"),
    ("empressOfLight", "光之女皇"),
    ("lunaticCultist", "邪教徒"),
    ("solarPillar", "日耀柱"),
    ("nebulaPillar", "星云柱"),
    ("vortexPillar", "漩涡柱"),
    ("stardustPillar", "星尘柱"),
    ("moonLord", "月亮领主"),
]

TIER_NONE = "none"
TIER_NONE_ZH = "无"

PROGRESSION_KEY_TO_ZH: dict[str, str] = dict(PROGRESSION_TIERS)
PROGRESSION_KEY_TO_ZH[TIER_NONE] = TIER_NONE_ZH
PROGRESSION_ZH_TO_KEY: dict[str, str] = {zh: key for key, zh in PROGRESSION_TIERS}
PROGRESSION_ZH_TO_KEY[TIER_NONE_ZH] = TIER_NONE
PROGRESSION_RANK: dict[str, int] = {key: i for i, (key, _) in enumerate(PROGRESSION_TIERS)}
PROGRESSION_RANK[TIER_NONE] = -1

# Tier options surfaced in dropdowns: 无 first, then 21 boss tiers in order
TIER_OPTIONS: list[tuple[str, str]] = [(TIER_NONE, TIER_NONE_ZH)] + PROGRESSION_TIERS


def parse_tier(raw: str) -> str | None:
    s = str(raw or "").strip()
    if not s:
        return None
    # Accept several aliases for "no requirement"
    if s in {TIER_NONE, TIER_NONE_ZH, "无要求", "None", "NONE"}:
        return TIER_NONE
    if s in PROGRESSION_KEY_TO_ZH:
        return s
    if s in PROGRESSION_ZH_TO_KEY:
        return PROGRESSION_ZH_TO_KEY[s]
    return None


def tier_zh(key: str) -> str:
    return PROGRESSION_KEY_TO_ZH.get(key, key)
