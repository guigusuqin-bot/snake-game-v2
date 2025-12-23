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


# ---------------- utils ----------------
def _app_dir():
    return os.path.dirname(os.path.abspath(__file__))


def _pick_existing(paths):
    for p in paths:
        if p and os.path.exists(p):
            return p
    return ""


# ---------------- snow layer ----------------
class SnowLayer(FloatLayout):
    def __init__(self, count=28, **kwargs):
        super().__init__(**kwargs)
        self.count = count
        self.flakes = []
        self.running = False

        Window.bind(size=self._on_resize)

        with self.canvas:
            Color(1, 1, 1, 0.75)
            for _ in range(self.count):
                f = self._new_flake(True)
                e = Ellipse(pos=(f["x"], f["y"]), size=(f["r"], f["r"]))
                f["e"] = e
                self.flakes.append(f)

    def _new_flake(self, top=False):
        w, h = Window.size
        r = random.uniform(2, 5)
        return {
            "x": random.uniform(0, w),
            "y": random.uniform(h, h * 1.2) if top else random.uniform(0, h),
            "r": r,
            "vy": random.uniform(50, 120),
        }

    def _on_resize(self, *_):
        for f in self.flakes:
            f["x"] = random.uniform(0, Window.width)
            f["y"] = random.uniform(0, Window.height)

    def start(self):
        if not self.running:
            self.running = True
            Clock.schedule_interval(self._tick, 1 / 30)

    def _tick(self, dt):
        w, h = Window.size
        for f in self.flakes:
            f["y"] -= f["vy"] * dt
            if f["y"] < -10:
                f.update(self._new_flake(True))
            f["e"].pos = (f["x"], f["y"])


# ---------------- app ----------------
class ProtonApp(App):
    def build(self):
        self.root_dir = _app_dir()
        self.assets = os.path.join(self.root_dir, "assets")

        resource_add_path(self.root_dir)
        resource_add_path(self.assets)

        # 音频
        self.listen = [os.path.join(self.root_dir, f"listen{i}.mp3") for i in range(1, 7)]
        self.love = os.path.join(self.root_dir, "listen7.mp3")
        self.novel_music = os.path.join(self.root_dir, "listen8.mp3")

        # 背景
        self.bg_list = [os.path.join(self.assets, f"listen_bg{i}.png") for i in range(1, 7)]
        self.bg_love = os.path.join(self.assets, "listen_bg7.png")
        self.bg_novel = os.path.join(self.assets, "listen_bg8.png")

        self.sound = None
        self.listen_i = 0
        self.bg_i = 0
        self.page = 0

        root = FloatLayout()

        # 背景图
        self.bg = Image(allow_stretch=True, keep_ratio=False)
        root.add_widget(self.bg)

        # 雪花
        self.snow = SnowLayer(size_hint=(1, 1))
        root.add_widget(self.snow)

        # 顶部文案（更醒目）
        self.title = Label(
            text="🎄 我是质子 1 号，陪你过这个冬天",
            size_hint=(1, None),
            height=120,
            font_size=28,
            color=(1, 1, 1, 1),
            pos_hint={"top": 1},
        )
        root.add_widget(self.title)

        # 按钮区
        box = BoxLayout(
            orientation="vertical",
            spacing=20,
            size_hint=(0.85, None),
            height=360,
            pos_hint={"center_x": 0.5, "y": 0.05},
        )

        self.btn_listen = self._btn("一起听歌", self.on_listen)
        self.btn_novel = self._btn("一起看小说", self.on_novel)
        self.btn_love = self._btn("我爱你", self.on_love)

        box.add_widget(self.btn_listen)
        box.add_widget(self.btn_novel)
        box.add_widget(self.btn_love)

        root.add_widget(box)

        # 小说区
        self.scroll = ScrollView(size_hint=(0.9, 0.55), pos_hint={"center_x": 0.5, "center_y": 0.6})
        self.novel = Label(
            size_hint_y=None,
            font_size=30,
            halign="center",
            valign="middle",
            color=(0.9, 0.1, 0.1, 1),
        )
        self.novel.bind(texture_size=lambda *_: setattr(self.novel, "height", self.novel.texture_size[1] + 40))
        self.scroll.add_widget(self.novel)

        self.pages = ["打开微信输入：我爱你❤️"] + ["我爱徐林静❤️"] * 9

        self.bg.source = self.bg_list[0]
        self.snow.start()
        return root

    def _btn(self, text, cb):
        b = Button(text=text, font_size=26, background_normal="", background_color=(0.6, 0.1, 0.1, 0.9))
        b.bind(on_press=cb)
        return b

    def play(self, path, loop=False):
        if self.sound:
            self.sound.stop()
        if os.path.exists(path):
            self.sound = SoundLoader.load(path)
            if self.sound:
                self.sound.loop = loop
                self.sound.play()

    def on_listen(self, *_):
        self.bg.source = self.bg_list[self.bg_i % len(self.bg_list)]
        self.play(self.listen[self.listen_i % len(self.listen)])
        self.listen_i += 1
        self.bg_i += 1

    def on_love(self, *_):
        self.bg.source = self.bg_love
        self.play(self.love)

    def on_novel(self, *_):
        if self.scroll.parent is None:
            self.root.add_widget(self.scroll)
            self.page = 0
            self.play(self.novel_music, loop=True)
        else:
            self.page += 1
        self.novel.text = self.pages[self.page % len(self.pages)]


if __name__ == "__main__":
    ProtonApp().run()
