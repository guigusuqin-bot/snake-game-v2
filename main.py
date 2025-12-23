# main.py（v0 稳定版：无 CoreImage/无线程预热；bg7=爱；bg8=小说；小说主题曲 listen8）
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
from kivy.uix.scrollview import ScrollView
from kivy.graphics import Color, RoundedRectangle


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

        # -------------------------
        # 资源规则（按你最新约定）
        # -------------------------
        # 背景：assets/listen_bg1~8.png
        bg_files = _sort_by_number(assets_files, r"^listen_bg(\d+)\.png$")
        self.all_bgs = [os.path.join(self.assets_dir, f) for f in bg_files]

        self.bg_love = os.path.join(self.assets_dir, "listen_bg7.png")   # 爱按钮
        self.bg_novel = os.path.join(self.assets_dir, "listen_bg8.png")  # 小说按钮

        # 听歌轮播背景：只用 1~6（排除 7/8）
        self.listen_bgs = []
        for i in range(1, 7):
            p = os.path.join(self.assets_dir, f"listen_bg{i}.png")
            if os.path.exists(p):
                self.listen_bgs.append(p)

        # 音频：根目录 listen1~8.mp3
        mp3_files = _sort_by_number(root_files, r"^listen(\d+)\.mp3$")
        self.all_tracks = [os.path.join(self.root_dir, f) for f in mp3_files]

        # 听歌轮播：listen1~6（排除 7/8）
        self.listen_tracks = []
        for i in range(1, 7):
            p = os.path.join(self.root_dir, f"listen{i}.mp3")
            if os.path.exists(p):
                self.listen_tracks.append(p)

        # 爱：listen7
        self.love_track = _pick_existing([
            os.path.join(self.root_dir, "listen7.mp3"),
        ])

        # 小说主题曲：listen8
        self.novel_track = _pick_existing([
            os.path.join(self.root_dir, "listen8.mp3"),
        ])

        # 小说 10 页（按你给的内容）
        self.novel_pages = self._make_novel_pages_10()
        self.novel_page_i = 0

        # 状态
        self.mode = "home"  # home / listen / love / novel
        self.sound = None
        self.listen_index = -1
        self.bg_index = -1

        # -------------------------
        # UI
        # -------------------------
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

        # 顶部文字
        self.top_label = Label(
            text="你好，静静，我是质子 1 号 。褚少华派我来陪伴你。",
            size_hint=(1, None),
            height=92,
            pos_hint={"x": 0, "top": 1},
            font_size=20,
            font_name=self.font if self.font else None,
        )
        root.add_widget(self.top_label)

        # 底部按钮区
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

        # 小说控件
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
        )
        self.novel_label.bind(texture_size=self._update_novel_label_height)
        self.novel_scroll.add_widget(self.novel_label)

        # 初始背景：先用 bg1，没有就 icon
        self._show_home()

        return root

    # ------------------ UI 工具 ------------------

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
        btn._col_up = (0.15, 0.15, 0.15, 0.78)
        btn._col_down = (0.10, 0.10, 0.10, 0.92)

        with btn.canvas.before:
            btn._bg_color = Color(*btn._col_up)
            btn._bg_rect = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[btn.height / 2])

        def _sync(*_):
            btn._bg_rect.pos = btn.pos
            btn._bg_rect.size = btn.size
            btn._bg_rect.radius = [btn.height / 2]

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

    # ------------------ 音频 ------------------

    def _stop_sound(self):
        try:
            if self.sound:
                self.sound.stop()
        except Exception:
            pass
        self.sound = None

    def _play_sound(self, path: str, loop: bool = False):
        self._stop_sound()
        if not path or not os.path.exists(path):
            self.top_label.text = f"找不到音频：{os.path.basename(path) if path else '空路径'}"
            return
        s = SoundLoader.load(path)
        if not s:
            self.top_label.text = f"无法加载音频：{os.path.basename(path)}"
            return
        self.sound = s
        self.sound.loop = loop
        self.sound.play()

    # ------------------ 小说 ------------------

    def _make_novel_pages_10(self):
        pages = []
        pages.append("打开微信找到褚少华对话聊天框输入  我爱你❤️  解锁新剧情…")
        for _ in range(9):
            pages.append("我爱徐林静❤️")
        return pages

    def _render_novel_page(self):
        total = len(self.novel_pages)
        i = self.novel_page_i % total
        self.novel_label.text = f"第 {i+1}/{total} 页\n\n{self.novel_pages[i]}"

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

    def _show_novel(self):
        self.mode = "novel"
        self._clear_content()
        self._set_bg(self.bg_novel if os.path.exists(self.bg_novel) else self._fallback_bg())
        self.content_area.add_widget(self.novel_scroll)
        self._render_novel_page()

        # 小说主题曲：listen8（循环）
        if self.novel_track:
            self._play_sound(self.novel_track, loop=True)
        else:
            self.top_label.text = "小说主题曲缺少 listen8.mp3（根目录）"

    # ------------------ 三按钮逻辑 ------------------

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
        self.top_label.text = f"听歌：{os.path.basename(track)} | 背景：{os.path.basename(bg)}"

    def on_love_press(self, *_):
        self.mode = "love"
        self._clear_content()

        self._set_bg(self.bg_love if os.path.exists(self.bg_love) else self._fallback_bg())

        if not self.love_track:
            self.top_label.text = "缺少 listen7.mp3（根目录）"
            return

        self._play_sound(self.love_track, loop=False)
        self.top_label.text = "我爱褚少华：listen7.mp3 | 背景：listen_bg7.png"

    def on_novel_press(self, *_):
        # 第一次：进入小说（bg8 + 循环 listen8）
        # 之后：翻页（音乐继续循环不重载）
        if self.mode != "novel":
            self.novel_page_i = 0
            self._show_novel()
            self.top_label.text = "小说模式：再按一次翻页（背景固定 bg8，主题曲 listen8 循环）"
        else:
            self.novel_page_i += 1
            self._render_novel_page()


if __name__ == "__main__":
    ProtonApp().run()
