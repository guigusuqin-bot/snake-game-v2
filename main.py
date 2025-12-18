from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.slider import Slider
from kivy.clock import Clock
from kivy.core.audio import SoundLoader
from kivy.core.text import LabelBase
from kivy.graphics import Color, Rectangle

# ===== 注册中文字体（不炸关键）=====
LabelBase.register(
    name="CN",
    fn_regular="NotoSansSC-VariableFont_wght.ttf"
)

# ===== 全局配置 =====
BG_COLOR = (0, 0, 0, 1)
BTN_COLOR = (0.3, 0.3, 0.3, 1)

# ===== 音乐管理 =====
bgm = SoundLoader.load("bgm.mp3")
if bgm:
    bgm.loop = True
    bgm.volume = 0.5

# ===== 基础屏幕 =====
class BaseScreen(Screen):
    def on_enter(self):
        with self.canvas.before:
            Color(*BG_COLOR)
            self.rect = Rectangle(size=self.size, pos=self.pos)
        self.bind(size=self._update_rect, pos=self._update_rect)

    def _update_rect(self, *args):
        self.rect.size = self.size
        self.rect.pos = self.pos
# ===== 主菜单 =====
class MenuScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = BoxLayout(orientation="vertical", spacing=20, padding=50)

        title = Label(
            text="欢迎静静来到我的世界",
            font_name="CN",
            font_size=32
        )

        start_btn = Button(text="开始", size_hint=(1, 0.2))
        start_btn.bind(on_press=self.start_game)

        setting_btn = Button(text="设置", size_hint=(1, 0.2))
        setting_btn.bind(on_press=lambda x: self.manager.current = "settings")

        exit_btn = Button(text="退出", size_hint=(1, 0.2))
        exit_btn.bind(on_press=App.get_running_app().stop)

        layout.add_widget(title)
        layout.add_widget(start_btn)
        layout.add_widget(setting_btn)
        layout.add_widget(exit_btn)

        self.add_widget(layout)

    def start_game(self, *args):
        if bgm:
            bgm.play()
        self.manager.current = "game"


# ===== 设置页 =====
class SettingScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = BoxLayout(orientation="vertical", spacing=20, padding=40)

        title = Label(text="设置", font_name="CN", font_size=28)

        volume_label = Label(text="音乐音量", font_name="CN")
        volume_slider = Slider(min=0, max=1, value=0.5)
        volume_slider.bind(value=self.set_volume)

        back_btn = Button(text="返回")
        back_btn.bind(on_press=lambda x: self.manager.current = "menu")

        layout.add_widget(title)
        layout.add_widget(volume_label)
        layout.add_widget(volume_slider)
        layout.add_widget(back_btn)

        self.add_widget(layout)

    def set_volume(self, instance, value):
        if bgm:
            bgm.volume = value


# ===== 游戏页（极简安全版）=====
class GameScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = BoxLayout(orientation="vertical")

        self.info = Label(
            text="游戏进行中\n（此处预留战斗系统）",
            font_name="CN",
            font_size=24
        )

        pause_btn = Button(text="暂停", size_hint=(1, 0.2))
        pause_btn.bind(on_press=self.pause_game)

        layout.add_widget(self.info)
        layout.add_widget(pause_btn)
        self.add_widget(layout)

    def pause_game(self, *args):
        self.manager.current = "pause"
        # ===== 暂停页 =====
class PauseScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = BoxLayout(orientation="vertical", spacing=20, padding=40)

        label = Label(text="已暂停", font_name="CN", font_size=26)

        resume_btn = Button(text="继续")
        resume_btn.bind(on_press=lambda x: self.manager.current = "game")

        restart_btn = Button(text="重开")
        restart_btn.bind(on_press=lambda x: self.manager.current = "game")

        menu_btn = Button(text="回主菜单")
        menu_btn.bind(on_press=lambda x: self.manager.current = "menu")

        layout.add_widget(label)
        layout.add_widget(resume_btn)
        layout.add_widget(restart_btn)
        layout.add_widget(menu_btn)

        self.add_widget(layout)


# ===== 失败页 =====
class FailScreen(BaseScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        layout = BoxLayout(orientation="vertical", spacing=20, padding=40)

        label = Label(
            text="我想静静！",
            font_name="CN",
            font_size=30
        )

        retry_btn = Button(text="再来一次")
        retry_btn.bind(on_press=lambda x: self.manager.current = "game")

        layout.add_widget(label)
        layout.add_widget(retry_btn)
        self.add_widget(layout)


# ===== App 主体 =====
class JingJingGame(App):
    def build(self):
        sm = ScreenManager()
        sm.add_widget(MenuScreen(name="menu"))
        sm.add_widget(SettingScreen(name="settings"))
        sm.add_widget(GameScreen(name="game"))
        sm.add_widget(PauseScreen(name="pause"))
        sm.add_widget(FailScreen(name="fail"))
        return sm


if __name__ == "__main__":
    JingJingGame().run()
