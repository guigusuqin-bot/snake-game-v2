# main.py  (Final UI + Snow + No Auto Play + No Thread + No CoreImage)
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
from kivy.graphics import Color, RoundedRectangle, Line, Ellipse, Rectangle
from kivy.animation import Animation


# ---------------------- Utils ----------------------
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


# ---------------------- Snow Layer (Canvas + Clock, no thread) ----------------------
class SnowLayer(FloatLayout):
    """
    轻量雪花层：纯 Canvas + Clock 更新；无线程；不卡为第一目标
    """
    def __init__(self, count=26, **kwargs):
        super().__init__(**kwargs)
        self.count = int(count)
        self._flakes = []
        self._running = False

        Window.bind(size=self._on_resize)

        with self.canvas:
            self._snow_color = Color(1, 1, 1, 0.75)
            for _ in range(self.count):
                flake = self._new_flake(spawn_top=False)
                e = Ellipse(pos=(flake["x"], flake["y"]), size=(flake["r"], flake["r"]))
                flake["e"] = e
                self._flakes.append(flake)

    def _new_flake(self, spawn_top=False):
        w, h = Window.size
        r = random.uniform(2.0, 5.0)
        x = random.uniform(0, max(1, w - r))
        if spawn_top:
            y = random.uniform(h, h + h * 0.25)
        else:
            y = random.uniform(0, h)
        vy = random.uniform(55.0, 130.0)
        vx = random.uniform(-12.0, 12.0)
        phase = random.uniform(0, 6.28)
        wob = random.uniform(0.8, 1.8)
        return {"x": x, "y": y, "r": r, "vy": vy, "vx": vx, "phase": phase, "wob": wob}

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

    def _tick(self, dt):
        w, h = Window.size
        for f in self._flakes:
            f["y"] -= f["vy"] * dt

            # 轻飘的横向漂移（不抖、不飙）
            f["x"] += f["vx"] * dt
            f["x"] += (f["wob"] * 10.0) * dt * (random.uniform(-1, 1))

            # wrap
            if f["x"] < -10:
                f["x"] = w + 10
            if f["x"] > w + 10:
                f["x"] = -10

            # 到底重生
            if f["y"] < -20:
                nf = self._new_flake(spawn_top=True)
                f.update(nf)

            f["e"].pos = (f["x"], f["y"])


# ---------------------- App ----------------------
class ProtonApp(App):
    def build(self):
        self.root_dir = _app_dir()
        self.assets_dir = os.path.join(self.root_dir, "assets")

        resource_add_path(self.root_dir)
        resource_add_path(self.assets_dir)

        root_files = _safe_listdir(self.root_dir)
        assets_files = _safe_listdir(self.assets_dir)

        # 字体兜底（可没有）
        self.font = _pick_existing([
            os.path.join(self.root_dir, "NotoSansSC-VariableFont_wght.ttf"),
            os.path.join(self.assets_dir, "NotoSansSC-VariableFont_wght.ttf"),
        ])

        # 背景：assets/listen_bg1~8.png（注意：你的截图是 listen_bg1.png 带下划线）
        self.bg_love = os.path.join(self.assets_dir, "listen_bg7.png")
        self.bg_novel = os.path.join(self.assets_dir, "listen_bg8.png")

        # 听歌背景：1~6
        self.listen_bgs = []
        for i in range(1, 7):
            p = os.path.join(self.assets_dir, f"listen_bg{i}.png")
            if os.path.exists(p):
                self.listen_bgs.append(p)

        # 听歌音频：listen1~6（根目录）
        self.listen_tracks = []
        for i in range(1, 7):
            p = os.path.join(self.root_dir, f"listen{i}.mp3")
            if os.path.exists(p):
                self.listen_tracks.append(p)

        # 爱：listen7
        self.love_track = _pick_existing([os.path.join(self.root_dir, "listen7.mp3")])

        # 小说主题曲：listen8
        self.novel_track = _pick_existing([os.path.join(self.root_dir, "listen8.mp3")])

        # 小说内容（10页）
        self.novel_pages = self._make_novel_pages_10()
        self.novel_page_i = 0

        # 状态
        self.mode = "home"
        self.sound = None
        self.listen_index = -1
        self.bg_index = -1
        self._sound_cache = {}

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

        # 背景暗化遮罩 + 轻微暗角（提升“成片感”）
        with root.canvas.after:
            # 全屏暗化
            self._mask_color = Color(0, 0, 0, 0.28)
            self._mask_rect = Rectangle(pos=root.pos, size=root.size)
        root.bind(size=self._sync_mask, pos=self._sync_mask)

        # 雪花层（背景之上）
        self.snow = SnowLayer(count=28, size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        root.add_widget(self.snow)

        # 顶部文案（两行，居中，轻“陪伴感”）
        self.title = Label(
            text="你好，静静\n我是质子 1 号。褚少华派我来陪你。",
            size_hint=(1, None),
            height=140,
            pos_hint={"center_x": 0.5, "top": 0.96},
            font_size=26,
            font_name=self.font if self.font else None,
            halign="center",
            valign="middle",
            color=(1, 1, 1, 0.96),
        )
        self.title.bind(size=self.title.setter("text_size"))
        root.add_widget(self.title)

        # 顶部状态（小字，不抢）
        self.status = Label(
            text="",
            size_hint=(1, None),
            height=40,
            pos_hint={"center_x": 0.5, "top": 0.77},
            font_size=18,
            font_name=self.font if self.font else None,
            halign="center",
            valign="middle",
            color=(1, 1, 1, 0.80),
        )
        self.status.bind(size=self.status.setter("text_size"))
        root.add_widget(self.status)

        # 底部卡片容器（UI 成品感核心）
        self.card = BoxLayout(
            orientation="vertical",
            spacing=16,
            padding=[20, 20, 20, 20],
            size_hint=(0.90, None),
            height=290,
            pos_hint={"center_x": 0.5, "y": 0.08},
        )
        with self.card.canvas.before:
            # 半透明玻璃卡片
            self._card_color = Color(1, 1, 1, 0.16)
            self._card_rect = RoundedRectangle(pos=self.card.pos, size=self.card.size, radius=[28])
            # 金色细边
            self._card_line_color = Color(0.95, 0.84, 0.35, 0.55)
            self._card_line = Line(rounded_rectangle=[self.card.x, self.card.y, self.card.width, self.card.height, 28], width=1.2)
        self.card.bind(pos=self._sync_card, size=self._sync_card)
        root.add_widget(self.card)

        # 三按钮（统一风格 + 按下动效）
        self.btn_listen = self._make_premium_button("🎵  和褚少华一起听歌")
        self.btn_novel = self._make_premium_button("📖  和褚少华一起看小说")
        self.btn_love = self._make_premium_button("❤️  我爱褚少华")

        self.btn_listen.bind(on_press=self.on_listen_press)
        self.btn_novel.bind(on_press=self.on_novel_press)
        self.btn_love.bind(on_press=self.on_love_press)

        self.card.add_widget(self.btn_listen)
        self.card.add_widget(self.btn_novel)
        self.card.add_widget(self.btn_love)

        # 小说区（覆盖在中部）
        self.content_area = FloatLayout(size_hint=(1, 1))
        root.add_widget(self.content_area)

        self.novel_scroll = ScrollView(
            size_hint=(0.92, 0.55),
            pos_hint={"center_x": 0.5, "center_y": 0.55},
        )
        self.novel_label = Label(
            text="",
            size_hint_y=None,
            text_size=(Window.width * 0.86, None),
            font_size=24,
            halign="left",
            valign="top",
            font_name=self.font if self.font else None,
            color=(0.98, 0.90, 0.70, 1),  # 暖金色（比纯红高级）
        )
        self.novel_label.bind(texture_size=self._update_novel_label_height)
        self.novel_scroll.add_widget(self.novel_label)
        Window.bind(size=self._on_window_resize)

        # 启动：首页不播放
        self._show_home()

        # 雪花开启
        self.snow.start()

        return root

    # ---------------- UI sync ----------------
    def _sync_mask(self, instance, *_):
        self._mask_rect.pos = instance.pos
        self._mask_rect.size = instance.size

    def _sync_card(self, *_):
        self._card_rect.pos = self.card.pos
        self._card_rect.size = self.card.size
        self._card_rect.radius = [28]
        self._card_line.rounded_rectangle = [self.card.x, self.card.y, self.card.width, self.card.height, 28]

    def _on_window_resize(self, *_):
        self.novel_label.text_size = (Window.width * 0.86, None)
        # 卡片高度自适配一点
        self.card.height = 290 if Window.height >= 720 else 260

    def _update_novel_label_height(self, *_):
        self.novel_label.height = self.novel_label.texture_size[1] + 24

    def _set_bg(self, path: str):
        if path and os.path.exists(path):
            self.bg.source = path
            self.bg.reload()

    def _clear_content(self):
        self.content_area.clear_widgets()

    # ---------------- Premium Button ----------------
    def _make_premium_button(self, text: str) -> Button:
        btn = Button(
            text=text,
            font_size=22,
            font_name=self.font if self.font else None,
            size_hint=(1, None),
            height=74,
            background_normal="",
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 0.98),
        )

        # 深红渐“质感” + 金边（比你现在纯红更高级）
        btn._col_up = (0.55, 0.14, 0.14, 0.85)
        btn._col_down = (0.40, 0.10, 0.10, 0.92)
        btn._stroke_col = (0.95, 0.84, 0.35, 0.90)

        with btn.canvas.before:
            btn._bg_color = Color(*btn._col_up)
            btn._bg_rect = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[20])
            btn._line_color = Color(*btn._stroke_col)
            btn._line = Line(rounded_rectangle=[btn.x, btn.y, btn.width, btn.height, 20], width=1.8)

        def _sync(*_):
            btn._bg_rect.pos = btn.pos
            btn._bg_rect.size = btn.size
            btn._bg_rect.radius = [20]
            btn._line.rounded_rectangle = [btn.x, btn.y, btn.width, btn.height, 20]

        btn.bind(pos=_sync, size=_sync)

        # 按下动效：轻缩放 + 颜色加深（成品感关键）
        def _down(*_):
            btn._bg_color.rgba = btn._col_down
            # 记录原始
            btn._orig_h = btn.height
            btn._orig_y = btn.y
            anim = Animation(height=btn._orig_h - 6, y=btn._orig_y + 3, d=0.06)
            anim.start(btn)

        def _up(*_):
            btn._bg_color.rgba = btn._col_up
            # 回弹
            try:
                oh = getattr(btn, "_orig_h", btn.height)
                oy = getattr(btn, "_orig_y", btn.y)
            except Exception:
                oh, oy = btn.height, btn.y
            anim = Animation(height=oh, y=oy, d=0.08)
            anim.start(btn)

        btn.bind(on_press=_down, on_release=_up)
        return btn

    # ---------------- Audio ----------------
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
            self.status.text = f"找不到音频：{os.path.basename(path) if path else '空路径'}"
            return
        s = self._get_sound_cached(path)
        if not s:
            self.status.text = f"无法加载音频：{os.path.basename(path)}"
            return
        self.sound = s
        self.sound.loop = loop
        try:
            if hasattr(self.sound, "seek"):
                self.sound.seek(0)
        except Exception:
            pass
        self.sound.play()

    # ---------------- Novel ----------------
    def _make_novel_pages_10(self):
        pages = []
        pages.append("打开微信找到褚少华对话聊天框输入：我爱你❤️  解锁新剧情…")
        for _ in range(9):
            pages.append("我爱徐林静❤️")
        return pages

    def _render_novel_page(self):
        total = len(self.novel_pages)
        i = self.novel_page_i % total
        self.novel_label.text = f"🎄 第 {i+1}/{total} 页\n\n{self.novel_pages[i]}"

    # ---------------- Modes ----------------
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
        self.status.text = "❄️ 选择一个入口（不会自动播放）"

    def _show_novel(self):
        self.mode = "novel"
        self._clear_content()
        self._set_bg(self.bg_novel if os.path.exists(self.bg_novel) else self._fallback_bg())
        self.content_area.add_widget(self.novel_scroll)
        self._render_novel_page()

        # 进入小说才循环播放 listen8
        if self.novel_track:
            self._play_sound(self.novel_track, loop=True)
            self.status.text = "🎄 小说模式：再按一次翻页"
        else:
            self.status.text = "缺少 listen8.mp3（根目录）"

    # ---------------- Buttons ----------------
    def on_listen_press(self, *_):
        if not self.listen_tracks:
            self.status.text = "缺少 listen1~listen6.mp3（根目录）"
            return
        if not self.listen_bgs:
            self.status.text = "缺少 assets/listen_bg1~listen_bg6.png"
            return

        self.mode = "listen"
        self._clear_content()

        self.listen_index = (self.listen_index + 1) % len(self.listen_tracks)
        self.bg_index = (self.bg_index + 1) % len(self.listen_bgs)

        track = self.listen_tracks[self.listen_index]
        bg = self.listen_bgs[self.bg_index]

        self._set_bg(bg)
        self._play_sound(track, loop=False)
        self.status.text = f"🎵 听歌：{os.path.basename(track)}"

    def on_love_press(self, *_):
        self.mode = "love"
        self._clear_content()

        self._set_bg(self.bg_love if os.path.exists(self.bg_love) else self._fallback_bg())
        if not self.love_track:
            self.status.text = "缺少 listen7.mp3（根目录）"
            return

        self._play_sound(self.love_track, loop=False)
        self.status.text = "❤️ 我爱褚少华"

    def on_novel_press(self, *_):
        if self.mode != "novel":
            self.novel_page_i = 0
            self._show_novel()
        else:
            self.novel_page_i += 1
            self._render_novel_page()


if __name__ == "__main__":
    ProtonApp().run()
