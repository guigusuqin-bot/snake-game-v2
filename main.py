import os
import random
from typing import Dict, List

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


# ----------------- 工具函数 -----------------
def _app_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _pick_existing(paths: List[str]) -> str:
    for p in paths:
        if p and os.path.exists(p):
            return p
    return ""


# ----------------- 雪花层（轻量） -----------------
class SnowLayer(FloatLayout):
    """轻量雪花：Canvas 画 Ellipse，30fps，不卡为第一目标"""

    def __init__(self, count: int = 28, **kwargs):
        super().__init__(**kwargs)
        self.count = int(count)
        self._flakes: List[Dict] = []
        self._running = False

        Window.bind(size=self._on_resize)

        with self.canvas:
            self._snow_color = Color(1, 1, 1, 0.78)
            for _ in range(self.count):
                flake = self._new_flake(spawn_top=False)
                e = Ellipse(pos=(flake["x"], flake["y"]), size=(flake["r"], flake["r"]))
                flake["e"] = e
                self._flakes.append(flake)

    def _new_flake(self, spawn_top: bool = False) -> Dict:
        w, h = Window.size
        r = random.uniform(2.2, 5.6)
        x = random.uniform(0, max(1, w - r))
        y = random.uniform(h, h + h * 0.25) if spawn_top else random.uniform(0, h)
        vy = random.uniform(55.0, 125.0)
        vx = random.uniform(-22.0, 22.0)
        wob = random.uniform(0.6, 1.5)
        phase = random.uniform(0, 6.28)
        return {"x": x, "y": y, "r": r, "vy": vy, "vx": vx, "wob": wob, "phase": phase}

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

    def _tick(self, dt: float):
        w, h = Window.size
        for f in self._flakes:
            f["y"] -= f["vy"] * dt
            f["x"] += f["vx"] * dt
            f["x"] += (f["wob"] * 20.0) * dt * (random.uniform(-1.0, 1.0))

            if f["x"] < -10:
                f["x"] = w + 10
            if f["x"] > w + 10:
                f["x"] = -10

            if f["y"] < -20:
                nf = self._new_flake(spawn_top=True)
                f.update(nf)

            f["e"].pos = (f["x"], f["y"])


# ----------------- 主 App -----------------
class ProtonApp(App):
    def build(self):
        self.root_dir = _app_dir()
        self.assets_dir = os.path.join(self.root_dir, "assets")

        resource_add_path(self.root_dir)
        resource_add_path(self.assets_dir)

        # 字体（可选）
        self.font = _pick_existing([
            os.path.join(self.root_dir, "NotoSansSC-VariableFont_wght.ttf"),
            os.path.join(self.assets_dir, "NotoSansSC-VariableFont_wght.ttf"),
        ])

        # 背景（固定命名）
        def bg(n: int) -> str:
            return os.path.join(self.assets_dir, f"listen_bg{n}.png")

        # ✅ 新增开始界面背景
        self.bg_start_fixed = bg(2)

        # ✅ 三按钮固定背景
        self.bg_listen_fixed = bg(1)
        self.bg_novel_fixed = bg(4)
        self.bg_love_fixed = bg(7)

        # 音频（固定命名）
        def track(n: int) -> str:
            return os.path.join(self.root_dir, f"listen{n}.mp3")

        self.listen_tracks = [track(i) for i in range(1, 7)]
        self.love_track = track(7)
        self.novel_track = track(8)

        # 状态
        self.mode = "start"   # ✅ 默认进入开始界面
        self.sound = None
        self.listen_index = -1
        self._sound_cache: Dict[str, object] = {}

        # 小说按钮触发计数：到 10 次停止
        self.novel_trigger_count = 0
        self.novel_trigger_limit = 10

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

        # 雪花层（背景之上）
        self.snow = SnowLayer(count=32, size_hint=(1, 1), pos_hint={"x": 0, "y": 0})
        root.add_widget(self.snow)

        # 顶部大标题（不动）
        self.top_label = Label(
            text="🎄❄️ 我是质子 1 号：圣诞快乐，。❄️🎄",
            size_hint=(1, None),
            height=120,
            pos_hint={"center_x": 0.5, "top": 1},
            font_size=28,
            bold=True,
            font_name=self.font if self.font else None,
            color=(1, 1, 1, 0.98),
        )
        root.add_widget(self.top_label)

        # 内容区（用于开始界面按钮 / 小说大金字）
        self.content_area = FloatLayout(size_hint=(1, 1))
        root.add_widget(self.content_area)

        # ----------------- 开始界面：圆形“进入”按钮 -----------------
        self.enter_btn = Button(
            text="进入",
            font_size=36,
            font_name=self.font if self.font else None,
            size_hint=(None, None),
            background_normal="",
            background_color=(0, 0, 0, 0),
            color=(1, 1, 1, 1),
        )
        self.enter_btn.bind(on_press=self.on_enter_press)

        # 圆形样式（红底金边，跟主按钮一致风格，但做圆）
        self.enter_btn._col_up = (0.62, 0.12, 0.12, 0.92)
        self.enter_btn._col_down = (0.40, 0.08, 0.08, 0.96)
        self.enter_btn._stroke_col = (0.96, 0.82, 0.28, 0.95)

        with self.enter_btn.canvas.before:
            self.enter_btn._bg_color = Color(*self.enter_btn._col_up)
            self.enter_btn._bg_rect = RoundedRectangle(pos=self.enter_btn.pos, size=self.enter_btn.size, radius=[999])
            self.enter_btn._line_color = Color(*self.enter_btn._stroke_col)
            self.enter_btn._line = Line(rounded_rectangle=[0, 0, 0, 0, 999], width=2.2)

        def _sync_enter(*_):
            # 尺寸：屏幕高度的 1/6，保持圆形
            d = max(120, int(Window.height / 6))
            self.enter_btn.size = (d, d)
            self.enter_btn.pos = (Window.width * 0.5 - d * 0.5, Window.height * 0.52 - d * 0.5)

            self.enter_btn._bg_rect.pos = self.enter_btn.pos
            self.enter_btn._bg_rect.size = self.enter_btn.size
            self.enter_btn._bg_rect.radius = [d / 2]

            self.enter_btn._line.rounded_rectangle = [
                self.enter_btn.x, self.enter_btn.y, self.enter_btn.width, self.enter_btn.height, d / 2
            ]

        self.enter_btn.bind(pos=_sync_enter, size=_sync_enter)

        def _down_enter(*_):
            self.enter_btn._bg_color.rgba = self.enter_btn._col_down

        def _up_enter(*_):
            self.enter_btn._bg_color.rgba = self.enter_btn._col_up

        self.enter_btn.bind(on_press=_down_enter, on_release=_up_enter)

        # ----------------- 主界面：3 按钮区（不动） -----------------
        self.btn_box = BoxLayout(
            orientation="vertical",
            spacing=18,
            padding=[0, 0, 0, 0],
            size_hint=(0.88, None),
            height=max(340, int(Window.height * 0.42)),
            pos_hint={"center_x": 0.5, "center_y": 0.30},
        )

        self.btn_listen = self._make_round_button("和褚少华一起听歌", font_size=28, height=112)
        self.btn_listen.bind(on_press=self.on_listen_press)

        self.btn_novel = self._make_round_button("和褚少华一起看小说", font_size=28, height=112)
        self.btn_novel.bind(on_press=self.on_novel_press)

        self.btn_love = self._make_round_button("我爱褚少华", font_size=28, height=112)
        self.btn_love.bind(on_press=self.on_love_press)

        self.btn_box.add_widget(self.btn_listen)
        self.btn_box.add_widget(self.btn_novel)
        self.btn_box.add_widget(self.btn_love)

        # ----------------- 小说输出：大金字 -----------------
        self.novel_scroll = ScrollView(
            size_hint=(0.92, 0.66),
            pos_hint={"center_x": 0.5, "center_y": 0.60},
        )

        self.novel_label = Label(
            text="",
            size_hint_y=None,
            text_size=(Window.width * 0.86, None),
            font_size=40,                # ✅ 大字
            halign="center",
            valign="middle",
            font_name=self.font if self.font else None,
            color=(0.98, 0.86, 0.25, 1), # ✅ 金色
        )
        self.novel_label.bind(texture_size=self._update_novel_label_height)
        self.novel_scroll.add_widget(self.novel_label)

        Window.bind(size=self._on_window_resize)

 # ✅ 默认展示开始界面（不自动播放）
        self._show_start()

        # ✅ 雪花开启
        self.snow.start()

        # ✅ 计算一次进入按钮位置
        _sync_enter()

        return root

    # ----------------- UI -----------------
    def _on_window_resize(self, *_):
        self.btn_box.height = max(340, int(Window.height * 0.42))
        self.novel_label.text_size = (Window.width * 0.86, None)

        # 同步进入按钮（防旋转/尺寸变化后错位）
        d = max(120, int(Window.height / 6))
        self.enter_btn.size = (d, d)
        self.enter_btn.pos = (Window.width * 0.5 - d * 0.5, Window.height * 0.52 - d * 0.5)
        self.enter_btn._bg_rect.pos = self.enter_btn.pos
        self.enter_btn._bg_rect.size = self.enter_btn.size
        self.enter_btn._bg_rect.radius = [d / 2]
        self.enter_btn._line.rounded_rectangle = [self.enter_btn.x, self.enter_btn.y, self.enter_btn.width, self.enter_btn.height, d / 2]

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

        btn._col_up = (0.62, 0.12, 0.12, 0.92)
        btn._col_down = (0.40, 0.08, 0.08, 0.96)
        btn._stroke_col = (0.96, 0.82, 0.28, 0.95)

        with btn.canvas.before:
            btn._bg_color = Color(*btn._col_up)
            btn._bg_rect = RoundedRectangle(pos=btn.pos, size=btn.size, radius=[btn.height / 2])
            btn._line_color = Color(*btn._stroke_col)
            btn._line = Line(rounded_rectangle=[btn.x, btn.y, btn.width, btn.height, btn.height / 2], width=2.0)

        def _sync(*_):
            btn._bg_rect.pos = btn.pos
            btn._bg_rect.size = btn.size
            btn._bg_rect.radius = [btn.height / 2]
            btn._line.rounded_rectangle = [btn.x, btn.y, btn.width, btn.height, btn.height / 2]

        btn.bind(pos=_sync, size=_sync)

        def _down(*_):
            btn._bg_color.rgba = btn._col_down

        def _up(*_):
            btn._bg_color.rgba = btn._col_up

        btn.bind(on_press=_down, on_release=_up)
        return btn

    def _update_novel_label_height(self, *_):
        self.novel_label.height = self.novel_label.texture_size[1] + 40

    def _clear_content(self):
        self.content_area.clear_widgets()

    def _fallback_bg(self) -> str:
        p = os.path.join(self.assets_dir, "listen_bg1.png")
        if os.path.exists(p):
            return p
        icon = os.path.join(self.root_dir, "icon.png")
        if os.path.exists(icon):
            return icon
        return ""

    def _set_bg(self, path: str):
        try:
            if path and os.path.exists(path):
                self.bg.source = path
                self.bg.reload()
                return
        except Exception:
            pass

        fb = self._fallback_bg()
        if fb and os.path.exists(fb):
            self.bg.source = fb
            try:
                self.bg.reload()
            except Exception:
                pass

    # ----------------- 音频 -----------------
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
        try:
            s = SoundLoader.load(path)
        except Exception:
            s = None
        if s:
            self._sound_cache[path] = s
        return s

    def _play_sound(self, path: str, loop: bool = False):
        # 每次都 stop + seek(0) + play（保证“重新播放”）
        self._stop_sound()

        if not path or not os.path.exists(path):
            self.top_label.text = f"⚠️ 找不到音频：{os.path.basename(path) if path else '空路径'}"
            return

        s = self._get_sound_cached(path)
        if not s:
            self.top_label.text = f"⚠️ 无法加载音频：{os.path.basename(path)}"
            return

        self.sound = s
        try:
            self.sound.loop = loop
        except Exception:
            pass

        try:
            if hasattr(self.sound, "seek"):
                self.sound.seek(0)
        except Exception:
            pass

        try:
            self.sound.play()
        except Exception:
            self.top_label.text = f"⚠️ 播放失败：{os.path.basename(path)}"
            self.sound = None

    # ----------------- 界面：开始 / 主界面 -----------------
    def _show_start(self):
        self.mode = "start"
        self._stop_sound()
        self._clear_content()
        self._set_bg(self.bg_start_fixed)

        # 开始界面只显示“进入”按钮
        self.content_area.add_widget(self.enter_btn)

        # 主界面三按钮不显示（确保不会叠在一起）
        if self.btn_box.parent:
            self.btn_box.parent.remove_widget(self.btn_box)

        self.top_label.text = "🎄 点击进入"

    def _show_main(self):
        self.mode = "home"
        self._stop_sound()
        self._clear_content()
        # 进入主界面时先用 bg1 兜底（你听歌按钮也固定 bg1）
        self._set_bg(self._fallback_bg())

        # 移除开始按钮（如果还在）
        if self.enter_btn.parent:
            self.enter_btn.parent.remove_widget(self.enter_btn)

        # 显示三按钮
        if not self.btn_box.parent:
            # btn_box 是 build() 时创建的，直接加回根容器：content_area 上层已经有，不能用
            # 这里用 App 的 root（FloatLayout）上的 children 关系：我们把 btn_box 加到 root（self.root）
            self.root.add_widget(self.btn_box)

        self.top_label.text = "🎄❄️ 我是质子 1 号：圣诞快乐，。❄️🎄"

    # ----------------- 事件：开始界面“进入” -----------------
    def on_enter_press(self, *_):
        self._show_main()

    # ----------------- 三按钮逻辑（按你要求） -----------------
    def on_listen_press(self, *_):
        # 固定背景：listen_bg1
        self.mode = "listen"
        self._clear_content()  # 保证不会残留大字
        self._set_bg(self.bg_listen_fixed)

        existing = [p for p in self.listen_tracks if os.path.exists(p)]
        if not existing:
            self.top_label.text = "⚠️ 缺少 listen1~listen6.mp3（根目录）"
            return

        self.listen_index = (self.listen_index + 1) % len(existing)
        track = existing[self.listen_index]

        self._play_sound(track, loop=False)
        self.top_label.text = f"❄️🎵 听歌：{os.path.basename(track)}（背景固定 listen_bg1）"

    def on_novel_press(self, *_):
        # 触发 10 次后停止
        if self.novel_trigger_count >= self.novel_trigger_limit:
            self.top_label.text = "🎄 已触发 10 次：小说按钮停止"
            return

        self.novel_trigger_count += 1
        self.mode = "novel"
        self._clear_content()

        # 固定背景：listen_bg4
        self._set_bg(self.bg_novel_fixed)

        # 只输出一句话：大金字
        self.novel_label.text = "跟褚少华说我爱你解锁新剧情！"
        self.content_area.add_widget(self.novel_scroll)

        # 背景音乐：listen8 循环
        if os.path.exists(self.novel_track):
            self._play_sound(self.novel_track, loop=True)
        else:
            self.top_label.text = "⚠️ 缺少 listen8.mp3（根目录）"
            return

        left = self.novel_trigger_limit - self.novel_trigger_count
        if left > 0:
            self.top_label.text = f"🎄 小说触发 {self.novel_trigger_count}/10（剩余 {left} 次）"
        else:
            self.top_label.text = "🎄 已触发 10 次：下次按将停止"

    def on_love_press(self, *_):
        self.mode = "love"
        self._clear_content()
        self._set_bg(self.bg_love_fixed)

        if not os.path.exists(self.love_track):
            self.top_label.text = "⚠️ 缺少 listen7.mp3（根目录）"
            return

        # 每次按下都从头播
        self._play_sound(self.love_track, loop=False)
        self.top_label.text = "🎄❤️ 我爱褚少华（listen7 每次重播｜背景固定 listen_bg7）"


if __name__ == "__main__":
    ProtonApp().run()
