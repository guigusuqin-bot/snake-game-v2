# main.py（质子 1 号 · 稳定美化版 v1.1 · 去掉按钮文字里的“褚少华”）
# 逻辑与之前一致，只改了 3 个按钮上的文字：
# - "和褚少华一起听歌" -> "一起听歌"
# - "和褚少华一起看小说" -> "一起看小说"
# - "我爱褚少华" -> "我爱"

import os
import random
from typing import Dict, List

from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.resources import resource_add_path
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.graphics import Color, RoundedRectangle, Line, Ellipse


# ----------------- 工具函数 -----------------
def _app_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _safe_listdir(path: str) -> List[str]:
    try:
        return os.listdir(path)
    except Exception:
        return []


def _pick_existing(paths: List[str]) -> str:
    for p in paths:
        if p and os.path.exists(p):
            return p
    return ""


# ----------------- 雪花层（轻量） -----------------
class SnowLayer(FloatLayout):
    """轻量雪花：Canvas 画 Ellipse，30fps，不卡为第一目标"""

    def __init__(self, count: int = 28, **kwargs):
        super().__init__(**kwargs)
        self.count = int(count)
        self._flakes: List[Dict] = []
        self._running = False

        Window.bind(size=self._on_resize)

        with self.canvas:
            self._snow_color = Color(1, 1, 1, 0.78)
            for _ in range(self.count):
                flake = self._new_flake(spawn_top=False)
                e = Ellipse(pos=(flake["x"], flake["y"]), size=(flake["r"], flake["r"]))
                flake["e"] = e
                self._flakes.append(flake)

    def _new_flake(self, spawn_top: bool = False) -> Dict:
        w, h = Window.size
        r = random.uniform(2.2, 5.6)
        x = random.uniform(0, max(1, w - r))
        y = random.uniform(h, h + h * 0.25) if spawn_top else random.uniform(0, h)
        vy = random.uniform(55.0, 125.0)
        vx = random.uniform(-22.0, 22.0)
        wob = random.uniform(0.6, 1.5)
        phase = random.uniform(0, 6.28)
        return {"x": x, "y": y, "r": r, "vy": vy, "vx": vx, "wob": wob, "phase": phase}

    def _on_resize(self, *_):
        if not self._flakes:
            return
        w, h = Window.size
        for f in self._flakes:
            f["x"] = random.uniform(0, max(1, w - f["r"]))
            f["y"] = random.uniform(0, h)
            f["phase"] = random.uniform(0, 6.28)
            if "e" in f:
                f["e"].pos = (f["x"], f["y"])
                f["e"].size = (f["r"], f["r"])

    def start(self):
        if self._running:
            return
        self._running = True
        Clock.schedule_interval(self._tick, 1 / 30.0)

    def stop(self):
        if not self._running:
            return
        self._running = False
        Clock.unschedule(self._tick)

    def _tick(self, dt: float):
        w, h = Window.size
        for f in self._flakes:
            f["y"] -= f["vy"] * dt
            f["x"] += f["vx"] * dt
            f["x"] += (f["wob"] * 20.0) * dt * (random.uniform(-1.0, 1.0))

            if f["x"] < -10:
                f["x"] = w + 10
            if f["x"] > w + 10:
                f["x"] = -10

            if f["y"] < -20:
                nf = self._new_flake(spawn_top=True)
                f.update(nf)

            f["e"].pos = (f["x"], f["y"])


# ----------------- 主 App -----------------
class ProtonApp(App):
    def build(self):
        self.root_dir = _app_dir()
        self.assets_dir = os.path.join(self.root_dir, "assets")

        resource_add_path(self.root_dir)
        resource_add_path(self.assets_dir)

        # 字体（可选）
        self.font = _pick_existing([
            os.path.join(self.root_dir, "NotoSansSC-VariableFont_wght.ttf"),
            os.path.join(self.assets_dir, "NotoSansSC-VariableFont_wght.ttf"),
        ])

        # 背景路径
        def bg(n: int) -> str:
            return os.path.join(self.assets_dir, f"listen_bg{n}.png")

        self.bg1 = bg(1)
        self.bg2 = bg(2)
        self.bg4 = bg(4)
        self.bg7 = bg(7)
        self.bg8 = bg(8)

        # 音频路径
        def track(n: int) -> str:
            return os.path.join(self.root_dir, f"listen{n}.mp3")

        self.listen_tracks = [track(i) for i in range(1, 7)]  # 听歌 1~6
        self.love_track = track(7)                            # 我爱按钮
        self.novel_track = track(8)                           # 小说按钮

        # 状态
        self.mode = "intro"         # intro / home / listen / novel / love
        self.sound = None
        self._sound_cache: Dict[str, object] = {}
        self.listen_index = -1      # 当前听歌索引
        self.novel_press_count = 0  # 小说触发次数（最多 10）

        # UI Root
        root = FloatLayout()

        # 背景图
        self.bg = Image(
            source="",
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
        )
        root.add_widget(self.bg)

        # 雪花层
        self.snow = SnowLayer(count=32, size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        root.add_widget(self.snow)

        # 顶部标题栏
        self.top_bar = FloatLayout(
            size_hint=(1, None),
            height=110,
            pos_hint={"center_x": 0.5, "top": 1},
        )
        with self.top_bar.canvas.before:
            self._top_bg_color = Color(0, 0, 0, 0.35)
            self._top_bg_rect = RoundedRectangle(
                pos=self.top_bar.pos,
                size=self.top_bar.size,
                radius=[0, 0, 26, 26],
            )

        def _sync_top_bar(*_):
            self._top_bg_rect.pos = self.top_bar.pos
            self._top_bg_rect.size = self.top_bar.size

        self.top_bar.bind(pos=_sync_top_bar, size=_sync_top_bar)

        self.top_label = Label(
            text="质子 1 号 · 圣诞陪伴",
            size_hint=(1, 1),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            font_size=26,
            bold=True,
            font_name=self.font if self.font else None,
            color=(1, 1, 1, 0.98),
        )
        self.sub_label = Label(
            text="他派我来陪着你。",
            size_hint=(1, 1),
            pos_hint={"center_x": 0.5, "center_y": 0.10},
            font_size=16,
            font_name=self.font if self.font else None,
            color=(0.95, 0.95, 0.95, 0.9),
        )
        self.top_bar.add_widget(self.top_label)
        self.top_bar.add_widget(self.sub_label)
        root.add_widget(self.top_bar)

        # 启动页 “进入” 按钮（圆形）
        self.start_button = Button(
            text="进入",
            font_size=30,
            font_name=self.font if self.font else None,
            size_hint=(None, None),
            width=Window.width * 0.35,
            height=Window.width * 0.35,
            pos_hint={"center_x": 0.5, "center_y": 0.45},
            background_normal="",
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 1),
        )

        with self.start_button.canvas.before:
            self._start_color = Color(0.62, 0.12, 0.12, 0.95)
            self._start_circle = RoundedRectangle(
                pos=self.start_button.pos,
                size=self.start_button.size,
                radius=[self.start_button.height / 2],
            )
            self._start_border_color = Color(0.96, 0.82, 0.28, 0.98)
            self._start_border = Line(
                rounded_rectangle=[
                    self.start_button.x,
                    self.start_button.y,
                    self.start_button.width,
                    self.start_button.height,
                    self.start_button.height / 2,
                ],
                width=2.5,
            )

        def _sync_start(*_):
            self._start_circle.pos = self.start_button.pos
            self._start_circle.size = self.start_button.size
            self._start_circle.radius = [self.start_button.height / 2]
            self._start_border.rounded_rectangle = [
                self.start_button.x,
                self.start_button.y,
                self.start_button.width,
                self.start_button.height,
                self.start_button.height / 2,
            ]

        self.start_button.bind(pos=_sync_start, size=_sync_start)

        def _start_down(*_):
            self._start_color.rgba = (0.4, 0.08, 0.08, 0.98)

        def _start_up(*_):
            self._start_color.rgba = (0.62, 0.12, 0.12, 0.95)

        self.start_button.bind(on_press=_start_down, on_release=_start_up)
        self.start_button.bind(on_release=self.on_start_press)
        root.add_widget(self.start_button)

        # 主界面按钮区（带半透明卡片背景）
        self.btn_box = BoxLayout(
            orientation="vertical",
            spacing=18,
            padding=[24, 24, 24, 24],
            size_hint=(0.9, None),
            height=max(320, int(Window.height * 0.42)),
            pos_hint={"center_x": 0.5, "center_y": 0.28},
            opacity=0.0,
            disabled=True,
        )
        with self.btn_box.canvas.before:
            self._btn_bg_color = Color(0, 0, 0, 0.35)
            self._btn_bg_rect = RoundedRectangle(
                pos=self.btn_box.pos,
                size=self.btn_box.size,
                radius=[28],
            )

        def _sync_btn_box(*_):
            self._btn_bg_rect.pos = self.btn_box.pos
            self._btn_bg_rect.size = self.btn_box.size

        self.btn_box.bind(pos=_sync_btn_box, size=_sync_btn_box)

        # 这里三个按钮的文字已经去掉“褚少华”
        self.btn_listen = self._make_round_button("一起听歌", font_size=28, height=110)
        self.btn_listen.bind(on_press=self.on_listen_press)

        self.btn_novel = self._make_round_button("一起看小说", font_size=28, height=110)
        self.btn_novel.bind(on_press=self.on_novel_press)

        self.btn_love = self._make_round_button("我爱", font_size=28, height=110)
        self.btn_love.bind(on_press=self.on_love_press)

        self.btn_box.add_widget(self.btn_listen)
        self.btn_box.add_widget(self.btn_novel)
        self.btn_box.add_widget(self.btn_love)
        root.add_widget(self.btn_box)

        # 小说显示区域（剧情卡片）
        self.content_area = FloatLayout(size_hint=(1, 1))
        root.add_widget(self.content_area)

        self.novel_label = Label(
            text="",
            size_hint=(0.92, None),
            pos_hint={"center_x": 0.5, "center_y": 0.63},
            text_size=(Window.width * 0.86, None),
            font_size=32,
            halign="center",
            valign="middle",
            font_name=self.font if self.font else None,
            color=(0.96, 0.82, 0.28, 1),  # 金色字体
        )
        with self.novel_label.canvas.before:
            self._novel_bg_color = Color(0, 0, 0, 0.45)
            self._novel_bg_rect = RoundedRectangle(
                pos=self.novel_label.pos,
                size=self.novel_label.size,
                radius=[24],
            )

        self.novel_label.bind(texture_size=self._update_novel_label_height)

        def _sync_novel_bg(*_):
            self._novel_bg_rect.pos = self.novel_label.pos
            self._novel_bg_rect.size = self.novel_label.size

        self.novel_label.bind(pos=_sync_novel_bg, size=_sync_novel_bg)

        # 底部小版本号
        self.footer_label = Label(
            text="Proton 1.0 · for you",
            size_hint=(1, None),
            height=32,
            pos_hint={"center_x": 0.5, "y": 0},
            font_size=12,
            font_name=self.font if self.font else None,
            color=(1, 1, 1, 0.6),
        )
        root.add_widget(self.footer_label)

        Window.bind(size=self._on_window_resize)

        # 启动页：背景固定 listen_bg2，不播放音乐
        self._show_intro()
        self.snow.start()

        return root

    # ----------------- UI & 背景 -----------------
    def _on_window_resize(self, *_):
        self.btn_box.height = max(320, int(Window.height * 0.42))
        self.novel_label.text_size = (Window.width * 0.86, None)

    def _make_round_button(self, text: str, font_size=26, height=96) -> Button:
        btn = Button(
            text=text,
            font_size=font_size,
            font_name=self.font if self.font else None,
            size_hint=(1, None),
            height=height,
            background_normal="",
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 1),
        )

        btn._col_up = (0.62, 0.12, 0.12, 0.92)
        btn._col_down = (0.40, 0.08, 0.08, 0.96)
        btn._stroke_col = (0.96, 0.82, 0.28, 0.95)

        with btn.canvas.before:
            btn._bg_color = Color(*btn._col_up)
            btn._bg_rect = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[btn.height / 2])
            btn._line_color = Color(*btn._stroke_col)
            btn._line = Line(
                rounded_rectangle=[btn.x, btn.y, btn.width, btn.height, btn.height / 2],
                width=2.0,
            )

        def _sync(*_):
            btn._bg_rect.pos = btn.pos
            btn._bg_rect.size = btn.size
            btn._bg_rect.radius = [btn.height / 2]
            btn._line.rounded_rectangle = [btn.x, btn.y, btn.width, btn.height, btn.height / 2]

        btn.bind(pos=_sync, size=_sync)

        def _down(*_):
            btn._bg_color.rgba = btn._col_down

        def _up(*_):
            btn._bg_color.rgba = btn._col_up

        btn.bind(on_press=_down, on_release=_up)
        return btn

    def _update_novel_label_height(self, *_):
        self.novel_label.height = max(self.novel_label.texture_size[1] + 32, Window.height * 0.30)

    def _fallback_bg(self) -> str:
        if self.bg1 and os.path.exists(self.bg1):
            return self.bg1
        icon = os.path.join(self.root_dir, "icon.png")
        if os.path.exists(icon):
            return icon
        return ""

    def _set_bg(self, path: str):
        try:
            if path and os.path.exists(path):
                self.bg.source = path
                self.bg.reload()
                return
        except Exception:
            pass

        fb = self._fallback_bg()
        if fb and os.path.exists(fb):
            self.bg.source = fb
            try:
                self.bg.reload()
            except Exception:
                pass

    def _clear_content(self):
        self.content_area.clear_widgets()

    # ----------------- 音频 -----------------
    def _stop_sound(self):
        try:
            if self.sound:
                self.sound.stop()
        except Exception:
            pass
        self.sound = None

    def _get_sound_cached(self, path: str):
        s = self._sound_cache.get(path)
        if s:
            return s
        try:
            s = SoundLoader.load(path)
        except Exception:
            s = None
        if s:
            self._sound_cache[path] = s
        return s

    def _play_sound(self, path: str, loop: bool = False):
        self._stop_sound()
        if not path or not os.path.exists(path):
            self.sub_label.text = "⚠️ 找不到音频资源"
            return

        s = self._get_sound_cached(path)
        if not s:
            self.sub_label.text = "⚠️ 无法加载音频文件"
            return

        self.sound = s
        try:
            self.sound.loop = loop
        except Exception:
            pass

        try:
            if hasattr(self.sound, "seek"):
                self.sound.seek(0)
        except Exception:
            pass

        try:
            self.sound.play()
        except Exception:
            self.sub_label.text = "⚠️ 音频播放失败"
            self.sound = None
            # ----------------- 模式切换（启动 / 主界面） -----------------
    def _show_intro(self):
        self.mode = "intro"
        self._clear_content()
        self._stop_sound()
        self._set_bg(self.bg2)
        self.top_label.text = "质子 1 号 · 圣诞陪伴"
        self.sub_label.text = "他派我来陪着你。"

        self.start_button.opacity = 1.0
        self.start_button.disabled = False
        self.btn_box.opacity = 0.0
        self.btn_box.disabled = True

    def _show_home(self):
        self.mode = "home"
        self._clear_content()
        self._stop_sound()
        self._set_bg(self.bg1)

        self.top_label.text = "质子 1 号 · 圣诞陪伴"
        self.sub_label.text = "点击下面三个按钮，开始今天的陪伴。"

        self.start_button.opacity = 0.0
        self.start_button.disabled = True
        self.btn_box.opacity = 1.0
        self.btn_box.disabled = False

    # ----------------- 按钮事件 -----------------
    def on_start_press(self, *_):
        self._show_home()

    def on_listen_press(self, *_):
        self.mode = "listen"
        self._clear_content()
        self._set_bg(self.bg1)

        tracks = [p for p in self.listen_tracks if os.path.exists(p)]
        if not tracks:
            self.sub_label.text = "⚠️ 缺少 listen1~listen6.mp3"
            return

        self.listen_index = (self.listen_index + 1) % len(tracks)
        track = tracks[self.listen_index]

        self._play_sound(track, loop=False)
        self.sub_label.text = f"🎵 正在播放：{os.path.basename(track)}"

    def on_novel_press(self, *_):
        if self.novel_press_count >= 10:
            self.sub_label.text = "剧情已全部解锁。"
            return

        self.mode = "novel"
        self._clear_content()
        self._set_bg(self.bg4)

        if self.novel_label.parent is None:
            self.content_area.add_widget(self.novel_label)

        # 这里只是显示一句话（保留原文）
        self.novel_label.text = "跟褚少华说我爱你，解锁新剧情！"

        self._play_sound(self.novel_track, loop=True)

        self.novel_press_count += 1
        self.sub_label.text = f"已解锁次数：{self.novel_press_count}/10"

    def on_love_press(self, *_):
        self.mode = "love"
        self._clear_content()
        self._set_bg(self.bg7)

        if not os.path.exists(self.love_track):
            self.sub_label.text = "⚠️ 缺少 listen7.mp3"
            return

        self._play_sound(self.love_track, loop=False)
        # 这里的提示文案同样只删了“褚少华”三个字
        self.sub_label.text = "❤️ 我爱"

if __name__ == "__main__":
    ProtonApp().run()
