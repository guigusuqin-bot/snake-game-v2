# main.py（最终版：圣诞主题稳态版）
# ✅ 雪花飘落（轻量 Canvas + Clock，无线程）
# ✅ 首页不自动播放
# ✅ 3 按钮整体居中（红底金边、圆角）
# ✅ 小说区更大、字体更大、整体居中
# ✅ 小说 10 页：第 1 页不动；第 2~10 页“写满”我爱徐林静❤️
# ✅ 背景兜底：任何图加载失败都回退，不闪退
# ✅ 音频兜底：任何音频加载失败只提示，不闪退

import os
import random
from typing import Dict, List, Optional

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
from kivy.uix.scrollview import ScrollView

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
            # 暖白雪花（圣诞氛围）
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

            # 轻微左右摆动（避免直线下坠的“假感”）
            f["x"] += f["vx"] * dt
            f["x"] += (f["wob"] * 20.0) * dt * (random.uniform(-1.0, 1.0))

            # wrap
            if f["x"] < -10:
                f["x"] = w + 10
            if f["x"] > w + 10:
                f["x"] = -10

            # 到底重生
            if f["y"] < -20:
                nf = self._new_flake(spawn_top=True)
                f.update(nf)

            # 更新绘制
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

        # 背景（固定命名）
        def bg(n: int) -> str:
            return os.path.join(self.assets_dir, f"listen_bg{n}.png")

        self.bg_list = [bg(i) for i in range(1, 7)]      # 听歌：1~6
        self.bg_love = bg(7)                             # 爱：7
        self.bg_novel = bg(8)                            # 小说：8

        # 音频（固定命名）
        def track(n: int) -> str:
            return os.path.join(self.root_dir, f"listen{n}.mp3")

        self.listen_tracks = [track(i) for i in range(1, 7)]  # 听歌：1~6
        self.love_track = track(7)                            # 爱：7
        self.novel_track = track(8)                           # 小说：8

        # 状态
        self.mode = "home"
        self.sound = None
        self.listen_index = -1
        self._sound_cache: Dict[str, object] = {}

        # 小说
        self.novel_pages = self._make_novel_pages_10()
        self.novel_page_i = 0

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

        # 雪花层（背景之上）
        self.snow = SnowLayer(count=32, size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        root.add_widget(self.snow)

        # 顶部大标题（更醒目）
        self.top_label = Label(
            text="🎄❄️ 我是质子 1 号：圣诞快乐，静静。❄️🎄",
            size_hint=(1, None),
            height=120,
            pos_hint={"center_x": 0.5, "top": 1},
            font_size=28,
            bold=True,
            font_name=self.font if self.font else None,
            color=(1, 1, 1, 0.98),
        )
        root.add_widget(self.top_label)

        # 3 按钮区：整体居中
        self.btn_box = BoxLayout(
            orientation="vertical",
            spacing=18,
            padding=[0, 0, 0, 0],
            size_hint=(0.88, None),
            height=max(340, int(Window.height * 0.42)),
            pos_hint={"center_x": 0.5, "center_y": 0.30},
        )

        self.btn_listen = self._make_round_button("和褚少华一起听歌", font_size=28, height=112)
        self.btn_listen.bind(on_press=self.on_listen_press)

        self.btn_novel = self._make_round_button("和褚少华一起看小说", font_size=28, height=112)
        self.btn_novel.bind(on_press=self.on_novel_press)

        self.btn_love = self._make_round_button("我爱褚少华", font_size=28, height=112)
        self.btn_love.bind(on_press=self.on_love_press)

        self.btn_box.add_widget(self.btn_listen)
        self.btn_box.add_widget(self.btn_novel)
        self.btn_box.add_widget(self.btn_love)

        root.add_widget(self.btn_box)

        # 小说区（更大 + 居中）
        self.content_area = FloatLayout(size_hint=(1, 1))
        root.add_widget(self.content_area)

        self.novel_scroll = ScrollView(
            size_hint=(0.92, 0.66),
            pos_hint={"center_x": 0.5, "center_y": 0.60},
        )

        self.novel_label = Label(
            text="",
            size_hint_y=None,
            text_size=(Window.width * 0.86, None),
            font_size=32,
            halign="center",
            valign="top",
            font_name=self.font if self.font else None,
            color=(0.95, 0.18, 0.18, 1),  # 圣诞红
        )
        self.novel_label.bind(texture_size=self._update_novel_label_height)
        self.novel_scroll.add_widget(self.novel_label)

        Window.bind(size=self._on_window_resize)

        # 启动：只显示首页，不播放
        self._show_home()
        self.snow.start()
        return root

    # ----------------- UI -----------------
    def _on_window_resize(self, *_):
        self.btn_box.height = max(340, int(Window.height * 0.42))
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

        # 圣诞红 + 金边
        btn._col_up = (0.62, 0.12, 0.12, 0.92)
        btn._col_down = (0.40, 0.08, 0.08, 0.96)
        btn._stroke_col = (0.96, 0.82, 0.28, 0.95)

        with btn.canvas.before:
            btn._bg_color = Color(*btn._col_up)
            btn._bg_rect = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[btn.height / 2])
            btn._line_color = Color(*btn._stroke_col)
            btn._line = Line(rounded_rectangle=[btn.x, btn.y, btn.width, btn.height, btn.height / 2], width=2.0)

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
        self.novel_label.height = self.novel_label.texture_size[1] + 24

    def _clear_content(self):
        self.content_area.clear_widgets()

    def _fallback_bg(self) -> str:
        # 优先 listen_bg1，再退 icon
        p = os.path.join(self.assets_dir, "listen_bg1.png")
        if os.path.exists(p):
            return p
        icon = os.path.join(self.root_dir, "icon.png")
        if os.path.exists(icon):
            return icon
        return ""

    def _set_bg(self, path: str):
        # 任何异常都不崩：回退
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
            self.top_label.text = f"⚠️ 找不到音频：{os.path.basename(path) if path else '空路径'}"
            return

        s = self._get_sound_cached(path)
        if not s:
            self.top_label.text = f"⚠️ 无法加载音频：{os.path.basename(path)}"
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
            self.top_label.text = f"⚠️ 播放失败：{os.path.basename(path)}"
            self.sound = None

    # ----------------- 小说 -----------------
    def _make_novel_pages_10(self) -> List[str]:
        pages: List[str] = []
        # 第 1 页：不动
        pages.append("打开微信找到褚少华对话聊天框输入  我爱你❤️  解锁新剧情…")

        # 第 2~10 页：写满（多行重复铺满屏幕）
        fill_lines = []
        for _ in range(42):  # 够填满大屏（ScrollView 也能滚）
            fill_lines.append("我爱徐林静❤️")
        filled = "\n".join(fill_lines)

        for _ in range(9):
            pages.append(filled)
        return pages

    def _render_novel_page(self):
        total = len(self.novel_pages)
        i = self.novel_page_i % total
        self.novel_label.text = f"🎄 第 {i + 1}/{total} 页\n\n{self.novel_pages[i]}"

    # ----------------- 模式切换 -----------------
    def _show_home(self):
        self.mode = "home"
        self._clear_content()
        self._set_bg(self._fallback_bg())
        self._stop_sound()  # 首页永远不播放
        self.top_label.text = "🎄❄️ 我是质子 1 号：圣诞快乐，静静。❄️🎄"

    def _show_novel(self):
        self.mode = "novel"
        self._clear_content()
        self._set_bg(self.bg_novel if os.path.exists(self.bg_novel) else self._fallback_bg())
        self.content_area.add_widget(self.novel_scroll)
        self._render_novel_page()

        # 进入小说：循环播放 listen8
        self._play_sound(self.novel_track, loop=True)

    # ----------------- 三按钮逻辑 -----------------
    def on_listen_press(self, *_):
        # 听歌：listen1~6 + 背景 bg1~6
        tracks = [p for p in self.listen_tracks if os.path.exists(p)]
        bgs = [p for p in self.bg_list if os.path.exists(p)]

        if not tracks:
            self.top_label.text = "⚠️ 缺少 listen1~listen6.mp3（根目录）"
            return
        if not bgs:
            self.top_label.text = "⚠️ 缺少 assets/listen_bg1~listen_bg6.png"
            return

        self.mode = "listen"
        self._clear_content()

        self.listen_index = (self.listen_index + 1) % len(tracks)
        track = tracks[self.listen_index]
        bg = bgs[self.listen_index % len(bgs)]

        self._set_bg(bg)
        self._play_sound(track, loop=False)
        self.top_label.text = f"❄️🎵 听歌：{os.path.basename(track)}"

    def on_love_press(self, *_):
        # 爱：bg7 + listen7（不循环）
        self.mode = "love"
        self._clear_content()
        self._set_bg(self.bg_love if os.path.exists(self.bg_love) else self._fallback_bg())

        if not os.path.exists(self.love_track):
            self.top_label.text = "⚠️ 缺少 listen7.mp3（根目录）"
            return

        self._play_sound(self.love_track, loop=False)
        self.top_label.text = "🎄❤️ 我爱褚少华"

    def on_novel_press(self, *_):
        # 第一次：进入小说；之后：翻页
        if self.mode != "novel":
            self.novel_page_i = 0
            self._show_novel()
            self.top_label.text = "🎄 小说模式：再按一次翻页（背景固定 bg8，主题曲 listen8 循环）"
        else:
            self.novel_page_i += 1
            self._render_novel_page()


if __name__ == "__main__":
    ProtonApp().run()
