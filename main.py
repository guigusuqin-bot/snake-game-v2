# main.py（整文件覆盖版：两按钮功能完整 + 音频预热不卡顿 + 圆角大按钮 2/5 屏）
import os
import re
import threading

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
from kivy.graphics import Color, RoundedRectangle
from kivy.core.image import Image as CoreImage


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


def _read_text_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


class ProtonApp(App):
    def build(self):
        # 基础路径
        self.root_dir = _app_dir()
        self.assets_dir = os.path.join(self.root_dir, "assets")
        resource_add_path(self.root_dir)
        resource_add_path(self.assets_dir)

        # 字体兜底（按钮中文）
        self.font = _pick_existing([
            os.path.join(self.root_dir, "NotoSansSC-VariableFont_wght.ttf"),
            os.path.join(self.assets_dir, "NotoSansSC-VariableFont_wght.ttf"),
        ])

        root_files = _safe_listdir(self.root_dir)
        assets_files = _safe_listdir(self.assets_dir)

        # ========== 听歌资源 ==========
        listen_mp3_root = _sort_by_number(root_files, r"^listen(\d+)\.mp3$")
        listen_mp3_assets = _sort_by_number(assets_files, r"^listen(\d+)\.mp3$")

        self.listen_tracks = []
        for f in listen_mp3_assets:
            self.listen_tracks.append(os.path.join(self.assets_dir, f))
        for f in listen_mp3_root:
            self.listen_tracks.append(os.path.join(self.root_dir, f))

        listen_bg_assets = _sort_by_number(assets_files, r"^listen_bg(\d+)\.png$")
        self.listen_bgs = [os.path.join(self.assets_dir, f) for f in listen_bg_assets]

        self.listen_index = -1
        self.bg_index = -1

        # ========== 小说资源 ==========
        self.novel_bg = _pick_existing([
            os.path.join(self.assets_dir, "novel_bg.png"),
            self.listen_bgs[0] if self.listen_bgs else "",
        ])

        novel_txt = _pick_existing([os.path.join(self.assets_dir, "novel.txt")])
        novel_content = _read_text_file(novel_txt) if novel_txt else ""
        if not novel_content.strip():
            novel_content = (
                "【小说占位内容】\n\n"
                "把小说文本放到：assets/novel.txt（约 5000 字）\n\n"
                "规则：第一次按“看小说” → 进入小说模式并显示第一页；\n"
                "之后每按一次 → 翻页（背景不切换）。\n\n"
                "示例：\n" + ("你好，静静。\n" * 120)
            )
        self.novel_pages = self._paginate_text(novel_content, page_chars=850)
        self.novel_page_i = 0

        # ========== 我爱资源 ==========
        self.love_bg = _pick_existing([
            os.path.join(self.assets_dir, "love_bg.png"),
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

        # ========== 缓存（解决卡顿） ==========
        self.sound_cache = {}   # path -> Sound
        self.tex_cache = {}     # path -> Texture
        self._warm_thread_started = False

        # 播放器
        self.sound = None
        self.mode = "home"  # home / listen / novel / love

        # ===== UI 根 =====
        root = FloatLayout()

        # 背景（用 texture 更顺滑）
        self.bg = Image(
            source="",
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
        )
        root.add_widget(self.bg)

        # 一层轻暗遮罩（更像 App）
        self.overlay = FloatLayout(size_hint=(1, 1))
        with self.overlay.canvas.before:
            Color(0, 0, 0, 0.18)
            self._overlay_rect = RoundedRectangle(pos=(0, 0), size=Window.size, radius=[0])
        self.overlay.bind(pos=self._sync_overlay, size=self._sync_overlay)
        root.add_widget(self.overlay)

        # 内容层（小说显示区）
        self.content_area = FloatLayout(size_hint=(1, 1))
        root.add_widget(self.content_area)

        # 顶部文案
        self.top_label = Label(
            text="你好，静静，我是质子 1 号 。褚少华派我来陪伴你。",
            size_hint=(1, None),
            height=92,
            pos_hint={"x": 0, "top": 1},
            font_size=20,
            font_name=self.font if self.font else None,
        )
        root.add_widget(self.top_label)

        # 底部按钮区：占屏幕 2/5
        self.btn_box = BoxLayout(
            orientation="vertical",
            spacing=18,
            padding=[24, 0, 24, 24],
            size_hint=(1, None),
            height=max(320, int(Window.height * 0.40)),
            pos_hint={"x": 0, "y": 0},
        )
        Window.bind(size=self._on_window_resize)

        # 三个圆角大按钮（更大字体）
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
            font_name=self.font if self.font else None,
            markup=True,
        )
        self.novel_label.bind(texture_size=self._update_novel_label_height)
        self.novel_scroll.add_widget(self.novel_label)

        # 初始背景
        self._show_home()

        # 启动预热（后台加载音频 + 预解码背景图）
        self._start_warmup_thread()

        return root

    # ------------------ 视觉/布局 ------------------

    def _sync_overlay(self, *_):
        self._overlay_rect.pos = (0, 0)
        self._overlay_rect.size = Window.size

    def _on_window_resize(self, *_):
        self.btn_box.height = max(320, int(Window.height * 0.40))
        # 小说文本宽度跟着屏幕走
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
        # 松开/按下颜色（更“专业”）
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

    # ------------------ 资源/缓存（预热不卡顿） ------------------

    def _start_warmup_thread(self):
        if self._warm_thread_started:
            return
        self._warm_thread_started = True

        def worker():
            # 1) 预加载背景图 texture（切图更顺）
            for p in (self.listen_bgs or []):
                self._cache_texture(p)
            for p in [self.novel_bg, self.love_bg]:
                if p:
                    self._cache_texture(p)

            # 2) 预加载音频（最关键：避免第一次播放卡顿）
            for p in (self.listen_tracks or []):
                self._cache_sound(p)
            for p in (self.love_tracks or []):
                self._cache_sound(p)

            Clock.schedule_once(lambda *_: self._warmup_done_tip(), 0)

        threading.Thread(target=worker, daemon=True).start()

    def _warmup_done_tip(self):
        # 不强提示，避免打扰；需要可打开
        # self.top_label.text = "预热完成：切歌更顺了"
        pass

    def _cache_texture(self, path: str):
        if not path or not os.path.exists(path):
            return None
        if path in self.tex_cache:
            return self.tex_cache[path]
        try:
            img = CoreImage(path)
            self.tex_cache[path] = img.texture
            return img.texture
        except Exception:
            return None

    def _cache_sound(self, path: str):
        if not path or not os.path.exists(path):
            return None
        if path in self.sound_cache and self.sound_cache[path]:
            return self.sound_cache[path]
        try:
            s = SoundLoader.load(path)
            self.sound_cache[path] = s
            return s
        except Exception:
            self.sound_cache[path] = None
            return None

    # ------------------ 通用工具 ------------------

    def _fallback_bg(self) -> str:
        if self.listen_bgs:
            return self.listen_bgs[0]
        icon = os.path.join(self.root_dir, "icon.png")
        if os.path.exists(icon):
            return icon
        return ""

    def _set_bg(self, path: str):
        if not path:
            return
        # 优先用 texture（更流畅）
        tex = self._cache_texture(path)
        if tex is not None:
            self.bg.texture = tex
            self.bg.source = ""
            return
        # 兜底 source
        if os.path.exists(path):
            self.bg.source = path
            self.bg.reload()

    def _paginate_text(self, text: str, page_chars: int = 850):
        pages = []
        cur = 0
        n = len(text)
        while cur < n:
            pages.append(text[cur: cur + page_chars])
            cur += page_chars
        return pages if pages else [""]

    def _update_novel_label_height(self, *_):
        self.novel_label.height = self.novel_label.texture_size[1] + 24

    def _clear_content(self):
        self.content_area.clear_widgets()

    # ------------------ 播放控制 ------------------

    def _stop_sound(self):
        try:
            if self.sound:
                self.sound.stop()
        except Exception:
            pass
        self.sound = None

    def _play_sound_cached(self, path: str, loop: bool = False):
        if not path or not os.path.exists(path):
            self.top_label.text = f"找不到音频：{os.path.basename(path) if path else '空路径'}"
            return
        self._stop_sound()

        s = self._cache_sound(path)
        if not s:
            self.top_label.text = f"无法加载音频：{os.path.basename(path)}"
            return

        self.sound = s
        self.sound.loop = loop
        # 关键：先 seek(0) 再 play，避免部分设备第二次播放异常
        try:
            self.sound.seek(0)
        except Exception:
            pass
        self.sound.play()

    # ------------------ 模式展示 ------------------

    def _show_home(self):
        self.mode = "home"
        self._clear_content()
        self._set_bg(self._fallback_bg())

    def _show_novel(self):
        self.mode = "novel"
        self._clear_content()
        self._set_bg(self.novel_bg if self.novel_bg else self._fallback_bg())
        self.content_area.add_widget(self.novel_scroll)
        self._render_novel_page()

    def _render_novel_page(self):
        if not self.novel_pages:
            self.novel_pages = [""]
        total = len(self.novel_pages)
        i = self.novel_page_i % total
        self.novel_label.text = f"[第 {i+1}/{total} 页]\n\n{self.novel_pages[i]}"

    # ------------------ 三按钮逻辑 ------------------

    def on_listen_press(self, *_):
        # 每按一次：下一首 + 下一背景 + 播放（不卡：用缓存）
        if not self.listen_tracks:
            self.top_label.text = "没找到 listen*.mp3（根目录或 assets/ 都行）"
            return
        if not self.listen_bgs:
            self.top_label.text = "没找到 assets/listen_bg*.png"
            return

        self.mode = "listen"
        self._clear_content()

        self.listen_index = (self.listen_index + 1) % len(self.listen_tracks)
        self.bg_index = (self.bg_index + 1) % len(self.listen_bgs)

        track = self.listen_tracks[self.listen_index]
        bg = self.listen_bgs[self.bg_index]

        self._set_bg(bg)
        self._play_sound_cached(track, loop=False)

        # 顺便“预热下一首”（进一步减少下一次卡顿）
        next_i = (self.listen_index + 1) % len(self.listen_tracks)
        threading.Thread(target=lambda: self._cache_sound(self.listen_tracks[next_i]), daemon=True).start()

        self.top_label.text = f"听歌：{os.path.basename(track)} | 背景：{os.path.basename(bg)}"

    def on_novel_press(self, *_):
        # 第一次按：进入小说模式（背景固定）+ 显示第一页
        # 后续按：翻页（背景不切换）
        if self.mode != "novel":
            self._stop_sound()
            self.novel_page_i = 0
            self._show_novel()
            self.top_label.text = "小说模式：再按一次翻页（背景不切换）"
        else:
            self.novel_page_i += 1
            self._render_novel_page()

    def on_love_press(self, *_):
        # 第一次按：切到 love_bg + 播放 love1
        # 后续按：只切换 love 音频，不切背景
        self._clear_content()

        if self.mode != "love":
            self.mode = "love"
            self._set_bg(self.love_bg if self.love_bg else self._fallback_bg())

        if not self.love_tracks:
            self.top_label.text = "没找到 love*.mp3（你上传后会自动识别）"
            return

        self.love_index = (self.love_index + 1) % len(self.love_tracks)
        track = self.love_tracks[self.love_index]
        self._play_sound_cached(track, loop=False)

        # 预热下一首 love
        next_i = (self.love_index + 1) % len(self.love_tracks)
        threading.Thread(target=lambda: self._cache_sound(self.love_tracks[next_i]), daemon=True).start()

        self.top_label.text = f"我爱褚少华：{os.path.basename(track)}"


if __name__ == "__main__":
    ProtonApp().run()
