from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.core.window import Window

# 固定竖屏比例（方便你在电脑/手机预览）
Window.size = (360, 640)

class StartScreen(FloatLayout):

    def start_app(self, instance):
        print("开始按钮被点击了")
        # 这里以后接：播放声音 / 跳转界面 / 启动闹铃
        # 现在先留钩子，不做复杂逻辑

class MyApp(App):
    def build(self):
        root = StartScreen()

        start_button = Button(
            text="❤️\n开始",
            font_size=48,
            size_hint=(0.6, 0.3),
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            background_normal="",
            background_color=(1, 0, 0, 1),  # 红色
            color=(1, 1, 1, 1),             # 白字
        )

        start_button.bind(on_press=root.start_app)
        root.add_widget(start_button)

        return root

if __name__ == "__main__":
    MyApp().run()
