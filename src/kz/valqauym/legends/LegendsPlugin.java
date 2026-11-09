package kz.valqauym.legends;

import net.kyori.adventure.text.Component;
import net.kyori.adventure.text.format.NamedTextColor;
import net.kyori.adventure.text.format.TextColor;
import net.kyori.adventure.text.format.TextDecoration;
import org.bukkit.*;
import org.bukkit.attribute.Attribute;
import org.bukkit.attribute.AttributeModifier;
import org.bukkit.command.*;
import org.bukkit.entity.LivingEntity;
import org.bukkit.entity.Player;
import org.bukkit.event.EventHandler;
import org.bukkit.event.Listener;
import org.bukkit.event.block.Action;
import org.bukkit.event.entity.EntityDamageByEntityEvent;
import org.bukkit.event.inventory.InventoryClickEvent;
import org.bukkit.event.player.PlayerInteractEvent;
import org.bukkit.inventory.EquipmentSlot;
import org.bukkit.inventory.EquipmentSlotGroup;
import org.bukkit.inventory.Inventory;
import org.bukkit.inventory.InventoryHolder;
import org.bukkit.inventory.ItemFlag;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.ItemMeta;
import org.bukkit.persistence.PersistentDataType;
import org.bukkit.plugin.java.JavaPlugin;

import java.util.*;

/**
 * ValqLegends: 13 legendary weapons with a passive, a primary (right click) and a secondary (sneak + right click) ability.
 * Works on its own; other plugins (the ValqCore battle royale / admin panel) can use {@link #create(String)} and {@link #ids()}.
 * Commands: /legend give &lt;id&gt; [player], /legend list, /legend gui, /legend reload.
 */
public final class LegendsPlugin extends JavaPlugin implements Listener, TabExecutor {
    private static LegendsPlugin instance;
    private NamespacedKey key;
    private Abilities abilities;
    private final Map<String, Long> cooldown = new HashMap<>();

    @Override public void onEnable() {
        instance = this;
        saveDefaultConfig();
        key = new NamespacedKey(this, "legend");
        abilities = new Abilities(this);
        getServer().getPluginManager().registerEvents(this, this);
        getCommand("legend").setExecutor(this);
        getCommand("legend").setTabCompleter(this);
        Bukkit.getScheduler().runTaskTimer(this, () -> {
            for (Player p : Bukkit.getOnlinePlayers()) {
                Weapons.Def d = defOf(p.getInventory().getItemInMainHand());
                if (d != null) abilities.held(p, d);
            }
        }, 20L, 10L);
    }

    // ------------------------------------------------------------------ public API
    /** A fresh item of the weapon, or null for an unknown id. */
    public static ItemStack create(String id) { return instance == null ? null : instance.build(Weapons.ALL.get(id)); }
    public static Set<String> ids() { return Collections.unmodifiableSet(Weapons.ALL.keySet()); }
    public static String idOf(ItemStack it) { Weapons.Def d = instance == null ? null : instance.defOf(it); return d == null ? null : d.id(); }

    // ------------------------------------------------------------------ items
    private ItemStack build(Weapons.Def d) {
        if (d == null) return null;
        Material m = Material.matchMaterial(d.material());
        if (m == null) m = Material.IRON_SWORD;
        ItemStack it = new ItemStack(m);
        ItemMeta im = it.getItemMeta();
        TextColor c = TextColor.fromHexString(d.color());
        im.displayName(Component.text(d.name(), c, TextDecoration.BOLD).decoration(TextDecoration.ITALIC, false));
        List<Component> lore = new ArrayList<>();
        lore.add(line("Легендарное оружие", NamedTextColor.GOLD));
        lore.add(Component.empty());
        if (!d.passive().equals("—")) lore.add(line("◆ " + d.passive(), NamedTextColor.GRAY));
        lore.add(line("▶ ПКМ: " + d.primary() + " (" + d.cdPrimary() + " с)", NamedTextColor.GREEN));
        lore.add(line("⇧▶ Shift+ПКМ: " + d.secondary() + " (" + d.cdSecondary() + " с)", NamedTextColor.AQUA));
        im.lore(lore);
        im.setUnbreakable(true);
        im.setCustomModelData(d.model());
        im.addItemFlags(ItemFlag.HIDE_UNBREAKABLE, ItemFlag.HIDE_ATTRIBUTES);
        NamespacedKey ak = new NamespacedKey(this, "dmg_" + d.id());
        im.addAttributeModifier(Attribute.ATTACK_DAMAGE, new AttributeModifier(ak, d.damage() - 1, AttributeModifier.Operation.ADD_NUMBER, EquipmentSlotGroup.MAINHAND));
        im.addAttributeModifier(Attribute.ATTACK_SPEED, new AttributeModifier(new NamespacedKey(this, "spd_" + d.id()), d.speed() + 4 > 0 ? d.speed() : -3.9,
                AttributeModifier.Operation.ADD_NUMBER, EquipmentSlotGroup.MAINHAND));
        if (d.health() > 0)
            im.addAttributeModifier(Attribute.MAX_HEALTH, new AttributeModifier(new NamespacedKey(this, "hp_" + d.id()), d.health(), AttributeModifier.Operation.ADD_NUMBER, EquipmentSlotGroup.MAINHAND));
        im.getPersistentDataContainer().set(key, PersistentDataType.STRING, d.id());
        it.setItemMeta(im);
        return it;
    }

    private static Component line(String s, NamedTextColor c) { return Component.text(s, c).decoration(TextDecoration.ITALIC, false); }

    private Weapons.Def defOf(ItemStack it) {
        if (it == null || !it.hasItemMeta()) return null;
        String id = it.getItemMeta().getPersistentDataContainer().get(key, PersistentDataType.STRING);
        return id == null ? null : Weapons.ALL.get(id);
    }

    // ------------------------------------------------------------------ events
    @EventHandler
    public void onUse(PlayerInteractEvent e) {
        if (e.getHand() != EquipmentSlot.HAND || (e.getAction() != Action.RIGHT_CLICK_AIR && e.getAction() != Action.RIGHT_CLICK_BLOCK)) return;
        Player p = e.getPlayer();
        Weapons.Def d = defOf(p.getInventory().getItemInMainHand());
        if (d == null) return;
        e.setCancelled(true);
        boolean sec = p.isSneaking();
        String k = p.getUniqueId() + d.id() + (sec ? "2" : "1");
        long now = System.currentTimeMillis(), until = cooldown.getOrDefault(k, 0L);
        if (now < until) {
            p.sendActionBar(Component.text("Перезарядка: " + ((until - now) / 1000 + 1) + " с", NamedTextColor.RED));
            return;
        }
        if (p.getGameMode() == GameMode.SPECTATOR) return;
        cooldown.put(k, now + (sec ? d.cdSecondary() : d.cdPrimary()) * 1000L);
        abilities.use(p, d, sec);
        p.sendActionBar(Component.text((sec ? d.secondary() : d.primary()).split(":")[0], TextColor.fromHexString(d.color())));
    }

    @EventHandler
    public void onHit(EntityDamageByEntityEvent e) {
        if (!(e.getDamager() instanceof Player p) || !(e.getEntity() instanceof LivingEntity t)) return;
        Weapons.Def d = defOf(p.getInventory().getItemInMainHand());
        if (d != null) abilities.onHit(p, d, t, e.getFinalDamage());
    }

    // ------------------------------------------------------------------ commands / menu
    private static final class Menu implements InventoryHolder {
        Inventory inv; @Override public Inventory getInventory() { return inv; }
    }

    private void gui(Player p) {
        Menu m = new Menu();
        m.inv = Bukkit.createInventory(m, 18, Component.text("Легендарное оружие"));
        int i = 0;
        for (String id : Weapons.ALL.keySet()) m.inv.setItem(i++, create(id));
        p.openInventory(m.inv);
    }

    @EventHandler
    public void onClick(InventoryClickEvent e) {
        if (!(e.getView().getTopInventory().getHolder() instanceof Menu)) return;
        e.setCancelled(true);
        if (e.getWhoClicked() instanceof Player p && p.hasPermission("legends.admin") && e.getClickedInventory() == e.getView().getTopInventory() && e.getCurrentItem() != null)
            p.getInventory().addItem(e.getCurrentItem().clone());
    }

    @Override
    public boolean onCommand(CommandSender s, Command c, String l, String[] a) {
        String sub = a.length == 0 ? "list" : a[0].toLowerCase(Locale.ROOT);
        if (!s.hasPermission("legends.admin")) { s.sendMessage(Component.text("Нет прав", NamedTextColor.RED)); return true; }
        switch (sub) {
            case "give" -> {
                if (a.length < 2) { s.sendMessage("/legend give <id> [игрок]"); return true; }
                Player t = a.length > 2 ? Bukkit.getPlayerExact(a[2]) : (s instanceof Player pl ? pl : null);
                ItemStack it = create(a[1]);
                if (t == null || it == null) { s.sendMessage(Component.text("Неизвестный id или игрок", NamedTextColor.RED)); return true; }
                t.getInventory().addItem(it);
                s.sendMessage(Component.text("Выдано: " + a[1] + " → " + t.getName(), NamedTextColor.GREEN));
            }
            case "gui" -> { if (s instanceof Player p) gui(p); }
            case "reload" -> { reloadConfig(); s.sendMessage(Component.text("Перезагружено", NamedTextColor.GREEN)); }
            default -> {
                s.sendMessage(Component.text("Легендарное оружие:", NamedTextColor.GOLD));
                for (Weapons.Def d : Weapons.ALL.values()) s.sendMessage(Component.text(" " + d.id() + " — " + d.name(), TextColor.fromHexString(d.color())));
            }
        }
        return true;
    }

    @Override
    public List<String> onTabComplete(CommandSender s, Command c, String l, String[] a) {
        if (a.length == 1) return List.of("give", "list", "gui", "reload");
        if (a.length == 2 && a[0].equalsIgnoreCase("give")) return new ArrayList<>(Weapons.ALL.keySet());
        return List.of();
    }
}
