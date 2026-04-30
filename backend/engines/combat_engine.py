"""Combat engine — turn-based combat resolution with dice mechanics."""

import uuid
import random
import logging
from models.combat import (
    CombatState, Combatant, CombatAction, CombatActionType,
    CombatLogEntry, StatusEffect, get_effect_rule,
)
from data.enemies import get_random_enemy, roll_loot, roll_damage, ENEMY_TEMPLATES
from models.game_state import Item

logger = logging.getLogger(__name__)


class CombatEngine:
    """Manages turn-based combat encounters."""

    def __init__(self):
        self.rng = random.Random()

    def initiate_combat(
        self,
        player_state,
        enemy_tier: int = 1,
        enemy_key: str | None = None,
        narrative_context: str = "",
        enemy_name_override: str | None = None,
    ) -> CombatState:
        """Create a new combat encounter."""
        # Pick enemy
        if enemy_key and enemy_key in ENEMY_TEMPLATES:
            template = ENEMY_TEMPLATES[enemy_key]
        else:
            template = get_random_enemy(enemy_tier, self.rng)

        # Build player combatant from PlayerState
        player = Combatant(
            name=player_state.name,
            hp=player_state.hp,
            max_hp=player_state.max_hp,
            armor=self._calc_player_armor(player_state),
            attack_bonus=self._calc_attack_bonus(player_state),
            mana=player_state.mana,
            max_mana=player_state.max_mana,
            is_player=True,
            abilities=player_state.__dict__.get("world_abilities", []),
        )

        # Build enemy combatant from template
        enemy = Combatant(
            name=enemy_name_override or template.name,
            hp=template.hp,
            max_hp=template.hp,
            armor=template.armor,
            attack_bonus=template.attack_bonus,
            abilities=template.abilities,
        )

        return CombatState(
            combat_id=str(uuid.uuid4()),
            enemies=[enemy],
            player=player,
            turn_number=1,
            current_turn="player",
            status="active",
        )

    def resolve_player_action(
        self, combat: CombatState, action: CombatAction
    ) -> CombatState:
        """Resolve a player's combat action."""
        if combat.status != "active":
            return combat

        player = combat.player
        enemy = combat.enemies[0] if combat.enemies else None
        if not enemy or not player:
            return combat

        # ── Phase 1: Apply status effects on player ──
        effect_msgs = self._apply_status_effects(player)
        for msg in effect_msgs:
            self._log(combat, player.name, "Effect Tick", "effect", 0, msg)

        # ── Phase 2: Can player act? ──
        if not self._can_act(player):
            return self._log(combat, player.name, "Stunned", "miss", 0,
                             "You are stunned and cannot act!")

        # Check mana
        if action.mana_cost > 0 and player.mana < action.mana_cost:
            return self._log(combat, player.name, action.ability_name, "insufficient_mana", 0,
                             f"Not enough mana for {action.ability_name}!")

        # Deduct mana
        player.mana = max(0, player.mana - action.mana_cost)

        if action.action_type == CombatActionType.FLEE:
            flee_roll = self.rng.randint(1, 20) + player.attack_bonus * 0.5
            if flee_roll >= 12:
                combat.status = "fled"
                return self._log(combat, player.name, "Flee", "fled", 0, "You escape the battle!")
            else:
                return self._log(combat, player.name, "Flee", "failed", 0, "You couldn't escape!")

        if action.action_type == CombatActionType.SUPPORT:
            # Self-buff / heal / item usage
            if action.ability_name.lower() == "heal" or "potion" in action.ability_name.lower():
                heal_amount = self.rng.randint(15, 25)
                player.hp = min(player.max_hp, player.hp + heal_amount)
                return self._log(combat, player.name, action.ability_name, "heal", heal_amount,
                                 f"You use {action.ability_name} for {heal_amount} HP!")
            # Status effect on self
            if action.status_effect:
                self._apply_effect(player, action.status_effect, action.status_duration)
                return self._log(combat, player.name, action.ability_name, "buff", 0,
                                 f"You cast {action.ability_name}!")
            return self._log(combat, player.name, action.ability_name, "support", 0,
                             f"You use {action.ability_name}.")

        # Attack / Spell / Defend
        if action.action_type == CombatActionType.DEFEND:
            self._apply_effect(player, "blocking", 1)
            return self._log(combat, player.name, action.ability_name or "Block", "defend", 0,
                             "You brace yourself for the next attack.")

        # ── Phase 3: Roll to hit ──
        roll = self.rng.randint(1, 20)
        roll_modifier = self._get_roll_modifier(player)
        attack_total = roll + player.attack_bonus + roll_modifier

        is_crit = roll == 20
        is_miss = roll == 1

        if is_miss:
            return self._log(combat, player.name, action.ability_name, "miss", 0, "Your attack misses!")

        enemy_armor = enemy.armor + self._get_armor_modifier(enemy)

        threshold = 8 + enemy_armor
        if attack_total < threshold and not is_crit:
            return self._log(combat, player.name, action.ability_name, "miss", 0, "Your attack glances off their armor!")

        # ── Phase 4: Calculate damage ──
        damage = roll_damage(action.damage_dice, self.rng) if action.damage_dice else self.rng.randint(1, 6)

        # Apply player's damage modifier (weaken, etc.)
        damage_modifier = self._get_damage_modifier(player)
        damage = max(1, int(damage * damage_modifier))

        if is_crit:
            damage = int(damage * 1.5)
            result = "crit"
        else:
            result = "hit"

        # ── Phase 5: Apply status effect to enemy ──
        if action.status_effect:
            self._apply_effect(enemy, action.status_effect, action.status_duration)

        # ── Phase 6: Apply damage ──
        enemy.hp = max(0, enemy.hp - damage)

        log = self._log(combat, player.name, action.ability_name, result, damage,
                        f"{'CRITICAL! ' if is_crit else ''}You deal {damage} damage to {enemy.name}!")
        if enemy.hp <= 0:
            log.status = "victory"
            combat.status = "victory"

        return log

    def resolve_enemy_action(self, combat: CombatState) -> CombatState:
        """AI-controlled enemy turn — heuristic-based, no LLM."""
        if combat.status != "active":
            return combat

        enemy = combat.enemies[0]
        player = combat.player
        if not player:
            return combat

        # ── Phase 1: Apply status effects on enemy ──
        effect_msgs = self._apply_status_effects(enemy)
        for msg in effect_msgs:
            self._log(combat, enemy.name, "Effect Tick", "effect", 0, msg)

        if enemy.hp <= 0:
            combat.status = "victory"
            return self._log(combat, enemy.name, "Death", "defeat", 0, f"{enemy.name} succumbs to its wounds!")

        # ── Phase 2: Can enemy act? ──
        if not self._can_act(enemy):
            return self._log(combat, enemy.name, "Stunned", "miss", 0,
                             f"{enemy.name} is stunned and cannot act!")

        # Simple AI: use abilities if available and hp < 50%, else basic attack
        action_name = "Attack"
        damage_dice = ""
        status_effect = None
        status_duration = 0

        if enemy.abilities and enemy.hp < enemy.max_hp * 0.5:
            # Try to use a special ability
            for abil in enemy.abilities:
                if abil.get("status_effect") and not any(e.name == abil["status_effect"] for e in player.status_effects):
                    action_name = abil["name"]
                    damage_dice = abil.get("damage_dice", "")
                    status_effect = abil.get("status_effect")
                    status_duration = abil.get("status_duration", 1)
                    break
            else:
                # Use highest damage ability
                best = max(enemy.abilities, key=lambda a: len(a.get("damage_dice", "")))
                action_name = best["name"]
                damage_dice = best.get("damage_dice", "")
                status_effect = best.get("status_effect")
                status_duration = best.get("status_duration", 1)
        elif enemy.abilities and self.rng.random() < 0.3:
            # 30% chance to use an ability
            abil = self.rng.choice(enemy.abilities)
            action_name = abil["name"]
            damage_dice = abil.get("damage_dice", "")
            status_effect = abil.get("status_effect")
            status_duration = abil.get("status_duration", 1)

        # ── Phase 3: Roll to hit ──
        roll = self.rng.randint(1, 20)
        roll_modifier = self._get_roll_modifier(enemy)
        attack_total = roll + enemy.attack_bonus + roll_modifier

        is_crit = roll == 20
        is_miss = roll == 1

        if is_miss:
            return self._log(combat, enemy.name, action_name, "miss", 0,
                             f"{enemy.name}'s attack misses!")

        # Player's effective armor
        player_armor = player.armor + self._get_armor_modifier(player)

        # Check dodge
        dodge_chance = self._get_dodge_chance(player)
        if dodge_chance > 0 and self.rng.random() < dodge_chance:
            return self._log(combat, enemy.name, action_name, "miss", 0,
                             f"{enemy.name}'s attack is dodged!")

        threshold = 8 + player_armor
        if attack_total < threshold and not is_crit:
            return self._log(combat, enemy.name, action_name, "miss", 0,
                             f"{enemy.name}'s attack glances off your armor!")

        # ── Phase 4: Calculate damage ──
        damage = roll_damage(damage_dice, self.rng) if damage_dice else self.rng.randint(1, 6) + int(enemy.attack_bonus)

        # Apply enemy's damage modifier (weaken, etc.)
        damage_modifier = self._get_damage_modifier(enemy)
        damage = max(1, int(damage * damage_modifier))

        if is_crit:
            damage = int(damage * 1.5)
            result = "crit"
        else:
            result = "hit"

        # ── Phase 5: Apply status effect to player ──
        if status_effect:
            self._apply_effect(player, status_effect, status_duration)

        # ── Phase 6: Apply damage ──
        player.hp = max(0, player.hp - damage)

        # Heal-self abilities (life drain, etc.)
        for abil in enemy.abilities:
            if abil.get("heal_self") and action_name == abil["name"]:
                heal = damage // 2
                enemy.hp = min(enemy.max_hp, enemy.hp + heal)

        log = self._log(combat, enemy.name, action_name, result, damage,
                        f"{'CRITICAL! ' if is_crit else ''}{enemy.name} deals {damage} damage to you!")
        if player.hp <= 0:
            combat.status = "defeat"

        return log

    def tick_player_effects(self, combat: CombatState) -> CombatState:
        """Tick status effects on player at start of their turn."""
        if combat.player:
            msgs = self._apply_status_effects(combat.player)
            for msg in msgs:
                self._log(combat, combat.player.name, "Effect Tick", "effect", 0, msg)
        return combat

    def get_combat_rewards(self, combat: CombatState) -> dict:
        """Calculate XP + loot on victory."""
        if combat.status != "victory":
            return {"xp": 0, "items": [], "loot_descriptions": []}

        total_xp = 0
        items = []
        descriptions = []

        for enemy in combat.enemies:
            template = ENEMY_TEMPLATES.get(
                next((k for k, v in ENEMY_TEMPLATES.items() if v.name == enemy.name), ""),
                None,
            )
            if template:
                total_xp += template.xp_reward
                loot = roll_loot(template, self.rng)
                for entry in loot:
                    item = Item(
                        name=entry["name"],
                        item_type=entry.get("type", "misc"),
                        description=f"Looted from {enemy.name}",
                        stat_bonus=entry.get("stat_bonus", {}),
                        hp_restore=entry.get("hp_restore", 0),
                        mana_restore=entry.get("mana_restore", 0),
                    )
                    items.append(item)
                    descriptions.append(f"Found: {entry['name']}")

        return {"xp": total_xp, "items": items, "loot_descriptions": descriptions}

    def _calc_player_armor(self, player_state) -> int:
        """Calculate total armor from inventory."""
        armor = 0
        for item in player_state.inventory:
            if hasattr(item, "item_type") and item.item_type == "armor":
                armor += getattr(item, "stat_bonus", {}).get("armor_bonus", 0) if isinstance(getattr(item, "stat_bonus", None), dict) else 0
        return armor

    def _calc_attack_bonus(self, player_state) -> float:
        """Calculate attack bonus from stats."""
        stats = player_state.stats
        return (stats.strength + stats.dexterity) / 4.0

    def _apply_status_effects(self, combatant: Combatant) -> list[str]:
        """Apply all status effects on a combatant. Returns narrative log messages."""
        messages = []
        expired = []

        for eff in combatant.status_effects:
            rule = get_effect_rule(eff.name)
            name = eff.name.lower()

            # DoT / HoT
            dot_lo, dot_hi = rule.get("dot", (0, 0))
            if dot_lo != 0 or dot_hi != 0:
                val = self.rng.randint(min(dot_lo, dot_hi), max(dot_lo, dot_hi))
                if val < 0:
                    # Heal
                    heal = abs(val)
                    combatant.hp = min(combatant.max_hp, combatant.hp + heal)
                    messages.append(f"{combatant.name} recovers {heal} HP from {eff.name}.")
                elif val > 0:
                    combatant.hp = max(0, combatant.hp - val)
                    messages.append(f"{combatant.name} takes {val} {eff.name} damage.")

            # Legacy damage_per_turn fallback
            if eff.damage_per_turn > 0:
                combatant.hp = max(0, combatant.hp - eff.damage_per_turn)
                messages.append(f"{combatant.name} takes {eff.damage_per_turn} damage from {eff.name}.")

            # Tick duration
            eff.duration -= 1
            if eff.duration <= 0:
                expired.append(eff)
                messages.append(f"{eff.name} fades from {combatant.name}.")

        for eff in expired:
            combatant.status_effects.remove(eff)

        return messages

    def _can_act(self, combatant: Combatant) -> bool:
        """Check if combatant can take an action this turn."""
        for eff in combatant.status_effects:
            rule = get_effect_rule(eff.name)
            if rule.get("skip_turn"):
                return False
        return True

    def _get_damage_modifier(self, combatant: Combatant) -> float:
        """Get combined outgoing damage modifier from all status effects."""
        modifier = 1.0
        for eff in combatant.status_effects:
            rule = get_effect_rule(eff.name)
            modifier *= rule.get("damage_modifier", 1.0)
        return modifier

    def _get_roll_modifier(self, combatant: Combatant) -> int:
        """Get combined d20 roll modifier from all status effects."""
        modifier = 0
        for eff in combatant.status_effects:
            rule = get_effect_rule(eff.name)
            modifier += rule.get("roll_modifier", 0)
        return modifier

    def _get_armor_modifier(self, combatant: Combatant) -> int:
        """Get combined armor modifier from all status effects."""
        modifier = 0
        for eff in combatant.status_effects:
            rule = get_effect_rule(eff.name)
            modifier += rule.get("armor_modifier", 0)
            # Legacy armor_modifier field on StatusEffect itself
            if eff.armor_modifier != 0:
                modifier += eff.armor_modifier
        return modifier

    def _get_dodge_chance(self, combatant: Combatant) -> float:
        """Get dodge chance from status effects."""
        chance = 0.0
        for eff in combatant.status_effects:
            rule = get_effect_rule(eff.name)
            chance = max(chance, rule.get("dodge_chance", 0.0))
            if eff.dodge_chance > 0:
                chance = max(chance, eff.dodge_chance)
        return chance

    def _apply_effect(self, combatant: Combatant, effect_name: str, duration: int):
        """Apply a status effect with stacking rules."""
        rule = get_effect_rule(effect_name)
        max_dur = rule.get("max_duration", 5)
        capped_duration = min(duration, max_dur)

        # Check if already has this effect
        existing = next((e for e in combatant.status_effects if e.name.lower() == effect_name.lower()), None)
        if existing:
            if rule.get("stacks"):
                # Stack: add another instance (capped at 3)
                if len([e for e in combatant.status_effects if e.name.lower() == effect_name.lower()]) < 3:
                    combatant.status_effects.append(
                        StatusEffect(name=effect_name, duration=capped_duration)
                    )
            else:
                # Refresh: just reset duration
                existing.duration = max(existing.duration, capped_duration)
        else:
            combatant.status_effects.append(
                StatusEffect(name=effect_name, duration=capped_duration)
            )

    def _log(self, combat: CombatState, actor: str, action: str, result: str,
             damage: int, message: str) -> CombatState:
        """Add a log entry to combat state."""
        combat.log.append(CombatLogEntry(
            turn=combat.turn_number, actor=actor, action=action,
            result=result, damage=damage, message=message,
        ))
        return combat
