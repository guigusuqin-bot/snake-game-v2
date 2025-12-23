# main.py（整文件覆盖版：预热/缓存防卡顿 + 圆角大按钮 + 中文字体兜底 + 3按钮逻辑）
import os
import re

from kivy.app import App
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.image import Image as CoreImage
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
        # 让 Kivy 认识当前目录与 assets 目录
        self.root_dir = _app_dir()
        self.assets_dir = os.path.join(self.root_dir, "assets")
        resource_add_path(self.root_dir)
        resource_add_path(self.assets_dir)

        # ====== 字体兜底（解决中文不显示）======
        self.font = _pick_existing([
            os.path.join(self.root_dir, "NotoSansSC-VariableFont_wght.ttf"),
            os.path.join(self.assets_dir, "NotoSansSC-VariableFont_wght.ttf"),
        ])

        # ====== 扫描资源（自动识别）======
        root_files = _safe_listdir(self.root_dir)
        assets_files = _safe_listdir(self.assets_dir)

        # 听歌：listenN.mp3（根目录或 assets）
        listen_mp3_root = _sort_by_number(root_files, r"^listen(\d+)\.mp3$")
        listen_mp3_assets = _sort_by_number(assets_files, r"^listen(\d+)\.mp3$")
        self.listen_tracks = [os.path.join(self.assets_dir, f) for f in listen_mp3_assets] + \
                             [os.path.join(self.root_dir, f) for f in listen_mp3_root]

        # 听歌背景：assets/listen_bgN.png
        listen_bg_assets = _sort_by_number(assets_files, r"^listen_bg(\d+)\.png$")
        self.listen_bgs = [os.path.join(self.assets_dir, f) for f in listen_bg_assets]

        self.listen_index = -1
        self.bg_index = -1

        # 爱模式资源（占位命名）
        self.love_bg = _pick_existing([
            os.path.join(self.assets_dir, "love_bg.png"),
            self.listen_bgs[0] if self.listen_bgs else "",
        ])

        love_mp3_root = _sort_by_number(root_files, r"^love(\d+)\.mp3$")
        love_mp3_assets = _sort_by_number(assets_files, r"^love(\d+)\.mp3$")
        self.love_tracks = [os.path.join(self.assets_dir, f) for f in love_mp3_assets] + \
                           [os.path.join(self.root_dir, f) for f in love_mp3_root]
        self.love_index = -1

        # 小说模式资源（占位命名）
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

        # ====== 缓存/预热（解决切歌卡顿） ======
        self.sound_cache = {}   # path -> Sound
        self.tex_cache = {}     # path -> Texture
        self._listen_busy = False

        self._warm_i = 0
        self._warm_pairs = []   # (bg_path, mp3_path)

        # ====== UI ======
        root = FloatLayout()

        # 背景图层（用 texture 切换更顺）
        self.bg = Image(
            source="",
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
        )
        root.add_widget(self.bg)

        # 中间内容层（小说用）
        self.content_area = FloatLayout(size_hint=(1, 1))
        root.add_widget(self.content_area)

        # 顶部欢迎文本
        self.top_label = Label(
            text="你好，静静，我是质子 1 号 。",
            size_hint=(1, None),
            height=100,
            pos_hint={"x": 0, "top": 1},
            font_size=22,
            font_name=self.font if self.font else None,
        )
        root.add_widget(self.top_label)

        # 底部按钮区：高度 = 屏幕 2/5
        self.btn_box = BoxLayout(
            orientation="vertical",
            spacing=22,
            padding=[28, 0, 28, 28],
            size_hint=(1, None),
            height=int(Window.height * 0.4),
            pos_hint={"x": 0, "y": 0},
        )

        # 三个圆角按钮（更大/字体更大）
        self.btn_listen = self._make_round_button("和褚少华一起听歌")
        self.btn_listen.bind(on_press=self.on_listen_press)

        self.btn_novel = self._make_round_button("和褚少华一起看小说")
        self.btn_novel.bind(on_press=self.on_novel_press)

        self.btn_love = self._make_round_button("我爱褚少华")
        self.btn_love.bind(on_press=self.on_love_press)

        self.btn_box.add_widget(self.btn_listen)
        self.btn_box.add_widget(self.btn_novel)
        self.btn_box.add_widget(self.btn_love)
        root.add_widget(self.btn_box)

        # 适配：屏幕尺寸变化时自动刷新按钮区高度和按钮尺寸
        Window.bind(size=self._on_window_resize)

        # 小说控件（创建但不默认显示）
        self.novel_scroll = ScrollView(
            size_hint=(0.92, 0.55),
            pos_hint={"center_x": 0.5, "center_y": 0.62},
        )
        self.novel_label = Label(
            text="",
            size_hint_y=None,
            text_size=(Window.width * 0.86, None),
            font_size=22,
            halign="left",
            valign="top",
            font_name=self.font if self.font else None,
            markup=True,
        )
        self.novel_label.bind(texture_size=self._update_novel_label_height)
        self.novel_scroll.add_widget(self.novel_label)

        # 初始展示
        self._show_home()

        # 启动预热（分帧加载：背景纹理 + 音频对象）
        self._start_warmup()

        return root

    # ------------------ 尺寸适配 ------------------

    def _on_window_resize(self, *_):
        # 按钮区 = 屏幕 2/5
        self.btn_box.height = int(Window.height * 0.4)

        # 单个按钮高度：按钮区扣掉 spacing/padding 后平均分配
        pad_bottom = 28
        pad_left_right = 28
        spacing = 22
        # 3 个按钮之间 2 个间隔
        available = self.btn_box.height - pad_bottom - (spacing * 2)
        btn_h = max(110, int(available / 3))  # 最小 110，保证够大
        for b in (self.btn_listen, self.btn_novel, self.btn_love):
            b.height = btn_h
            # 半径随高度更新（胶囊）
            try:
                b._bg_rect.radius = [b.height / 2]
            except Exception:
                pass

    # ------------------ 圆角按钮工厂 ------------------

    def _make_round_button(self, text: str) -> Button:
        btn = Button(
            text=text,
            font_size=30,  # 字体更大
            font_name=self.font if self.font else None,
            size_hint=(1, None),
            height=120,    # 初始大一些（后续 resize 会再算）
            background_normal="",
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 1),
        )

        btn._col_up = (0.18, 0.18, 0.18, 0.88)
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

    # ------------------ 文本小工具 ------------------

    def _set_top_text(self, s: str):
        try:
            self.top_label.text = s
        except Exception:
            pass

    # ------------------ 缓存：纹理 & 音频 ------------------

    def _get_texture_cached(self, path: str):
        if not path or not os.path.exists(path):
            return None
        tex = self.tex_cache.get(path)
        if tex is None:
            tex = CoreImage(path).texture
            self.tex_cache[path] = tex
        return tex

    def _set_bg(self, path: str):
        tex = self._get_texture_cached(path)
        if tex is not None:
            self.bg.texture = tex

    def _stop_sound(self):
        try:
            if self.sound:
                self.sound.stop()
        except Exception:
            pass
        self.sound = None

    def _play_sound_cached(self, path: str, loop: bool = False):
        self._stop_sound()
        if not path or not os.path.exists(path):
            self._set_top_text(f"找不到音频：{os.path.basename(path) if path else '空路径'}")
            return

        snd = self.sound_cache.get(path)
        if snd is None:
            snd = SoundLoader.load(path)
            if snd:
                self.sound_cache[path] = snd

        if not snd:
            self._set_top_text(f"无法加载音频：{os.path.basename(path)}")
            return

        self.sound = snd
        self.sound.loop = loop
        self.sound.play()

    # ------------------ 预热：分帧加载避免卡 ------------------

    def _start_warmup(self):
        # 只预热听歌资源：背景 + 对应音频（按顺序配对）
        pairs = []
        n = min(len(self.listen_bgs), len(self.listen_tracks))
        for i in range(n):
            pairs.append((self.listen_bgs[i], self.listen_tracks[i]))

        self._warm_pairs = pairs
        self._warm_i = 0

        if not self._warm_pairs:
            return

        # 启动后稍等再开始预热，避免影响首屏渲染
        Clock.schedule_once(self._warmup_step, 0.3)

    def _warmup_step(self, dt):
        if self._warm_i >= len(self._warm_pairs):
            # 预热完成
            self._set_top_text("你好，静静，我是质子 1 号 。")
            return

        bg, mp3 = self._warm_pairs[self._warm_i]

        # 预热背景纹理
        try:
            self._get_texture_cached(bg)
        except Exception:
            pass

        # 预热音频对象（只 load，不播放）
        try:
            if mp3 and os.path.exists(mp3) and mp3 not in self.sound_cache:
                snd = SoundLoader.load(mp3)
                if snd:
                    self.sound_cache[mp3] = snd
        except Exception:
            pass

        self._warm_i += 1

        # 下一帧继续（你想更慢更丝滑：改成 0.05）
        Clock.schedule_once(self._warmup_step, 0)

    # ------------------ 小说分页 ------------------

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

    # ------------------ 模式切换 ------------------

    def _clear_content(self):
        self.content_area.clear_widgets()

    def _fallback_bg(self) -> str:
        if self.listen_bgs:
            return self.listen_bgs[0]
        icon = os.path.join(_app_dir(), "icon.png")
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

    # 听歌：为了“按下不卡顿”，把真正切换放到下一帧执行
    def on_listen_press(self, *args):
        if self._listen_busy:
            return
        self._listen_busy = True
        self.mode = "listen"
        self._set_top_text("切换中...")
        Clock.schedule_once(self._do_listen_switch, 0)

    def _do_listen_switch(self, dt):
        try:
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
            self._play_sound_cached(track, loop=False)

            self._set_top_text(f"听歌：{os.path.basename(track)} | 背景：{os.path.basename(bg)}")
        finally:
            self._listen_busy = False

    # 小说：第一次进入小说模式，之后翻页（背景不切）
    def on_novel_press(self, *args):
        if self.mode != "novel":
            self._stop_sound()
            self.novel_page_i = 0
            self._show_novel()
            self._set_top_text("小说模式：再按一次翻页（背景不切换）")
        else:
            self.novel_page_i += 1
            self._render_novel_page()

    # 爱：第一次切背景 + 播放，后续只切音频（不切背景）
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
        self._play_sound_cached(track, loop=False)
        self._set_top_text(f"我爱褚少华：{os.path.basename(track)}")


if __name__ == "__main__":
    ProtonApp().run()
