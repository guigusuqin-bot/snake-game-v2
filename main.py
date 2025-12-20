from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.core.audio import SoundLoader
from kivy.core.window import Window

# 方便预览（不影响手机实际运行）
Window.size = (360, 640)

class StartScreen(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # 1) 预加载音频（最稳）
        self.sound = SoundLoader.load("bgm.mp3")
        if self.sound:
            self.sound.loop = False  # 先不循环；你要循环我再改
        else:
            print("❌ 没找到 bgm.mp3（请确认文件在仓库根目录）")

        # 2) 创建按钮
        start_button = Button(
            text="❤️\n开始",
            font_size=48,
            size_hint=(0.6, 0.3),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            background_normal="",
            background_color=(1, 0, 0, 1),  # 红色
            color=(1, 1, 1, 1),             # 白字
        )
        start_button.bind(on_press=self.start_app)
        self.add_widget(start_button)

    def start_app(self, instance):
        print("✅ 开始按钮被点击")
        if self.sound:
            self.sound.stop()   # 防止重复点击叠音
            self.sound.play()
            print("🔊 正在播放 bgm.mp3")


class MyApp(App):
    def build(self):
        return StartScreen()

if __name__ == "__main__":
    MyApp().run()
