# -*- coding: utf-8 -*-
import os
from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.storage.jsonstore import JsonStore
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.slider import Slider
from kivy.uix.spinner import Spinner
from kivy.uix.switch import Switch
from kivy.graphics import Color, Rectangle


# -----------------------
# 安全工具：字体/资源路径
# -----------------------
def asset_path(filename: str) -> str:
    return os.path.join(os.path.dirname(__file__), filename)

def pick_font() -> str:
    # 你已上传的字体文件名（在仓库根目录）
    p = asset_path("NotoSansSC-VariableFont_wght.ttf")
    return p if os.path.exists(p) else ""


# -----------------------
# 全局配置（持久化）
# -----------------------
class GameConfig:
    def __init__(self):
        self.store = JsonStore(asset_path("settings.json"))
        self.music_on = True
        self.volume = 0.8
        self.difficulty = "普通"   # 影响速度
        self.load()

    def load(self):
        if self.store.exists("cfg"):
            d = self.store.get("cfg")
            self.music_on = bool(d.get("music_on", True))
            self.volume = float(d.get("volume", 0.8))
            self.difficulty = str(d.get("difficulty", "普通"))

    def save(self):
        self.store.put("cfg",
                       music_on=self.music_on,
                       volume=self.volume,
                       difficulty=self.difficulty)


# -----------------------
# 音乐控制（不炸：集中管理）
# -----------------------
class MusicBus:
    def __init__(self, cfg: GameConfig):
        self.cfg = cfg
        self.bgm = None

    def load(self):
        if self.bgm is None:
            self.bgm = SoundLoader.load(asset_path("bgm.mp3"))
            if self.bgm:
                self.bgm.loop = True
        self.apply()

    def apply(self):
        if not self.bgm:
            return
        self.bgm.volume = max(0.0, min(1.0, self.cfg.volume))
        if self.cfg.music_on:
            # 避免重复 play
            if self.bgm.state != "play":
                self.bgm.play()
        else:
            self.bgm.stop()

    def stop(self):
        if self.bgm:
            self.bgm.stop()


# -----------------------
# 基础UI组件
# -----------------------
def ui_btn(text, on_press=None, font_name="", height_dp=52):
    b = Button(
        text=text,
        size_hint=(1, None),
        height=dp(height_dp),
        font_name=font_name if font_name else None
    )
    if on_press:
        b.bind(on_press=on_press)
    return b


# -----------------------
# 页面：主菜单
# -----------------------
class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        app = App.get_running_app()
        font = app.font_name

        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))

        root.add_widget(Label(
            text="欢迎静静来到我的世界！",
            font_name=font if font else None,
            font_size="22sp",
            size_hint=(1, None),
            height=dp(90)
        ))

        root.add_widget(ui_btn("开始", self.on_start, font))
        root.add_widget(ui_btn("设置", self.on_settings, font))
        root.add_widget(ui_btn("退出", self.on_quit, font))

        root.add_widget(Label(text="", size_hint=(1, 1)))
        self.add_widget(root)

    def on_start(self, *args):
        app = App.get_running_app()
        # 进入游戏前再统一加载/应用音乐（不炸）
        app.music.load()
        self.manager.current = "game"
        self.manager.get_screen("game").start_new_game()

    def on_settings(self, *args):
        self.manager.current = "settings"

    def on_quit(self, *args):
        App.get_running_app().stop()
# -----------------------
# 页面：设置
# -----------------------
class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        app = App.get_running_app()
        font = app.font_name

        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))

        root.add_widget(Label(text="设置", font_name=font if font else None, font_size="20sp",
                              size_hint=(1, None), height=dp(60)))

        # 音乐开关
        row1 = BoxLayout(size_hint=(1, None), height=dp(52))
        row1.add_widget(Label(text="音乐开关", font_name=font if font else None))
        self.sw_music = Switch(active=app.cfg.music_on)
        self.sw_music.bind(active=self.on_music_toggle)
        row1.add_widget(self.sw_music)
        root.add_widget(row1)

        # 音量
        root.add_widget(Label(text="音量", font_name=font if font else None,
                              size_hint=(1, None), height=dp(28)))
        self.slider_vol = Slider(min=0.0, max=1.0, value=app.cfg.volume)
        self.slider_vol.bind(value=self.on_volume)
        root.add_widget(self.slider_vol)

        # 难度
        root.add_widget(Label(text="难度（速度）", font_name=font if font else None,
                              size_hint=(1, None), height=dp(28)))
        self.spn = Spinner(
            text=app.cfg.difficulty,
            values=("简单", "普通", "困难"),
            size_hint=(1, None),
            height=dp(52),
            font_name=font if font else None
        )
        self.spn.bind(text=self.on_difficulty)
        root.add_widget(self.spn)

        root.add_widget(ui_btn("返回主菜单", self.on_back, font))
        root.add_widget(Label(text="", size_hint=(1, 1)))
        self.add_widget(root)

    def on_music_toggle(self, instance, value):
        app = App.get_running_app()
        app.cfg.music_on = bool(value)
        app.cfg.save()
        app.music.apply()

    def on_volume(self, instance, value):
        app = App.get_running_app()
        app.cfg.volume = float(value)
        app.cfg.save()
        app.music.apply()

    def on_difficulty(self, instance, text):
        app = App.get_running_app()
        app.cfg.difficulty = str(text)
        app.cfg.save()
        # 游戏内实时生效（不炸：只改数值，不重建对象）
        if app.sm.has_screen("game"):
            app.sm.get_screen("game").apply_difficulty()

    def on_back(self, *args):
        self.manager.current = "menu"


# -----------------------
# 对打核心：极简“激龟对打原型”
# 不炸策略：不用物理引擎，不用复杂贴图，先用矩形+数值状态机。
# -----------------------
class ArenaWidget(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # 角色状态
        self.player_pos = [dp(60), dp(200)]
        self.enemy_pos = [dp(260), dp(420)]
        self.player_hp = 3
        self.score = 0

        self.player_size = [dp(44), dp(44)]
        self.enemy_size = [dp(44), dp(44)]

        # 移动/攻击参数（受难度影响）
        self.player_speed = dp(4)
        self.enemy_speed = dp(2.2)
        self.enemy_aggressive = 1.0

        self.attack_cd = 0.0

        with self.canvas:
            Color(0.08, 0.08, 0.08, 1)
            self.bg = Rectangle(pos=self.pos, size=self.size)
            # 玩家
            Color(0.2, 0.8, 0.4, 1)
            self.player_rect = Rectangle(pos=self.player_pos, size=self.player_size)
            # 敌人
            Color(0.9, 0.3, 0.3, 1)
            self.enemy_rect = Rectangle(pos=self.enemy_pos, size=self.enemy_size)

        self.bind(pos=self._redraw, size=self._redraw)

        # 输入状态（按钮按住）
        self.hold = {"up": False, "down": False, "left": False, "right": False}

        self._ev = None

    def _redraw(self, *args):
        self.bg.pos = self.pos
        self.bg.size = self.size

    def start(self):
        self.stop()
        self._ev = Clock.schedule_interval(self.update, 1 / 60.0)

    def stop(self):
        if self._ev:
            self._ev.cancel()
            self._ev = None

    def reset(self):
        self.player_pos = [dp(60), dp(200)]
        self.enemy_pos = [dp(260), dp(420)]
        self.player_hp = 3
        self.score = 0
        self.attack_cd = 0.0
        self._apply_rects()

    def set_difficulty(self, diff: str):
        # 不炸：只改数字，不改结构
        if diff == "简单":
            self.enemy_speed = dp(1.8)
            self.enemy_aggressive = 0.85
        elif diff == "困难":
            self.enemy_speed = dp(3.2)
            self.enemy_aggressive = 1.25
        else:
            self.enemy_speed = dp(2.2)
            self.enemy_aggressive = 1.0

    def _apply_rects(self):
        self.player_rect.pos = self.player_pos
        self.enemy_rect.pos = self.enemy_pos

    def _clamp_in_bounds(self, pos, size):
        # arena 边界：控在窗口内（不炸：不依赖外部坐标系）
        w, h = self.width, self.height
        x = max(0, min(w - size[0], pos[0]))
        y = max(0, min(h - size[1], pos[1]))
        return [x, y]

    def player_attack(self):
        # 简单近战：距离足够近就打到
        if self.attack_cd > 0:
            return
        self.attack_cd = 0.35

        px, py = self.player_pos
        ex, ey = self.enemy_pos
        dx = (px - ex)
        dy = (py - ey)
        if dx * dx + dy * dy <= (dp(80) ** 2):
            self.score += 1
            # 敌人被打退一点
            self.enemy_pos[0] -= dx * 0.15
            self.enemy_pos[1] -= dy * 0.15
            self.enemy_pos = self._clamp_in_bounds(self.enemy_pos, self.enemy_size)

    def update(self, dt):
        # 冷却
        if self.attack_cd > 0:
            self.attack_cd = max(0.0, self.attack_cd - dt)

        # 玩家移动
        vx = 0
        vy = 0
        if self.hold["left"]:
            vx -= 1
        if self.hold["right"]:
            vx += 1
        if self.hold["up"]:
            vy += 1
        if self.hold["down"]:
            vy -= 1

        self.player_pos[0] += vx * self.player_speed
        self.player_pos[1] += vy * self.player_speed
        self.player_pos = self._clamp_in_bounds(self.player_pos, self.player_size)

        # 敌人追踪（极简AI）
        px, py = self.player_pos
        ex, ey = self.enemy_pos
        if px > ex:
            ex += self.enemy_speed * self.enemy_aggressive
        if px < ex:
            ex -= self.enemy_speed * self.enemy_aggressive
        if py > ey:
            ey += self.enemy_speed * self.enemy_aggressive
        if py < ey:
            ey -= self.enemy_speed * self.enemy_aggressive

        self.enemy_pos = self._clamp_in_bounds([ex, ey], self.enemy_size)

        # 碰撞：敌人贴到玩家就扣血并弹开
        if self._rect_hit(self.player_pos, self.player_size, self.enemy_pos, self.enemy_size):
            self.player_hp -= 1
            # 弹开
            self.enemy_pos[0] += dp(60)
            self.enemy_pos[1] += dp(60)
            self.enemy_pos = self._clamp_in_bounds(self.enemy_pos, self.enemy_size)

            if self.player_hp <= 0:
                # 通知上层失败（不炸：用回调，不直接切screen）
                if hasattr(self, "on_fail") and callable(self.on_fail):
                    self.on_fail(self.score)
                return

        self._apply_rects()

        # 通知上层刷新HUD
        if hasattr(self, "on_hud") and callable(self.on_hud):
            self.on_hud(self.player_hp, self.score)

    @staticmethod
    def _rect_hit(p1, s1, p2, s2):
        x1, y1 = p1
        w1, h1 = s1
        x2, y2 = p2
        w2, h2 = s2
        return not (x1 + w1 < x2 or x2 + w2 < x1 or y1 + h1 < y2 or y2 + h2 < y1)

# -----------------------
# 页面：游戏（含暂停入口）
# -----------------------
class GameScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        app = App.get_running_app()
        font = app.font_name

        root = BoxLayout(orientation="vertical")

        # 顶部HUD
        hud = BoxLayout(size_hint=(1, None), height=dp(52), padding=dp(10), spacing=dp(10))
        self.lbl_hud = Label(text="HP: 3  分数: 0", font_name=font if font else None)
        btn_pause = Button(text="暂停", size_hint=(None, 1), width=dp(90),
                           font_name=font if font else None)
        btn_pause.bind(on_press=self.on_pause)
        hud.add_widget(self.lbl_hud)
        hud.add_widget(btn_pause)
        root.add_widget(hud)

        # 对战场地
        self.arena = ArenaWidget()
        self.arena.on_hud = self._on_hud
        self.arena.on_fail = self._on_fail
        root.add_widget(self.arena)

        # 底部控制
        ctrl = BoxLayout(size_hint=(1, None), height=dp(120), padding=dp(10), spacing=dp(10))

        # 方向键（按住移动）
        dpad = BoxLayout(orientation="vertical", size_hint=(0.65, 1), spacing=dp(8))
        row_u = BoxLayout()
        row_m = BoxLayout(spacing=dp(8))
        row_d = BoxLayout()

        btn_up = Button(text="↑", font_name=font if font else None)
        btn_left = Button(text="←", font_name=font if font else None)
        btn_right = Button(text="→", font_name=font if font else None)
        btn_down = Button(text="↓", font_name=font if font else None)

        self._bind_hold(btn_up, "up")
        self._bind_hold(btn_down, "down")
        self._bind_hold(btn_left, "left")
        self._bind_hold(btn_right, "right")

        row_u.add_widget(Label(text=""))
        row_u.add_widget(btn_up)
        row_u.add_widget(Label(text=""))

        row_m.add_widget(btn_left)
        row_m.add_widget(Label(text=""))
        row_m.add_widget(btn_right)

        row_d.add_widget(Label(text=""))
        row_d.add_widget(btn_down)
        row_d.add_widget(Label(text=""))

        dpad.add_widget(row_u)
        dpad.add_widget(row_m)
        dpad.add_widget(row_d)

        # 攻击按钮
        action = BoxLayout(orientation="vertical", size_hint=(0.35, 1), spacing=dp(8))
        btn_hit = Button(text="打", font_size="20sp", font_name=font if font else None)
        btn_hit.bind(on_press=lambda *_: self.arena.player_attack())
        action.add_widget(btn_hit)

        ctrl.add_widget(dpad)
        ctrl.add_widget(action)
        root.add_widget(ctrl)

        self.add_widget(root)

    def _bind_hold(self, btn, key):
        def down(*_):
            self.arena.hold[key] = True
        def up(*_):
            self.arena.hold[key] = False
        btn.bind(on_press=down)
        btn.bind(on_release=up)

    def apply_difficulty(self):
        app = App.get_running_app()
        self.arena.set_difficulty(app.cfg.difficulty)

    def start_new_game(self):
        self.apply_difficulty()
        self.arena.reset()
        self.arena.start()

    def on_pause(self, *args):
        self.arena.stop()
        self.manager.current = "pause"

    def _on_hud(self, hp, score):
        self.lbl_hud.text = f"HP: {hp}  分数: {score}"

    def _on_fail(self, score):
        self.arena.stop()
        fs = self.manager.get_screen("fail")
        fs.set_result(score)
        self.manager.current = "fail"


# -----------------------
# 页面：暂停
# -----------------------
class PauseScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        app = App.get_running_app()
        font = app.font_name

        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))

        root.add_widget(Label(text="已暂停", font_name=font if font else None, font_size="22sp",
                              size_hint=(1, None), height=dp(80)))

        root.add_widget(ui_btn("继续", self.on_resume, font))
        root.add_widget(ui_btn("重开", self.on_restart, font))
        root.add_widget(ui_btn("回主菜单", self.on_menu, font))

        root.add_widget(Label(text="", size_hint=(1, 1)))
        self.add_widget(root)

    def on_resume(self, *args):
        gs = self.manager.get_screen("game")
        self.manager.current = "game"
        gs.arena.start()

    def on_restart(self, *args):
        self.manager.current = "game"
        self.manager.get_screen("game").start_new_game()

    def on_menu(self, *args):
        self.manager.current = "menu"


# -----------------------
# 页面：失败
# -----------------------
class FailScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        app = App.get_running_app()
        font = app.font_name

        self.score = 0
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))

        root.add_widget(Label(text="我想静静！", font_name=font if font else None,
                              font_size="26sp", size_hint=(1, None), height=dp(90)))

        self.lbl_score = Label(text="分数：0", font_name=font if font else None,
                               font_size="20sp", size_hint=(1, None), height=dp(60))
        root.add_widget(self.lbl_score)

        root.add_widget(ui_btn("再来一次", self.on_retry, font))
        root.add_widget(ui_btn("回主菜单", self.on_menu, font))

        root.add_widget(Label(text="", size_hint=(1, 1)))
        self.add_widget(root)

    def set_result(self, score):
        self.score = score
        self.lbl_score.text = f"分数：{score}"

    def on_retry(self, *args):
        self.manager.current = "game"
        self.manager.get_screen("game").start_new_game()

    def on_menu(self, *args):
        self.manager.current = "menu"


# -----------------------
# App
# -----------------------
class MyGameApp(App):
    def build(self):
        self.font_name = pick_font()
        self.cfg = GameConfig()
        self.music = MusicBus(self.cfg)

        self.sm = ScreenManager()
        self.sm.add_widget(MenuScreen(name="menu"))
        self.sm.add_widget(SettingsScreen(name="settings"))
        self.sm.add_widget(GameScreen(name="game"))
        self.sm.add_widget(PauseScreen(name="pause"))
        self.sm.add_widget(FailScreen(name="fail"))

        # 默认进主菜单（音乐只在开始游戏时播放：不炸 & 可控）
        self.sm.current = "menu"
        return self.sm

    def on_stop(self):
        # 退出时停音乐
        self.music.stop()


if __name__ == "__main__":
    MyGameApp().run()

