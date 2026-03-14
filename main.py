import pygame
import sys
import random
import math

# ═══════════════════════════ 定数 ════════════════════════════
SCREEN_W, SCREEN_H = 700, 900
FPS         = 60
BG_SCROLL   = 3

WHITE  = (255, 255, 255)
BLACK  = (  0,   0,   0)
RED    = (220,  50,  50)
GREEN  = (  0, 200,   0)
GRAY   = (150, 150, 150)
YELLOW = (255, 220,   0)
CYAN   = (  0, 220, 220)

# プレイヤー
P_W, P_H         = 80, 80
P_SPEED          = 5
P_COOLDOWN       = 15
P_HIT_W, P_HIT_H = 28, 28        # コア当たり判定
PLAYER_MAX_HP    = 3
INVINCIBLE_TIME  = 120            # 無敵フレーム数（2 秒）
BANK_ANGLE       = 18.0           # 旋回最大角度
BANK_LERP        = 0.18           # 角度補間係数

# 自機弾（現在値の 3 倍: 20×40 → 60×120）
PB_W, PB_H  = 60, 120
PB_SPEED    = 10

# 雑魚敵（現在値の 3 倍: 90×90 → 270×270）
E_W, E_H       = 270, 270
E_SPEED_BASE   = 1.5
SPAWN_BASE     = 80
SPAWN_MIN      = 30
BOSS_EVERY     = 50

# ボス
BO_W, BO_H  = 140, 140
BOSS_HP     = 10
BOSS_ENTER  = 80
BOSS_SHOOT  = 80

# 敵弾（現在値の 3 倍: 36×36 → 108×108）
EB_W, EB_H  = 108, 108
EB_SPEED    = 5

# 必殺技
SPECIAL_COOLDOWN = 30 * FPS       # 30 秒チャージ
MISSILE_W        = 400
MISSILE_H        = 400
MISSILE_SHOW     = 70             # ミサイル表示フレーム
FLASH_FRAMES     = 25             # 白フラッシュ継続フレーム


# ═══════════════════════ ユーティリティ ══════════════════════
def _play(snd):
    """None チェック付き効果音再生"""
    if snd:
        snd.play()


def load_img(path, size):
    return pygame.transform.smoothscale(
        pygame.image.load(path).convert_alpha(), size)


def load_snd(path):
    try:
        return pygame.mixer.Sound(path)
    except Exception:
        return None


# ═══════════════════════ スクロール背景 ══════════════════════
class ScrollBG:
    def __init__(self, image):
        self.image = image
        self.h     = image.get_height()
        self.y     = 0

    def update(self):
        self.y = (self.y + BG_SCROLL) % self.h

    def draw(self, surf):
        for off in (-1, 0, 1):
            surf.blit(self.image, (0, self.y + off * self.h))


# ═══════════════════════════ プレイヤー ═══════════════════════
class Player(pygame.sprite.Sprite):
    def __init__(self, img):
        super().__init__()
        self.base_image = img
        self.image      = img
        self.rect       = img.get_rect(midbottom=(SCREEN_W // 2, SCREEN_H - 40))
        self.hitbox     = pygame.Rect(0, 0, P_HIT_W, P_HIT_H)
        self.hitbox.center    = self.rect.center
        self.cooldown         = 0
        self.hp               = PLAYER_MAX_HP
        self.invincible_timer = 0
        self.angle            = 0.0    # 旋回アニメーション用

    @property
    def invincible(self):
        return self.invincible_timer > 0

    @property
    def blink_visible(self):
        """無敵中は 5 フレームごとに点滅"""
        if not self.invincible:
            return True
        return (self.invincible_timer // 5) % 2 == 0

    def take_damage(self, snd_damage):
        """被弾。True を返したら HP ゼロ（ゲームオーバー）"""
        if self.invincible:
            return False
        _play(snd_damage)
        self.hp -= 1
        self.invincible_timer = INVINCIBLE_TIME
        return self.hp <= 0

    def update(self, keys):
        if keys[pygame.K_LEFT]  and self.rect.left   > 0:        self.rect.x -= P_SPEED
        if keys[pygame.K_RIGHT] and self.rect.right  < SCREEN_W: self.rect.x += P_SPEED
        if keys[pygame.K_UP]    and self.rect.top    > 0:        self.rect.y -= P_SPEED
        if keys[pygame.K_DOWN]  and self.rect.bottom < SCREEN_H: self.rect.y += P_SPEED

        # 旋回バンクアニメーション（←→ で傾く）
        target = 0.0
        if keys[pygame.K_LEFT]:  target =  BANK_ANGLE
        if keys[pygame.K_RIGHT]: target = -BANK_ANGLE
        self.angle += (target - self.angle) * BANK_LERP

        old_center = self.rect.center
        self.image = pygame.transform.rotate(self.base_image, self.angle)
        self.rect  = self.image.get_rect(center=old_center)

        if self.cooldown         > 0: self.cooldown         -= 1
        if self.invincible_timer > 0: self.invincible_timer -= 1

        self.hitbox.center = self.rect.center

    def shoot(self, img):
        if self.cooldown == 0:
            self.cooldown = P_COOLDOWN
            return PlayerBullet(img, self.rect.centerx, self.rect.top)
        return None


# ══════════════════════════ 自機弾 ════════════════════════════
class PlayerBullet(pygame.sprite.Sprite):
    def __init__(self, img, x, y):
        super().__init__()
        self.image = img
        self.rect  = img.get_rect(midbottom=(x, y))

    def update(self):
        self.rect.y -= PB_SPEED
        if self.rect.bottom < 0:
            self.kill()


# ═══════════════════════════ 雑魚敵 ═══════════════════════════
class Enemy(pygame.sprite.Sprite):
    def __init__(self, img, speed):
        super().__init__()
        self.image = img
        x = random.randint(E_W // 2, SCREEN_W - E_W // 2)
        self.rect  = img.get_rect(midtop=(x, -E_H))
        self.speed = speed

    def update(self):
        self.rect.y += self.speed


# ══════════════════════════ ボス ══════════════════════════════
class Boss(pygame.sprite.Sprite):
    def __init__(self, img):
        super().__init__()
        self.image       = img
        self.rect        = img.get_rect(midtop=(SCREEN_W // 2, -BO_H))
        self.hp          = BOSS_HP
        self.entered     = False
        self.shoot_timer = 0
        self.sway_t      = 0

    def update(self):
        if not self.entered:
            self.rect.y += 2
            if self.rect.top >= BOSS_ENTER:
                self.rect.top = BOSS_ENTER
                self.entered  = True
        else:
            self.sway_t += 1
            self.rect.centerx = SCREEN_W // 2 + int(math.sin(self.sway_t * 0.02) * 200)
        if self.entered:
            self.shoot_timer += 1

    def can_shoot(self):
        if self.shoot_timer >= BOSS_SHOOT:
            self.shoot_timer = 0
            return True
        return False

    def take_hit(self):
        self.hp -= 1
        return self.hp <= 0

    def draw_hp_bar(self, surf):
        bx, by = self.rect.left, self.rect.top - 14
        pygame.draw.rect(surf, RED,   (bx, by, BO_W, 8))
        pygame.draw.rect(surf, GREEN, (bx, by, int(BO_W * self.hp / BOSS_HP), 8))
        pygame.draw.rect(surf, WHITE, (bx, by, BO_W, 8), 1)


# ═══════════════════════════ 敵弾 ═════════════════════════════
class EnemyBullet(pygame.sprite.Sprite):
    def __init__(self, img, x, y, vx, vy):
        super().__init__()
        self.image = img
        self.rect  = img.get_rect(center=(x, y))
        self.fx, self.fy = float(x), float(y)
        self.vx, self.vy = vx, vy

    def update(self):
        self.fx += self.vx
        self.fy += self.vy
        self.rect.center = (int(self.fx), int(self.fy))
        if (self.rect.top > SCREEN_H + 60 or self.rect.bottom < -60 or
                self.rect.left > SCREEN_W + 60 or self.rect.right < -60):
            self.kill()


# ═══════════════════ ボス 3-way 弾生成 ═══════════════════════
def boss_shoot(img, bx, by, px, py, n=3, spread=0.28):
    base   = math.atan2(py - by, px - bx)
    result = []
    for i in range(n):
        a  = base + (i - n // 2) * spread
        result.append(EnemyBullet(img, bx, by,
                                  math.cos(a) * EB_SPEED,
                                  math.sin(a) * EB_SPEED))
    return result


# ══════════════════════════ HUD 描画 ═════════════════════════
def draw_hud(screen, font, font_large, player, special_charge, score, boss):
    # スコア（左上）
    screen.blit(font.render(f"Score: {score}", True, WHITE), (10, 10))

    # ボス HP（右上）
    if boss:
        t = font.render(f"BOSS HP: {boss.hp} / {BOSS_HP}", True, RED)
        screen.blit(t, (SCREEN_W - t.get_width() - 10, 10))

    # 残機（左下）✈ × N
    for i in range(PLAYER_MAX_HP):
        color = WHITE if i < player.hp else (80, 80, 80)
        icon  = font.render("✈", True, color)
        screen.blit(icon, (10 + i * 28, SCREEN_H - 65))
    lives_label = font.render(f"  ×{player.hp}", True, WHITE)
    screen.blit(lives_label, (10 + PLAYER_MAX_HP * 28, SCREEN_H - 65))

    # 操作ガイド（中央下）
    hint = font.render("矢印: 移動  Space: 弾  X: 必殺技", True, GRAY)
    screen.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, SCREEN_H - 22))

    # 必殺技ゲージ（右下）
    if special_charge >= SPECIAL_COOLDOWN:
        r_surf = font_large.render("READY", True, YELLOW)
        p_surf = font.render("(Push X Key!!)", True, YELLOW)
        screen.blit(r_surf, (SCREEN_W - r_surf.get_width() - 10, SCREEN_H - 80))
        screen.blit(p_surf, (SCREEN_W - p_surf.get_width()  - 10, SCREEN_H - 44))
    else:
        secs  = max(0, (SPECIAL_COOLDOWN - special_charge) // FPS)
        label = font.render(f"RECHARGING... {secs}s", True, GRAY)
        screen.blit(label, (SCREEN_W - label.get_width() - 10, SCREEN_H - 44))


# ══════════════════════ ゲームオーバー画面 ════════════════════
def gameover_screen(screen, go_img, font, score):
    surf = pygame.transform.smoothscale(go_img, (SCREEN_W, SCREEN_H))
    while True:
        screen.blit(surf, (0, 0))
        hint = font.render(
            f"Score: {score}    Enter: もう一回    Q: 終了", True, WHITE)
        screen.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, SCREEN_H - 50))
        pygame.display.flip()
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                return False
            if ev.type == pygame.KEYDOWN:
                if ev.key in (pygame.K_r, pygame.K_RETURN): return True
                if ev.key == pygame.K_q:                     return False


# ═════════════════════════ ゲームループ ═══════════════════════
def play(screen, clock, A):
    bg         = ScrollBG(A['bg'])
    font       = A['font']
    font_large = A['font_large']

    player_grp = pygame.sprite.GroupSingle(Player(A['player']))
    pbullets   = pygame.sprite.Group()
    enemies    = pygame.sprite.Group()
    boss_grp   = pygame.sprite.GroupSingle()
    ebullets   = pygame.sprite.Group()
    player     = player_grp.sprite

    score          = 0
    spawn_total    = 0
    spawn_timer    = 0
    e_speed        = E_SPEED_BASE
    special_charge = 0             # チャージカウンター（0 ～ SPECIAL_COOLDOWN）

    # 必殺技ミサイル状態
    # None か {'x', 'y', 'vy', 'start_y', 'sf', 'cleared'} の dict
    missile     = None
    flash_alpha = 0               # 白フラッシュ透過度（0-255）
    flash_surf  = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)

    while True:
        # ─── イベント ───────────────────────────────────────
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if ev.type == pygame.KEYDOWN:
                # 弾を撃つ
                if ev.key == pygame.K_SPACE:
                    b = player.shoot(A['pbullet'])
                    if b:
                        pbullets.add(b)
                        _play(A['snd_shot'])
                        _play(random.choice(A['snd_vo_shots']))

                # 必殺技
                if ev.key == pygame.K_x:
                    if special_charge >= SPECIAL_COOLDOWN and missile is None:
                        special_charge = 0
                        flash_alpha    = 0
                        _play(A['snd_special'])
                        # 自機の現在位置からミサイルを発射
                        missile = {
                            'x':       float(player.rect.centerx),
                            'y':       float(player.rect.centery),
                            'vy':      -18.0,       # 上方向へ猛スピード
                            'start_y': float(player.rect.centery),
                            'sf':      0.2,         # 初期サイズ係数（20%）
                            'cleared': False,       # 敵一掃フラグ
                        }

        # ─── 難易度 ─────────────────────────────────────────
        e_speed   = E_SPEED_BASE + score * 0.008
        spawn_ivl = max(SPAWN_MIN, SPAWN_BASE - score // 8)

        # ─── チャージ ────────────────────────────────────────
        if special_charge < SPECIAL_COOLDOWN:
            special_charge += 1

        # ─── 敵スポーン ──────────────────────────────────────
        spawn_timer += 1
        if spawn_timer >= spawn_ivl:
            spawn_timer = 0
            spawn_total += 1
            if spawn_total % BOSS_EVERY == 0 and not boss_grp.sprite:
                boss_grp.add(Boss(A['boss']))
            else:
                enemies.add(Enemy(A['enemy'], e_speed))

        # ─── ボス攻撃 ────────────────────────────────────────
        boss = boss_grp.sprite
        if boss and boss.can_shoot():
            for b in boss_shoot(A['ebullet'],
                                boss.rect.centerx, boss.rect.bottom,
                                player.rect.centerx, player.rect.centery):
                ebullets.add(b)

        # ─── 更新 ────────────────────────────────────────────
        keys = pygame.key.get_pressed()
        player.update(keys)
        pbullets.update()
        enemies.update()
        boss_grp.update()
        ebullets.update()
        bg.update()

        # ─── 必殺技ミサイル：移動・フラッシュ・敵一掃 ──────────
        if missile is not None:
            missile['y']  += missile['vy']
            missile['sf']  = min(1.0, missile['sf'] + 0.03)   # サイズを徐々に拡大

            # フラッシュ：中間点到達前は徐々に増加（溜め演出）
            mid = SCREEN_H // 2
            if missile['y'] > mid:
                progress    = (missile['start_y'] - missile['y']) / max(1, missile['start_y'] - mid)
                flash_alpha = int(min(220, progress * 220))
            else:
                # 中間点を過ぎたらフラッシュをフェードアウト
                flash_alpha = max(0, flash_alpha - 18)

            # 画面中間到達 → 敵を一掃
            if not missile['cleared'] and missile['y'] <= mid:
                missile['cleared'] = True
                enemies.empty()
                ebullets.empty()
                if boss_grp.sprite:
                    boss_grp.empty()
                    score += 100

            # 画面外に出たらミサイル消去
            if missile['y'] < -(MISSILE_H * missile['sf']):
                missile     = None
                flash_alpha = 0

        # ─── 当たり判定: 自機弾 vs 雑魚 ─────────────────────
        hits = pygame.sprite.groupcollide(enemies, pbullets, True, True)
        for _ in hits:
            score += 10
            _play(A['snd_expl'])

        # ─── 当たり判定: 自機弾 vs ボス ─────────────────────
        if boss:
            for pb in list(pbullets):
                if boss.rect.colliderect(pb.rect):
                    pb.kill()
                    if boss.take_hit():
                        boss_grp.empty()
                        score += 100
                        _play(A['snd_expl'])
                    break

        # ─── 被弾判定（プレイヤー hitbox でコア判定）─────────
        def check_hit():
            if any(player.hitbox.colliderect(eb.rect) for eb in ebullets):
                # 当たった弾を消す
                for eb in list(ebullets):
                    if player.hitbox.colliderect(eb.rect):
                        eb.kill(); break
                return True
            if any(player.hitbox.colliderect(e.rect) for e in enemies):
                return True
            if boss and player.hitbox.colliderect(boss.rect):
                return True
            return False

        if check_hit():
            if player.take_damage(A['snd_damage']):
                _play(A['snd_go'])
                _play(A['snd_vo_dead'])
                pygame.time.wait(700)
                return score

        # ─── 敵が画面下端突破 → HP を 1 減らす ───────────────
        escaped = [e for e in enemies if e.rect.top >= SCREEN_H]
        for e in escaped:
            e.kill()
        if escaped:
            if player.take_damage(A['snd_damage']):
                _play(A['snd_go'])
                _play(A['snd_vo_dead'])
                pygame.time.wait(700)
                return score

        # ─── 描画 ────────────────────────────────────────────
        bg.draw(screen)
        enemies.draw(screen)
        boss_grp.draw(screen)
        if boss:
            boss.draw_hp_bar(screen)
        pbullets.draw(screen)
        ebullets.draw(screen)

        # 自機（無敵中は点滅）
        if player.blink_visible:
            screen.blit(player.image, player.rect)

        # ─── 必殺技エフェクト（飛行アニメーション）────────────
        if missile is not None:
            w  = max(1, int(MISSILE_W * missile['sf']))
            h  = max(1, int(MISSILE_H * missile['sf']))
            ms = pygame.transform.scale(A['missile'], (w, h))
            mx = int(missile['x']) - w // 2
            my = int(missile['y']) - h // 2
            screen.blit(ms, (mx, my))

        # 白フラッシュ（ミサイル飛行中の溜め → 一掃後フェード）
        if flash_alpha > 0:
            flash_surf.fill((255, 255, 255, flash_alpha))
            screen.blit(flash_surf, (0, 0))

        # HUD
        draw_hud(screen, font, font_large, player, special_charge, score, boss)

        pygame.display.flip()
        clock.tick(FPS)


# ══════════════════════════ メイン ════════════════════════════
def main():
    pygame.init()
    pygame.mixer.init()

    screen     = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("2D Shooting Game")
    clock      = pygame.time.Clock()
    font       = pygame.font.SysFont(None, 28)
    font_large = pygame.font.SysFont(None, 48)

    # 背景: 700×700 正方形タイルでスクロール
    bg_img = pygame.transform.smoothscale(
        pygame.image.load('background.png').convert(), (SCREEN_W, SCREEN_W))

    A = {
        'bg':           bg_img,
        'player':       load_img('player.png',         (P_W,  P_H)),
        'pbullet':      load_img('bullet_player.png',  (PB_W, PB_H)),
        'enemy':        load_img('enemy.png',           (E_W,  E_H)),
        'boss':         load_img('enemy_bear.png',      (BO_W, BO_H)),
        'ebullet':      load_img('bullet_enemy.png',   (EB_W, EB_H)),
        'missile':      load_img('special_missile.png', (MISSILE_W, MISSILE_H)),
        'gameover':     pygame.image.load('gameover.png').convert_alpha(),
        'font':         font,
        'font_large':   font_large,
        # 効果音
        'snd_shot':     load_snd('shot.wav'),
        'snd_vo_shots': [load_snd('vo_shot_1.wav'),
                         load_snd('vo_shot_2.wav'),
                         load_snd('vo_shot_3.wav')],
        'snd_expl':     load_snd('se_explosion.wav'),
        'snd_go':       load_snd('explosion.wav'),
        'snd_vo_dead':  load_snd('vo_dead.wav'),
        'snd_damage':   load_snd('vo_damage.wav'),
        'snd_special':  load_snd('vo_special.wav'),
    }

    def start_bgm():
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.load('bgm.mp3')
            pygame.mixer.music.set_volume(0.6)
            pygame.mixer.music.play(-1)
        except Exception:
            pass

    def start_gameover_bgm():
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.load('gameover.mp3')
            pygame.mixer.music.set_volume(0.8)
            pygame.mixer.music.play(-1)
        except Exception:
            pass

    start_bgm()

    while True:
        score = play(screen, clock, A)
        start_gameover_bgm()
        if not gameover_screen(screen, A['gameover'], font, score):
            break
        start_bgm()   # リトライ時は BGM を戻す

    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()
