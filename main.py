# main.py（v1.3 精致不炸版：✅圣诞氛围叠加 ✅“我是质子1号”更醒目 ✅雪花保留 ✅不自动播放 ✅音频缓存）
# 资源约定：
# - 背景：assets/listen_bg1~8.png（听歌轮播用 1~6，爱=7，小说=8）
# - 音频：根目录 listen1~8.mp3（听歌轮播用 1~6，爱=7，小说主题=8）
# - 字体：NotoSansSC-VariableFont_wght.ttf（根或 assets 均可）

import os
import re
import random

from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.resources import resource_add_path

from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.scrollview import ScrollView

from kivy.graphics import Color, RoundedRectangle, Line, Ellipse


def _app_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _safe_listdir(path: str):
    try:
        return os.listdir(path)
    except Exception:
        return []


def _sort_by_number(files, pattern: str):
    reg = re.compile(pattern, re.IGNORECASE)
    pairs = []
    for f in files:
        m = reg.match(f)
        if m:
            pairs.append((int(m.group(1)), f))
    pairs.sort(key=lambda x: x[0])
    return [f for _, f in pairs]


def _pick_existing(path_candidates):
    for p in path_candidates:
        if p and os.path.exists(p):
            return p
    return ""


class SnowLayer(FloatLayout):
    """
    稳定雪花层：纯 Canvas + Clock 更新；无线程；轻量
    """
    def __init__(self, count=32, **kwargs):
        super().__init__(**kwargs)
        self.count = int(count)
        self._flakes = []
        self._running = False

        Window.bind(size=self._on_resize)

        with self.canvas:
            self._snow_color = Color(1, 1, 1, 0.78)
            for _ in range(self.count):
                flake = self._new_flake(spawn_top=False)
                e = Ellipse(pos=(flake["x"], flake["y"]), size=(flake["r"], flake["r"]))
                flake["e"] = e
                self._flakes.append(flake)

    def _new_flake(self, spawn_top=False):
        w, h = Window.size
        r = random.uniform(2.0, 5.5)
        x = random.uniform(0, max(1, w - r))
        y = random.uniform(h, h + h * 0.25) if spawn_top else random.uniform(0, h)
        vy = random.uniform(55.0, 125.0)
        vx = random.uniform(-14.0, 14.0)
        return {"x": x, "y": y, "r": r, "vy": vy, "vx": vx}

    def _on_resize(self, *_):
        if not self._flakes:
            return
        w, h = Window.size
        for f in self._flakes:
            f["x"] = random.uniform(0, max(1, w - f["r"]))
            f["y"] = random.uniform(0, h)
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

    def _tick(self, dt):
        w, h = Window.size
        for f in self._flakes:
            f["y"] -= f["vy"] * dt
            f["x"] += f["vx"] * dt

            if random.random() < 0.15:
                f["x"] += random.uniform(-6.0, 6.0) * dt

            if f["x"] < -10:
                f["x"] = w + 10
            if f["x"] > w + 10:
                f["x"] = -10

            if f["y"] < -20:
                nf = self._new_flake(spawn_top=True)
                f.update(nf)

            f["e"].pos = (f["x"], f["y"])
            class ProtonApp(App):
    def build(self):
        # -------------------------
        # 路径 / 资源索引
        # -------------------------
        self.root_dir = _app_dir()
        self.assets_dir = os.path.join(self.root_dir, "assets")
        resource_add_path(self.root_dir)
        resource_add_path(self.assets_dir)

        root_files = _safe_listdir(self.root_dir)
        assets_files = _safe_listdir(self.assets_dir)

        self.font = _pick_existing([
            os.path.join(self.root_dir, "NotoSansSC-VariableFont_wght.ttf"),
            os.path.join(self.assets_dir, "NotoSansSC-VariableFont_wght.ttf"),
        ])

        self.bg_love = os.path.join(self.assets_dir, "listen_bg7.png")
        self.bg_novel = os.path.join(self.assets_dir, "listen_bg8.png")

        self.listen_bgs = []
        for i in range(1, 7):
            p = os.path.join(self.assets_dir, f"listen_bg{i}.png")
            if os.path.exists(p):
                self.listen_bgs.append(p)

        self.listen_tracks = []
        for i in range(1, 7):
            p = os.path.join(self.root_dir, f"listen{i}.mp3")
            if os.path.exists(p):
                self.listen_tracks.append(p)

        self.love_track = _pick_existing([os.path.join(self.root_dir, "listen7.mp3")])
        self.novel_track = _pick_existing([os.path.join(self.root_dir, "listen8.mp3")])

        # 小说：第一页不动；后 9 页写满
        self.novel_pages = self._make_novel_pages_10()
        self.novel_page_i = 0

        self.mode = "home"
        self.sound = None
        self.listen_index = -1
        self.bg_index = -1

        # 音频缓存
        self._sound_cache = {}

        # -------------------------
        # UI Root
        # -------------------------
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

        # ✅ 圣诞氛围叠加（不加新图片）：暖红灯光 + 金色光晕 + 暗角
        self.christmas_fx = FloatLayout(size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        with self.christmas_fx.canvas:
            # 暖红整体色调（像圣诞灯光）
            Color(0.45, 0.06, 0.06, 0.22)
            self.fx_red = RoundedRectangle(pos=(0, 0), size=Window.size, radius=[0])

            # 顶部金色“灯光”区域（更节日）
            Color(0.95, 0.80, 0.25, 0.10)
            self.fx_gold_top = RoundedRectangle(
                pos=(0, Window.height * 0.55),
                size=(Window.width, Window.height * 0.45),
                radius=[0]
            )

            # 底部暗角（让前景更突出）
            Color(0, 0, 0, 0.30)
            self.fx_vignette = RoundedRectangle(pos=(0, 0), size=Window.size, radius=[0])

        def _sync_fx(*_):
            self.fx_red.size = Window.size
            self.fx_vignette.size = Window.size
            self.fx_gold_top.pos = (0, Window.height * 0.55)
            self.fx_gold_top.size = (Window.width, Window.height * 0.45)

        Window.bind(size=_sync_fx)
        root.add_widget(self.christmas_fx)

        # 雪花
        self.snow = SnowLayer(count=32, size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        root.add_widget(self.snow)

        # ✅ 顶部标题玻璃块（更醒目）
        self.header = FloatLayout(
            size_hint=(0.92, None),
            height=184,
            pos_hint={"center_x": 0.5, "top": 0.98},
        )
        with self.header.canvas.before:
            Color(0, 0, 0, 0.30)
            self.header_shadow = RoundedRectangle(pos=(self.header.x, self.header.y - 6), size=self.header.size, radius=[18])
            Color(0, 0, 0, 0.22)
            self.header_rect = RoundedRectangle(pos=self.header.pos, size=self.header.size, radius=[18])
            Color(1, 1, 1, 0.08)
            self.header_gloss = RoundedRectangle(
                pos=(self.header.x, self.header.y + self.header.height * 0.55),
                size=(self.header.width, self.header.height * 0.45),
                radius=[18]
            )
            Color(1, 1, 1, 0.12)
            self.header_line = Line(rounded_rectangle=[self.header.x, self.header.y, self.header.width, self.header.height, 18], width=1.2)

        def _sync_header(*_):
            self.header_shadow.pos = (self.header.x, self.header.y - 6)
            self.header_shadow.size = self.header.size
            self.header_rect.pos = self.header.pos
            self.header_rect.size = self.header.size
            self.header_gloss.pos = (self.header.x, self.header.y + self.header.height * 0.55)
            self.header_gloss.size = (self.header.width, self.header.height * 0.45)
            self.header_line.rounded_rectangle = [self.header.x, self.header.y, self.header.width, self.header.height, 18]

        self.header.bind(pos=_sync_header, size=_sync_header)

        # ✅ 让“我是质子1号...”更醒目：两层文字叠加（假描边/发光）
        self.main_line_shadow = Label(
            text="我是质子 1 号",
            font_size=38,
            font_name=self.font if self.font else None,
            color=(0, 0, 0, 0.55),
            size_hint=(1, None),
            height=60,
            pos_hint={"center_x": 0.5, "top": 0.98},
        )
        self.main_line = Label(
            text="我是质子 1 号",
            font_size=38,
            font_name=self.font if self.font else None,
            color=(0.98, 0.86, 0.35, 1),  # 金色更醒目
            size_hint=(1, None),
            height=60,
            pos_hint={"center_x": 0.5, "top": 0.985},
        )

        self.sub_line = Label(
            text="褚少华派我来陪伴你。",
            font_size=24,
            font_name=self.font if self.font else None,
            color=(1, 1, 1, 0.96),
            size_hint=(1, None),
            height=60,
            halign="center",
            valign="middle",
            pos_hint={"center_x": 0.5, "y": 0.10},
        )
        self.sub_line.bind(size=lambda *_: setattr(self.sub_line, "text_size", (self.sub_line.width * 0.92, None)))

        self.header.add_widget(self.main_line_shadow)
        # 轻微偏移做描边效果
        self.main_line_shadow.pos_hint = {"center_x": 0.5, "top": 0.975}
        self.header.add_widget(self.main_line)
        self.header.add_widget(self.sub_line)
        root.add_widget(self.header)

        # 主卡片（玻璃+阴影）
        self.card = FloatLayout(
            size_hint=(0.92, None),
            height=max(540, int(Window.height * 0.58)),
            pos_hint={"center_x": 0.5, "center_y": 0.40},
        )
        with self.card.canvas.before:
            Color(0, 0, 0, 0.30)
            self.card_shadow = RoundedRectangle(pos=(self.card.x, self.card.y - 8), size=self.card.size, radius=[20])
            Color(0, 0, 0, 0.18)
            self.card_rect = RoundedRectangle(pos=self.card.pos, size=self.card.size, radius=[20])
            Color(1, 1, 1, 0.06)
            self.card_gloss = RoundedRectangle(
                pos=(self.card.x, self.card.y + self.card.height * 0.60),
                size=(self.card.width, self.card.height * 0.40),
                radius=[20]
            )
            Color(1, 1, 1, 0.10)
            self.card_line = Line(rounded_rectangle=[self.card.x, self.card.y, self.card.width, self.card.height, 20], width=1.2)

        def _sync_card(*_):
            self.card_shadow.pos = (self.card.x, self.card.y - 8)
            self.card_shadow.size = self.card.size
            self.card_rect.pos = self.card.pos
            self.card_rect.size = self.card.size
            self.card_gloss.pos = (self.card.x, self.card.y + self.card.height * 0.60)
            self.card_gloss.size = (self.card.width, self.card.height * 0.40)
            self.card_line.rounded_rectangle = [self.card.x, self.card.y, self.card.width, self.card.height, 20]

        self.card.bind(pos=_sync_card, size=_sync_card)
        root.add_widget(self.card)

        # 三按钮
        self.btn_box = BoxLayout(
            orientation="vertical",
            spacing=18,
            padding=[18, 18, 18, 14],
            size_hint=(1, None),
            height=388,
            pos_hint={"x": 0, "top": 1},
        )

        self.btn_listen = self._make_pill_button("🎧  和褚少华一起听歌", kind="green", font_size=26, height=112)
        self.btn_listen.bind(on_press=self.on_listen_press)

        self.btn_novel = self._make_pill_button("📖  和褚少华一起看小说", kind="green", font_size=26, height=112)
        self.btn_novel.bind(on_press=self.on_novel_press)

        self.btn_love = self._make_pill_button("❤️  我爱褚少华", kind="red", font_size=26, height=112)
        self.btn_love.bind(on_press=self.on_love_press)

        self.btn_box.add_widget(self.btn_listen)
        self.btn_box.add_widget(self.btn_novel)
        self.btn_box.add_widget(self.btn_love)
        self.card.add_widget(self.btn_box)
        # 状态条（玻璃）
        self.status = FloatLayout(
            size_hint=(0.94, None),
            height=90,
            pos_hint={"center_x": 0.5, "y": 0.02},
        )
        with self.status.canvas.before:
            Color(0, 0, 0, 0.26)
            self.status_rect = RoundedRectangle(pos=self.status.pos, size=self.status.size, radius=[16])
            Color(1, 1, 1, 0.07)
            self.status_gloss = RoundedRectangle(
                pos=(self.status.x, self.status.y + self.status.height * 0.55),
                size=(self.status.width, self.status.height * 0.45),
                radius=[16]
            )
            Color(1, 1, 1, 0.10)
            self.status_line = Line(rounded_rectangle=[self.status.x, self.status.y, self.status.width, self.status.height, 16], width=1.1)

        def _sync_status(*_):
            self.status_rect.pos = self.status.pos
            self.status_rect.size = self.status.size
            self.status_gloss.pos = (self.status.x, self.status.y + self.status.height * 0.55)
            self.status_gloss.size = (self.status.width, self.status.height * 0.45)
            self.status_line.rounded_rectangle = [self.status.x, self.status.y, self.status.width, self.status.height, 16]

        self.status.bind(pos=_sync_status, size=_sync_status)

        self.status_label = Label(
            text="就绪：点击按钮开始（不会自动播放）",
            font_size=18,
            font_name=self.font if self.font else None,
            color=(1, 1, 1, 0.92),
            halign="left",
            valign="middle",
            size_hint=(0.96, 1),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
        )
        self.status_label.bind(size=lambda *_: setattr(self.status_label, "text_size", (self.status_label.width, None)))
        self.status.add_widget(self.status_label)
        self.card.add_widget(self.status)

        # 小说区：更大 + 居中 + 玻璃面板
        self.content_area = FloatLayout(size_hint=(1, 1))
        root.add_widget(self.content_area)

        self.novel_panel = FloatLayout(
            size_hint=(0.94, 0.70),
            pos_hint={"center_x": 0.5, "center_y": 0.44},
        )
        with self.novel_panel.canvas.before:
            Color(0, 0, 0, 0.36)
            self.novel_shadow = RoundedRectangle(pos=(self.novel_panel.x, self.novel_panel.y - 10), size=self.novel_panel.size, radius=[18])
            Color(0, 0, 0, 0.44)
            self.novel_panel_rect = RoundedRectangle(pos=self.novel_panel.pos, size=self.novel_panel.size, radius=[18])
            Color(1, 1, 1, 0.08)
            self.novel_gloss = RoundedRectangle(
                pos=(self.novel_panel.x, self.novel_panel.y + self.novel_panel.height * 0.62),
                size=(self.novel_panel.width, self.novel_panel.height * 0.38),
                radius=[18]
            )
            Color(0.95, 0.80, 0.25, 0.22)
            self.novel_gold_outer = Line(
                rounded_rectangle=[self.novel_panel.x, self.novel_panel.y, self.novel_panel.width, self.novel_panel.height, 18],
                width=2.4
            )
            Color(1, 1, 1, 0.10)
            self.novel_panel_line = Line(
                rounded_rectangle=[self.novel_panel.x, self.novel_panel.y, self.novel_panel.width, self.novel_panel.height, 18],
                width=1.2
            )

        def _sync_novel_panel(*_):
            self.novel_shadow.pos = (self.novel_panel.x, self.novel_panel.y - 10)
            self.novel_shadow.size = self.novel_panel.size
            self.novel_panel_rect.pos = self.novel_panel.pos
            self.novel_panel_rect.size = self.novel_panel.size
            self.novel_gloss.pos = (self.novel_panel.x, self.novel_panel.y + self.novel_panel.height * 0.62)
            self.novel_gloss.size = (self.novel_panel.width, self.novel_panel.height * 0.38)
            self.novel_gold_outer.rounded_rectangle = [
                self.novel_panel.x, self.novel_panel.y, self.novel_panel.width, self.novel_panel.height, 18
            ]
            self.novel_panel_line.rounded_rectangle = [
                self.novel_panel.x, self.novel_panel.y, self.novel_panel.width, self.novel_panel.height, 18
            ]

        self.novel_panel.bind(pos=_sync_novel_panel, size=_sync_novel_panel)

        self.novel_scroll = ScrollView(size_hint=(0.94, 0.92), pos_hint={"center_x": 0.5, "center_y": 0.50})

        self.novel_label = Label(
            text="",
            size_hint_y=None,
            text_size=(Window.width * 0.88, None),
            font_size=32,
            halign="center",
            valign="top",
            font_name=self.font if self.font else None,
            color=(0.92, 0.10, 0.10, 1),
        )
        self.novel_label.bind(texture_size=self._update_novel_label_height)
        self.novel_scroll.add_widget(self.novel_label)
        self.novel_panel.add_widget(self.novel_scroll)

        Window.bind(size=self._on_window_resize)

        # 启动：首页不播
        self._show_home()

        # 开启雪花
        self.snow.start()

        return root

    # ------------------ UI ------------------

    def _on_window_resize(self, *_):
        self.novel_label.text_size = (Window.width * 0.88, None)

    def _make_pill_button(self, text: str, kind="green", font_size=26, height=108) -> Button:
        btn = Button(
            text=text,
            font_size=font_size,
            font_name=self.font if self.font else None,
            size_hint=(1, None),
            height=height,
            background_normal="",
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 0.98),
        )

        if kind == "green":
            col_up = (0.12, 0.30, 0.22, 0.86)
            col_down = (0.10, 0.22, 0.16, 0.96)
        else:
            col_up = (0.54, 0.12, 0.12, 0.88)
            col_down = (0.40, 0.08, 0.08, 0.97)

        gold = (0.95, 0.80, 0.25, 0.78)

        with btn.canvas.before:
            Color(0, 0, 0, 0.34)
            btn._shadow = RoundedRectangle(pos=(btn.x, btn.y - 6), size=(btn.width, btn.height), radius=[btn.height / 2])

            btn._bg_color = Color(*col_up)
            btn._bg_rect = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[btn.height / 2])

            btn._shine_color = Color(1, 1, 1, 0.08)
            btn._shine_rect = RoundedRectangle(
                pos=(btn.x, btn.y + btn.height * 0.55),
                size=(btn.width, btn.height * 0.45),
                radius=[btn.height / 2]
            )

            btn._glow_color = Color(gold[0], gold[1], gold[2], 0.16)
            btn._glow = Line(rounded_rectangle=[btn.x, btn.y, btn.width, btn.height, btn.height / 2], width=4.2)

            btn._line_color = Color(*gold)
            btn._line = Line(rounded_rectangle=[btn.x, btn.y, btn.width, btn.height, btn.height / 2], width=2.0)

        def _sync(*_):
            btn._shadow.pos = (btn.x, btn.y - 6)
            btn._shadow.size = (btn.width, btn.height)
            btn._shadow.radius = [btn.height / 2]

            btn._bg_rect.pos = btn.pos
            btn._bg_rect.size = btn.size
            btn._bg_rect.radius = [btn.height / 2]

            btn._shine_rect.pos = (btn.x, btn.y + btn.height * 0.55)
            btn._shine_rect.size = (btn.width, btn.height * 0.45)
            btn._shine_rect.radius = [btn.height / 2]

            btn._glow.rounded_rectangle = [btn.x, btn.y, btn.width, btn.height, btn.height / 2]
            btn._line.rounded_rectangle = [btn.x, btn.y, btn.width, btn.height, btn.height / 2]

        btn.bind(pos=_sync, size=_sync)

        def _down(*_):
            btn._bg_color.rgba = col_down
            btn._shine_color.rgba = (1, 1, 1, 0.04)
            btn._glow_color.rgba = (gold[0], gold[1], gold[2], 0.10)

        def _up(*_):
            btn._bg_color.rgba = col_up
            btn._shine_color.rgba = (1, 1, 1, 0.08)
            btn._glow_color.rgba = (gold[0], gold[1], gold[2], 0.16)

        btn.bind(on_press=_down, on_release=_up)
        return btn

    def _update_novel_label_height(self, *_):
        self.novel_label.height = self.novel_label.texture_size[1] + 28

    def _set_bg(self, path: str):
        if path and os.path.exists(path):
            self.bg.source = path
            self.bg.reload()

    def _clear_content(self):
        self.content_area.clear_widgets()

    # ------------------ 音频 ------------------

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
        s = SoundLoader.load(path)
        if s:
            self._sound_cache[path] = s
        return s

    def _play_sound(self, path: str, loop: bool = False):
        self._stop_sound()
        if not path or not os.path.exists(path):
            self.status_label.text = f"找不到音频：{os.path.basename(path) if path else '空路径'}"
            return
        s = self._get_sound_cached(path)
        if not s:
            self.status_label.text = f"无法加载音频：{os.path.basename(path)}"
            return
        self.sound = s
        self.sound.loop = loop
        try:
            if hasattr(self.sound, "seek"):
                self.sound.seek(0)
        except Exception:
            pass
        self.sound.play()

    # ------------------ 小说 ------------------

    def _make_novel_pages_10(self):
        pages = []
        pages.append("打开微信找到褚少华对话聊天框输入  我爱你❤️  解锁新剧情…")

        fill_block = "\n".join(["我爱徐林静❤️" for _ in range(44)])
        for _ in range(9):
            pages.append(fill_block)

        return pages

    def _render_novel_page(self):
        total = len(self.novel_pages)
        i = self.novel_page_i % total
        self.novel_label.text = f"🎄 第 {i+1}/{total} 页\n\n{self.novel_pages[i]}"

    # ------------------ 模式 ------------------

    def _fallback_bg(self):
        p = os.path.join(self.assets_dir, "listen_bg1.png")
        if os.path.exists(p):
            return p
        icon = os.path.join(self.root_dir, "icon.png")
        if os.path.exists(icon):
            return icon
        return ""

    def _show_home(self):
        self.mode = "home"
        self._clear_content()
        self._set_bg(self._fallback_bg())
        self.status_label.text = "就绪：点击按钮开始（不会自动播放）"

    def _show_novel(self):
        self.mode = "novel"
        self._clear_content()
        self._set_bg(self.bg_novel if os.path.exists(self.bg_novel) else self._fallback_bg())

        self.content_area.add_widget(self.novel_panel)
        self._render_novel_page()

        if self.novel_track:
            self._play_sound(self.novel_track, loop=True)
            self.status_label.text = "小说：listen8.mp3（循环） | 背景：listen_bg8.png"
        else:
            self.status_label.text = "小说主题曲缺少 listen8.mp3（根目录）"

    # ------------------ 三按钮 ------------------

    def on_listen_press(self, *_):
        if not self.listen_tracks:
            self.status_label.text = "缺少 listen1~listen6.mp3（根目录）"
            return
        if not self.listen_bgs:
            self.status_label.text = "缺少 assets/listen_bg1~listen_bg6.png"
            return

        self.mode = "listen"
        self._clear_content()

        self.listen_index = (self.listen_index + 1) % len(self.listen_tracks)
        self.bg_index = (self.bg_index + 1) % len(self.listen_bgs)

        track = self.listen_tracks[self.listen_index]
        bg = self.listen_bgs[self.bg_index]

        self._set_bg(bg)
        self._play_sound(track, loop=False)
        self.status_label.text = f"听歌：{os.path.basename(track)} | 背景：{os.path.basename(bg)}"

    def on_love_press(self, *_):
        self.mode = "love"
        self._clear_content()

        self._set_bg(self.bg_love if os.path.exists(self.bg_love) else self._fallback_bg())

        if not self.love_track:
            self.status_label.text = "缺少 listen7.mp3（根目录）"
            return

        self._play_sound(self.love_track, loop=False)
        self.status_label.text = "我爱：listen7.mp3 | 背景：listen_bg7.png"

    def on_novel_press(self, *_):
        if self.mode != "novel":
            self.novel_page_i = 0
            self._show_novel()
        else:
            self.novel_page_i += 1
            self._render_novel_page()


if __name__ == "__main__":
    ProtonApp().run()
