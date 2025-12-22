# main.py（整文件覆盖版：圆角按钮 + 中文字体兜底 + 3按钮逻辑不变 + 按钮区占屏幕2/5）
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
        # ========== 基础路径 ==========
        self.root_dir = _app_dir()
        self.assets_dir = os.path.join(self.root_dir, "assets")
        resource_add_path(self.root_dir)
        resource_add_path(self.assets_dir)

        # ========== 字体兜底（解决中文不显示） ==========
        self.font = _pick_existing([
            os.path.join(self.root_dir, "NotoSansSC-VariableFont_wght.ttf"),
            os.path.join(self.assets_dir, "NotoSansSC-VariableFont_wght.ttf"),
        ])

        # ========== 自适配尺寸（不同手机都保持好看） ==========
        w, h = Window.size
        # 按钮区占屏幕 2/5
        self.btn_area_ratio = 0.40

        # 单个按钮高度：按钮区高度扣掉间距后均分（并设上下限）
        # 3个按钮 + 2个间距 + padding
        self.btn_spacing = max(16, int(h * 0.018))      # 大约 1.8% 屏高
        self.btn_padding_lr = max(24, int(w * 0.06))    # 左右 padding
        self.btn_padding_bottom = max(24, int(h * 0.03))

        btn_area_h = h * self.btn_area_ratio
        usable_h = btn_area_h - self.btn_padding_bottom - (self.btn_spacing * 2)
        self.btn_h = int(max(110, min(170, usable_h / 3)))  # 110~170 之间自适配

        # 字体：跟随按钮高度（并设上下限）
        self.btn_font = int(max(26, min(36, self.btn_h * 0.24)))  # 约按钮高度的 1/4
        self.top_font = int(max(18, min(24, h * 0.02)))

        # ========== 扫描资源（自动识别） ==========
        root_files = _safe_listdir(self.root_dir)
        assets_files = _safe_listdir(self.assets_dir)

        # 听歌：listenN.mp3（根目录或 assets）
        listen_mp3_root = _sort_by_number(root_files, r"^listen(\d+)\.mp3$")
        listen_mp3_assets = _sort_by_number(assets_files, r"^listen(\d+)\.mp3$")
        self.listen_tracks = [os.path.join(self.assets_dir, f) for f in listen_mp3_assets] + \
                             [os.path.join(self.root_dir, f) for f in listen_mp3_root]

        # 背景图：assets/listen_bgN.png
        listen_bg_assets = _sort_by_number(assets_files, r"^listen_bg(\d+)\.png$")
        self.listen_bgs = [os.path.join(self.assets_dir, f) for f in listen_bg_assets]

        self.listen_index = -1
        self.bg_index = -1

        # “爱”模式资源（占位命名规则）
        self.love_bg = _pick_existing([
            os.path.join(self.assets_dir, "love_bg.png"),
            self.listen_bgs[0] if self.listen_bgs else "",
        ])

        love_mp3_root = _sort_by_number(root_files, r"^love(\d+)\.mp3$")
        love_mp3_assets = _sort_by_number(assets_files, r"^love(\d+)\.mp3$")
        self.love_tracks = [os.path.join(self.assets_dir, f) for f in love_mp3_assets] + \
                           [os.path.join(self.root_dir, f) for f in love_mp3_root]
        self.love_index = -1

        # 小说模式资源（占位命名规则）
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

        # 播放器
        self.sound = None
        self.mode = "home"  # home / listen / novel / love

        # ========== UI ==========
        root = FloatLayout()

        # 背景
        self.bg = Image(
            source=self._fallback_bg(),
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
        )
        root.add_widget(self.bg)

        # 内容层（小说用）
        self.content_area = FloatLayout(size_hint=(1, 1))
        root.add_widget(self.content_area)

        # 顶部欢迎文字（加阴影更清晰）
        self.top_label = Label(
            text="你好，静静，我是质子 1 号 。褚少华派我来陪伴你。",
            size_hint=(1, None),
            height=int(max(80, h * 0.10)),
            pos_hint={"x": 0, "top": 1},
            font_size=self.top_font,
            font_name=self.font if self.font else None,
            color=(1, 1, 1, 1),
        )
        # 阴影（第二层 Label）
        self.top_shadow = Label(
            text=self.top_label.text,
            size_hint=self.top_label.size_hint,
            height=self.top_label.height,
            pos_hint={"x": 0, "top": 1},
            font_size=self.top_label.font_size,
            font_name=self.top_label.font_name,
            color=(0, 0, 0, 0.75),
        )
        self.top_shadow.pos_hint = {"x": 0.005, "top": 0.995}  # 轻微偏移形成阴影
        root.add_widget(self.top_shadow)
        root.add_widget(self.top_label)

        # 底部按钮区：占屏幕 2/5
        btn_box = BoxLayout(
            orientation="vertical",
            spacing=self.btn_spacing,
            padding=[self.btn_padding_lr, 0, self.btn_padding_lr, self.btn_padding_bottom],
            size_hint=(1, self.btn_area_ratio),
            pos_hint={"x": 0, "y": 0},
        )

        # 三个圆角按钮（胶囊）
        self.btn_listen = self._make_round_button("和褚少华一起听歌")
        self.btn_listen.bind(on_press=self.on_listen_press)

        self.btn_novel = self._make_round_button("和褚少华一起看小说")
        self.btn_novel.bind(on_press=self.on_novel_press)

        self.btn_love = self._make_round_button("我爱褚少华")
        self.btn_love.bind(on_press=self.on_love_press)

        btn_box.add_widget(self.btn_listen)
        btn_box.add_widget(self.btn_novel)
        btn_box.add_widget(self.btn_love)

        root.add_widget(btn_box)

        # 小说控件（创建但不默认显示）
        self.novel_scroll = ScrollView(
            size_hint=(0.92, 0.55),
            pos_hint={"center_x": 0.5, "center_y": 0.62},
        )
        self.novel_label = Label(
            text="",
            size_hint_y=None,
            text_size=(Window.width * 0.86, None),
            font_size=int(max(18, min(24, h * 0.02))),
            halign="left",
            valign="top",
            font_name=self.font if self.font else None,
            markup=True,
            color=(1, 1, 1, 1),
        )
        self.novel_label.bind(texture_size=self._update_novel_label_height)
        self.novel_scroll.add_widget(self.novel_label)

        self._show_home()
        return root

    # ------------------ 圆角按钮工厂 ------------------

    def _make_round_button(self, text: str) -> Button:
        btn = Button(
            text=text,
            font_size=self.btn_font,
            font_name=self.font if self.font else None,
            size_hint=(1, None),
            height=self.btn_h,
            background_normal="",
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 1),
        )

        # 松开 / 按下 颜色
        btn._col_up = (0.15, 0.15, 0.15, 0.82)
        btn._col_down = (0.10, 0.10, 0.10, 0.95)

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

    # ------------------ 工具 ------------------

    def _fallback_bg(self) -> str:
        if hasattr(self, "listen_bgs") and self.listen_bgs:
            return self.listen_bgs[0]
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
            self._set_top_text(f"找不到音频：{os.path.basename(path) if path else '空路径'}")
            return
        self.sound = SoundLoader.load(path)
        if self.sound:
            self.sound.loop = loop
            self.sound.play()
        else:
            self._set_top_text(f"无法加载音频：{os.path.basename(path)}")

    def _set_top_text(self, text: str):
        self.top_label.text = text
        self.top_shadow.text = text

    # ------------------ 模式切换 ------------------

    def _clear_content(self):
        self.content_area.clear_widgets()

    def _show_home(self):
        self.mode = "home"
        self._clear_content()
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
        self.novel_label.text = f"[b][第 {i+1}/{total} 页][/b]\n\n{self.novel_pages[i]}"

    # ------------------ 按钮逻辑 ------------------

    def on_listen_press(self, *args):
        self.mode = "listen"

        if not self.listen_tracks:
            self._set_top_text("没找到 listen*.mp3（放根目录或 assets 都行）")
            return
        if not self.listen_bgs:
            self._set_top_text("没找到 assets/listen_bg*.png")
            return

        self.listen_index = (self.listen_index + 1) % len(self.listen_tracks)
        self.bg_index = (self.bg_index + 1) % len(self.listen_bgs)

        track = self.listen_tracks[self.listen_index]
        bg = self.listen_bgs[self.bg_index]

        self._clear_content()
        self._set_bg(bg)
        self._play_sound(track, loop=False)

        self._set_top_text(f"听歌：{os.path.basename(track)} | 背景：{os.path.basename(bg)}")

    def on_novel_press(self, *args):
        if self.mode != "novel":
            self._stop_sound()
            self.novel_page_i = 0
            self._show_novel()
            self._set_top_text("小说模式：再按一次翻页（背景不切换）")
        else:
            self.novel_page_i += 1
            self._render_novel_page()

    def on_love_press(self, *args):
        if self.mode != "love":
            self.mode = "love"
            self._clear_content()
            self._set_bg(self.love_bg)

        if not self.love_tracks:
            self._set_top_text("没找到 love*.mp3（你上传后会自动识别）")
            return

        self.love_index = (self.love_index + 1) % len(self.love_tracks)
        track = self.love_tracks[self.love_index]
        self._play_sound(track, loop=False)
        self._set_top_text(f"我爱褚少华：{os.path.basename(track)}")


if __name__ == "__main__":
    ProtonApp().run()
