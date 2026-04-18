"""Combat engine — turn-based combat resolution with dice mechanics."""

import uuid
import random
import logging
from models.combat import (
    CombatState, Combatant, CombatAction, CombatActionType,
    CombatLogEntry, StatusEffect,
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
            name=template.name,
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
            # Self-buff / heal
            if action.ability_name.lower() == "heal":
                heal_amount = self.rng.randint(15, 25)
                player.hp = min(player.max_hp, player.hp + heal_amount)
                return self._log(combat, player.name, "Heal", "heal", heal_amount,
                                 f"You heal for {heal_amount} HP!")
            # Status effect on self
            if action.status_effect:
                eff = StatusEffect(name=action.status_effect, duration=action.status_duration)
                player.status_effects.append(eff)
                return self._log(combat, player.name, action.ability_name, "buff", 0,
                                 f"You cast {action.ability_name}!")
            return self._log(combat, player.name, action.ability_name, "support", 0,
                             f"You use {action.ability_name}.")

        # Attack / Spell / Defend
        if action.action_type == CombatActionType.DEFEND:
            eff = StatusEffect(name="blocking", duration=1, armor_modifier=3)
            player.status_effects.append(eff)
            return self._log(combat, player.name, action.ability_name or "Block", "defend", 0,
                             "You brace yourself for the next attack.")

        # Roll to hit
        roll = self.rng.randint(1, 20)
        attack_total = roll + player.attack_bonus
        # Apply player status effect modifiers
        for eff in player.status_effects:
            attack_total += eff.stat_modifier.get("strength", 0)

        # Crit on natural 20
        is_crit = roll == 20
        is_miss = roll == 1

        if is_miss:
            return self._log(combat, player.name, action.ability_name, "miss", 0, "Your attack misses!")

        # Check against enemy armor
        threshold = 8 + enemy.armor
        if attack_total < threshold and not is_crit:
            return self._log(combat, player.name, action.ability_name, "miss", 0, "Your attack glances off their armor!")

        # Calculate damage
        damage = roll_damage(action.damage_dice, self.rng) if action.damage_dice else self.rng.randint(1, 6)
        if is_crit:
            damage = int(damage * 1.5)
            result = "crit"
        else:
            result = "hit"

        # Apply status effect to enemy
        if action.status_effect:
            enemy.status_effects.append(
                StatusEffect(name=action.status_effect, duration=action.status_duration)
            )

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

        # Tick status effects on enemy
        self._tick_effects(enemy)

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

        # Roll to hit
        roll = self.rng.randint(1, 20)
        attack_total = roll + enemy.attack_bonus
        is_crit = roll == 20
        is_miss = roll == 1

        if is_miss:
            return self._log(combat, enemy.name, action_name, "miss", 0,
                             f"{enemy.name}'s attack misses!")

        # Apply enemy status modifiers
        for eff in enemy.status_effects:
            attack_total += eff.stat_modifier.get("strength", 0)

        # Player's effective armor (base + blocking + effects)
        player_armor = player.armor
        for eff in player.status_effects:
            player_armor += eff.armor_modifier

        threshold = 8 + player_armor
        if attack_total < threshold and not is_crit:
            return self._log(combat, enemy.name, action_name, "miss", 0,
                             f"{enemy.name}'s attack glances off your armor!")

        # Damage
        damage = roll_damage(damage_dice, self.rng) if damage_dice else self.rng.randint(1, 6) + int(enemy.attack_bonus)
        if is_crit:
            damage = int(damage * 1.5)
            result = "crit"
        else:
            result = "hit"

        # Apply status effect to player
        if status_effect:
            player.status_effects.append(
                StatusEffect(name=status_effect, duration=status_duration)
            )

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
            self._tick_effects(combat.player)
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

    def _tick_effects(self, combatant: Combatant):
        """Tick status effects, apply damage-over-time, remove expired."""
        expired = []
        for eff in combatant.status_effects:
            eff.duration -= 1
            # DOT
            if eff.damage_per_turn > 0:
                combatant.hp = max(0, combatant.hp - eff.damage_per_turn)
            if eff.duration <= 0:
                expired.append(eff)
        for eff in expired:
            combatant.status_effects.remove(eff)

    def _log(self, combat: CombatState, actor: str, action: str, result: str,
             damage: int, message: str) -> CombatState:
        """Add a log entry to combat state."""
        combat.log.append(CombatLogEntry(
            turn=combat.turn_number, actor=actor, action=action,
            result=result, damage=damage, message=message,
        ))
        return combat
