package kz.valqauym.legends;

import org.bukkit.Bukkit;
import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.player.PlayerJoinEvent;
import org.bukkit.event.world.LootGenerateEvent;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.ShapedRecipe;

import java.util.*;

/**
 * Every weapon can be crafted: the base item in the middle and eight ingredients around it ("ABA / CXC / ABA").
 * recipes.mode in config.yml: hard (default, very expensive: nether stars, netherite, rare drops), easy (battle royale: iron, gold, diamonds) or off.
 * The weapons also drop (rarely) from the richest vanilla loot: ancient cities, bastion treasure, end cities and ominous vaults.
 */
final class Recipes implements Listener {
    private record Ring(Material a, Material b, Material c) { }
    private static final Map<String, Ring> HARD = new LinkedHashMap<>();
    static {
        HARD.put("crimson_fang", new Ring(Material.NETHERITE_INGOT, Material.NETHER_STAR, Material.GHAST_TEAR));
        HARD.put("inferno_scythe", new Ring(Material.NETHERITE_INGOT, Material.NETHER_STAR, Material.BLAZE_ROD));
        HARD.put("soul_staff", new Ring(Material.DIAMOND_BLOCK, Material.NETHER_STAR, Material.ECHO_SHARD));
        HARD.put("warden_mace", new Ring(Material.NETHERITE_INGOT, Material.HEAVY_CORE, Material.ECHO_SHARD));
        HARD.put("storm_trident", new Ring(Material.NETHERITE_INGOT, Material.NETHER_STAR, Material.ENCHANTED_GOLDEN_APPLE));
        HARD.put("thorn_blade", new Ring(Material.DIAMOND_BLOCK, Material.NETHER_STAR, Material.WITHER_ROSE));
        HARD.put("time_daggers", new Ring(Material.DIAMOND_BLOCK, Material.NETHER_STAR, Material.RECOVERY_COMPASS));
        HARD.put("umbral_knives", new Ring(Material.NETHERITE_INGOT, Material.NETHER_STAR, Material.DRAGON_BREATH));
        HARD.put("void_axe", new Ring(Material.NETHERITE_INGOT, Material.NETHER_STAR, Material.SHULKER_SHELL));
        HARD.put("frost_brand", new Ring(Material.DIAMOND_BLOCK, Material.NETHER_STAR, Material.BLUE_ICE));
        HARD.put("gale_blade", new Ring(Material.DIAMOND_BLOCK, Material.NETHER_STAR, Material.BREEZE_ROD));
        HARD.put("earth_hammer", new Ring(Material.NETHERITE_INGOT, Material.NETHER_STAR, Material.ANCIENT_DEBRIS));
        HARD.put("life_staff", new Ring(Material.DIAMOND_BLOCK, Material.NETHER_STAR, Material.TOTEM_OF_UNDYING));
    }
    private static final Ring EASY = new Ring(Material.GOLD_INGOT, Material.DIAMOND, Material.IRON_INGOT);

    private final LegendsPlugin plugin;
    private final List<NamespacedKey> keys = new ArrayList<>();
    private final Random rnd = new Random();

    Recipes(LegendsPlugin plugin) { this.plugin = plugin; register(); }

    /** (Re)register the recipes for the mode in the config. */
    void register() {
        for (NamespacedKey k : keys) Bukkit.removeRecipe(k);
        keys.clear();
        String mode = plugin.getConfig().getString("recipes.mode", "hard");
        if (mode.equalsIgnoreCase("off")) return;
        boolean easy = mode.equalsIgnoreCase("easy");
        for (Weapons.Def d : Weapons.ALL.values()) {
            ItemStack result = LegendsPlugin.create(d.id());
            Material base = Material.matchMaterial(d.material());
            if (result == null || base == null) continue;
            Ring r = easy ? EASY : HARD.get(d.id());
            NamespacedKey key = new NamespacedKey(plugin, "legend_" + d.id());
            ShapedRecipe sr = new ShapedRecipe(key, result);
            sr.shape("ABA", "CXC", "ABA");
            sr.setIngredient('A', r.a()); sr.setIngredient('B', r.b()); sr.setIngredient('C', r.c()); sr.setIngredient('X', base);
            Bukkit.addRecipe(sr);
            keys.add(key);
        }
    }

    /** Human readable recipe lines (for guides). */
    static String describe(String id, boolean easy) {
        Weapons.Def d = Weapons.ALL.get(id);
        Ring r = easy ? EASY : HARD.get(id);
        return d.name() + ": центр " + d.material().toLowerCase(Locale.ROOT) + "; углы 4× " + r.a().name().toLowerCase(Locale.ROOT)
                + ", сверху и снизу 2× " + r.b().name().toLowerCase(Locale.ROOT) + ", по бокам 2× " + r.c().name().toLowerCase(Locale.ROOT);
    }

    @EventHandler
    public void onJoin(PlayerJoinEvent e) { for (NamespacedKey k : keys) e.getPlayer().discoverRecipe(k); }

    @EventHandler
    public void onLoot(LootGenerateEvent e) {
        double chance = plugin.getConfig().getDouble("loot.chance", 0.04);
        if (chance <= 0 || e.getLootTable() == null) return;
        String t = e.getLootTable().getKey().getKey();
        if (!(t.contains("ancient_city") || t.contains("bastion_treasure") || t.contains("end_city_treasure") || t.contains("reward_ominous") || t.contains("stronghold_library"))) return;
        if (rnd.nextDouble() >= chance) return;
        List<String> ids = new ArrayList<>(Weapons.ALL.keySet());
        ItemStack w = LegendsPlugin.create(ids.get(rnd.nextInt(ids.size())));
        if (w != null) e.getLoot().add(w);
    }
}
