package kz.valqauym.legends;

import org.bukkit.*;
import org.bukkit.attribute.Attribute;
import org.bukkit.entity.*;
import org.bukkit.potion.PotionEffect;
import org.bukkit.potion.PotionEffectType;
import org.bukkit.util.Vector;

import java.util.*;

/** What each weapon does. All effects are cosmetic on blocks: nothing is broken or set on fire in the world. */
final class Abilities {
    private final LegendsPlugin plugin;
    private final Map<UUID, ArrayDeque<double[]>> trail = new HashMap<>();   // last seconds of position + health for the time dagger

    Abilities(LegendsPlugin plugin) {
        this.plugin = plugin;
        Bukkit.getScheduler().runTaskTimer(plugin, this::sample, 20L, 20L);
    }

    private void sample() {
        for (Player p : Bukkit.getOnlinePlayers()) {
            var q = trail.computeIfAbsent(p.getUniqueId(), k -> new ArrayDeque<>());
            Location l = p.getLocation();
            q.addLast(new double[]{l.getX(), l.getY(), l.getZ(), l.getYaw(), l.getPitch(), p.getHealth()});
            while (q.size() > 6) q.pollFirst();
        }
    }

    // ------------------------------------------------------------------ helpers
    private static List<LivingEntity> near(Player p, double r) {
        List<LivingEntity> out = new ArrayList<>();
        for (Entity e : p.getNearbyEntities(r, r, r)) if (e instanceof LivingEntity le && !(e instanceof ArmorStand) && e != p) out.add(le);
        return out;
    }
    private static void hurt(LivingEntity t, Player by, double dmg) { t.damage(dmg, by); }
    private static void heal(Player p, double hearts) {
        double max = p.getAttribute(Attribute.MAX_HEALTH).getValue();
        p.setHealth(Math.min(max, p.getHealth() + hearts * 2));
    }
    private static Location aim(Player p, int range) {
        var r = p.getWorld().rayTraceBlocks(p.getEyeLocation(), p.getEyeLocation().getDirection(), range);
        return r != null && r.getHitPosition() != null ? r.getHitPosition().toLocation(p.getWorld()) : p.getEyeLocation().add(p.getEyeLocation().getDirection().multiply(range));
    }
    private static void burst(Location l, Particle pt, int n, double spread, Material block) { l.getWorld().spawnParticle(pt, l, n, spread, spread, spread, 0.02, block.createBlockData()); }
    private static void burst(Location l, Particle pt, int n, double spread) { l.getWorld().spawnParticle(pt, l, n, spread, spread, spread, 0.02); }

    /** A short run of particles along the line of sight (visual only). */
    private static void beam(Player p, Particle pt, double len) {
        Location s = p.getEyeLocation(); Vector d = s.getDirection();
        for (double i = 1; i < len; i += 0.5) s.getWorld().spawnParticle(pt, s.clone().add(d.clone().multiply(i)), 1, 0, 0, 0, 0);
    }

    // ------------------------------------------------------------------ dispatcher
    void use(Player p, Weapons.Def d, boolean secondary) {
        switch (d.id() + (secondary ? ":2" : ":1")) {
            case "crimson_fang:1" -> dash(p, 8, 9, Particle.DAMAGE_INDICATOR);
            case "crimson_fang:2" -> { for (LivingEntity t : near(p, 8)) { t.addPotionEffect(new PotionEffect(PotionEffectType.WITHER, 100, 1)); burst(t.getLocation().add(0, 1, 0), Particle.DAMAGE_INDICATOR, 12, 0.4); } p.playSound(p, Sound.ENTITY_WITHER_SPAWN, 0.4f, 1.6f); }
            case "inferno_scythe:1" -> cone(p, 7, 6, Particle.FLAME);
            case "inferno_scythe:2" -> meteor(p);
            case "soul_staff:1" -> bolt(p);
            case "soul_staff:2" -> { for (LivingEntity t : near(p, 30)) t.addPotionEffect(new PotionEffect(PotionEffectType.GLOWING, 160, 0)); burst(p.getLocation().add(0, 1, 0), Particle.SOUL, 40, 1.5); p.playSound(p, Sound.PARTICLE_SOUL_ESCAPE, 1f, 1f); }
            case "warden_mace:1" -> slam(p, 6, 8, false);
            case "warden_mace:2" -> { p.addPotionEffect(new PotionEffect(PotionEffectType.ABSORPTION, 120, 3)); burst(p.getLocation().add(0, 1, 0), Particle.SCULK_SOUL, 30, 0.8); p.playSound(p, Sound.BLOCK_BEACON_ACTIVATE, 1f, 0.7f); }
            case "storm_trident:1" -> chain(p);
            case "storm_trident:2" -> storm(p);
            case "thorn_blade:1" -> pull(p, 1);
            case "thorn_blade:2" -> { LivingEntity t = target(p, 25); if (t != null) { t.addPotionEffect(new PotionEffect(PotionEffectType.POISON, 120, 2)); hurt(t, p, 6); burst(t.getLocation(), Particle.COMPOSTER, 25, 0.5); } }
            case "time_daggers:1" -> { LivingEntity t = target(p, 25); if (t != null) { t.addPotionEffect(new PotionEffect(PotionEffectType.SLOWNESS, 60, 9)); t.addPotionEffect(new PotionEffect(PotionEffectType.WEAKNESS, 60, 4)); burst(t.getLocation().add(0, 1, 0), Particle.END_ROD, 30, 0.5); p.playSound(p, Sound.BLOCK_BELL_USE, 1f, 0.5f); } }
            case "time_daggers:2" -> rewind(p);
            case "umbral_knives:1" -> blink(p, 12, Particle.PORTAL);
            case "umbral_knives:2" -> volley(p);
            case "void_axe:1" -> { for (LivingEntity t : near(p, 8)) t.setVelocity(p.getLocation().toVector().subtract(t.getLocation().toVector()).normalize().multiply(1.3).setY(0.35)); burst(p.getLocation().add(0, 1, 0), Particle.REVERSE_PORTAL, 60, 2); }
            case "void_axe:2" -> blink(p, 10, Particle.REVERSE_PORTAL);
            case "frost_brand:1" -> { for (LivingEntity t : near(p, 6)) { t.addPotionEffect(new PotionEffect(PotionEffectType.SLOWNESS, 100, 3)); hurt(t, p, 5); } burst(p.getLocation().add(0, 1, 0), Particle.SNOWFLAKE, 80, 3); p.playSound(p, Sound.BLOCK_GLASS_BREAK, 1f, 0.6f); }
            case "frost_brand:2" -> { p.addPotionEffect(new PotionEffect(PotionEffectType.SPEED, 100, 2)); p.addPotionEffect(new PotionEffect(PotionEffectType.SLOW_FALLING, 100, 0)); burst(p.getLocation(), Particle.SNOWFLAKE, 30, 0.6); }
            case "gale_blade:1" -> { p.setVelocity(p.getEyeLocation().getDirection().multiply(1.6).setY(0.9)); burst(p.getLocation(), Particle.CLOUD, 25, 0.4); p.playSound(p, Sound.ENTITY_BREEZE_WIND_BURST, 1f, 1f); }
            case "gale_blade:2" -> { for (LivingEntity t : near(p, 4)) { hurt(t, p, 6); t.setVelocity(t.getLocation().toVector().subtract(p.getLocation().toVector()).normalize().multiply(1.1).setY(0.5)); } burst(p.getLocation().add(0, 1, 0), Particle.SWEEP_ATTACK, 12, 1.8); }
            case "earth_hammer:1" -> slam(p, 5, 9, true);
            case "earth_hammer:2" -> { for (LivingEntity t : near(p, 10)) t.addPotionEffect(new PotionEffect(PotionEffectType.SLOWNESS, 120, 2)); burst(p.getLocation(), Particle.BLOCK, 80, 3, Material.DIRT); p.playSound(p, Sound.ENTITY_GENERIC_EXPLODE, 0.6f, 0.5f); }
            case "life_staff:1" -> { heal(p, 8); burst(p.getLocation().add(0, 1, 0), Particle.HEART, 12, 0.6); p.playSound(p, Sound.ENTITY_PLAYER_LEVELUP, 1f, 1.4f); }
            case "life_staff:2" -> { for (Entity e : p.getNearbyEntities(8, 8, 8)) if (e instanceof Player o) { heal(o, 6); burst(o.getLocation().add(0, 1, 0), Particle.HEART, 8, 0.5); } p.playSound(p, Sound.BLOCK_BEACON_POWER_SELECT, 1f, 1.5f); }
            default -> { }
        }
    }

    // ------------------------------------------------------------------ passives (called from the listener)
    void onHit(Player p, Weapons.Def d, LivingEntity t, double dealt) {
        switch (d.id()) {
            case "crimson_fang" -> { heal(p, dealt * 0.15 / 2); burst(p.getLocation().add(0, 1, 0), Particle.HEART, 3, 0.3); }
            case "frost_brand" -> { t.addPotionEffect(new PotionEffect(PotionEffectType.SLOWNESS, 60, 1)); burst(t.getLocation().add(0, 1, 0), Particle.SNOWFLAKE, 10, 0.3); }
            default -> { }
        }
    }

    /** Called every 10 ticks for the weapon in the main hand. */
    void held(Player p, Weapons.Def d) {
        switch (d.id()) {
            case "inferno_scythe" -> { p.addPotionEffect(new PotionEffect(PotionEffectType.FIRE_RESISTANCE, 40, 0, true, false)); p.setFireTicks(0); }
            case "void_axe" -> { for (LivingEntity t : near(p, 3)) t.addPotionEffect(new PotionEffect(PotionEffectType.SLOWNESS, 40, 0, true, false)); }
            case "life_staff" -> p.addPotionEffect(new PotionEffect(PotionEffectType.REGENERATION, 40, 0, true, false));
            case "storm_trident" -> { if (new Random().nextInt(12) == 0) burst(p.getLocation().add(0, 1.5, 0), Particle.ELECTRIC_SPARK, 10, 0.6); }
            default -> { }
        }
    }

    // ------------------------------------------------------------------ abilities
    private LivingEntity target(Player p, int range) {
        Entity e = p.getTargetEntity(range);
        return e instanceof LivingEntity le && !(le instanceof ArmorStand) ? le : null;
    }

    private void dash(Player p, double len, double dmg, Particle pt) {
        Location s = p.getLocation(); Vector d = p.getEyeLocation().getDirection().setY(0).normalize();
        Set<UUID> hit = new HashSet<>();
        for (double i = 0.5; i <= len; i += 0.5) {
            Location l = s.clone().add(d.clone().multiply(i)).add(0, 1, 0);
            if (!l.getBlock().isPassable()) break;
            burst(l, pt, 3, 0.2);
            for (Entity e : l.getWorld().getNearbyEntities(l, 1, 1, 1)) if (e instanceof LivingEntity le && e != p && !(e instanceof ArmorStand) && hit.add(e.getUniqueId())) hurt(le, p, dmg);
        }
        p.setVelocity(d.multiply(2.2).setY(0.1));
        p.playSound(p, Sound.ENTITY_PLAYER_ATTACK_SWEEP, 1f, 0.7f);
    }

    private void cone(Player p, double range, double dmg, Particle pt) {
        Vector d = p.getEyeLocation().getDirection();
        for (double i = 1; i <= range; i += 0.7) for (int k = -2; k <= 2; k++) {
            Vector side = d.clone().crossProduct(new Vector(0, 1, 0)).normalize().multiply(k * i * 0.12);
            p.getWorld().spawnParticle(pt, p.getEyeLocation().add(d.clone().multiply(i)).add(side), 1, 0, 0, 0, 0.01);
        }
        for (LivingEntity t : near(p, range)) {
            Vector to = t.getEyeLocation().toVector().subtract(p.getEyeLocation().toVector());
            if (to.angle(d) < 0.55) { hurt(t, p, dmg); t.setFireTicks(80); }
        }
        p.playSound(p, Sound.ITEM_FIRECHARGE_USE, 1f, 0.8f);
    }

    private void meteor(Player p) {
        Location at = aim(p, 40);
        Location from = at.clone().add(0, 18, 0);
        Fireball f = p.getWorld().spawn(from, Fireball.class, fb -> { fb.setShooter(p); fb.setIsIncendiary(false); fb.setYield(2.5f); fb.setDirection(new Vector(0, -1, 0)); });
        f.setVelocity(new Vector(0, -1.6, 0));
        p.playSound(p, Sound.ENTITY_BLAZE_SHOOT, 1f, 0.5f);
    }

    private void bolt(Player p) {
        Location s = p.getEyeLocation(); Vector d = s.getDirection();
        for (double i = 1; i <= 30; i += 0.6) {
            Location l = s.clone().add(d.clone().multiply(i));
            if (!l.getBlock().isPassable()) break;
            l.getWorld().spawnParticle(Particle.SOUL_FIRE_FLAME, l, 2, 0.05, 0.05, 0.05, 0.01);
            boolean done = false;
            for (Entity e : l.getWorld().getNearbyEntities(l, 0.8, 0.8, 0.8)) if (e instanceof LivingEntity le && e != p && !(e instanceof ArmorStand)) { hurt(le, p, 8); burst(le.getLocation().add(0, 1, 0), Particle.SOUL, 15, 0.4); done = true; break; }
            if (done) break;
        }
        p.playSound(p, Sound.ENTITY_ALLAY_ITEM_GIVEN, 1f, 0.6f);
    }

    private void slam(Player p, double r, double dmg, boolean launch) {
        for (LivingEntity t : near(p, r)) {
            hurt(t, p, dmg);
            Vector v = t.getLocation().toVector().subtract(p.getLocation().toVector());
            t.setVelocity(v.lengthSquared() < 0.01 ? new Vector(0, 0.6, 0) : v.normalize().multiply(launch ? 0.4 : 1.2).setY(launch ? 1.0 : 0.5));
        }
        burst(p.getLocation(), Particle.BLOCK, 120, r / 2, Material.DEEPSLATE);
        p.playSound(p, Sound.ENTITY_GENERIC_EXPLODE, 0.8f, 0.6f);
    }

    private void chain(Player p) {
        LivingEntity cur = target(p, 25);
        if (cur == null) return;
        Set<UUID> done = new HashSet<>();
        Location prev = p.getEyeLocation();
        for (int i = 0; i < 4 && cur != null; i++) {
            done.add(cur.getUniqueId());
            Location l = cur.getLocation().add(0, 1, 0);
            Vector dir = l.toVector().subtract(prev.toVector());
            for (double k = 0; k < dir.length(); k += 0.5) l.getWorld().spawnParticle(Particle.ELECTRIC_SPARK, prev.clone().add(dir.clone().normalize().multiply(k)), 1, 0, 0, 0, 0);
            cur.getWorld().strikeLightningEffect(cur.getLocation());
            hurt(cur, p, 7);
            prev = l;
            LivingEntity next = null; double best = 36;
            for (Entity e : cur.getNearbyEntities(6, 6, 6)) if (e instanceof LivingEntity le && e != p && !(e instanceof ArmorStand) && !done.contains(e.getUniqueId())) {
                double dd = le.getLocation().distanceSquared(cur.getLocation());
                if (dd < best) { best = dd; next = le; }
            }
            cur = next;
        }
    }

    private void storm(Player p) {
        Location c = aim(p, 40);
        Random r = new Random();
        for (int i = 0; i < 7; i++) {
            final int n = i;
            Bukkit.getScheduler().runTaskLater(plugin, () -> {
                Location l = c.clone().add(r.nextDouble() * 8 - 4, 0, r.nextDouble() * 8 - 4);
                l.setY(c.getWorld().getHighestBlockYAt(l) + 1);
                l.getWorld().strikeLightningEffect(l);
                for (Entity e : l.getWorld().getNearbyEntities(l, 2.5, 3, 2.5)) if (e instanceof LivingEntity le && e != p && !(e instanceof ArmorStand)) hurt(le, p, 6);
            }, 4L * n);
        }
    }

    private void pull(Player p, int unused) {
        LivingEntity t = target(p, 20);
        if (t == null) return;
        t.setVelocity(p.getLocation().toVector().subtract(t.getLocation().toVector()).normalize().multiply(1.5).setY(0.3));
        beam(p, Particle.COMPOSTER, 20);
        p.playSound(p, Sound.BLOCK_VINE_STEP, 1f, 0.6f);
    }

    private void rewind(Player p) {
        var q = trail.get(p.getUniqueId());
        if (q == null || q.isEmpty()) return;
        double[] s = q.peekFirst();
        Location l = new Location(p.getWorld(), s[0], s[1], s[2], (float) s[3], (float) s[4]);
        burst(p.getLocation().add(0, 1, 0), Particle.REVERSE_PORTAL, 40, 0.6);
        p.teleport(l);
        p.setHealth(Math.min(p.getAttribute(Attribute.MAX_HEALTH).getValue(), Math.max(p.getHealth(), s[5])));
        burst(l.clone().add(0, 1, 0), Particle.END_ROD, 40, 0.6);
        p.playSound(p, Sound.BLOCK_RESPAWN_ANCHOR_CHARGE, 1f, 1.5f);
    }

    private void blink(Player p, double range, Particle pt) {
        Location s = p.getEyeLocation(); Vector d = s.getDirection();
        Location best = p.getLocation();
        for (double i = 1; i <= range; i += 0.5) {
            Location l = s.clone().add(d.clone().multiply(i));
            if (!l.getBlock().isPassable() || !l.clone().add(0, 1, 0).getBlock().isPassable()) break;
            best = l.clone().subtract(0, 1, 0);
        }
        burst(p.getLocation().add(0, 1, 0), pt, 40, 0.5);
        best.setYaw(p.getLocation().getYaw()); best.setPitch(p.getLocation().getPitch());
        p.teleport(best);
        burst(best.clone().add(0, 1, 0), pt, 40, 0.5);
        p.playSound(p, Sound.ENTITY_ENDERMAN_TELEPORT, 1f, 1f);
    }

    private void volley(Player p) {
        Vector d = p.getEyeLocation().getDirection();
        for (int k = -1; k <= 1; k++) {
            Vector side = d.clone().crossProduct(new Vector(0, 1, 0)).normalize().multiply(k * 0.12);
            SpectralArrow a = p.getWorld().spawn(p.getEyeLocation().add(d), SpectralArrow.class, ar -> { ar.setShooter(p); ar.setDamage(6); ar.setPickupStatus(AbstractArrow.PickupStatus.DISALLOWED); });
            a.setVelocity(d.clone().add(side).multiply(2.4));
        }
        p.playSound(p, Sound.ENTITY_ARROW_SHOOT, 1f, 1.4f);
    }
}
