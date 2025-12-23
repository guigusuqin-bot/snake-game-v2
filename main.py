# main.py（第 1/2 段：整文件覆盖版）
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


class ProtonApp(App):
    def build(self):
        # 路径
        self.root_dir = _app_dir()
        self.assets_dir = os.path.join(self.root_dir, "assets")
        resource_add_path(self.root_dir)
        resource_add_path(self.assets_dir)

        root_files = _safe_listdir(self.root_dir)
        assets_files = _safe_listdir(self.assets_dir)

        # 字体兜底（按钮中文）
        self.font = _pick_existing([
            os.path.join(self.root_dir, "NotoSansSC-VariableFont_wght.ttf"),
            os.path.join(self.assets_dir, "NotoSansSC-VariableFont_wght.ttf"),
        ])

        # =========================
        # 资源扫描
        # =========================

        # 音频：listenN.mp3（根目录或 assets）
        listen_mp3_root = _sort_by_number(root_files, r"^listen(\d+)\.mp3$")
        listen_mp3_assets = _sort_by_number(assets_files, r"^listen(\d+)\.mp3$")

        # 听歌轮播：只用 listen1~6（排除 7/8）
        self.listen_tracks = []
        for f in listen_mp3_assets:
            n = int(re.findall(r"\d+", f)[0])
            if n in (7, 8):
                continue
            self.listen_tracks.append(os.path.join(self.assets_dir, f))
        for f in listen_mp3_root:
            n = int(re.findall(r"\d+", f)[0])
            if n in (7, 8):
                continue
            self.listen_tracks.append(os.path.join(self.root_dir, f))

        # 背景：assets/listen_bgN.png
        listen_bg_assets = _sort_by_number(assets_files, r"^listen_bg(\d+)\.png$")
        all_listen_bgs = [os.path.join(self.assets_dir, f) for f in listen_bg_assets]

        # 你指定：bg7=爱，bg8=小说
        self.love_bg = os.path.join(self.assets_dir, "listen_bg7.png")
        self.novel_bg = os.path.join(self.assets_dir, "listen_bg8.png")

        # 听歌轮播背景：排除 7/8（避免冲突）
        self.listen_bgs = []
        for p in all_listen_bgs:
            base = os.path.basename(p).lower()
            if base in ("listen_bg7.png", "listen_bg8.png"):
                continue
            self.listen_bgs.append(p)

        # 听歌轮播索引
        self.listen_index = -1
        self.bg_index = -1

        # Love 固定音频：listen7.mp3
        self.love_tracks = []
        love7 = _pick_existing([
            os.path.join(self.root_dir, "listen7.mp3"),
            os.path.join(self.assets_dir, "listen7.mp3"),
        ])
        if love7:
            self.love_tracks = [love7]
        self.love_index = -1

        # 小说主题曲：listen8.mp3（你要求：开App就循环播放；小说按钮也用它）
        self.novel_theme = _pick_existing([
            os.path.join(self.root_dir, "listen8.mp3"),
            os.path.join(self.assets_dir, "listen8.mp3"),
        ])

        # 小说 10 页：你写死的内容
        self.novel_pages = self._make_novel_pages_10()
        self.novel_page_i = 0

        # =========================
        # 缓存/预热（减少卡顿）
        # =========================
        self.sound_cache = {}  # path -> Sound
        self.tex_cache = {}    # path -> Texture
        self._warm_thread_started = False

        # 播放器状态
        self.sound = None
        self.mode = "home"  # home / listen / novel / love

        # =========================
        # UI
        # =========================
        root = FloatLayout()

        # 背景（用 texture 更顺）
        self.bg = Image(
            source="",
            allow_stretch=True,
            keep_ratio=False,
            size_hint=(1, 1),
            pos_hint={"x": 0, "y": 0},
        )
        root.add_widget(self.bg)

        # 轻遮罩（更像 App）
        self.overlay = FloatLayout(size_hint=(1, 1))
        with self.overlay.canvas.before:
            Color(0, 0, 0, 0.18)
            self._overlay_rect = RoundedRectangle(pos=(0, 0), size=Window.size, radius=[0])
        Window.bind(size=self._sync_overlay)
        root.add_widget(self.overlay)

        # 内容层（小说）
        self.content_area = FloatLayout(size_hint=(1, 1))
        root.add_widget(self.content_area)

        # 顶部文本
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
            font_size=24,
            halign="left",
            valign="top",
            font_name=self.font if self.font else None,
            markup=True,
        )
        self.novel_label.bind(texture_size=self._update_novel_label_height)
        self.novel_scroll.add_widget(self.novel_label)

        # 初始首页背景
        self._show_home()

        # 预热（后台加载音频/图片）
        self._start_warmup_thread()

        # ✅ 开App立刻循环播放 listen8（不点任何按钮也播放）
        Clock.schedule_once(self._autoplay_novel_theme, 0.1)

        return root
        # main.py（第 2/2 段：接上面继续粘贴）
    # ------------------ 开机自动播放（listen8 循环） ------------------

    def _autoplay_novel_theme(self, *_):
        if not self.novel_theme or not os.path.exists(self.novel_theme):
            self.top_label.text = "未找到 listen8.mp3（开机自动播放失败）"
            return
        # 不改变当前背景，只播放
        self._play_sound_cached(self.novel_theme, loop=True)
        self.top_label.text = "🎄 圣诞主题曲已播放：listen8.mp3（循环）"

    # ------------------ 小说固定 10 页 ------------------

    def _make_novel_pages_10(self):
        pages = []
        pages.append("打开微信找到褚少华对话聊天框输入  我爱你❤️  解锁新剧情…")
        for _ in range(9):  # 第2~10页
            pages.append("我爱徐林静❤️")
        return pages

    # ------------------ 布局/视觉 ------------------

    def _sync_overlay(self, *_):
        self._overlay_rect.pos = (0, 0)
        self._overlay_rect.size = Window.size

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

    # ------------------ 缓存/预热（不卡顿核心） ------------------

    def _start_warmup_thread(self):
        if self._warm_thread_started:
            return
        self._warm_thread_started = True

        def worker():
            # 预解码背景图
            for p in (self.listen_bgs or []):
                self._cache_texture(p)
            self._cache_texture(self.love_bg)
            self._cache_texture(self.novel_bg)

            # 预加载音频
            for p in (self.listen_tracks or []):
                self._cache_sound(p)
            for p in (self.love_tracks or []):
                self._cache_sound(p)
            if self.novel_theme:
                self._cache_sound(self.novel_theme)

            Clock.schedule_once(lambda *_: None, 0)

        threading.Thread(target=worker, daemon=True).start()

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
        if hasattr(self, "listen_bgs") and self.listen_bgs:
            return self.listen_bgs[0]
        if os.path.exists(self.love_bg):
            return self.love_bg
        if os.path.exists(self.novel_bg):
            return self.novel_bg
        icon = os.path.join(self.root_dir, "icon.png")
        if os.path.exists(icon):
            return icon
        return ""

    def _set_bg(self, path: str):
        if not path:
            return
        tex = self._cache_texture(path)
        if tex is not None:
            self.bg.texture = tex
            self.bg.source = ""
            return
        if os.path.exists(path):
            self.bg.source = path
            self.bg.reload()

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
        # bg8
        if os.path.exists(self.novel_bg):
            self._set_bg(self.novel_bg)
        else:
            self._set_bg(self._fallback_bg())
        self.content_area.add_widget(self.novel_scroll)
        self._render_novel_page()

    def _render_novel_page(self):
        total = len(self.novel_pages)
        i = self.novel_page_i % total
        self.novel_label.text = f"[第 {i+1}/{total} 页]\n\n{self.novel_pages[i]}"

    # ------------------ 三按钮逻辑 ------------------

    def on_listen_press(self, *_):
        # 每按一次：下一首 + 下一背景 + 播放（listen1~6）
        if not self.listen_tracks:
            self.top_label.text = "没找到 listen1~6.mp3（根目录或 assets/ 都行）"
            return
        if not self.listen_bgs:
            self.top_label.text = "没找到可轮播背景（assets/listen_bg*.png，排除 7/8）"
            return

        self.mode = "listen"
        self._clear_content()

        self.listen_index = (self.listen_index + 1) % len(self.listen_tracks)
        self.bg_index = (self.bg_index + 1) % len(self.listen_bgs)

        track = self.listen_tracks[self.listen_index]
        bg = self.listen_bgs[self.bg_index]

        self._set_bg(bg)
        self._play_sound_cached(track, loop=False)

        # 预热下一首（减少卡顿）
        next_i = (self.listen_index + 1) % len(self.listen_tracks)
        threading.Thread(target=lambda: self._cache_sound(self.listen_tracks[next_i]), daemon=True).start()

        self.top_label.text = f"听歌：{os.path.basename(track)} | 背景：{os.path.basename(bg)}"

    def on_novel_press(self, *_):
        # 小说：bg8 + 主题曲 listen8 循环
        if self.mode != "novel":
            self.novel_page_i = 0
            self._show_novel()

            # ✅ 进入小说模式就循环 listen8（且翻页不重启）
            if self.novel_theme and os.path.exists(self.novel_theme):
                # 如果当前不是 listen8 在播，就切到 listen8 循环
                cur = None
                try:
                    cur = getattr(self.sound, "source", None)
                except Exception:
                    cur = None
                self._play_sound_cached(self.novel_theme, loop=True)

            self.top_label.text = "小说模式：再按一次翻页（bg8 固定，listen8 循环）"
        else:
            self.novel_page_i += 1
            self._render_novel_page()

    def on_love_press(self, *_):
        # 爱：bg7 + listen7（不循环）
        self._clear_content()
        self.mode = "love"

        if os.path.exists(self.love_bg):
            self._set_bg(self.love_bg)
        else:
            self._set_bg(self._fallback_bg())

        if not self.love_tracks:
            self.top_label.text = "缺少 listen7.mp3（根目录或 assets/）"
            return

        track = self.love_tracks[0]
        self._play_sound_cached(track, loop=False)
        self.top_label.text = f"我爱褚少华：{os.path.basename(track)} | 背景：listen_bg7.png"


if __name__ == "__main__":
    ProtonApp().run()
