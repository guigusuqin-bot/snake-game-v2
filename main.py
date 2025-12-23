# main.py（v0 圣诞雪花增强版：红金按钮 + 雪花飘落；不自动播放；无 CoreImage/无线程）
import os
import re
import random

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
    轻量雪花层：纯 Canvas + Clock 更新；无线程；不卡为第一目标
    """
    def __init__(self, count=28, **kwargs):
        super().__init__(**kwargs)
        self.count = int(count)
        self._flakes = []
        self._running = False

        # 绑定尺寸变化，确保雪花分布适配屏幕
        Window.bind(size=self._on_resize)

        with self.canvas:
            # 雪花颜色：略带暖白（更圣诞），透明一点
            self._snow_color = Color(1, 1, 1, 0.78)
            for _ in range(self.count):
                flake = self._new_flake(spawn_top=True)
                e = Ellipse(pos=(flake["x"], flake["y"]), size=(flake["r"], flake["r"]))
                flake["e"] = e
                self._flakes.append(flake)

    def _new_flake(self, spawn_top=False):
        w, h = Window.size
        r = random.uniform(2.0, 5.5)
        x = random.uniform(0, max(1, w - r))
        y = random.uniform(h * 0.2, h) if spawn_top else random.uniform(0, h)
        if spawn_top:
            y = random.uniform(h, h + h * 0.25)
        vy = random.uniform(50.0, 120.0)     # 下落速度
        vx = random.uniform(-18.0, 18.0)     # 左右漂移
        wob = random.uniform(0.8, 2.0)       # 摆动强度
        phase = random.uniform(0, 6.28)
        return {"x": x, "y": y, "r": r, "vy": vy, "vx": vx, "wob": wob, "phase": phase}

    def _on_resize(self, *_):
        # 重置雪花，避免旋转/尺寸变化后堆在角落
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
        # 30fps：更稳、更省
        Clock.schedule_interval(self._tick, 1 / 30.0)

    def stop(self):
        if not self._running:
            return
        self._running = False
        Clock.unschedule(self._tick)

    def _tick(self, dt):
        w, h = Window.size
        t = Clock.get_boottime()

        for f in self._flakes:
            # 下落
            f["y"] -= f["vy"] * dt

            # 轻微左右摆动（更像雪）
            f["x"] += (f["vx"] + (random.uniform(-1, 1) * 2.0)) * dt
            f["x"] += (f["wob"] * 18.0) * (dt) * (0.6 * (1 + 0.35 * (random.random())))
            f["x"] += 12.0 * dt * (0.5 * (1 + 0.2 * random.random())) * (random.choice([-1, 1]))

            # 用 phase 做一点柔和的正弦漂移（避免“直线下坠”）
            f["x"] += (10.0 * dt) * (1.0 if random.random() > 0.5 else -1.0)
            f["x"] += (6.0 * dt) * (0.5 + 0.5 * (random.random()))
            f["x"] += (8.0 * dt) * (0.5 + 0.5 * (random.random())) * (0.5 + 0.5 * (random.random()))
            f["x"] += 14.0 * dt * (0.6 * (random.random() - 0.5))

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


class ProtonApp(App):
    def build(self):
        self.root_dir = _app_dir()
        self.assets_dir = os.path.join(self.root_dir, "assets")
        resource_add_path(self.root_dir)
        resource_add_path(self.assets_dir)

        root_files = _safe_listdir(self.root_dir)
        assets_files = _safe_listdir(self.assets_dir)

        # 字体兜底
        self.font = _pick_existing([
            os.path.join(self.root_dir, "NotoSansSC-VariableFont_wght.ttf"),
            os.path.join(self.assets_dir, "NotoSansSC-VariableFont_wght.ttf"),
        ])

        # 背景：assets/listen_bg1~8.png
        bg_files = _sort_by_number(assets_files, r"^listen_bg(\d+)\.png$")
        self.bg_love = os.path.join(self.assets_dir, "listen_bg7.png")
        self.bg_novel = os.path.join(self.assets_dir, "listen_bg8.png")

        # 听歌轮播背景：只用 1~6
        self.listen_bgs = []
        for i in range(1, 7):
            p = os.path.join(self.assets_dir, f"listen_bg{i}.png")
            if os.path.exists(p):
                self.listen_bgs.append(p)

        # 听歌轮播：listen1~6
        self.listen_tracks = []
        for i in range(1, 7):
            p = os.path.join(self.root_dir, f"listen{i}.mp3")
            if os.path.exists(p):
                self.listen_tracks.append(p)

        # 爱：listen7
        self.love_track = _pick_existing([os.path.join(self.root_dir, "listen7.mp3")])

        # 小说主题曲：listen8
        self.novel_track = _pick_existing([os.path.join(self.root_dir, "listen8.mp3")])

        # 小说
        self.novel_pages = self._make_novel_pages_10()
        self.novel_page_i = 0

        # 状态
        self.mode = "home"
        self.sound = None
        self.listen_index = -1
        self.bg_index = -1

        # 音频缓存：减少切歌卡顿
        self._sound_cache = {}

        # UI Root
        root = FloatLayout()

        # 背景
        self.bg = Image(
            source="",
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
        )
        root.add_widget(self.bg)

        # ✅ 雪花层（放在背景之上、按钮/文字之下）
        self.snow = SnowLayer(count=30, size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        root.add_widget(self.snow)

        # 顶部文字
        self.top_label = Label(
            text="❄️🎄 圣诞快乐，静静。质子 1 号陪你过这个冬天。",
            size_hint=(1, None),
            height=92,
            pos_hint={"x": 0, "top": 1},
            font_size=21,
            font_name=self.font if self.font else None,
            color=(1, 1, 1, 0.98),
        )
        root.add_widget(self.top_label)

        # 按钮区
        self.btn_box = BoxLayout(
            orientation="vertical",
            spacing=18,
            padding=[24, 0, 24, 24],
            size_hint=(1, None),
            height=max(320, int(Window.height * 0.40)),
            pos_hint={"x": 0, "y": 0},
        )
        Window.bind(size=self._on_window_resize)

        self.btn_listen = self._make_round_button("和褚少华一起听歌", font_size=28, height=110)
        self.btn_listen.bind(on_press=self.on_listen_press)

        self.btn_novel = self._make_round_button("和褚少华一起看小说", font_size=28, height=110)
        self.btn_novel.bind(on_press=self.on_novel_press)

        self.btn_love = self._make_round_button("我爱褚少华", font_size=28, height=110)
        self.btn_love.bind(on_press=self.on_love_press)

        self.btn_box.add_widget(self.btn_listen)
        self.btn_box.add_widget(self.btn_novel)
        self.btn_box.add_widget(self.btn_love)
        root.add_widget(self.btn_box)

        # 小说区
        self.content_area = FloatLayout(size_hint=(1, 1))
        root.add_widget(self.content_area)

        self.novel_scroll = ScrollView(
            size_hint=(0.92, 0.55),
            pos_hint={"center_x": 0.5, "center_y": 0.62},
        )
        self.novel_label = Label(
            text="",
            size_hint_y=None,
            text_size=(Window.width * 0.86, None),
            font_size=24,
            halign="left",
            valign="top",
            font_name=self.font if self.font else None,
            color=(0.92, 0.10, 0.10, 1),  # ✅ 小说内容红色
        )
        self.novel_label.bind(texture_size=self._update_novel_label_height)
        self.novel_scroll.add_widget(self.novel_label)

        # ✅ 启动：只进首页，不播放任何音乐（删除“进App自动循环 listen8”）
        self._show_home()

        # ✅ 开启雪花（纯 Clock，无线程）
        self.snow.start()

        return root

    # -------- UI -------
    def _on_window_resize(self, *_):
        self.btn_box.height = max(320, int(Window.height * 0.40))
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

        # ✅ 圣诞红 + 金边
        btn._col_up = (0.60, 0.12, 0.12, 0.88)
        btn._col_down = (0.40, 0.08, 0.08, 0.95)
        btn._stroke_col = (0.95, 0.80, 0.25, 0.95)

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

    def _set_bg(self, path: str):
        if path and os.path.exists(path):
            self.bg.source = path
            self.bg.reload()

    def _clear_content(self):
        self.content_area.clear_widgets()

    # -------- 音频 -------
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
            self.top_label.text = f"找不到音频：{os.path.basename(path) if path else '空路径'}"
            return
        s = self._get_sound_cached(path)
        if not s:
            self.top_label.text = f"无法加载音频：{os.path.basename(path)}"
            return
        self.sound = s
        self.sound.loop = loop
        try:
            if hasattr(self.sound, "seek"):
                self.sound.seek(0)
        except Exception:
            pass
        self.sound.play()

    # -------- 小说 -------
    def _make_novel_pages_10(self):
        pages = []
        pages.append("打开微信找到褚少华对话聊天框输入  我爱你❤️  解锁新剧情…")
        for _ in range(9):
            pages.append("我爱徐林静❤️")
        return pages

    def _render_novel_page(self):
        total = len(self.novel_pages)
        i = self.novel_page_i % total
        self.novel_label.text = f"🎄 第 {i+1}/{total} 页\n\n{self.novel_pages[i]}"

    # -------- 模式 -------
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
        # ✅ 首页不播放任何音乐（删除“进App自动循环 listen8”）

    def _show_novel(self):
        self.mode = "novel"
        self._clear_content()
        self._set_bg(self.bg_novel if os.path.exists(self.bg_novel) else self._fallback_bg())
        self.content_area.add_widget(self.novel_scroll)
        self._render_novel_page()

        # 小说主题曲：listen8（循环）——只在进入小说时播放
        if self.novel_track:
            self._play_sound(self.novel_track, loop=True)
        else:
            self.top_label.text = "小说主题曲缺少 listen8.mp3（根目录）"

    # -------- 三按钮 -------
    def on_listen_press(self, *_):
        if not self.listen_tracks:
            self.top_label.text = "缺少 listen1~listen6.mp3（根目录）"
            return
        if not self.listen_bgs:
            self.top_label.text = "缺少 assets/listen_bg1~listen_bg6.png"
            return

        self.mode = "listen"
        self._clear_content()

        self.listen_index = (self.listen_index + 1) % len(self.listen_tracks)
        self.bg_index = (self.bg_index + 1) % len(self.listen_bgs)

        track = self.listen_tracks[self.listen_index]
        bg = self.listen_bgs[self.bg_index]

        self._set_bg(bg)
        self._play_sound(track, loop=False)
        self.top_label.text = f"❄️🎵 听歌：{os.path.basename(track)} | 背景：{os.path.basename(bg)}"

    def on_love_press(self, *_):
        self.mode = "love"
        self._clear_content()

        self._set_bg(self.bg_love if os.path.exists(self.bg_love) else self._fallback_bg())

        if not self.love_track:
            self.top_label.text = "缺少 listen7.mp3（根目录）"
            return

        self._play_sound(self.love_track, loop=False)
        self.top_label.text = "🎄❤️ 我爱褚少华：listen7.mp3 | 背景：listen_bg7.png"

    def on_novel_press(self, *_):
        if self.mode != "novel":
            self.novel_page_i = 0
            self._show_novel()
            self.top_label.text = "🎄 小说模式：再按一次翻页（背景固定 bg8，主题曲 listen8 循环）"
        else:
            self.novel_page_i += 1
            self._render_novel_page()


if __name__ == "__main__":
    ProtonApp().run()
