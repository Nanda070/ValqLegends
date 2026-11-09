#!/usr/bin/env python3
"""ValqLegends pack from existing 3D weapon packs (the server owner's choice): picks one model per weapon out of
'Blades of Majestica' and 'Zerotekz's Blades of War 2', copies the models and the textures they need, and writes
our own item definitions (assets/valqlegends/items/<id>.json) so the weapons use them through the item_model component.
Vanilla items stay untouched (the source packs' own overrides are NOT copied).

usage: python bundle.py <majestica.zip> <bladesofwar2.zip> <hunting-rifle-crossbow.zip> <out.zip>
"""
import hashlib, json, re, sys, zipfile

MAJ, BOW, RIFLE, OUT = sys.argv[1:5]
zm, zb, zr = zipfile.ZipFile(MAJ), zipfile.ZipFile(BOW), zipfile.ZipFile(RIFLE)

# weapon id -> (source, model path inside assets/minecraft/models/item/, kind)
PICK = {
    "crimson_fang": ("m", "bloodedge"), "inferno_scythe": ("b", "swords/crimson_scythe"), "soul_staff": ("m", "soul_collector"),
    "warden_mace": ("m", "sculkcleaver"), "storm_trident": ("m", "thunderbringer"), "thorn_blade": ("m", "bramblethorn"),
    "time_daggers": ("m", "chrono_blade"), "umbral_knives": ("m", "death_knight_dagger"), "void_axe": ("m", "demonlordsgreataxe"),
    "frost_brand": ("m", "frostblade"), "gale_blade": ("m", "whisperwind"), "earth_hammer": ("m", "mjolnir"),
    "life_staff": ("m", "forest_guardian_glaive"), "lunar_katana": ("m", "holymoonlightsword"), "blaze_cleaver": ("m", "emberblade"),
    "venom_fang": ("b", "swords/venom_fang_new"), "star_wand": ("m", "stars_edge"), "reaper_scythe": ("m", "abominablescythe"),
    "solar_bow": ("b", "bows/angelic_bow"), "abyss_crossbow": ("r", "abyss_crossbow"),
}

out = zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED)
written = set()


def put(name, data):
    if name in written: return
    written.add(name); out.writestr(name, data)


def src(kind): return zm if kind == "m" else zb if kind == "b" else zr


def model_path(n): return f"assets/minecraft/models/item/{n}.json"


def grow(j, f=1.2):
    d = j.setdefault("display", {})
    for k in ("thirdperson_righthand", "thirdperson_lefthand", "firstperson_righthand", "firstperson_lefthand"):
        t = d.setdefault(k, {"rotation": [0, 0, 0], "translation": [0, 0, 0], "scale": [1, 1, 1]})
        t["scale"] = [round(v * f, 3) for v in t.get("scale", [1, 1, 1])]


def need_model(kind, rel):
    """copy a model (and its parents / textures) from the source pack, rel like 'swords/xxx' (under models/item)."""
    z = src(kind); path = model_path(rel)
    try: raw = z.read(path)
    except KeyError: raise SystemExit(f"missing model {kind}:{rel}")
    j = json.loads(raw.decode("utf-8-sig"))
    grow(j)
    put(path, json.dumps(j))
    for t in (j.get("textures") or {}).values():
        if t.startswith("#"): continue
        tp = t.replace("minecraft:", "")
        for ext in (".png", ".png.mcmeta"):
            try: put(f"assets/minecraft/textures/{tp}{ext}", z.read(f"assets/minecraft/textures/{tp}{ext}"))
            except KeyError:
                if ext == ".png": print("  texture not found:", kind, tp)
    par = j.get("parent", "")
    if par.startswith("minecraft:item/") or par.startswith("item/"):
        pr = par.split("item/", 1)[1]
        if pr not in ("generated", "handheld", "handheld_rod", "handheld_mace") and f"assets/minecraft/models/item/{pr}.json" in z.namelist(): need_model(kind, pr)


def refs(node):
    """all model references in an item definition tree."""
    if isinstance(node, dict):
        if node.get("type") == "minecraft:model": yield node["model"]
        for v in node.values(): yield from refs(v)
    elif isinstance(node, list):
        for v in node: yield from refs(v)


def case_tree(z, item_file, display_name):
    d = json.loads(z.read(f"assets/minecraft/items/{item_file}.json").decode("utf-8-sig"))
    for c in d["model"].get("cases", []):
        w = c["when"]
        if (w if isinstance(w, str) else w[0]).lower() == display_name.lower(): return c["model"]
    raise SystemExit(f"no case {display_name} in {item_file}")


for wid, (kind, rel) in PICK.items():
    if rel.startswith("bows/"):
        tree = case_tree(zb, "bow", "Angelic Bow")
        for r in set(refs(tree)): need_model("b", r.replace("minecraft:item/", ""))
        put(f"assets/valqlegends/items/{wid}.json", json.dumps({"model": tree}))
    elif kind == "r":     # a real crossbow model (Hunting rifle crossbow): renamed so that it does not replace the vanilla crossbow
        j = json.loads(zr.read("assets/minecraft/models/item/crossbow.json").decode("utf-8-sig"))
        j["textures"] = {"0": "item/legend_rifle_crossbow", "particle": "item/legend_rifle_crossbow"}
        grow(j)
        put("assets/minecraft/models/item/legend_rifle_crossbow.json", json.dumps(j))
        put("assets/minecraft/textures/item/legend_rifle_crossbow.png", zr.read("assets/minecraft/textures/item/crossbow.png"))
        put(f"assets/valqlegends/items/{wid}.json", json.dumps({"model": {"type": "minecraft:model", "model": "minecraft:item/legend_rifle_crossbow"}}))
    else:
        need_model(kind, rel)
        put(f"assets/valqlegends/items/{wid}.json", json.dumps({"model": {"type": "minecraft:model", "model": f"minecraft:item/{rel}"}}))

put("pack.mcmeta", json.dumps({"pack": {"description": "ValqLegends: 3D legendary weapons (models by Blades of Majestica and Zerotekz)", "min_format": 75, "max_format": 79}}))
put("CREDITS.txt", "Models and textures: 'Blades of Majestica', \"Zerotekz's Blades of War 2\" and 'Hunting rifle crossbow' (Modrinth). Used by the server owner's decision for the VALQAUYM server.\n")
out.close()
print("pack", OUT, "files", len(written), "sha1", hashlib.sha1(open(OUT, "rb").read()).hexdigest())
