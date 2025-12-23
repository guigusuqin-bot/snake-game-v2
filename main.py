# main.py（v0 稳定版：卡片式专业 UI；关闭雪花；不自动播放 listen8；小说字体红色；bg7=爱；bg8=小说；小说主题曲 listen8）
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
        # 资源规则（按你约定）
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

        # 小说主题曲：listen8（⚠️不再启动自动播放，只在进入小说按钮后播放）
        self.novel_track = _pick_existing([
            os.path.join(self.root_dir, "listen8.mp3"),
        ])

        # 小说 10 页（不删）
        self.novel_pages = self._make_novel_pages_10()
        self.novel_page_i = 0

        # 状态
        self.mode = "home"  # home / listen / love / novel
        self.sound = None
        self.listen_index = -1
        self.bg_index = -1

        # 音频缓存：减少切歌卡顿（不引入线程，不加依赖）
        self._sound_cache = {}

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

        # 顶部标题（白字）
        self.top_label = Label(
            text="你好，静静，我是质子 1 号。\n褚少华派我来陪伴你。",
            size_hint=(1, None),
            height=110,
            pos_hint={"x": 0, "top": 1},
            font_size=22,
            halign="center",
            valign="middle",
            font_name=self.font if self.font else None,
            color=(1, 1, 1, 1),
        )
        self.top_label.bind(size=self._sync_top_text)
        root.add_widget(self.top_label)

        # 中央卡片（专业风）
        self.card = FloatLayout(
            size_hint=(0.92, None),
            height=max(420, int(Window.height * 0.60)),
            pos_hint={"center_x": 0.5, "center_y": 0.47},
        )
        with self.card.canvas.before:
            Color(0, 0, 0, 0.35)
            self.card_rect = RoundedRectangle(pos=self.card.pos, size=self.card.size, radius=[22])
            # 外圈淡描边
            Color(1, 1, 1, 0.10)
            self.card_border = RoundedRectangle(pos=self.card.pos, size=self.card.size, radius=[22])

        self.card.bind(pos=self._sync_card_rect, size=self._sync_card_rect)
        root.add_widget(self.card)

        # 按钮区（卡片里）
        self.btn_col = BoxLayout(
            orientation="vertical",
            spacing=16,
            padding=[22, 22, 22, 16],
            size_hint=(1, None),
            height=260,
            pos_hint={"x": 0, "top": 1},
        )
        self.card.add_widget(self.btn_col)

        self.btn_listen = self._make_pill_button("🎧  和褚少华一起听歌", kind="green")
        self.btn_listen.bind(on_press=self.on_listen_press)

        self.btn_novel = self._make_pill_button("📖  和褚少华一起看小说", kind="green")
        self.btn_novel.bind(on_press=self.on_novel_press)

        self.btn_love = self._make_pill_button("❤️  我爱褚少华", kind="red")
        self.btn_love.bind(on_press=self.on_love_press)

        self.btn_col.add_widget(self.btn_listen)
        self.btn_col.add_widget(self.btn_novel)
        self.btn_col.add_widget(self.btn_love)

        # 状态信息（卡片里）
        self.state_box = FloatLayout(size_hint=(1, None), height=170, pos_hint={"x": 0, "y": 0})
        with self.state_box.canvas.before:
            Color(0, 0, 0, 0.22)
            self.state_rect = RoundedRectangle(pos=self.state_box.pos, size=self.state_box.size, radius=[18])
            Color(1, 1, 1, 0.08)
            self.state_border = RoundedRectangle(pos=self.state_box.pos, size=self.state_box.size, radius=[18])
        self.state_box.bind(pos=self._sync_state_rect, size=self._sync_state_rect)

        self.state_label = Label(
            text="准备就绪。",
            size_hint=(0.92, None),
            height=120,
            pos_hint={"center_x": 0.5, "center_y": 0.62},
            font_size=18,
            halign="left",
            valign="top",
            font_name=self.font if self.font else None,
            color=(1, 1, 1, 0.95),
        )
        self.state_label.bind(size=self._sync_state_text)
        self.state_box.add_widget(self.state_label)

        self.btn_stop = self._make_pill_button("⏹️  停止播放", kind="dark")
        self.btn_stop.size_hint = (0.70, None)
        self.btn_stop.height = 62
        self.btn_stop.pos_hint = {"center_x": 0.5, "y": 0.06}
        self.btn_stop.bind(on_press=self.on_stop_press)
        self.state_box.add_widget(self.btn_stop)

        self.card.add_widget(self.state_box)

        # 小说控件（进入小说后显示在卡片下半部分，不改小说内容）
        self.novel_scroll = ScrollView(
            size_hint=(0.92, None),
            height=240,
            pos_hint={"center_x": 0.5, "y": 0.05},
        )
        self.novel_label = Label(
            text="",
            size_hint_y=None,
            text_size=(Window.width * 0.82, None),
            font_size=24,
            halign="left",
            valign="top",
            font_name=self.font if self.font else None,
            color=(1, 0.25, 0.25, 1),  # 小说内容红色（你要求）
        )
        self.novel_label.bind(texture_size=self._update_novel_label_height)
        self.novel_scroll.add_widget(self.novel_label)

        Window.bind(size=self._on_window_resize)

        # 初始：home（⚠️不自动播放 listen8）
        self._show_home()

        return root

    # ------------------ 画面同步 ------------------

    def _sync_top_text(self, *_):
        self.top_label.text_size = (self.top_label.width * 0.96, None)

    def _sync_card_rect(self, *_):
        self.card_rect.pos = self.card.pos
        self.card_rect.size = self.card.size
        self.card_border.pos = self.card.pos
        self.card_border.size = self.card.size

    def _sync_state_rect(self, *_):
        self.state_rect.pos = self.state_box.pos
        self.state_rect.size = self.state_box.size
        self.state_border.pos = self.state_box.pos
        self.state_border.size = self.state_box.size

    def _sync_state_text(self, *_):
        self.state_label.text_size = (self.state_label.width, None)

    def _on_window_resize(self, *_):
        self.card.height = max(420, int(Window.height * 0.60))
        self.novel_label.text_size = (Window.width * 0.82, None)

    # ------------------ UI 工具 ------------------

    def _make_pill_button(self, text: str, kind: str = "green") -> Button:
        btn = Button(
            text=text,
            font_size=22,
            font_name=self.font if self.font else None,
            size_hint=(1, None),
            height=76,
            background_normal="",
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 1),
        )

        # 配色（不炸：纯绘制圆角，不用滤镜）
        if kind == "green":
            col_up = (0.10, 0.38, 0.28, 0.78)
            col_down = (0.08, 0.32, 0.24, 0.92)
            border = (1, 1, 1, 0.16)
        elif kind == "red":
            col_up = (0.42, 0.10, 0.12, 0.78)
            col_down = (0.36, 0.08, 0.10, 0.92)
            border = (1, 1, 1, 0.16)
        else:  # dark
            col_up = (0.12, 0.12, 0.12, 0.65)
            col_down = (0.10, 0.10, 0.10, 0.85)
            border = (1, 1, 1, 0.12)

        btn._col_up = col_up
        btn._col_down = col_down
        btn._border = border

        with btn.canvas.before:
            btn._bg_color = Color(*btn._col_up)
            btn._bg_rect = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[btn.height / 2])
            btn._bd_color = Color(*btn._border)
            btn._bd_rect = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[btn.height / 2])

        def _sync(*_):
            btn._bg_rect.pos = btn.pos
            btn._bg_rect.size = btn.size
            btn._bg_rect.radius = [btn.height / 2]
            btn._bd_rect.pos = btn.pos
            btn._bd_rect.size = btn.size
            btn._bd_rect.radius = [btn.height / 2]

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
            # 不强制 reload：减少卡顿
            self.bg.source = path

    def _clear_novel(self):
        if self.novel_scroll.parent:
            self.novel_scroll.parent.remove_widget(self.novel_scroll)

    # ------------------ 音频（稳定：缓存 + 不自动播放） ------------------

    def _stop_sound(self):
        try:
            if self.sound:
                self.sound.stop()
        except Exception:
            pass
        self.sound = None

    def _get_sound(self, path: str):
        if not path or not os.path.exists(path):
            return None
        if path in self._sound_cache:
            return self._sound_cache[path]
        s = SoundLoader.load(path)
        if s:
            self._sound_cache[path] = s
        return s

    def _play_sound(self, path: str, loop: bool = False):
        self._stop_sound()
        s = self._get_sound(path)
        if not s:
            self.state_label.text = f"无法加载音频：{os.path.basename(path) if path else '空路径'}"
            return
        self.sound = s
        self.sound.loop = loop
        self.sound.play()

    # ------------------ 小说（不删内容） ------------------

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
        self._clear_novel()
        self._set_bg(self._fallback_bg())
        self.state_label.text = "准备就绪。\n（提示：进入 App 不会自动播放任何音乐）"

    def _show_novel(self):
        self.mode = "novel"
        self._set_bg(self.bg_novel if os.path.exists(self.bg_novel) else self._fallback_bg())
        if not self.novel_scroll.parent:
            self.card.add_widget(self.novel_scroll)
        self._render_novel_page()

    # ------------------ 三按钮逻辑（不自动播 listen8） ------------------

    def on_stop_press(self, *_):
        self._stop_sound()
        self.state_label.text = "已停止播放。"

    def on_listen_press(self, *_):
        if not self.listen_tracks:
            self.state_label.text = "缺少 listen1~listen6.mp3（根目录）"
            return
        if not self.listen_bgs:
            self.state_label.text = "缺少 assets/listen_bg1~listen_bg6.png"
            return

        self.mode = "listen"
        self._clear_novel()

        self.listen_index = (self.listen_index + 1) % len(self.listen_tracks)
        self.bg_index = (self.bg_index + 1) % len(self.listen_bgs)

        track = self.listen_tracks[self.listen_index]
        bg = self.listen_bgs[self.bg_index]

        self._set_bg(bg)
        self._play_sound(track, loop=False)
        self.state_label.text = f"听歌：{os.path.basename(track)}\n背景：{os.path.basename(bg)}"

    def on_love_press(self, *_):
        self.mode = "love"
        self._clear_novel()

        self._set_bg(self.bg_love if os.path.exists(self.bg_love) else self._fallback_bg())

        if not self.love_track:
            self.state_label.text = "缺少 listen7.mp3（根目录）"
            return

        self._play_sound(self.love_track, loop=False)
        self.state_label.text = "我爱褚少华：listen7.mp3\n背景：listen_bg7.png"

    def on_novel_press(self, *_):
        # 第一次：进入小说（bg8 + 显示小说；⚠️不自动播放）
        # 之后：翻页（不重载音乐）
        if self.mode != "novel":
            self.novel_page_i = 0
            self._show_novel()
            self.state_label.text = "小说模式：再按一次翻页。\n（进入小说时不会自动播放，只有你点“开始播放”才播）"
            # 不自动播放 listen8 —— 已删除
        else:
            self.novel_page_i += 1
            self._render_novel_page()
            self.state_label.text = "小说模式：已翻页。\n（音乐不会被重复加载）"

    # 额外：小说主题曲手动播放按钮（不改你三按钮，但给你一个“稳的播放入口”）
    # 你要完全不要这个按钮就告诉我，我再删掉（整文件覆盖）
    def on_start_novel_music(self, *_):
        if not self.novel_track:
            self.state_label.text = "缺少 listen8.mp3（根目录）"
            return
        self._play_sound(self.novel_track, loop=True)
        self.state_label.text = "小说主题曲：listen8.mp3（循环）"

    def on_start(self):
        # 在卡片底部加一个“开始播放❤️”按钮（只负责播放 listen8，默认不自动播放）
        self.btn_start = self._make_pill_button("▶️  开始播放❤️", kind="red")
        self.btn_start.size_hint = (0.92, None)
        self.btn_start.height = 72
        self.btn_start.pos_hint = {"center_x": 0.5, "y": 0.015}
        self.btn_start.bind(on_press=self.on_start_novel_music)
        # 放到 state_box 里，和“停止播放”并存
        self.state_box.add_widget(self.btn_start)


if __name__ == "__main__":
    ProtonApp().run()
