import pygame
import sys
import random
import math
import os
from enum import Enum, auto

# ═══════════════════════════ 定数 ════════════════════════════
SCREEN_W, SCREEN_H = 700, 900
FPS            = 60
BG_SCROLL      = 3
ASSETS_IMG_DIR = 'assets/images'

# 背景設定: (最小スコア, ファイル名, スクロール有無)
BG_CONFIGS = [
    (0,   'background.png',  True),
    (401, 'background2.png', True),
    (601, 'background3.png', True),
    (801, 'background4.png', False),
]

WHITE  = (255, 255, 255)
BLACK  = (  0,   0,   0)
RED    = (220,  50,  50)
GREEN  = (  0, 200,   0)
GRAY   = (150, 150, 150)
YELLOW = (255, 220,   0)
CYAN   = (  0, 220, 220)
GOLD   = (255, 215,   0)

# プレイヤー
P_W, P_H         = 80, 80
P_SPEED          = 5
P_COOLDOWN       = 15
P_HIT_W, P_HIT_H = 8, 8    # コアのみ当たり判定
PLAYER_MAX_HP    = 3
INVINCIBLE_TIME  = 120
BANK_ANGLE       = 18.0
BANK_LERP        = 0.18

# 自機弾
PB_W, PB_H = 60, 120
PB_SPEED   = 10

# 雑魚敵
E_W, E_H     = 270, 270
E_SPEED_BASE = 1.5
SPAWN_BASE   = 80
SPAWN_MIN    = 30

# ジグザグ敵 (Enemy2)
E2_SPEED_MUL   = 0.75
E2_ZIGZAG_AMP  = 80
E2_ZIGZAG_FREQ = 0.05

# 突進敵 (Enemy3)
E3_SPEED_MUL_SLOW = 0.5
E3_SPEED_RUSH     = 12.0
E3_RUSH_DIST      = 100

# 敵出現スコア閾値・隊列設定
E2_SPAWN_SCORE      = 100
E3_SPAWN_SCORE      = 401
FORMATION_SCORE     = 601
FORMATION_MIN       = 3
FORMATION_MAX       = 5
FORMATION_GAP       = 90
FORMATION_CHANCE    = 0.3
FORMATION_DELAY_MUL = 1.5

# ボス
BO_W, BO_H  = 140, 140
BOSS_HP     = 10
BOSS_ENTER  = 80
BOSS_SHOOT  = 112   # 攻撃間隔（フレーム）

# ボス HP バー
BOSS_BAR_W      = 420
BOSS_BAR_H      = 22
BOSS_BAR_X      = (SCREEN_W - BOSS_BAR_W) // 2
BOSS_BAR_NAME_Y = 6
BOSS_BAR_Y      = 46
BOSS_WARNING_HP = 3

# ボス登場演出
INTRO_WAIT_FRAMES  = 120
INTRO_BLINK_FRAMES = 90
INTRO_FLASH_FRAMES = 30
INTRO_BLINK_PERIOD = 6

# 敵弾
EB_W, EB_H = 108, 108
EB_SPEED   = 5

# 必殺技
SPECIAL_COOLDOWN = 30 * FPS
MISSILE_W        = 400
MISSILE_H        = 400
MISSILE_DAMAGE   = 5

# ステージ
STAGE3_SCORE          = 3001
STAGE_ANNOUNCE_FRAMES = 150

# 背景トランジション
BG_TRANSITION_FRAMES = 30

# ステージクリア演出
CLEAR_SHOW_FRAMES       = 120
CLEAR_FADE_FRAMES       = 30
CLEAR_FLY_CENTER_FRAMES = 50
CLEAR_FLY_UP_FRAMES     = 80
CLEAR_FLASH_FRAMES      = 30
STAGE2_ANNOUNCE_FRAMES  = 90

# フォントパス
FONT_GLITCH   = '瀞ノグリッチゴシックH4.ttf'
FONT_HERO_PATH = os.path.join('assets', 'fonts', 'JK-Maru-Gothic-M.otf')
FONT_ONI_PATH  = os.path.join('assets', 'fonts', 'ZenMaruGothic-Regular.ttf')

# 会話イベント
CONV_TRIGGER_SCORE  = 801
CONV_WIN_H          = 220
CONV_WIN_Y          = SCREEN_H - CONV_WIN_H - 8
CONV_FACE_SIZE      = 120
CONV_TYPEWRITER_SPF = 1
CONV_BLINK_FRAMES   = 30


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

def _score_to_stage(score: int) -> int:
    """スコアから現在のステージ番号を返す（ステージ2はボス撃破経由のみ）"""
    if score >= STAGE3_SCORE: return 3
    return 1

# ステージ別難易度係数 (speed_mul, spawn_interval_mul)
STAGE_MULS = {1: (1.0, 1.0), 2: (1.1, 0.9), 3: (1.2, 0.8)}

def _load_bg_or_fallback(filename: str, fallback: pygame.Surface) -> pygame.Surface:
    """assets/images/ から背景画像を読み込む。存在しない場合は fallback を返す"""
    path = os.path.join(ASSETS_IMG_DIR, filename)
    try:
        return pygame.transform.smoothscale(
            pygame.image.load(path).convert(), (SCREEN_W, SCREEN_H))
    except Exception:
        return fallback

def _load_enemy_or_fallback(filename: str, size: tuple,
                             color: tuple) -> pygame.Surface:
    """assets/images/から敵画像を読み込む。失敗時は色付き矩形で代替"""
    path = os.path.join(ASSETS_IMG_DIR, filename)
    try:
        return pygame.transform.smoothscale(
            pygame.image.load(path).convert_alpha(), size)
    except Exception:
        surf = pygame.Surface(size, pygame.SRCALPHA)
        pygame.draw.rect(surf, color, surf.get_rect(), border_radius=12)
        return surf

def _load_face_natural(filename: str, fallback_size: tuple,
                       fallback_color: tuple) -> pygame.Surface:
    """立ち絵画像を元のサイズのまま読み込む。失敗時は色付き矩形で代替"""
    path = os.path.join(ASSETS_IMG_DIR, filename)
    try:
        return pygame.image.load(path).convert_alpha()
    except Exception:
        surf = pygame.Surface(fallback_size, pygame.SRCALPHA)
        pygame.draw.rect(surf, fallback_color, surf.get_rect(), border_radius=12)
        return surf

def _pick_enemy_type(score: int) -> int:
    """0=通常, 1=ジグザグ, 2=突進。スコアが上がるほど2・3の比率が増加"""
    if score < E2_SPAWN_SCORE:
        return 0
    if score < E3_SPAWN_SCORE:
        return random.choices([0, 1], weights=[80, 20])[0]
    if score < FORMATION_SCORE:
        return random.choices([0, 1, 2], weights=[60, 25, 15])[0]
    t  = min(1.0, (score - FORMATION_SCORE) / 2000)
    w0 = max(20, 40 - int(t * 20))
    w2 = min(40, 15 + int(t * 25))
    return random.choices([0, 1, 2], weights=[w0, 30, w2])[0]

def _score_to_bg_idx(score: int) -> int:
    """スコアから対応する背景インデックスを返す"""
    idx = 0
    for i, (threshold, _f, _s) in enumerate(BG_CONFIGS):
        if score >= threshold:
            idx = i
    return idx

def _make_space_bg() -> pygame.Surface:
    """Stage2: 黒背景 + 白い星をランダム配置した宇宙背景"""
    surf = pygame.Surface((SCREEN_W, SCREEN_H))
    surf.fill(BLACK)
    rng = random.Random(42)   # シード固定で毎回同じ星配置
    for _ in range(200):
        x = rng.randint(0, SCREEN_W - 1)
        y = rng.randint(0, SCREEN_H - 1)
        r = rng.randint(1, 2)
        b = rng.randint(180, 255)
        pygame.draw.circle(surf, (b, b, b), (x, y), r)
    return surf

def _make_lava_bg() -> pygame.Surface:
    """Stage3: 黒背景 + 赤・オレンジの星 + 惑星っぽい円"""
    surf = pygame.Surface((SCREEN_W, SCREEN_H))
    surf.fill(BLACK)
    rng = random.Random(99)
    lava_colors = [(255, 80, 0), (255, 150, 30), (255, 50, 50), (200, 40, 0)]
    for _ in range(120):
        x = rng.randint(0, SCREEN_W - 1)
        y = rng.randint(0, SCREEN_H - 1)
        r = rng.randint(1, 2)
        pygame.draw.circle(surf, rng.choice(lava_colors), (x, y), r)
    for cx, cy, pr in [(170, 180, 55), (520, 640, 42), (360, 430, 35)]:
        pygame.draw.circle(surf, (160, 30,   0), (cx, cy), pr)
        pygame.draw.circle(surf, (210, 70,  10), (cx, cy), int(pr * 0.65))
        pygame.draw.circle(surf, (255, 130, 30), (cx, cy), int(pr * 0.3))
    return surf


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

        # 会話フォント
        self.font_hero24 = self._cfont(FONT_HERO_PATH, 24)
        self.font_oni24  = self._cfont(FONT_ONI_PATH,  24)
        self.font_oni32  = self._cfont(FONT_ONI_PATH,  32)

        # タイトル背景
        self.bg_title = pygame.transform.smoothscale(
            pygame.image.load('title_bg.png').convert(), (SCREEN_W, SCREEN_H))

        # ゲーム中背景
        _plain = pygame.Surface((SCREEN_W, SCREEN_H))
        _plain.fill((20, 20, 40))
        _fallbacks = [_plain, _make_space_bg(), _make_lava_bg(), _make_lava_bg()]
        self.bg_images = [
            _load_bg_or_fallback(cfg[1], _fallbacks[i])
            for i, cfg in enumerate(BG_CONFIGS)
        ]

        # スプライト画像
        self.img_player     = load_img('player.png',          (P_W,       P_H))
        self.img_pbullet    = load_img('bullet_player.png',   (PB_W,      PB_H))
        self.img_enemy      = load_img('enemy.png',           (E_W,       E_H))
        self.img_enemy2     = _load_enemy_or_fallback('enemy2.png',      (E_W,  E_H),  ( 80, 160, 255))
        self.img_enemy3     = _load_enemy_or_fallback('enemy3.png',      (E_W,  E_H),  (255,  80,  80))
        self.img_boss       = _load_enemy_or_fallback('enemy_bear.png',  (BO_W, BO_H), ( 80,  80, 200))
        self.img_boss_sleep = _load_enemy_or_fallback('enemy_bear2.png', (BO_W, BO_H), ( 80,  80, 160))
        self.img_ebullet    = load_img('bullet_enemy.png',    (EB_W,      EB_H))
        self.img_missile    = load_img('special_missile.png', (MISSILE_W, MISSILE_H))
        self.img_gameover   = pygame.image.load('gameover.png').convert_alpha()

        # 会話立ち絵（元サイズで読み込み、失敗時は色付き矩形）
        self.face_player = _load_face_natural(
            'player_face.png', (CONV_FACE_SIZE, CONV_FACE_SIZE), ( 80, 120, 200))
        self.face_boss   = _load_face_natural(
            'boss_face.png',   (CONV_FACE_SIZE, CONV_FACE_SIZE), (200,  60,  60))

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
        try:
            return pygame.font.Font(FONT_GLITCH, size)
        except Exception:
            return pygame.font.SysFont(None, size)

    @staticmethod
    def _cfont(path: str, size: int) -> pygame.font.Font:
        try:
            return pygame.font.Font(path, size)
        except Exception:
            return pygame.font.SysFont(None, size)


# ══════════════════════ BGM 管理 ══════════════════════════════
class MusicManager:
    """同じ BGM を二重再生しないBGM管理クラス"""

    _TITLE_BGM    = 'gametitle.mp3'
    _GAME_BGM     = 'bgm.mp3'
    _GAMEOVER_BGM = 'gameover.mp3'

    def __init__(self):
        self._current: str | None = None

    def play_title(self):
        self._start(self._TITLE_BGM, volume=0.6)

    def play_game(self):
        self._start(self._GAME_BGM, volume=0.6)

    def play_gameover(self):
        self._start(self._GAMEOVER_BGM, volume=0.8)

    def play_stage2(self):
        path = os.path.join('assets', 'sounds', 'bgm2.mp3')
        if os.path.exists(path):
            self._start(path, volume=0.6)

    def _start(self, path: str, volume: float = 0.6):
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

    @staticmethod
    def screen_glitch(surf: pygame.Surface, intensity: float = 1.0):
        """画面全体にグリッチ/ノイズ効果を描画（背景トランジション用）"""
        w, h = surf.get_size()
        colors = [(255, 0, 60), (0, 255, 200), (255, 220, 0), (255, 80, 255)]
        n_lines = max(1, int(25 * intensity))
        for _ in range(n_lines):
            y   = random.randint(0, h - 1)
            lh  = random.randint(1, max(1, int(8 * intensity)))
            col = random.choice(colors)
            s   = pygame.Surface((w, lh), pygame.SRCALPHA)
            s.fill((*col, int(100 * intensity)))
            surf.blit(s, (random.randint(-12, 12), y))
        n_slices = max(1, int(6 * intensity))
        for _ in range(n_slices):
            ry = random.randint(0, h - 2)
            sh = random.randint(2, max(2, int(15 * intensity)))
            sx = random.randint(-int(40 * intensity), int(40 * intensity))
            if sx == 0:
                continue
            region_h = min(sh, h - ry)
            if region_h <= 0:
                continue
            try:
                region = surf.subsurface(pygame.Rect(0, ry, w, region_h)).copy()
                surf.blit(region, (sx, ry))
            except Exception:
                pass


# ══════════════════════════ HUD 描画 ══════════════════════════
class HudRenderer:
    """ゲーム中 HUD の各パーツを個別に描画するクラス"""

    def __init__(self, assets: Assets):
        self._a = assets

    def draw_score(self, surf: pygame.Surface, score: int):
        GlitchRenderer.shake(surf, self._a.font_g24,
                             f"Score: {score}", WHITE, 10, 10, 1)

    def draw_lives(self, surf: pygame.Surface, hp: int):
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
            p_surf = self._a.font_sys.render(p_txt, True, BLACK)
            surf.blit(p_surf, (SCREEN_W - p_surf.get_width() - 10, SCREEN_H - 44))
        else:
            secs = max(0, (SPECIAL_COOLDOWN - charge) // FPS)
            txt  = f"RECHARGING... {secs}s"
            GlitchRenderer.shake(surf, font_g, txt, GRAY,
                                 SCREEN_W - font_g.size(txt)[0] - 10, SCREEN_H - 44, 1)

    def draw_boss_hpbar_fancy(self, surf: pygame.Surface, boss: 'Boss | None'):
        """ボス HP バー（画面上部中央・派手版）"""
        if boss is None:
            return
        a   = self._a
        hp  = boss.hp
        pct = max(0.0, hp / BOSS_HP)

        name_surf = a.font_oni32.render('⚡ ENEMY BEAR ⚡', True, GOLD)
        surf.blit(name_surf,
                  (SCREEN_W // 2 - name_surf.get_width() // 2, BOSS_BAR_NAME_Y))

        bar_rect = pygame.Rect(BOSS_BAR_X, BOSS_BAR_Y, BOSS_BAR_W, BOSS_BAR_H)
        pygame.draw.rect(surf, (55, 0, 0), bar_rect)

        r = int(220 * pct + 90 * (1 - pct))
        g = int(20  * pct)
        bar_w = max(0, int(BOSS_BAR_W * pct))
        pygame.draw.rect(surf, (r, g, 0),
                         (BOSS_BAR_X, BOSS_BAR_Y, bar_w, BOSS_BAR_H))

        seg = BOSS_BAR_W / BOSS_HP
        for i in range(1, BOSS_HP):
            sx = BOSS_BAR_X + int(seg * i)
            pygame.draw.line(surf, (160, 0, 0),
                             (sx, BOSS_BAR_Y), (sx, BOSS_BAR_Y + BOSS_BAR_H), 1)

        pygame.draw.rect(surf, GOLD, bar_rect, 2)

        hp_surf = a.font_sys.render(f'HP {hp} / {BOSS_HP}', True, WHITE)
        surf.blit(hp_surf,
                  (SCREEN_W // 2 - hp_surf.get_width() // 2,
                   BOSS_BAR_Y + BOSS_BAR_H + 3))

        if hp <= BOSS_WARNING_HP:
            if (pygame.time.get_ticks() // 300) % 2 == 0:
                w_surf = a.font_oni32.render('⚠ WARNING ⚠', True, RED)
                surf.blit(w_surf,
                          (SCREEN_W // 2 - w_surf.get_width() // 2,
                           BOSS_BAR_Y + BOSS_BAR_H + 26))

    def draw_hint(self, surf: pygame.Surface):
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
        if keys[pygame.K_LEFT]  and self.rect.left   > 0:        self.rect.x -= P_SPEED
        if keys[pygame.K_RIGHT] and self.rect.right  < SCREEN_W: self.rect.x += P_SPEED
        if keys[pygame.K_UP]    and self.rect.top    > 0:        self.rect.y -= P_SPEED
        if keys[pygame.K_DOWN]  and self.rect.bottom < SCREEN_H: self.rect.y += P_SPEED

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


# ══════════════════════════ ジグザグ敵 ════════════════════════
class Enemy2(pygame.sprite.Sprite):
    """ジグザグ型: サイン波で横揺れしながらゆっくり降下する"""

    def __init__(self, img: pygame.Surface, speed: float):
        super().__init__()
        self.image   = img
        bx = random.randint(E_W // 2, SCREEN_W - E_W // 2)
        self._base_x = float(bx)
        self._fy     = float(-E_H)
        self._t      = random.uniform(0, math.pi * 2)
        self.speed   = speed * E2_SPEED_MUL
        self.rect    = img.get_rect(midtop=(bx, -E_H))

    def update(self):
        self._t  += E2_ZIGZAG_FREQ
        self._fy += self.speed
        cx = self._base_x + math.sin(self._t) * E2_ZIGZAG_AMP
        cx = max(E_W // 2, min(SCREEN_W - E_W // 2, cx))
        self.rect.centerx = int(cx)
        self.rect.top     = int(self._fy)


# ══════════════════════════ 突進型敵 ══════════════════════════
class Enemy3(pygame.sprite.Sprite):
    """突進型: ゆっくり降下し、自機X座標に近づいたら急加速突進"""

    def __init__(self, img: pygame.Surface, speed: float,
                 get_player_x: callable):
        super().__init__()
        self.image    = img
        x = random.randint(E_W // 2, SCREEN_W - E_W // 2)
        self._fx      = float(x)
        self._fy      = float(-E_H)
        self._vy      = speed * E3_SPEED_MUL_SLOW
        self._vx      = 0.0
        self._rushing = False
        self._get_px  = get_player_x
        self.rect     = img.get_rect(midtop=(x, -E_H))

    def update(self):
        if not self._rushing:
            px = self._get_px()
            if abs(self._fx - px) < E3_RUSH_DIST:
                self._rushing = True
                dx       = px - self._fx
                self._vx = (dx / max(1, abs(dx))) * E3_SPEED_RUSH * 0.15
                self._vy = E3_SPEED_RUSH
        self._fx += self._vx
        self._fy += self._vy
        self.rect.centerx = int(self._fx)
        self.rect.top     = int(self._fy)


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
        self.cleared = False   # 中間ダメージ処理済みフラグ
        self.alive   = True    # False になったら除去

    @property
    def flash_alpha(self) -> int:
        return self._flash

    def update(self, enemies: pygame.sprite.Group,
               ebullets: pygame.sprite.Group,
               boss_grp: pygame.sprite.GroupSingle) -> int:
        """更新。ボス撃破ボーナス点数を返す（通常は 0）"""
        bonus = 0
        self.y    += self.vy
        self.scale = min(1.0, self.scale + 0.03)
        mid = SCREEN_H // 2

        if self.y > mid:
            progress    = (self.start_y - self.y) / max(1, self.start_y - mid)
            self._flash = int(min(220, progress * 220))
        else:
            self._flash = max(0, self._flash - 18)

        if not self.cleared and self.y <= mid:
            self.cleared = True
            enemies.empty()
            ebullets.empty()
            boss = boss_grp.sprite
            if boss:
                for _ in range(MISSILE_DAMAGE):
                    if boss.take_hit():
                        boss_grp.empty()
                        bonus = 100
                        break

        if self.y < -(MISSILE_H * self.scale):
            self.alive  = False
            self._flash = 0

        return bonus

    def draw(self, surf: pygame.Surface, img: pygame.Surface):
        w = max(1, int(MISSILE_W * self.scale))
        h = max(1, int(MISSILE_H * self.scale))
        scaled = pygame.transform.scale(img, (w, h))
        surf.blit(scaled, (int(self.x) - w // 2, int(self.y) - h // 2))


# ════════════════════════ 会話オーバーレイ ════════════════════
class ConversationOverlay:
    """スコア801で発動する会話イベント。PlayScene の上に重ねて描画する"""

    # (speaker: 0=主人公 / 1=赤鬼, text, font_size)
    _LINES = [
        (0, 'たのもー！悪業三昧の醜い赤鬼よ、いざ尋常に……えっ？！', 24),
        (1, '…はい、赤鬼ですが、何か御用ですか？', 24),
        (0, 'え…？あの、赤鬼…さん？えっと…もっとTPOわきまえた鬼っぽい恰好じゃないの…？虎柄は？', 24),
        (1, 'はぁぁァ？！何着ててもアタシの勝手てしょうが！！フリフリのなぁにが悪いんじゃぁぁぁァァァ！！！', 32),
    ]
    _NAMES = ['主人公', '赤鬼']

    _KEY_LOCK_FRAMES = 30   # 0.5秒キーロック（スペース連打で即飛ばし防止）

    def __init__(self, assets: 'Assets'):
        self._a        = assets
        self._line_idx = 0
        self._chars    = 0        # タイプライター: 現在表示文字数
        self._blink_t  = 0
        self.finished  = False
        self._key_lock = self._KEY_LOCK_FRAMES   # 開始直後のキー無効フレーム数

        self._win_surf = pygame.Surface((SCREEN_W, CONV_WIN_H), pygame.SRCALPHA)

        # 立ち絵: ボス=基準幅×1.5、主人公=基準幅×0.8
        _MAX_W = SCREEN_W // 2

        def _fit_face(img: pygame.Surface, target_w: int) -> pygame.Surface:
            w, h = img.get_size()
            ratio = target_w / w
            return pygame.transform.smoothscale(img, (target_w, int(h * ratio)))

        boss_face   = _fit_face(assets.face_boss,   int(_MAX_W * 1.5))
        player_face = _fit_face(assets.face_player, int(_MAX_W * 0.8))

        self._face_bright = [player_face, boss_face]
        self._face_dim    = []
        for f in self._face_bright:
            dim = f.copy()
            dim.set_alpha(128)
            self._face_dim.append(dim)

    # ── プロパティ ────────────────────────────────────────────
    @property
    def _current(self):
        return self._LINES[self._line_idx]

    def _font_for(self, speaker: int, size: int) -> pygame.font.Font:
        if speaker == 0:
            return self._a.font_hero24
        return self._a.font_oni32 if size == 32 else self._a.font_oni24

    # ── 入力 ──────────────────────────────────────────────────
    def handle_key(self, key: int):
        """Space / Z キーで文字送り"""
        if self._key_lock > 0:
            return
        if key not in (pygame.K_SPACE, pygame.K_z):
            return
        _, text, _ = self._current
        if self._chars < len(text):
            self._chars = len(text)   # 残りを一気に表示
        else:
            self._line_idx += 1
            if self._line_idx >= len(self._LINES):
                self.finished = True
            else:
                self._chars = 0

    # ── 更新 ──────────────────────────────────────────────────
    def update(self):
        if self.finished:
            return
        if self._key_lock > 0:
            self._key_lock -= 1
            return
        self._blink_t += 1
        _, text, _ = self._current
        if self._chars < len(text):
            self._chars = min(len(text), self._chars + CONV_TYPEWRITER_SPF)

    # ── 描画 ──────────────────────────────────────────────────
    def draw(self, surf: pygame.Surface):
        if self.finished:
            return

        # キーロック中: 画面中央に「Loading...」を表示して通常描画をスキップ
        if self._key_lock > 0:
            loading = self._a.font_g24.render('Loading...', True, WHITE)
            surf.blit(loading, (SCREEN_W // 2 - loading.get_width()  // 2,
                                SCREEN_H // 2 - loading.get_height() // 2))
            return

        speaker, text, font_size = self._current

        # 立ち絵（背面）
        for i in range(2):
            face_img = self._face_bright[i] if i == speaker else self._face_dim[i]
            fw, fh = face_img.get_size()
            fx = 0 if i == 0 else SCREEN_W - fw
            surf.blit(face_img, (fx, SCREEN_H - fh))

        # 会話ウィンドウ（前面）
        self._win_surf.fill((0, 0, 0, 185))
        surf.blit(self._win_surf, (0, CONV_WIN_Y))
        pygame.draw.rect(surf, GOLD, (0, CONV_WIN_Y, SCREEN_W, CONV_WIN_H), 2)

        text_x = 12
        text_w = SCREEN_W - 24

        # 話者名
        name_font  = self._a.font_hero24 if speaker == 0 else self._a.font_oni24
        name_color = (180, 210, 255) if speaker == 0 else (255, 160, 160)
        surf.blit(name_font.render(self._NAMES[speaker], True, name_color),
                  (text_x, CONV_WIN_Y + 8))

        # セリフ（タイプライター、最後のセリフは横シェイク）
        font      = self._font_for(speaker, font_size)
        displayed = text[:self._chars]
        sx        = text_x + (random.randint(-3, 3) if font_size == 32 and self._chars > 0 else 0)
        self._draw_wrapped(surf, font, displayed, sx, CONV_WIN_Y + 38, text_w, WHITE)

        # ▼ 点滅（全文字表示済みのときのみ）
        if self._chars >= len(text) and (self._blink_t // CONV_BLINK_FRAMES) % 2 == 0:
            arr = name_font.render('▼', True, WHITE)
            surf.blit(arr, (SCREEN_W - arr.get_width() - 12,
                            CONV_WIN_Y + CONV_WIN_H - arr.get_height() - 8))

    # ── 内部ヘルパー ──────────────────────────────────────────
    @staticmethod
    def _draw_wrapped(surf: pygame.Surface, font: pygame.font.Font,
                      text: str, x: int, y: int, max_w: int,
                      color: tuple):
        """日本語文字単位で折り返してテキストを描画する"""
        line = ''
        for ch in text:
            test = line + ch
            if font.size(test)[0] > max_w:
                surf.blit(font.render(line, True, color), (x, y))
                y   += font.get_linesize()
                line = ch
            else:
                line = test
        if line:
            surf.blit(font.render(line, True, color), (x, y))


# ════════════════════════ ボス登場演出 ════════════════════════
class BossIntroOverlay:
    """会話終了後に再生するボス登場アニメーション。
    静止 → 点滅 → 白フラッシュフェードアウト の3フェーズ。
    done フラグが True になったらボス戦を開始してよい。
    """

    _PHASE_WAIT  = 'wait'
    _PHASE_BLINK = 'blink'
    _PHASE_FLASH = 'flash'

    def __init__(self, assets: 'Assets'):
        self._a     = assets
        self._t     = 0
        self._phase = self._PHASE_WAIT
        self.done   = False

        self._flash_surf  = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        self._flash_alpha = 255
        self._bx = SCREEN_W // 2 - BO_W // 2
        self._by = SCREEN_H // 2 - BO_H // 2 - 90

    def update(self):
        if self.done:
            return
        self._t += 1

        if self._phase == self._PHASE_WAIT:
            if self._t >= INTRO_WAIT_FRAMES:
                self._phase = self._PHASE_BLINK
                self._t = 0

        elif self._phase == self._PHASE_BLINK:
            if self._t >= INTRO_BLINK_FRAMES:
                self._phase      = self._PHASE_FLASH
                self._flash_alpha = 255
                self._t = 0

        elif self._phase == self._PHASE_FLASH:
            self._flash_alpha = max(
                0, 255 - int(self._t / INTRO_FLASH_FRAMES * 255))
            if self._t >= INTRO_FLASH_FRAMES:
                self.done = True

    def draw(self, surf: pygame.Surface):
        if self.done:
            return

        if self._phase == self._PHASE_WAIT:
            surf.blit(self._a.img_boss_sleep, (self._bx, self._by))

        elif self._phase == self._PHASE_BLINK:
            if (self._t // INTRO_BLINK_PERIOD) % 2 == 0:
                surf.blit(self._a.img_boss_sleep, (self._bx, self._by))

        elif self._phase == self._PHASE_FLASH:
            surf.blit(self._a.img_boss_sleep, (self._bx, self._by))
            if self._flash_alpha > 0:
                self._flash_surf.fill((255, 255, 255, self._flash_alpha))
                surf.blit(self._flash_surf, (0, 0))


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

        tw = self._assets.font_g90.size('雷光')[0]
        self._tx = SCREEN_W // 2 - tw // 2
        self._ty = SCREEN_H // 3 - 30
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

        GlitchRenderer.shake(surf, a.font_g90, '雷光',
                             WHITE, self._tx, self._ty, 1)

        sub = a.font_g24.render('RAIKOU  —  SPECIAL SHOOTING', True, GRAY)
        surf.blit(sub, (SCREEN_W // 2 - sub.get_width() // 2, self._ty + 105))

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

            for _ in range(ghosts):
                gc = random.choice(((255, 255, 255), YELLOW, CYAN))
                gs = a.font_g90.render('雷光', True, gc)
                gs.set_alpha(glow_alpha // (ghosts + 1))
                self._game.screen.blit(
                    gs, (self._tx + random.randint(-intensity, intensity),
                         self._ty + random.randint(-intensity, intensity)))

            self._game.screen.blit(
                a.font_g90.render('雷光', True, WHITE), (self._tx, self._ty))

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


# ══════════════════ ステージクリア演出 ════════════════════════
class StageClearOverlay:
    """ボス撃破後のステージクリア演出。
    テキスト表示 → フェードアウト → 自機飛び去り → 白フラッシュ の4フェーズ。
    """

    def __init__(self, assets: 'Assets', player_x: int, player_y: int):
        self._a      = assets
        self._timer  = 0
        self._phase  = 'show'   # show → fade → fly → flash
        self.done    = False

        # 自機飛び去り用
        self._px    = float(player_x)
        self._py    = float(player_y)
        self._pvy   = 0.0
        self._pscale = 1.0

        # フラッシュ用
        self._flash_surf  = pygame.Surface((SCREEN_W, SCREEN_H))
        self._flash_surf.fill(WHITE)
        self._flash_alpha = 0

        self._font_clear = pygame.font.SysFont(None, 64)

    @property
    def hide_player(self) -> bool:
        """True の間は PlayScene の通常自機描画を抑制する"""
        return self._phase in ('fly', 'flash')

    def update(self):
        self._timer += 1
        if self._phase == 'show':
            if self._timer >= CLEAR_SHOW_FRAMES:
                self._timer = 0
                self._phase = 'fade'

        elif self._phase == 'fade':
            if self._timer >= CLEAR_FADE_FRAMES:
                self._timer = 0
                self._phase = 'fly'

        elif self._phase == 'fly':
            # 前半: 画面中央Xへ移動
            if self._timer <= CLEAR_FLY_CENTER_FRAMES:
                cx = SCREEN_W // 2
                self._px += (cx - self._px) * 0.1
            else:
                # 後半: 上へ加速しながら縮小
                self._pvy   = min(self._pvy + 0.7, 28.0)
                self._py   -= self._pvy
                self._pscale = max(0.05, self._pscale - 0.012)
            if self._timer >= CLEAR_FLY_CENTER_FRAMES + CLEAR_FLY_UP_FRAMES:
                self._timer       = 0
                self._phase       = 'flash'
                self._flash_alpha = 255

        elif self._phase == 'flash':
            self._flash_alpha = max(
                0, int(255 * (1 - self._timer / CLEAR_FLASH_FRAMES)))
            if self._timer >= CLEAR_FLASH_FRAMES:
                self.done = True

    def draw(self, surf: pygame.Surface, player_img: pygame.Surface):
        if self.done:
            return

        if self._phase == 'show':
            self._draw_clear_text(surf, 255)

        elif self._phase == 'fade':
            alpha = int(255 * (1 - self._timer / CLEAR_FADE_FRAMES))
            self._draw_clear_text(surf, alpha)

        elif self._phase == 'fly':
            w = max(1, int(P_W * self._pscale))
            h = max(1, int(P_H * self._pscale))
            img = pygame.transform.smoothscale(player_img, (w, h))
            surf.blit(img, (int(self._px) - w // 2, int(self._py) - h // 2))

        elif self._phase == 'flash':
            self._flash_surf.set_alpha(self._flash_alpha)
            surf.blit(self._flash_surf, (0, 0))

    def _draw_clear_text(self, surf: pygame.Surface, alpha: int):
        rendered = self._font_clear.render('STAGE 1  CLEAR', True, WHITE)
        rendered.set_alpha(alpha)
        x = SCREEN_W // 2 - rendered.get_width()  // 2
        y = SCREEN_H // 2 - rendered.get_height() // 2
        surf.blit(rendered, (x, y))


# ══════════════════════════ プレイ画面 ════════════════════════
class PlayScene(Scene):
    """ゲームプレイシーン。スポーン・当たり判定・描画・スコア管理"""

    def __init__(self, game: 'Game'):
        self._game = game
        a = game.assets

        # 背景（スコア連動）
        self._bg_list        = [ScrollBG(img) for img in a.bg_images]
        self._bg_scrollable  = [cfg[2] for cfg in BG_CONFIGS]
        self._current_bg_idx = 0
        self._bg             = self._bg_list[0]
        self._player_grp = pygame.sprite.GroupSingle(Player(a.img_player))
        self._pbullets   = pygame.sprite.Group()
        self._enemies    = pygame.sprite.Group()
        self._boss_grp   = pygame.sprite.GroupSingle()
        self._ebullets   = pygame.sprite.Group()

        # ゲーム変数
        self._score          = 0
        self._spawn_total    = 0
        self._spawn_timer    = 0
        self._spawn_ivl      = SPAWN_BASE   # 隊列後ディレイ計算用
        self._e_speed        = E_SPEED_BASE
        self._special_charge = 0
        self._missile: Missile | None = None
        self._flash_surf     = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        self._current_stage        = 1
        self._stage_announce_timer = 0

        # 背景トランジション
        self._bg_transition_timer = 0
        self._bg_pending_idx      = -1

        # 会話イベント → ボス登場演出 → ステージクリア演出
        self._conv_triggered  = False
        self._conv_overlay:  ConversationOverlay | None = None
        self._boss_intro:    BossIntroOverlay    | None = None
        self._stage_clear:   StageClearOverlay   | None = None
        self._stage2_announce_timer = 0

        # Stage2用手続き型スペース背景（background2.pngは使用しない）
        self._space_bg = ScrollBG(_make_space_bg())

        self._font_announce = pygame.font.SysFont(None, 64)
        self._hud = HudRenderer(a)

        # BGM 切り替え（一度だけ）
        game.music.play_game()

    @property
    def _player(self) -> Player:
        return self._player_grp.sprite

    def handle_event(self, ev: pygame.event.Event) -> GameState | None:
        if self._conv_overlay is not None:
            if ev.type == pygame.KEYDOWN:
                self._conv_overlay.handle_key(ev.key)
            return None

        a = self._game.assets
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_SPACE:
                b = self._player.shoot(a.img_pbullet)
                if b:
                    self._pbullets.add(b)
                    _play(a.snd_shot)
                    _play(random.choice(a.snd_vo_shots))
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
        # 会話オーバーレイ中: ゲームロジックをすべて停止
        if self._conv_overlay is not None:
            self._conv_overlay.update()
            if self._conv_overlay.finished:
                self._conv_overlay = None
                self._boss_intro   = BossIntroOverlay(self._game.assets)  # ボス演出へ
            return None

        if self._boss_intro is not None:
            self._boss_intro.update()
            if self._boss_intro.done:
                self._boss_intro = None
                self._start_boss_battle()
            return None

        if self._stage_clear is not None:
            self._stage_clear.update()
            if self._stage_clear.done:
                self._stage_clear = None
                self._start_stage2()
            return None

        if self._stage2_announce_timer > 0:
            self._stage2_announce_timer -= 1

        a     = self._game.assets
        score = self._score

        if not self._conv_triggered and score >= CONV_TRIGGER_SCORE:
            self._conv_triggered = True
            self._enemies.empty()
            self._ebullets.empty()
            self._pbullets.empty()
            self._conv_overlay = ConversationOverlay(a)
            return None

        # 背景切り替え（ステージ2以降はスコア連動を無効）
        if self._current_stage < 2:
            new_bg_idx = _score_to_bg_idx(score)
            if new_bg_idx != self._current_bg_idx and self._bg_pending_idx == -1:
                self._bg_pending_idx      = new_bg_idx
                self._bg_transition_timer = BG_TRANSITION_FRAMES
            if self._bg_pending_idx != -1:
                self._bg_transition_timer -= 1
                if self._bg_transition_timer <= 0:
                    self._current_bg_idx = self._bg_pending_idx
                    self._bg             = self._bg_list[self._bg_pending_idx]
                    self._bg_pending_idx = -1

        new_stage = _score_to_stage(score)
        if new_stage > self._current_stage:
            self._current_stage        = new_stage
            self._stage_announce_timer = STAGE_ANNOUNCE_FRAMES
        if self._stage_announce_timer > 0:
            self._stage_announce_timer -= 1

        # 難易度スケール（ステージ係数適用）
        s_mul, p_mul      = STAGE_MULS[self._current_stage]
        self._e_speed     = (E_SPEED_BASE + score * 0.008) * s_mul
        spawn_ivl         = max(SPAWN_MIN, int((SPAWN_BASE - score // 8) * p_mul))
        if score >= CONV_TRIGGER_SCORE:
            spawn_ivl = int(spawn_ivl / 0.7)
        self._spawn_ivl   = spawn_ivl

        if self._special_charge < SPECIAL_COOLDOWN:
            self._special_charge += 1

        self._spawn_timer += 1
        if self._spawn_timer >= spawn_ivl:
            self._spawn_timer = 0
            self._spawn_total += 1
            self._spawn_enemy()

        boss = self._boss_grp.sprite
        if boss and boss.can_shoot():
            p = self._player
            for b in _boss_shoot(a.img_ebullet,
                                  boss.rect.centerx, boss.rect.bottom,
                                  p.rect.centerx, p.rect.centery):
                self._ebullets.add(b)

        keys = pygame.key.get_pressed()
        self._player.update(keys)
        self._pbullets.update()
        self._enemies.update()
        self._boss_grp.update()
        self._ebullets.update()
        if self._bg_scrollable[self._current_bg_idx]:
            self._bg.update()

        if self._missile is not None:
            _was_boss = self._boss_grp.sprite is not None
            bonus = self._missile.update(
                self._enemies, self._ebullets, self._boss_grp)
            self._score += bonus
            if not self._missile.alive:
                self._missile = None
            if _was_boss and not self._boss_grp.sprite and self._stage_clear is None:
                p = self._player
                self._stage_clear = StageClearOverlay(
                    a, p.rect.centerx, p.rect.centery)

        # 当たり判定: 自機弾 vs 雑魚
        for _ in pygame.sprite.groupcollide(
                self._enemies, self._pbullets, True, True):
            self._score += 10
            _play(a.snd_expl)

        # 当たり判定: 自機弾 vs ボス
        boss = self._boss_grp.sprite
        if boss:
            for pb in list(self._pbullets):
                if boss.rect.colliderect(pb.rect):
                    pb.kill()
                    if boss.take_hit():
                        self._boss_grp.empty()
                        self._score += 100
                        _play(a.snd_expl)
                        p = self._player
                        self._stage_clear = StageClearOverlay(
                            a, p.rect.centerx, p.rect.centery)
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

        # 自機描画（ステージクリア飛び去り中は抑制）
        hiding = (self._stage_clear is not None and self._stage_clear.hide_player)
        if self._player.blink_visible and not hiding:
            surf.blit(self._player.image, self._player.rect)

        # 必殺技ミサイル描画
        if self._missile is not None:
            self._missile.draw(surf, self._game.assets.img_missile)
            if self._missile.flash_alpha > 0:
                self._flash_surf.fill(
                    (255, 255, 255, self._missile.flash_alpha))
                surf.blit(self._flash_surf, (0, 0))

        if self._stage_announce_timer > 0:
            txt = f"STAGE  {self._current_stage}"
            fnt = self._game.assets.font_g52
            tx  = SCREEN_W // 2 - fnt.size(txt)[0] // 2
            ty  = SCREEN_H // 2 - fnt.size(txt)[1] // 2
            GlitchRenderer.glitch(surf, fnt, txt, tx, ty, 6)

        # HUD
        self._hud.draw_score(surf, self._score)
        self._hud.draw_lives(surf, self._player.hp)
        self._hud.draw_special_gauge(surf, self._special_charge)
        self._hud.draw_boss_hpbar_fancy(surf, boss)
        self._hud.draw_hint(surf)

        if self._bg_transition_timer > 0:
            GlitchRenderer.screen_glitch(
                surf, self._bg_transition_timer / BG_TRANSITION_FRAMES)

        if self._conv_overlay is not None:
            self._conv_overlay.draw(surf)
        if self._boss_intro is not None:
            self._boss_intro.draw(surf)
        if self._stage_clear is not None:
            self._stage_clear.draw(surf, self._game.assets.img_player)

        # ステージ2アナウンス
        if self._stage2_announce_timer > 0:
            txt = 'STAGE  2'
            tx  = SCREEN_W // 2 - self._font_announce.size(txt)[0] // 2
            ty  = SCREEN_H // 2 - self._font_announce.size(txt)[1] // 2
            surf.blit(self._font_announce.render(txt, True, WHITE), (tx, ty))

    # ── ボス戦開始 ────────────────────────────────────────────
    def _start_boss_battle(self):
        self._boss_grp.add(Boss(self._game.assets.img_boss))

    # ── ステージ2移行 ──────────────────────────────────────────
    def _start_stage2(self):
        self._game.music.play_stage2()
        self._bg_list[1]       = self._space_bg
        self._bg               = self._space_bg
        self._current_bg_idx   = 1
        self._bg_scrollable[1] = True
        self._enemies.empty()
        self._ebullets.empty()
        self._pbullets.empty()
        self._missile = None
        p = self._player
        p.rect.centerx = SCREEN_W // 2
        p.rect.bottom  = SCREEN_H - 80
        self._current_stage         = 2
        self._stage2_announce_timer = STAGE2_ANNOUNCE_FRAMES
        self._spawn_timer           = 0

    # ── スポーンヘルパー ──────────────────────────────────────
    def _spawn_enemy(self):
        """スコアに応じた敵タイプを1体 or 隊列でスポーン"""
        score = self._score
        if score >= FORMATION_SCORE and random.random() < FORMATION_CHANCE:
            self._spawn_formation()
        else:
            self._add_single_enemy(_pick_enemy_type(score))

    def _spawn_formation(self):
        """同じ敵タイプを縦に連ねて出現させる"""
        etype = _pick_enemy_type(self._score)
        count = random.randint(FORMATION_MIN, FORMATION_MAX)
        for i in range(count):
            self._add_single_enemy(etype, y_offset=-(i * FORMATION_GAP))
        self._spawn_timer = -int(self._spawn_ivl * (FORMATION_DELAY_MUL - 1))

    def _add_single_enemy(self, etype: int, y_offset: int = 0):
        a = self._game.assets
        if etype == 1:
            e = Enemy2(a.img_enemy2, self._e_speed)
        elif etype == 2:
            e = Enemy3(a.img_enemy3, self._e_speed,
                       lambda: self._player.rect.centerx)
        else:
            e = Enemy(a.img_enemy, self._e_speed)
        if y_offset != 0:
            e.rect.y += y_offset
            if hasattr(e, '_fy'):
                e._fy += y_offset
        self._enemies.add(e)

    # ── 内部ヘルパー ──────────────────────────────────────────
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

    _INPUT_BLOCK_SEC = 1.0

    def __init__(self, game: 'Game'):
        self._game       = game
        self._birth_tick = pygame.time.get_ticks()
        game.music.play_gameover()

        a = game.assets
        self._surf = pygame.transform.smoothscale(
            a.img_gameover, (SCREEN_W, SCREEN_H))
        self._hint = a.font_sys.render(
            f"Score: {game.last_score}  │  キーを押してタイトルへ戻る",
            True, GRAY)

    def _input_ready(self) -> bool:
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
        return None

    def draw(self, surf: pygame.Surface):
        surf.blit(self._surf, (0, 0))
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
        self.last_score = 0

        self._state: GameState = GameState.TITLE
        self._scene: Scene     = TitleScene(self)

    # ── 状態遷移 ─────────────────────────────────────────────
    def _set_state(self, new_state: GameState):
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
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit(); sys.exit()
                next_state = self._scene.handle_event(ev)
                if next_state is not None:
                    self._set_state(next_state)
                    break
            next_state = self._scene.update()
            if next_state is not None:
                self._set_state(next_state)
            self._scene.draw(self.screen)
            pygame.display.flip()
            self.clock.tick(FPS)


# ══════════════════════════ エントリーポイント ════════════════
if __name__ == '__main__':
    Game().run()
