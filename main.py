import pygame
import sys
import random
import math
import os
from enum import Enum, auto

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
P_HIT_W, P_HIT_H = 8, 8    # 画像(80×80)の約10%: コアのみ判定
PLAYER_MAX_HP    = 3
INVINCIBLE_TIME  = 120
BANK_ANGLE       = 18.0
BANK_LERP        = 0.18

# 自機弾
PB_W, PB_H  = 60, 120
PB_SPEED    = 10

# 雑魚敵
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

# 敵弾
EB_W, EB_H  = 108, 108
EB_SPEED    = 5

# 必殺技
SPECIAL_COOLDOWN = 30 * FPS
MISSILE_W        = 400
MISSILE_H        = 400


# グリッチフォントパス
FONT_GLITCH = '瀞ノグリッチゴシックH4.ttf'


# ═══════════════════════════ 状態管理 ════════════════════════
class GameState(Enum):
    TITLE    = auto()
    PLAYING  = auto()
    GAMEOVER = auto()


# ═══════════════════════ ユーティリティ ══════════════════════
def _play(snd):
    """効果音を安全に再生"""
    if snd:
        snd.play()

def load_img(path: str, size: tuple) -> pygame.Surface:
    return pygame.transform.smoothscale(
        pygame.image.load(path).convert_alpha(), size)

def load_snd(path: str) -> pygame.mixer.Sound | None:
    try:
        return pygame.mixer.Sound(path)
    except Exception:
        return None


# ═══════════════════════ アセット管理 ════════════════════════
class Assets:
    """ゲームで使う全リソースをまとめて管理するクラス"""

    def __init__(self):
        # フォント
        self.font_sys = pygame.font.SysFont(None, 28)
        self.font_g24 = self._gfont(24)   # HUD 通常
        self.font_g36 = self._gfont(36)   # タイトルメニュー
        self.font_g52 = self._gfont(52)   # READY 大文字
        self.font_g90 = self._gfont(90)   # タイトルロゴ

        # 背景画像
        self.bg_game  = pygame.transform.smoothscale(
            pygame.image.load('background.png').convert(), (SCREEN_W, SCREEN_W))
        self.bg_title = pygame.transform.smoothscale(
            pygame.image.load('title_bg.png').convert(), (SCREEN_W, SCREEN_H))

        # スプライト画像
        self.img_player  = load_img('player.png',          (P_W,       P_H))
        self.img_pbullet = load_img('bullet_player.png',   (PB_W,      PB_H))
        self.img_enemy   = load_img('enemy.png',            (E_W,       E_H))
        self.img_boss    = load_img('enemy_bear.png',       (BO_W,      BO_H))
        self.img_ebullet = load_img('bullet_enemy.png',    (EB_W,      EB_H))
        self.img_missile = load_img('special_missile.png', (MISSILE_W, MISSILE_H))
        self.img_gameover = pygame.image.load('gameover.png').convert_alpha()

        # 効果音
        self.snd_shot     = load_snd('shot.wav')
        self.snd_vo_shots = [
            load_snd('vo_shot_1.wav'),
            load_snd('vo_shot_2.wav'),
            load_snd('vo_shot_3.wav'),
        ]
        self.snd_expl    = load_snd('se_explosion.wav')
        self.snd_go_expl = load_snd('explosion.wav')
        self.snd_damage  = load_snd('vo_damage.wav')
        self.snd_dead    = load_snd('vo_dead.wav')
        self.snd_special = load_snd('vo_special.wav')

    @staticmethod
    def _gfont(size: int) -> pygame.font.Font:
        """グリッチフォント。読み込み失敗時は SysFont でフォールバック"""
        try:
            return pygame.font.Font(FONT_GLITCH, size)
        except Exception:
            return pygame.font.SysFont(None, size)


# ══════════════════════ BGM 管理 ══════════════════════════════
class MusicManager:
    """状態変化のタイミングで BGM を一度だけ切り替える"""

    # 実際に存在するファイル名を直接指定（フォールバック不要）
    _TITLE_BGM    = 'gametitle.mp3'
    _GAME_BGM     = 'bgm.mp3'
    _GAMEOVER_BGM = 'gameover.mp3'

    def __init__(self):
        self._current: str | None = None   # 現在再生中のパス

    def play_title(self):
        self._start(self._TITLE_BGM, volume=0.6)

    def play_game(self):
        self._start(self._GAME_BGM, volume=0.6)

    def play_gameover(self):
        self._start(self._GAMEOVER_BGM, volume=0.8)

    def _start(self, path: str, volume: float = 0.6):
        """同じ BGM を二重再生しない"""
        if self._current == path:
            return
        try:
            pygame.mixer.music.stop()
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play(-1)
            self._current = path
        except Exception:
            pass


# ═══════════════════════ グリッチ演出 ════════════════════════
class GlitchRenderer:
    """テキストグリッチ／シェイク描画の静的メソッド集"""

    @staticmethod
    def shake(surf: pygame.Surface, font: pygame.font.Font,
              text: str, color: tuple, x: int, y: int, intensity: int = 2):
        """テキストをランダムに数ピクセル震わせて描画"""
        s = font.render(text, True, color)
        surf.blit(s, (x + random.randint(-intensity, intensity),
                      y + random.randint(-intensity, intensity)))

    @staticmethod
    def glitch(surf: pygame.Surface, font: pygame.font.Font,
               text: str, x: int, y: int, intensity: int = 4):
        """激しいグリッチ: RGBゴーストレイヤー + 色サイクル + シェイク"""
        for gc in ((255, 0, 60), (0, 255, 200), (255, 220, 0)):
            gs = font.render(text, True, gc)
            gs.set_alpha(110)
            surf.blit(gs, (x + random.randint(-intensity, intensity),
                           y + random.randint(-intensity, intensity)))
        cycle = [WHITE, YELLOW, CYAN, (255, 80, 255), WHITE]
        color = cycle[(pygame.time.get_ticks() // 60) % len(cycle)]
        ms = font.render(text, True, color)
        surf.blit(ms, (x + random.randint(-2, 2), y + random.randint(-2, 2)))


# ══════════════════════════ HUD 描画 ══════════════════════════
class HudRenderer:
    """ゲーム中 HUD の各パーツを個別に描画するクラス"""

    def __init__(self, assets: Assets):
        self._a = assets

    def draw_score(self, surf: pygame.Surface, score: int):
        """スコア（左上、グリッチ + シェイク）"""
        GlitchRenderer.shake(surf, self._a.font_g24,
                             f"Score: {score}", WHITE, 10, 10, 1)

    def draw_lives(self, surf: pygame.Surface, hp: int):
        """残機表示（左下）✈ × N"""
        font = self._a.font_sys
        for i in range(PLAYER_MAX_HP):
            color = WHITE if i < hp else (75, 75, 75)
            surf.blit(font.render("✈", True, color),
                      (10 + i * 28, SCREEN_H - 65))
        surf.blit(font.render(f"  ×{hp}", True, WHITE),
                  (10 + PLAYER_MAX_HP * 28, SCREEN_H - 65))

    def draw_special_gauge(self, surf: pygame.Surface, charge: int):
        """必殺技ゲージ（右下、チャージ完了時はグリッチ演出）"""
        font_g = self._a.font_g24
        font_r = self._a.font_g52
        if charge >= SPECIAL_COOLDOWN:
            r_txt = "READY"
            p_txt = "(Push X Key!!)"
            GlitchRenderer.glitch(surf, font_r, r_txt,
                                  SCREEN_W - font_r.size(r_txt)[0] - 10, SCREEN_H - 82)
            GlitchRenderer.glitch(surf, font_g, p_txt,
                                  SCREEN_W - font_g.size(p_txt)[0] - 10, SCREEN_H - 44)
        else:
            secs = max(0, (SPECIAL_COOLDOWN - charge) // FPS)
            txt  = f"RECHARGING... {secs}s"
            GlitchRenderer.shake(surf, font_g, txt, GRAY,
                                 SCREEN_W - font_g.size(txt)[0] - 10, SCREEN_H - 44, 1)

    def draw_boss_hp(self, surf: pygame.Surface, boss: 'Boss | None'):
        """ボス HP（右上）"""
        if boss:
            t = self._a.font_sys.render(
                f"BOSS HP: {boss.hp} / {BOSS_HP}", True, RED)
            surf.blit(t, (SCREEN_W - t.get_width() - 10, 10))

    def draw_hint(self, surf: pygame.Surface):
        """操作ガイド（中央下）"""
        hint = self._a.font_sys.render(
            "矢印: 移動  Space: 弾  X: 必殺技", True, GRAY)
        surf.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, SCREEN_H - 22))


# ═══════════════════════ スクロール背景 ══════════════════════
class ScrollBG:
    """垂直ループスクロール背景"""

    def __init__(self, image: pygame.Surface):
        self.image = image
        self.h     = image.get_height()
        self.y     = 0

    def update(self):
        self.y = (self.y + BG_SCROLL) % self.h

    def draw(self, surf: pygame.Surface):
        for off in (-1, 0, 1):
            surf.blit(self.image, (0, self.y + off * self.h))


# ═══════════════════════════ プレイヤー ═══════════════════════
class Player(pygame.sprite.Sprite):
    """自機スプライト。バンクアニメーション・コア hitbox・無敵フレームを管理"""

    def __init__(self, img: pygame.Surface):
        super().__init__()
        self.base_image       = img
        self.image            = img
        self.rect             = img.get_rect(midbottom=(SCREEN_W // 2, SCREEN_H - 40))
        self.hitbox           = pygame.Rect(0, 0, P_HIT_W, P_HIT_H)
        self.hitbox.center    = self.rect.center
        self.cooldown         = 0
        self.hp               = PLAYER_MAX_HP
        self.invincible_timer = 0
        self.angle            = 0.0

    @property
    def invincible(self) -> bool:
        return self.invincible_timer > 0

    @property
    def blink_visible(self) -> bool:
        return (not self.invincible) or (self.invincible_timer // 5) % 2 == 0

    def take_damage(self, snd_damage) -> bool:
        """ダメージ処理。死亡したら True を返す"""
        if self.invincible:
            return False
        _play(snd_damage)
        self.hp -= 1
        self.invincible_timer = INVINCIBLE_TIME
        return self.hp <= 0

    def update(self, keys: pygame.key.ScancodeWrapper):
        # 移動
        if keys[pygame.K_LEFT]  and self.rect.left   > 0:        self.rect.x -= P_SPEED
        if keys[pygame.K_RIGHT] and self.rect.right  < SCREEN_W: self.rect.x += P_SPEED
        if keys[pygame.K_UP]    and self.rect.top    > 0:        self.rect.y -= P_SPEED
        if keys[pygame.K_DOWN]  and self.rect.bottom < SCREEN_H: self.rect.y += P_SPEED

        # バンクアニメーション（LERP 補間）
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

    def shoot(self, img: pygame.Surface) -> 'PlayerBullet | None':
        if self.cooldown == 0:
            self.cooldown = P_COOLDOWN
            return PlayerBullet(img, self.rect.centerx, self.rect.top)
        return None


# ══════════════════════════ 自機弾 ════════════════════════════
class PlayerBullet(pygame.sprite.Sprite):
    def __init__(self, img: pygame.Surface, x: int, y: int):
        super().__init__()
        self.image = img
        self.rect  = img.get_rect(midbottom=(x, y))

    def update(self):
        self.rect.y -= PB_SPEED
        if self.rect.bottom < 0:
            self.kill()


# ═══════════════════════════ 雑魚敵 ═══════════════════════════
class Enemy(pygame.sprite.Sprite):
    def __init__(self, img: pygame.Surface, speed: float):
        super().__init__()
        self.image = img
        x = random.randint(E_W // 2, SCREEN_W - E_W // 2)
        self.rect  = img.get_rect(midtop=(x, -E_H))
        self.speed = speed

    def update(self):
        self.rect.y += self.speed


# ══════════════════════════ ボス ══════════════════════════════
class Boss(pygame.sprite.Sprite):
    def __init__(self, img: pygame.Surface):
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

    def can_shoot(self) -> bool:
        if self.shoot_timer >= BOSS_SHOOT:
            self.shoot_timer = 0
            return True
        return False

    def take_hit(self) -> bool:
        """被弾処理。撃破なら True を返す"""
        self.hp -= 1
        return self.hp <= 0

    def draw_hp_bar(self, surf: pygame.Surface):
        bx, by = self.rect.left, self.rect.top - 14
        pygame.draw.rect(surf, RED,   (bx, by, BO_W, 8))
        pygame.draw.rect(surf, GREEN, (bx, by, int(BO_W * self.hp / BOSS_HP), 8))
        pygame.draw.rect(surf, WHITE, (bx, by, BO_W, 8), 1)


# ═══════════════════════════ 敵弾 ═════════════════════════════
class EnemyBullet(pygame.sprite.Sprite):
    def __init__(self, img: pygame.Surface, x: int, y: int,
                 vx: float, vy: float):
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


def _boss_shoot(img: pygame.Surface, bx: int, by: int,
                px: int, py: int, n: int = 3, spread: float = 0.28) -> list[EnemyBullet]:
    """ボスが自機へ向けて n-way 弾を生成"""
    base = math.atan2(py - by, px - bx)
    return [EnemyBullet(img, bx, by,
                        math.cos(base + (i - n // 2) * spread) * EB_SPEED,
                        math.sin(base + (i - n // 2) * spread) * EB_SPEED)
            for i in range(n)]


# ══════════════════════════ 必殺技ミサイル ════════════════════
class Missile:
    """必殺技ミサイルの状態・更新・描画をカプセル化"""

    def __init__(self, start_x: float, start_y: float):
        self.x       = start_x
        self.y       = start_y
        self.vy      = -18.0
        self.start_y = start_y
        self.scale   = 0.2
        self._flash  = 0       # 白フラッシュのアルファ値
        self.cleared = False   # 中間クリア（敵一掃）済みフラグ
        self.alive   = True    # False になったら除去

    @property
    def flash_alpha(self) -> int:
        return self._flash

    def update(self, enemies: pygame.sprite.Group,
               ebullets: pygame.sprite.Group,
               boss_grp: pygame.sprite.GroupSingle) -> int:
        """毎フレーム呼び出し。ボス撃破ボーナス点数を返す（通常は 0）"""
        bonus = 0
        self.y     += self.vy
        self.scale  = min(1.0, self.scale + 0.03)
        mid = SCREEN_H // 2

        # フラッシュ輝度計算（中間地点へ近づくにつれ白く）
        if self.y > mid:
            progress   = (self.start_y - self.y) / max(1, self.start_y - mid)
            self._flash = int(min(220, progress * 220))
        else:
            self._flash = max(0, self._flash - 18)

        # 中間地点で全敵一掃
        if not self.cleared and self.y <= mid:
            self.cleared = True
            enemies.empty()
            ebullets.empty()
            if boss_grp.sprite:
                boss_grp.empty()
                bonus = 100

        # 画面上端を抜けたら消滅
        if self.y < -(MISSILE_H * self.scale):
            self.alive   = False
            self._flash  = 0

        return bonus

    def draw(self, surf: pygame.Surface, img: pygame.Surface):
        w = max(1, int(MISSILE_W * self.scale))
        h = max(1, int(MISSILE_H * self.scale))
        scaled = pygame.transform.scale(img, (w, h))
        surf.blit(scaled, (int(self.x) - w // 2, int(self.y) - h // 2))


# ════════════════════════ シーン基底クラス ════════════════════
class Scene:
    """全シーンが継承する基底クラス"""

    def handle_event(self, ev: pygame.event.Event) -> GameState | None:
        """イベント処理。状態遷移が必要なら新 GameState を返す"""
        return None

    def update(self) -> GameState | None:
        """フレーム更新。状態遷移が必要なら新 GameState を返す"""
        return None

    def draw(self, surf: pygame.Surface):
        """描画"""
        pass


# ══════════════════════════ タイトル画面 ══════════════════════
class TitleScene(Scene):
    """タイトル画面シーン。BGM 再生・メニュー選択・「雷光」発進演出を担う"""

    def __init__(self, game: 'Game'):
        self._game   = game
        self._assets = game.assets
        self._selected = 0
        self._menu     = ['START', 'OPTION']

        # タイトルロゴ位置
        tw = self._assets.font_g90.size('雷光')[0]
        self._tx = SCREEN_W // 2 - tw // 2
        self._ty = SCREEN_H // 3 - 30

        # BGM 切り替え（一度だけ）
        game.music.play_title()

    def handle_event(self, ev: pygame.event.Event) -> GameState | None:
        if ev.type == pygame.KEYDOWN:
            if ev.key in (pygame.K_UP, pygame.K_DOWN):
                self._selected = 1 - self._selected
            if ev.key in (pygame.K_SPACE, pygame.K_RETURN):
                if self._selected == 0:
                    self._play_raikou_flash()
                    return GameState.PLAYING
        return None

    def update(self) -> GameState | None:
        return None

    def draw(self, surf: pygame.Surface):
        a = self._assets
        surf.blit(a.bg_title, (0, 0))

        # タイトルロゴ（軽くシェイク）
        GlitchRenderer.shake(surf, a.font_g90, '雷光',
                             WHITE, self._tx, self._ty, 1)

        # サブタイトル
        sub = a.font_g24.render('RAIKOU  —  SPECIAL SHOOTING', True, GRAY)
        surf.blit(sub, (SCREEN_W // 2 - sub.get_width() // 2, self._ty + 105))

        # メニュー項目
        base_y = SCREEN_H - 210
        for i, item in enumerate(self._menu):
            iy = base_y + i * 68
            if i == self._selected:
                label = f'>>  {item}'
                lx    = SCREEN_W // 2 - a.font_g36.size(label)[0] // 2
                GlitchRenderer.glitch(surf, a.font_g36, label, lx, iy, 2)
            else:
                s = a.font_g36.render(item, True, GRAY)
                surf.blit(s, (SCREEN_W // 2 - s.get_width() // 2, iy))

        # OPTION 未実装ヒント
        if self._selected == 1:
            cs = a.font_g24.render('—  COMING SOON  —', True, (90, 90, 90))
            surf.blit(cs, (SCREEN_W // 2 - cs.get_width() // 2,
                           base_y + 2 * 68 + 8))

    # ── 内部: 「雷光」発進演出（ブロッキングサブループ） ──────
    def _play_raikou_flash(self):
        """START 決定時にタイトルロゴが激しく輝き画面フラッシュ（約85フレーム）"""
        a          = self._assets
        flash_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        DURATION   = 85

        for f in range(DURATION):
            self._game.screen.blit(a.bg_title, (0, 0))

            intensity  = min(10, 1 + f // 8)
            glow_alpha = min(255, int((f / DURATION) * 255))
            ghosts     = min(7, 1 + f // 10)

            # ゴーストレイヤーで発光エフェクト
            for _ in range(ghosts):
                gc = random.choice(((255, 255, 255), YELLOW, CYAN))
                gs = a.font_g90.render('雷光', True, gc)
                gs.set_alpha(glow_alpha // (ghosts + 1))
                self._game.screen.blit(
                    gs, (self._tx + random.randint(-intensity, intensity),
                         self._ty + random.randint(-intensity, intensity)))

            # メインロゴ
            self._game.screen.blit(
                a.font_g90.render('雷光', True, WHITE), (self._tx, self._ty))

            # 後半60%から全画面ホワイトフラッシュ
            if f > DURATION * 0.6:
                alpha = min(255, int(
                    ((f - DURATION * 0.6) / (DURATION * 0.4)) * 255))
                flash_surf.fill((255, 255, 255, alpha))
                self._game.screen.blit(flash_surf, (0, 0))

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()

            pygame.display.flip()
            self._game.clock.tick(FPS)


# ══════════════════════════ プレイ画面 ════════════════════════
class PlayScene(Scene):
    """ゲームプレイシーン。スポーン・当たり判定・描画・スコア管理"""

    def __init__(self, game: 'Game'):
        self._game = game
        a = game.assets

        # スプライトグループ
        self._bg         = ScrollBG(a.bg_game)
        self._player_grp = pygame.sprite.GroupSingle(Player(a.img_player))
        self._pbullets   = pygame.sprite.Group()
        self._enemies    = pygame.sprite.Group()
        self._boss_grp   = pygame.sprite.GroupSingle()
        self._ebullets   = pygame.sprite.Group()

        # ゲーム変数
        self._score          = 0
        self._spawn_total    = 0
        self._spawn_timer    = 0
        self._e_speed        = E_SPEED_BASE
        self._special_charge = 0
        self._missile: Missile | None = None
        self._flash_surf     = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)

        self._hud = HudRenderer(a)

        # BGM 切り替え（一度だけ）
        game.music.play_game()

    @property
    def _player(self) -> Player:
        return self._player_grp.sprite

    def handle_event(self, ev: pygame.event.Event) -> GameState | None:
        a = self._game.assets
        if ev.type == pygame.KEYDOWN:
            # 通常弾
            if ev.key == pygame.K_SPACE:
                b = self._player.shoot(a.img_pbullet)
                if b:
                    self._pbullets.add(b)
                    _play(a.snd_shot)
                    _play(random.choice(a.snd_vo_shots))
            # 必殺技
            if ev.key == pygame.K_x:
                if (self._special_charge >= SPECIAL_COOLDOWN
                        and self._missile is None):
                    self._special_charge = 0
                    _play(a.snd_special)
                    p = self._player
                    self._missile = Missile(
                        float(p.rect.centerx), float(p.rect.centery))
        return None

    def update(self) -> GameState | None:
        a     = self._game.assets
        score = self._score

        # 難易度スケール
        self._e_speed  = E_SPEED_BASE + score * 0.008
        spawn_ivl      = max(SPAWN_MIN, SPAWN_BASE - score // 8)

        if self._special_charge < SPECIAL_COOLDOWN:
            self._special_charge += 1

        # 敵スポーン
        self._spawn_timer += 1
        if self._spawn_timer >= spawn_ivl:
            self._spawn_timer = 0
            self._spawn_total += 1
            if (self._spawn_total % BOSS_EVERY == 0
                    and not self._boss_grp.sprite):
                self._boss_grp.add(Boss(a.img_boss))
            else:
                self._enemies.add(Enemy(a.img_enemy, self._e_speed))

        # ボス射撃
        boss = self._boss_grp.sprite
        if boss and boss.can_shoot():
            p = self._player
            for b in _boss_shoot(a.img_ebullet,
                                  boss.rect.centerx, boss.rect.bottom,
                                  p.rect.centerx, p.rect.centery):
                self._ebullets.add(b)

        # スプライト更新
        keys = pygame.key.get_pressed()
        self._player.update(keys)
        self._pbullets.update()
        self._enemies.update()
        self._boss_grp.update()
        self._ebullets.update()
        self._bg.update()

        # 必殺技ミサイル更新
        if self._missile is not None:
            bonus = self._missile.update(
                self._enemies, self._ebullets, self._boss_grp)
            self._score += bonus
            if not self._missile.alive:
                self._missile = None

        # 当たり判定: 自機弾 vs 雑魚
        for _ in pygame.sprite.groupcollide(
                self._enemies, self._pbullets, True, True):
            self._score += 10
            _play(a.snd_expl)

        # 当たり判定: 自機弾 vs ボス
        boss = self._boss_grp.sprite   # ミサイル更新後に再取得
        if boss:
            for pb in list(self._pbullets):
                if boss.rect.colliderect(pb.rect):
                    pb.kill()
                    if boss.take_hit():
                        self._boss_grp.empty()
                        self._score += 100
                        _play(a.snd_expl)
                    break

        # 被弾判定（コア hitbox）
        if self._check_hit():
            return self._on_player_death()

        # 敵が画面下端を突破
        escaped = [e for e in self._enemies if e.rect.top >= SCREEN_H]
        for e in escaped:
            e.kill()
        if escaped:
            return self._on_player_death()

        return None

    def draw(self, surf: pygame.Surface):
        boss = self._boss_grp.sprite

        self._bg.draw(surf)
        self._enemies.draw(surf)
        self._boss_grp.draw(surf)
        if boss:
            boss.draw_hp_bar(surf)
        self._pbullets.draw(surf)
        self._ebullets.draw(surf)

        if self._player.blink_visible:
            surf.blit(self._player.image, self._player.rect)

        # 必殺技ミサイル描画
        if self._missile is not None:
            self._missile.draw(surf, self._game.assets.img_missile)
            if self._missile.flash_alpha > 0:
                self._flash_surf.fill(
                    (255, 255, 255, self._missile.flash_alpha))
                surf.blit(self._flash_surf, (0, 0))

        # HUD
        self._hud.draw_score(surf, self._score)
        self._hud.draw_lives(surf, self._player.hp)
        self._hud.draw_special_gauge(surf, self._special_charge)
        self._hud.draw_boss_hp(surf, boss)
        self._hud.draw_hint(surf)

    # ── 内部ヘルパー ─────────────────────────────────────────
    def _check_hit(self) -> bool:
        """自機コア hitbox への被弾を判定"""
        p    = self._player
        boss = self._boss_grp.sprite
        for eb in list(self._ebullets):
            if p.hitbox.colliderect(eb.rect):
                eb.kill()
                return True
        if any(p.hitbox.colliderect(e.rect) for e in self._enemies):
            return True
        return bool(boss and p.hitbox.colliderect(boss.rect))

    def _on_player_death(self) -> GameState | None:
        """被弾処理。HP がゼロになったらゲームオーバーへ遷移"""
        a = self._game.assets
        if self._player.take_damage(a.snd_damage):
            _play(a.snd_go_expl)
            _play(a.snd_dead)
            pygame.time.wait(700)
            # wait 中に溜まったキーイベントを破棄してから遷移
            pygame.event.clear()
            self._game.last_score = self._score
            return GameState.GAMEOVER
        return None


# ══════════════════════════ ゲームオーバー画面 ════════════════
class GameOverScene(Scene):
    """ゲームオーバーシーン。キー入力があるまで画面を維持し続ける"""

    # シーン生成後この秒数はキー入力を無視（誤入力防止）
    _INPUT_BLOCK_SEC = 1.0

    def __init__(self, game: 'Game'):
        self._game       = game
        self._birth_tick = pygame.time.get_ticks()   # 生成時刻を記録

        # BGM 切り替え（一度だけ）
        game.music.play_gameover()

        a = game.assets
        self._surf = pygame.transform.smoothscale(
            a.img_gameover, (SCREEN_W, SCREEN_H))
        self._hint = a.font_sys.render(
            f"Score: {game.last_score}  │  キーを押してタイトルへ戻る",
            True, GRAY)

    def _input_ready(self) -> bool:
        """生成から _INPUT_BLOCK_SEC 秒経過したら入力を受け付ける"""
        elapsed = (pygame.time.get_ticks() - self._birth_tick) / 1000.0
        return elapsed >= self._INPUT_BLOCK_SEC

    def handle_event(self, ev: pygame.event.Event) -> GameState | None:
        # 生成直後は入力を無視（wait 中に溜まったイベントの誤処理を防ぐ二重ガード）
        if not self._input_ready():
            return None
        if ev.type == pygame.KEYDOWN:
            return GameState.TITLE   # どのキーでもタイトルへ
        return None

    def update(self) -> GameState | None:
        # 自動遷移なし — キー待ちのみ
        return None

    def draw(self, surf: pygame.Surface):
        surf.blit(self._surf, (0, 0))
        # 入力受付前はヒントを薄く表示
        alpha_hint = 255 if self._input_ready() else 80
        hint = self._hint.copy()
        hint.set_alpha(alpha_hint)
        surf.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, SCREEN_H - 50))


# ════════════════════════ ゲームコントローラ ══════════════════
class Game:
    """全シーンとシステムを束ねるコントローラ"""

    def __init__(self):
        pygame.init()
        pygame.mixer.init()

        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("雷光  —  KAP Special Shooting Game")
        self.clock = pygame.time.Clock()

        self.assets     = Assets()
        self.music      = MusicManager()
        self.last_score = 0          # PlayScene → GameOverScene スコア受け渡し

        self._state: GameState = GameState.TITLE
        self._scene: Scene     = TitleScene(self)

    # ── 状態遷移 ─────────────────────────────────────────────
    def _set_state(self, new_state: GameState):
        """状態を変えてシーンを切り替える"""
        self._state = new_state
        if new_state == GameState.TITLE:
            self._scene = TitleScene(self)
        elif new_state == GameState.PLAYING:
            self._scene = PlayScene(self)
        elif new_state == GameState.GAMEOVER:
            self._scene = GameOverScene(self)

    # ── メインループ ─────────────────────────────────────────
    def run(self):
        while True:
            # イベント処理
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                next_state = self._scene.handle_event(ev)
                if next_state is not None:
                    self._set_state(next_state)
                    break   # シーンが切り替わったのでイベントループ再開

            # 更新
            next_state = self._scene.update()
            if next_state is not None:
                self._set_state(next_state)

            # 描画
            self._scene.draw(self.screen)
            pygame.display.flip()
            self.clock.tick(FPS)


# ══════════════════════════ エントリーポイント ════════════════
if __name__ == '__main__':
    Game().run()
