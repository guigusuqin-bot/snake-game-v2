from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.image import Image
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label

from kivy.core.audio import SoundLoader
from kivy.core.text import LabelBase
from kivy.resources import resource_find
from kivy.clock import Clock


# ========== 工具：安全找资源 ==========
def rfind(name: str) -> str:
    p = resource_find(name)
    return p if p else ""


# ========== Screen 1：应用内欢迎页（用来实现“加载界面一句话”） ==========
class SplashScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        root = FloatLayout()

        # 你可以把这里背景换成你想要的（也可以用 presplash.png 同一张）
        bg = Image(
            source=rfind("presplash.png") or rfind("app_icon.png"),
            allow_stretch=True,
            keep_ratio=False
        )
        root.add_widget(bg)

        self.label = Label(
            text="你好，静静，我是质子 1 号 。褚少华派我来陪伴你。",
            font_name="NotoSansSC",
            font_size=24,
            halign="center",
            valign="middle",
            size_hint=(0.9, 0.3),
            pos_hint={"center_x": 0.5, "center_y": 0.18}
        )
        self.label.bind(size=lambda *_: setattr(self.label, "text_size", self.label.size))
        root.add_widget(self.label)

        self.add_widget(root)

    def on_enter(self, *args):
        # 1.2 秒后进入主菜单
        Clock.schedule_once(lambda dt: self.manager.set_current("menu"), 1.2)


# ========== Screen 2：主菜单（3 个按钮） ==========
class MenuScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app

        root = FloatLayout()

        # 默认背景：先用 listen_bg1 做兜底，没有就黑
        self.bg = Image(
            source=rfind("listen_bg1.png"),
            allow_stretch=True,
            keep_ratio=False
        )
        root.add_widget(self.bg)

        # 三个按钮：文字必须完全按你写的
        self.btn1 = Button(
            text="和褚少华一起听歌",
            font_name="NotoSansSC",
            font_size=28,
            size_hint=(0.88, 0.16),
            pos_hint={"center_x": 0.5, "center_y": 0.62},
            background_normal="",
            background_color=(0.2, 0.2, 0.2, 0.7),
            color=(1, 1, 1, 1)
        )
        self.btn2 = Button(
            text="和褚少华一起看小说",
            font_name="NotoSansSC",
            font_size=28,
            size_hint=(0.88, 0.16),
            pos_hint={"center_x": 0.5, "center_y": 0.42},
            background_normal="",
            background_color=(0.2, 0.2, 0.2, 0.7),
            color=(1, 1, 1, 1)
        )
        self.btn3 = Button(
            text="我爱褚少华",
            font_name="NotoSansSC",
            font_size=28,
            size_hint=(0.88, 0.16),
            pos_hint={"center_x": 0.5, "center_y": 0.22},
            background_normal="",
            background_color=(0.2, 0.2, 0.2, 0.7),
            color=(1, 1, 1, 1)
        )

        self.btn1.bind(on_release=lambda *_: self.app.action_listen(self))
        self.btn2.bind(on_release=lambda *_: self.app.action_novel(self))
        self.btn3.bind(on_release=lambda *_: self.app.action_love(self))

        root.add_widget(self.btn1)
        root.add_widget(self.btn2)
        root.add_widget(self.btn3)

        self.add_widget(root)


# ========== Screen 3：小说阅读页（固定背景 + 翻页） ==========
class ReaderScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app = app

        root = FloatLayout()

        self.bg = Image(
            source=rfind("novel_bg.png"),
            allow_stretch=True,
            keep_ratio=False
        )
        root.add_widget(self.bg)

        # 小说内容区域（ScrollView + Label）
        self.scroll = ScrollView(
            size_hint=(0.92, 0.68),
            pos_hint={"center_x": 0.5, "center_y": 0.60},
            do_scroll_x=False
        )

        self.label = Label(
            text="",
            font_name="NotoSansSC",
            font_size=22,
            halign="left",
            valign="top",
            size_hint_y=None
        )
        self.label.bind(width=self._update_text_size)

        self.scroll.add_widget(self.label)
        root.add_widget(self.scroll)

        # 翻页按钮（沿用第二按钮文字，不改字）
        self.next_btn = Button(
            text="和褚少华一起看小说",
            font_name="NotoSansSC",
            font_size=26,
            size_hint=(0.88, 0.14),
            pos_hint={"center_x": 0.5, "center_y": 0.14},
            background_normal="",
            background_color=(0.2, 0.2, 0.2, 0.75),
            color=(1, 1, 1, 1)
        )
        self.next_btn.bind(on_release=lambda *_: self.app.novel_next_page())
        root.add_widget(self.next_btn)

        self.add_widget(root)

    def _update_text_size(self, *_):
        self.label.text_size = (self.label.width, None)

    def set_page_text(self, text: str):
        self.label.text = text
        # 让 label 高度随文字增长（否则 scroll 不工作）
        self.label.texture_update()
        self.label.height = self.label.texture_size[1]
        self.scroll.scroll_y = 1


# ========== ScreenManager 小扩展 ==========
class MySM(ScreenManager):
    def set_current(self, name: str):
        self.current = name


class MyApp(App):
    def build(self):
        # 1) 中文字体注册（必须）
        font_path = rfind("NotoSansSC-VariableFont_wght.ttf")
        if font_path:
            LabelBase.register(name="NotoSansSC", fn_regular=font_path)

        # 2) 音频状态
        self.sound = None
        self.mode = None  # "listen" / "love" / None

        # 3) 听歌资源（3 首 + 3 背景）
        self.listen_tracks = [rfind("listen1.mp3"), rfind("listen2.mp3"), rfind("listen3.mp3")]
        self.listen_bgs = [rfind("listen_bg1.png"), rfind("listen_bg2.png"), rfind("listen_bg3.png")]
        self.listen_i = -1

        # 4) love 资源（背景只切一次 + 音频循环切换）
        self.love_bg = rfind("love_bg.png")
        self.love_tracks = [rfind("love1.mp3"), rfind("love2.mp3"), rfind("love3.mp3")]
        self.love_i = -1
        self.love_bg_applied = False

        # 5) 小说资源（固定背景 + 分页）
        self.novel_text = self._load_text("novel.txt")
        self.novel_page_size = 900  # 每页约 900 字（你觉得太少/太多再调）
        self.novel_pages = self._split_pages(self.novel_text, self.novel_page_size)
        self.novel_page_index = 0

        # 6) 组装界面
        self.sm = MySM()
        self.sm.add_widget(SplashScreen(name="splash"))
        self.menu = MenuScreen(app=self, name="menu")
        self.reader = ReaderScreen(app=self, name="reader")

        self.sm.add_widget(self.menu)
        self.sm.add_widget(self.reader)

        self.sm.current = "splash"
        return self.sm

    # ====== 公共：停止当前音频 ======
    def stop_sound(self):
        if self.sound:
            try:
                self.sound.stop()
            except:
                pass
        self.sound = None

    # ====== 公共：播放指定音频（只在按钮点击时调用） ======
    def play_sound(self, path: str):
        if not path:
            return
        self.stop_sound()
        s = SoundLoader.load(path)
        if not s:
            return
        s.loop = True
        s.play()
        self.sound = s

    # ========== 按钮 1：听歌（按一下：切一首 + 切背景） ==========
    def action_listen(self, menu_screen: MenuScreen):
        self.mode = "listen"
        self.love_bg_applied = False  # 切回听歌时，允许下次 love 再切背景一次

        # 下一个 index
        self.listen_i = (self.listen_i + 1) % 3

        # 切背景
        bg = self.listen_bgs[self.listen_i] if self.listen_bgs[self.listen_i] else ""
        if bg:
            menu_screen.bg.source = bg
            menu_screen.bg.reload()

        # 切音频
        track = self.listen_tracks[self.listen_i]
        self.play_sound(track)

    # ========== 按钮 2：看小说 ==========
    # 第一次按：进入阅读页 + 显示第 1 页
    # 后续在阅读页按同名按钮：翻页（背景不切）
    def action_novel(self, menu_screen: MenuScreen):
        self.mode = "novel"
        # 看小说不要求播放音频，保险起见先停
        self.stop_sound()
        self.novel_page_index = 0
        self._show_current_page()
        self.sm.set_current("reader")

    def novel_next_page(self):
        if not self.novel_pages:
            return
        self.novel_page_index = (self.novel_page_index + 1) % len(self.novel_pages)
        self._show_current_page()

    def _show_current_page(self):
        if not self.novel_pages:
            self.reader.set_page_text("novel.txt 没有内容或未找到。")
            return
        page_text = self.novel_pages[self.novel_page_index]
        # 可以加一个页码提示（不改按钮文字，只在正文末尾附加）
        footer = f"\n\n—— 第 {self.novel_page_index + 1} / {len(self.novel_pages)} 页 ——"
        self.reader.set_page_text(page_text + footer)

    # ========== 按钮 3：我爱褚少华 ==========
    # 第一次按：切 love_bg + 播放 love1
    # 后续再按：只切换 love 音频（背景不再切）
    def action_love(self, menu_screen: MenuScreen):
        self.mode = "love"

        # 第一次进入 love：切背景一次
        if (not self.love_bg_applied) and self.love_bg:
            menu_screen.bg.source = self.love_bg
            menu_screen.bg.reload()
            self.love_bg_applied = True

        # 每次按都切音频
        if not self.love_tracks:
            return
        self.love_i = (self.love_i + 1) % len(self.love_tracks)
        self.play_sound(self.love_tracks[self.love_i])

    # ====== 读文本 ======
    def _load_text(self, filename: str) -> str:
        path = rfind(filename)
        if not path:
            return ""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except:
            # 某些情况下可能是 utf-8-sig
            try:
                with open(path, "r", encoding="utf-8-sig") as f:
                    return f.read()
            except:
                return ""

    # ====== 分页（按字符数粗切，稳定够用） ======
    def _split_pages(self, text: str, size: int):
        if not text:
            return []
        pages = []
        i = 0
        n = len(text)
        while i < n:
            pages.append(text[i:i + size])
            i += size
        return pages


if __name__ == "__main__":
    MyApp().run()
