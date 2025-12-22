# main.py  （整文件覆盖版）
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


def _app_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _safe_listdir(path: str):
    try:
        return os.listdir(path)
    except Exception:
        return []


def _sort_by_number(files, pattern: str):
    # pattern example: r"^listen(\d+)\.mp3$"
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
        # 让 Kivy 认识当前目录与 assets 目录
        self.root_dir = _app_dir()
        self.assets_dir = os.path.join(self.root_dir, "assets")
        resource_add_path(self.root_dir)
        resource_add_path(self.assets_dir)

        # ====== 扫描资源（B：自动识别，不用你手写列表）======
        root_files = _safe_listdir(self.root_dir)
        assets_files = _safe_listdir(self.assets_dir)

        # 音乐：支持放根目录 或 assets/
        listen_mp3_root = _sort_by_number(root_files, r"^listen(\d+)\.mp3$")
        listen_mp3_assets = _sort_by_number(assets_files, r"^listen(\d+)\.mp3$")
        self.listen_tracks = []

        # 先用 assets 的（更规范），再补根目录的
        for f in listen_mp3_assets:
            self.listen_tracks.append(os.path.join(self.assets_dir, f))
        for f in listen_mp3_root:
            self.listen_tracks.append(os.path.join(self.root_dir, f))

        # 背景图：只认 assets/ 里的 listen_bgN.png
        listen_bg_assets = _sort_by_number(assets_files, r"^listen_bg(\d+)\.png$")
        self.listen_bgs = [os.path.join(self.assets_dir, f) for f in listen_bg_assets]

        # 兜底：你至少要有 1 首歌或 1 张图，否则不崩溃但会提示
        self.listen_index = -1
        self.bg_index = -1

        # ====== “爱”模式的占位资源（你后续上传时按这个命名）======
        # 背景：assets/love_bg.png
        # 音频：love1.mp3, love2.mp3...（放根目录或 assets 都行）
        self.love_bg = _pick_existing([
            os.path.join(self.assets_dir, "love_bg.png"),
            # 没有就兜底用第一张 listen 背景
            self.listen_bgs[0] if self.listen_bgs else "",
        ])

        love_mp3_root = _sort_by_number(root_files, r"^love(\d+)\.mp3$")
        love_mp3_assets = _sort_by_number(assets_files, r"^love(\d+)\.mp3$")
        self.love_tracks = []
        for f in love_mp3_assets:
            self.love_tracks.append(os.path.join(self.assets_dir, f))
        for f in love_mp3_root:
            self.love_tracks.append(os.path.join(self.root_dir, f))
        self.love_index = -1

        # ====== 小说模式占位资源（你后续上传时按这个命名）======
        # 背景：assets/novel_bg.png
        self.novel_bg = _pick_existing([
            os.path.join(self.assets_dir, "novel_bg.png"),
            self.listen_bgs[0] if self.listen_bgs else "",
        ])
        self.novel_text = (
            "【小说占位内容】\n\n"
            "你把大约 5000 字的小说文本发我，我会替换到这里。\n\n"
            "当前版本用于验证：进入小说模式 → 再按按钮翻页（背景不变）。\n\n"
            "第 1 页示例：\n" + ("静静，" * 200)
        )
        self.novel_pages = self._paginate_text(self.novel_text, page_chars=800)
        self.novel_page_i = 0

        # ====== 播放器 ======
        self.sound = None
        self.mode = "home"  # home / listen / novel / love

        # ====== UI ======
        root = FloatLayout()

        # 背景图层
        self.bg = Image(
            source=self._fallback_bg(),
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
        )
        root.add_widget(self.bg)

        # 中间内容层（小说用）
        self.content_area = FloatLayout(size_hint=(1, 1))
        root.add_widget(self.content_area)

        # 顶部欢迎文本（你要的那句话，做成 App 内“等待/欢迎”显示）
        self.top_label = Label(
            text="你好，静静，我是质子 1 号 。褚少华派我来陪伴你。",
            size_hint=(1, None),
            height=80,
            pos_hint={"x": 0, "top": 1},
            font_size=20,
        )
        root.add_widget(self.top_label)

        # 底部按钮区
        btn_box = BoxLayout(
            orientation="vertical",
            spacing=16,
            padding=24,
            size_hint=(1, None),
            height=320,
            pos_hint={"x": 0, "y": 0},
        )

        self.btn_listen = Button(
            text="和褚少华一起听歌",
            font_size=26,
            size_hint=(1, 1),
        )
        self.btn_listen.bind(on_press=self.on_listen_press)

        self.btn_novel = Button(
            text="和褚少华一起看小说",
            font_size=26,
            size_hint=(1, 1),
        )
        self.btn_novel.bind(on_press=self.on_novel_press)

        self.btn_love = Button(
            text="我爱褚少华",
            font_size=26,
            size_hint=(1, 1),
        )
        self.btn_love.bind(on_press=self.on_love_press)

        btn_box.add_widget(self.btn_listen)
        btn_box.add_widget(self.btn_novel)
        btn_box.add_widget(self.btn_love)

        root.add_widget(btn_box)

        # 小说控件（先创建但不显示）
        self.novel_scroll = ScrollView(
            size_hint=(0.92, 0.55),
            pos_hint={"center_x": 0.5, "center_y": 0.62},
        )
        self.novel_label = Label(
            text="",
            size_hint_y=None,
            text_size=(Window.width * 0.86, None),
            font_size=20,
            halign="left",
            valign="top",
        )
        self.novel_label.bind(texture_size=self._update_novel_label_height)
        self.novel_scroll.add_widget(self.novel_label)

        # 初始状态：只显示背景 + 顶部话
        self._show_home()

        return root

    # ------------------ 工具 ------------------

    def _fallback_bg(self) -> str:
        # 优先用 assets 里第一张 listen_bg
        if hasattr(self, "listen_bgs") and self.listen_bgs:
            return self.listen_bgs[0]
        # 再兜底用 root 下 icon.png（如果有）
        icon = os.path.join(_app_dir(), "icon.png")
        if os.path.exists(icon):
            return icon
        return ""

    def _paginate_text(self, text: str, page_chars: int = 800):
        pages = []
        cur = 0
        n = len(text)
        while cur < n:
            pages.append(text[cur: cur + page_chars])
            cur += page_chars
        return pages if pages else [""]

    def _update_novel_label_height(self, *args):
        self.novel_label.height = self.novel_label.texture_size[1] + 20

    def _set_bg(self, path: str):
        if path and os.path.exists(path):
            self.bg.source = path
            self.bg.reload()

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
            # 不崩溃，只提示
            self.top_label.text = f"找不到音频：{os.path.basename(path) if path else '空路径'}"
            return
        self.sound = SoundLoader.load(path)
        if self.sound:
            self.sound.loop = loop
            self.sound.play()
        else:
            self.top_label.text = f"无法加载音频：{os.path.basename(path)}"

    # ------------------ 模式切换 ------------------

    def _clear_content(self):
        # 只清 content_area 里的控件
        self.content_area.clear_widgets()

    def _show_home(self):
        self.mode = "home"
        self._clear_content()
        # 背景回到默认
        self._set_bg(self._fallback_bg())

    def _show_novel(self):
        self.mode = "novel"
        self._clear_content()
        self._set_bg(self.novel_bg)
        self.content_area.add_widget(self.novel_scroll)
        self._render_novel_page()

    def _render_novel_page(self):
        if not self.novel_pages:
            self.novel_pages = [""]
        total = len(self.novel_pages)
        i = self.novel_page_i % total
        self.novel_label.text = f"[第 {i+1}/{total} 页]\n\n{self.novel_pages[i]}"

    # ------------------ 按钮逻辑 ------------------

    def on_listen_press(self, *args):
        # 每按一次：下一首 + 下一背景 + 播放
        self.mode = "listen"

        if not self.listen_tracks:
            self.top_label.text = "没找到 listen*.mp3（放根目录或 assets 都行）"
            return
        if not self.listen_bgs:
            self.top_label.text = "没找到 assets/listen_bg*.png"
            return

        self.listen_index = (self.listen_index + 1) % len(self.listen_tracks)
        self.bg_index = (self.bg_index + 1) % len(self.listen_bgs)

        track = self.listen_tracks[self.listen_index]
        bg = self.listen_bgs[self.bg_index]

        self._clear_content()      # 听歌模式不显示小说区域
        self._set_bg(bg)
        self._play_sound(track, loop=False)

        self.top_label.text = f"听歌：{os.path.basename(track)} | 背景：{os.path.basename(bg)}"

    def on_novel_press(self, *args):
        # 第一次按：进入小说模式（背景固定）
        # 后续按：翻页（背景不切换）
        if self.mode != "novel":
            self._stop_sound()  # 看小说不播放
            self.novel_page_i = 0
            self._show_novel()
            self.top_label.text = "小说模式：再按一次翻页（背景不切换）"
        else:
            self.novel_page_i += 1
            self._render_novel_page()

    def on_love_press(self, *args):
        # 第一次按：切背景 + 播放 love 音频
        # 后续按：只切音频，不切背景
        if not self.love_tracks:
            self.top_label.text = "没找到 love*.mp3（你后续上传后会自动识别）"
            # 但仍然切到 love 背景（如果有）
            self._set_bg(self.love_bg)
            self.mode = "love"
            return

        if self.mode != "love":
            self.mode = "love"
            self._clear_content()
            self._set_bg(self.love_bg)

        self.love_index = (self.love_index + 1) % len(self.love_tracks)
        track = self.love_tracks[self.love_index]
        self._play_sound(track, loop=False)
        self.top_label.text = f"我爱褚少华：{os.path.basename(track)}"


if __name__ == "__main__":
    ProtonApp().run()
