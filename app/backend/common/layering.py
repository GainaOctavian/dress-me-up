"""Layering model (plan 11): what each garment type is, where it sits on the
body and in which order layers are drawn. Single source of truth for the API,
the worker (CLIP prompts) and the app (served by GET /meta/layering)."""
from enum import Enum
from typing import Dict, List, NamedTuple, Optional

FORMAT = 1


class Slot(str, Enum):
    HEAD = "head"
    EYES = "eyes"
    NECK = "neck"
    TORSO = "torso"
    FULL = "full"      # dress / jumpsuit: torso + legs
    WAIST = "waist"
    LEGS = "legs"
    FEET = "feet"
    WRIST = "wrist"
    HANDS = "hands"
    BAG = "bag"


class Role(str, Enum):
    BASE = "base"              # tights, undershirt, socks
    MID = "mid"                # shirt, trousers, shoes
    INSULATION = "insulation"  # sweater, hoodie
    OUTER = "outer"            # blazer, jacket
    OVER = "over"              # coat, parka; scarf over everything
    ACCESSORY = "accessory"


class Sub(NamedTuple):
    category: str      # one of models.ItemCategory values
    slot: Slot
    role: Role
    label: str         # shown in the app
    prompt: str        # CLIP text ("a product photo of ...")
    tucked: bool = False  # default for tops: drawn under the trousers


S, R = Slot, Role
SUBCATEGORIES: Dict[str, Sub] = {
    # tops
    "tank_top": Sub("top", S.TORSO, R.BASE, "Tank top", "a tank top", True),
    "undershirt": Sub("top", S.TORSO, R.BASE, "Undershirt", "a white undershirt", True),
    "t_shirt": Sub("top", S.TORSO, R.MID, "T-shirt", "a t-shirt"),
    "shirt": Sub("top", S.TORSO, R.MID, "Shirt", "a button-up shirt", True),
    "polo": Sub("top", S.TORSO, R.MID, "Polo", "a polo shirt"),
    "blouse": Sub("top", S.TORSO, R.MID, "Blouse", "a blouse", True),
    "sweater": Sub("top", S.TORSO, R.INSULATION, "Sweater", "a knit sweater"),
    "hoodie": Sub("top", S.TORSO, R.INSULATION, "Hoodie", "a hoodie"),
    "cardigan": Sub("top", S.TORSO, R.INSULATION, "Cardigan", "a cardigan"),
    "sweatshirt": Sub("top", S.TORSO, R.INSULATION, "Sweatshirt", "a sweatshirt"),
    # outerwear
    "blazer": Sub("outerwear", S.TORSO, R.OUTER, "Blazer", "a blazer suit jacket"),
    "jacket": Sub("outerwear", S.TORSO, R.OUTER, "Jacket", "a casual jacket"),
    "denim_jacket": Sub("outerwear", S.TORSO, R.OUTER, "Denim jacket", "a denim jacket"),
    "leather_jacket": Sub("outerwear", S.TORSO, R.OUTER, "Leather jacket", "a leather jacket"),
    "bomber": Sub("outerwear", S.TORSO, R.OUTER, "Bomber", "a bomber jacket"),
    "gilet": Sub("outerwear", S.TORSO, R.OUTER, "Gilet", "a sleeveless gilet vest"),
    "coat": Sub("outerwear", S.TORSO, R.OVER, "Coat", "a long wool coat"),
    "parka": Sub("outerwear", S.TORSO, R.OVER, "Parka", "a parka with a hood"),
    "trench": Sub("outerwear", S.TORSO, R.OVER, "Trench coat", "a trench coat"),
    "puffer": Sub("outerwear", S.TORSO, R.OVER, "Puffer", "a puffer jacket"),
    # bottoms
    "tights": Sub("bottom", S.LEGS, R.BASE, "Tights", "a pair of tights"),
    "leggings": Sub("bottom", S.LEGS, R.BASE, "Leggings", "a pair of leggings"),
    "jeans": Sub("bottom", S.LEGS, R.MID, "Jeans", "a pair of jeans"),
    "trousers": Sub("bottom", S.LEGS, R.MID, "Trousers", "a pair of trousers"),
    "chinos": Sub("bottom", S.LEGS, R.MID, "Chinos", "a pair of chino pants"),
    "sweatpants": Sub("bottom", S.LEGS, R.MID, "Sweatpants", "a pair of sweatpants"),
    "shorts": Sub("bottom", S.LEGS, R.MID, "Shorts", "a pair of shorts"),
    "skirt": Sub("bottom", S.LEGS, R.MID, "Skirt", "a skirt"),
    # one-pieces
    "dress": Sub("dress", S.FULL, R.MID, "Dress", "a dress"),
    "jumpsuit": Sub("dress", S.FULL, R.MID, "Jumpsuit", "a jumpsuit"),
    # footwear
    "socks": Sub("shoes", S.FEET, R.BASE, "Socks", "a pair of socks"),
    "sneakers": Sub("shoes", S.FEET, R.MID, "Sneakers", "a pair of sneakers"),
    "boots": Sub("shoes", S.FEET, R.MID, "Boots", "a pair of boots"),
    "dress_shoes": Sub("shoes", S.FEET, R.MID, "Dress shoes", "formal leather dress shoes"),
    "loafers": Sub("shoes", S.FEET, R.MID, "Loafers", "a pair of loafers"),
    "sandals": Sub("shoes", S.FEET, R.MID, "Sandals", "a pair of sandals"),
    "heels": Sub("shoes", S.FEET, R.MID, "Heels", "a pair of high heels"),
    # accessories
    "hat": Sub("accessory", S.HEAD, R.ACCESSORY, "Hat", "a hat"),
    "cap": Sub("accessory", S.HEAD, R.ACCESSORY, "Cap", "a baseball cap"),
    "beanie": Sub("accessory", S.HEAD, R.ACCESSORY, "Beanie", "a knit beanie"),
    "glasses": Sub("accessory", S.EYES, R.ACCESSORY, "Glasses", "a pair of glasses"),
    "sunglasses": Sub("accessory", S.EYES, R.ACCESSORY, "Sunglasses", "a pair of sunglasses"),
    "tie": Sub("accessory", S.NECK, R.MID, "Tie", "a necktie"),
    "bow_tie": Sub("accessory", S.NECK, R.MID, "Bow tie", "a bow tie"),
    "necklace": Sub("accessory", S.NECK, R.BASE, "Necklace", "a necklace"),
    "scarf": Sub("accessory", S.NECK, R.OVER, "Scarf", "a scarf"),
    "belt": Sub("accessory", S.WAIST, R.ACCESSORY, "Belt", "a leather belt"),
    "watch": Sub("accessory", S.WRIST, R.ACCESSORY, "Watch", "a wristwatch"),
    "bracelet": Sub("accessory", S.WRIST, R.ACCESSORY, "Bracelet", "a bracelet"),
    "gloves": Sub("accessory", S.HANDS, R.ACCESSORY, "Gloves", "a pair of gloves"),
    "bag": Sub("accessory", S.BAG, R.ACCESSORY, "Bag", "a handbag"),
    "backpack": Sub("accessory", S.BAG, R.ACCESSORY, "Backpack", "a backpack"),
}

Subcategory = Enum("Subcategory", {k.upper(): k for k in SUBCATEGORIES}, type=str)

# Draw order, bottom to top. A (slot, role) band; gaps leave room for
# special cases (tucked tops, trousers tucked into boots).
BANDS: Dict[str, int] = {
    "bag.accessory": 0,
    "legs.base": 10,     # tights under everything on the legs
    "feet.base": 15,     # socks
    "torso.base": 20,    # undershirt
    # 25: tucked tops (under the trousers)
    # 27: trousers tucked into boots (under the shoes)
    "feet.mid": 28,      # shoes; trousers cover their tops by default
    "legs.mid": 30,      # trousers, shorts, skirt
    "full.mid": 32,      # dress
    "waist.accessory": 35,  # belt: over trousers, tucked tops and dresses;
                            # under an untucked top, which hides it
    "torso.mid": 40,     # t-shirt, shirt (untucked)
    "neck.base": 42,     # necklace
    "neck.mid": 45,      # tie: over the shirt, under knitwear and jackets
    "torso.insulation": 50,
    "torso.outer": 60,
    "torso.over": 70,
    "neck.over": 75,     # scarf over the coat
    "wrist.accessory": 80,
    "hands.accessory": 80,
    "eyes.accessory": 85,
    "head.accessory": 90,
}
TUCKED_BAND = 25
INTO_SHOES_BAND = 27


def band(subcategory: Optional[str]) -> Optional[int]:
    sub = SUBCATEGORIES.get(subcategory or "")
    return BANDS.get(f"{sub.slot.value}.{sub.role.value}") if sub else None


class Placed(NamedTuple):
    """What the sort needs about one outfit item."""
    subcategory: Optional[str]
    tucked: Optional[bool] = None       # tops; None = subcategory default
    into_shoes: bool = False            # trousers tucked into boots/shoes
    layer_offset: int = 0               # manual reorder within the band


def z_of(p: Placed) -> int:
    sub = SUBCATEGORIES.get(p.subcategory or "")
    b = band(p.subcategory)
    if sub is None or b is None:
        return 50  # unknown type: middle of the stack
    if sub.slot == Slot.TORSO and sub.role in (Role.BASE, Role.MID, Role.INSULATION):
        tucked = sub.tucked if p.tucked is None else p.tucked
        if tucked and sub.role != Role.BASE:
            return TUCKED_BAND
    if sub.slot == Slot.LEGS and sub.role == Role.MID and p.into_shoes:
        return INTO_SHOES_BAND
    return b


def draw_order(items: List[Placed]) -> List[int]:
    """Indices of `items` bottom to top. Stable: ties keep list order."""
    return sorted(range(len(items)), key=lambda i: (z_of(items[i]), items[i].layer_offset, i))


def warnings(subcategories: List[Optional[str]]) -> List[str]:
    """Soft checks shown in the editor; never blocking."""
    subs = [SUBCATEGORIES[s] for s in subcategories if s in SUBCATEGORIES]
    out = []
    count = lambda pred: sum(1 for s in subs if pred(s))
    if count(lambda s: s.slot == Slot.FULL) and count(lambda s: s.slot == Slot.LEGS and s.role == Role.MID):
        out.append("A dress with trousers or a skirt")
    if count(lambda s: s.slot == Slot.TORSO and s.role == Role.OVER) > 1:
        out.append("More than one coat")
    if count(lambda s: s.slot == Slot.FEET and s.role == Role.MID) > 1:
        out.append("More than one pair of shoes")
    if count(lambda s: s.slot == Slot.LEGS and s.role == Role.MID) > 1:
        out.append("More than one pair of trousers/shorts/skirt")
    if count(lambda s: s.slot == Slot.HEAD) > 1:
        out.append("More than one hat")
    return out


def as_json() -> dict:
    """Served to the app (GET /meta/layering)."""
    return {
        "format": FORMAT,
        "subcategories": {
            k: {"category": v.category, "slot": v.slot.value, "role": v.role.value,
                "label": v.label, "tucked_default": v.tucked, "band": band(k)}
            for k, v in SUBCATEGORIES.items()
        },
        "bands": BANDS,
        "tucked_band": TUCKED_BAND,
        "into_shoes_band": INTO_SHOES_BAND,
    }


if __name__ == "__main__":
    # self-check: the classic stacks from plan 11
    def order(*specs):
        items = [Placed(*s) if isinstance(s, tuple) else Placed(s) for s in specs]
        return [items[i].subcategory for i in draw_order(items)]

    assert order("shorts", "tights") == ["tights", "shorts"]
    assert order("belt", "trousers", "shirt") == ["shirt", "trousers", "belt"]          # tucked shirt
    assert order("belt", "trousers", ("shirt", False)) == ["trousers", "belt", "shirt"]  # untucked hides belt
    assert order("scarf", "coat", "blazer", "sweater", "tie", "shirt") == \
        ["shirt", "tie", "sweater", "blazer", "coat", "scarf"]
    assert order("sneakers", "socks") == ["socks", "sneakers"]
    assert order("boots", "jeans") == ["boots", "jeans"]                                  # jeans over boots
    assert order(("jeans", None, True), "boots") == ["jeans", "boots"]                    # tucked into boots
    assert order("t_shirt", "jeans") == ["jeans", "t_shirt"]                              # tee untucked by default
    assert order("dress", "tights", "coat") == ["tights", "dress", "coat"]
    assert order("belt", "dress") == ["dress", "belt"]
    assert order("cap", "sunglasses", "watch", "hoodie") == ["hoodie", "watch", "sunglasses", "cap"]
    assert order(("coat", None, False, 1), ("parka", None, False, 0)) == ["parka", "coat"]  # manual order
    assert warnings(["dress", "jeans"]) == ["A dress with trousers or a skirt"]
    assert warnings(["shirt", "jeans", "sneakers"]) == []
    assert all(v.category in {"top", "bottom", "dress", "outerwear", "shoes", "accessory"}
               for v in SUBCATEGORIES.values())
    print("layering ok:", len(SUBCATEGORIES), "subcategories")
