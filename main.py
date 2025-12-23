# main.py（v0稳定版 1/2：只保证“按钮必响应 + 必有声音 + 必不黑屏”）
import os
import re

from kivy.app import App
from kivy.core.audio import SoundLoader
from kivy.core.window import Window
from kivy.resources import resource_add_path
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label


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


def _pick_existing(candidates):
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return ""


class ProtonV0(App):
    def build(self):
        self.root_dir = _app_dir()
        self.assets_dir = os.path.join(self.root_dir, "assets")
        resource_add_path(self.root_dir)
        resource_add_path(self.assets_dir)

        root_files = _safe_listdir(self.root_dir)
        assets_files = _safe_listdir(self.assets_dir)

        # 中文字体兜底（你现在根目录有这个）
        self.font = _pick_existing([
            os.path.join(self.root_dir, "NotoSansSC-VariableFont_wght.ttf"),
            os.path.join(self.assets_dir, "NotoSansSC-VariableFont_wght.ttf"),
        ])

        # 背景：assets/listen_bg*.png（允许没有7/8也能跑）
        bg_files = _sort_by_number(assets_files, r"^listen_bg(\d+)\.png$")
        self.bgs = [os.path.join(self.assets_dir, f) for f in bg_files]

        # 听歌：listen1..listen6（排除 7/8，避免和“爱/小说主题曲”冲突）
        listen_files = _sort_by_number(root_files, r"^listen(\d+)\.mp3$")
        self.listen_tracks = []
        for f in listen_files:
            num = int(re.findall(r"\d+", f)[0])
            if num in (7, 8):
                continue
            self.listen_tracks.append(os.path.join(self.root_dir, f))

        # 爱：listen7.mp3
        self.love_track = _pick_existing([
            os.path.join(self.root_dir, "listen7.mp3"),
            os.path.join(self.assets_dir, "listen7.mp3"),
        ])

        # 小说主题曲：listen8.mp3（你要求：App刚打开就循环播放它）
        self.theme_track = _pick_existing([
            os.path.join(self.root_dir, "listen8.mp3"),
            os.path.join(self.assets_dir, "listen8.mp3"),
        ])

        # bg7/bg8（允许不存在，照样不崩）
        self.bg7 = os.path.join(self.assets_dir, "listen_bg7.png")
        self.bg8 = os.path.join(self.assets_dir, "listen_bg8.png")

        self.listen_i = -1
        self.bg_i = -1
        self.sound = None

        # ===== UI =====
        root = FloatLayout()

        self.bg = Image(
            source=self._fallback_bg(),
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
        )
        root.add_widget(self.bg)

        self.top = Label(
            text="你好，静静，我是质子 1 号 。褚少华派我来陪伴你。",
            size_hint=(1, None),
            height=90,
            pos_hint={"x": 0, "top": 1},
            font_size=20,
            font_name=self.font if self.font else None,
        )
        root.add_widget(self.top)

        btn_box = BoxLayout(
            orientation="vertical",
            spacing=18,
            padding=[24, 0, 24, 24],
            size_hint=(1, None),
            height=max(320, int(Window.height * 0.40)),
            pos_hint={"x": 0, "y": 0},
        )

        self.btn_listen = Button(
            text="和褚少华一起听歌",
            font_size=28,
            font_name=self.font if self.font else None,
            size_hint=(1, None),
            height=110,
        )
        self.btn_novel = Button(
            text="和褚少华一起看小说",
            font_size=28,
            font_name=self.font if self.font else None,
            size_hint=(1, None),
            height=110,
        )
        self.btn_love = Button(
            text="我爱褚少华",
            font_size=28,
            font_name=self.font if self.font else None,
            size_hint=(1, None),
            height=110,
        )

        self.btn_listen.bind(on_press=self.on_listen)
        self.btn_novel.bind(on_press=self.on_novel)
        self.btn_love.bind(on_press=self.on_love)

        btn_box.add_widget(self.btn_listen)
        btn_box.add_widget(self.btn_novel)
        btn_box.add_widget(self.btn_love)
        root.add_widget(btn_box)

        # ===== v0 关键：启动即循环播放 listen8（如果存在）=====
        self._play(self.theme_track, loop=True, label_hint="主题曲 listen8 循环")

        return root
       # main.py（v0稳定版 2/2：播放/切换逻辑 —— 极简、必响应）

    def _fallback_bg(self):
        # 有 listen_bg1 就用它，否则 icon.png，否则空
        if self.bgs:
            return self.bgs[0]
        icon = os.path.join(self.root_dir, "icon.png")
        if os.path.exists(icon):
            return icon
        return ""

    def _set_bg(self, path):
        if path and os.path.exists(path):
            self.bg.source = path
            self.bg.reload()

    def _stop(self):
        try:
            if self.sound:
                self.sound.stop()
        except Exception:
            pass
        self.sound = None

    def _play(self, path, loop=False, label_hint=""):
        # v0：任何错误都显示到 top，便于你截图给我定位
        if not path or not os.path.exists(path):
            self.top.text = f"缺少音频：{os.path.basename(path) if path else '空路径'}"
            return
        self._stop()
        s = SoundLoader.load(path)
        if not s:
            self.top.text = f"无法加载音频：{os.path.basename(path)}"
            return
        self.sound = s
        self.sound.loop = loop
        self.sound.play()
        if label_hint:
            self.top.text = label_hint

    # ===== 三个按钮：点一下必有变化（文字提示 + 背景切换 + 播放）=====

    def on_listen(self, *_):
        # 下一首（listen1~6） + 下一背景（排除7/8不强制）
        if not self.listen_tracks:
            self.top.text = "缺少 listen1~listen6.mp3（根目录）"
            return

        self.listen_i = (self.listen_i + 1) % len(self.listen_tracks)
        track = self.listen_tracks[self.listen_i]

        # 背景轮播：如果有多张就轮播，没有也不影响播放
        if self.bgs:
            self.bg_i = (self.bg_i + 1) % len(self.bgs)
            bg = self.bgs[self.bg_i]
            # 如果刚好是 bg7/bg8，也没关系，v0先不管“语义”，只保证能切
            self._set_bg(bg)

        self._play(track, loop=False, label_hint=f"听歌：{os.path.basename(track)}")

    def on_love(self, *_):
        # bg7 + 播放 listen7（不循环）
        if os.path.exists(self.bg7):
            self._set_bg(self.bg7)
        if not self.love_track:
            self.top.text = "缺少 listen7.mp3"
            return
        self._play(self.love_track, loop=False, label_hint="我爱褚少华：listen7")

    def on_novel(self, *_):
        # bg8 + 主题曲 listen8（循环）
        if os.path.exists(self.bg8):
            self._set_bg(self.bg8)
        if not self.theme_track:
            self.top.text = "缺少 listen8.mp3（主题曲）"
            return
        self._play(self.theme_track, loop=True, label_hint="小说主题曲 listen8 循环")


if __name__ == "__main__":
    ProtonV0().run() 
