# ✈ KAP Special Shooting Game

A fully-featured 2D vertical-scrolling shooter built with **Python + Pygame**.

---

## 🎮 Gameplay

Take control of a fighter plane soaring over the sea. Shoot down waves of enemies, survive boss battles, and unleash your devastating special missile!

### Controls

| Key | Action |
|-----|--------|
| `← →` `↑ ↓` | Move (with banking animation) |
| `Space` | Fire bullets |
| `X` | Launch special missile (30s charge) |
| `Enter` / `R` | Retry after Game Over |
| `Q` | Quit |

---

## ⚙️ Features

- **Scrolling sea background** — smooth vertical loop scroll for full immersion
- **Banking animation** — player sprite tilts left/right during movement
- **HP system** — 3 lives with invincibility frames and blink effect on damage
- **Core hitbox** — tight 28×28 collision box inside the player sprite for fair gameplay
- **Enemy waves** — enemies spawn at increasing speed and frequency as score rises
- **Boss battles** — a giant bear boss appears every 50 enemies, with HP bar and 3-way bullet spread
- **Special missile** — launches from player position, grows in size as it flies, with white flash buildup and mid-screen enemy wipe
- **Full voice & SFX** — shot voices, damage voice, special voice, explosion sounds, and BGM

---

## 🚀 Setup

### Requirements

- Python 3.10+
- pygame 2.x

### Install & Run

```bash
pip install pygame
python main.py
```

---

## 📁 Project Structure

```
ShootingGame_KAP/
├── main.py               # Game source code
├── background.png        # Scrolling sea background
├── player.png            # Player aircraft
├── enemy.png             # Standard enemy
├── enemy_bear.png        # Boss enemy
├── bullet_player.png     # Player bullet
├── bullet_enemy.png      # Enemy heart bullet
├── special_missile.png   # Special weapon
├── gameover.png          # Game over screen
├── bgm.mp3               # Background music
├── gameover.mp3          # Game over BGM
├── se_explosion.wav      # Explosion SFX
├── explosion.wav         # Player death explosion
├── shot.wav              # Shot SFX
├── vo_shot_1~3.wav       # Shot voice lines
├── vo_damage.wav         # Damage voice
├── vo_dead.wav           # Death voice
└── vo_special.wav        # Special weapon voice
```

---

## 🏆 Scoring

| Event | Points |
|-------|--------|
| Destroy enemy | +10 |
| Destroy boss | +100 |
| Special missile boss kill | +100 |

---

## 📝 License

For educational and personal use.
