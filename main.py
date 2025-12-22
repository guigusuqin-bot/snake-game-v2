from kivy.app import App
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.core.audio import SoundLoader
from kivy.core.text import LabelBase
from kivy.resources import resource_find
from kivy.clock import Clock


class MusicOneButtonApp(App):
    def build(self):
        # 1) 注册中文字体（必须）
        font_path = resource_find("NotoSansSC-VariableFont_wght.ttf")
        if font_path:
            LabelBase.register(name="NotoSansSC", fn_regular=font_path)

        self.sound = None
        self.is_playing = False

        # 2) 背景图（先用你现有的 icon.png 做兜底，避免找不到就黑屏）
        bg_path = resource_find("icon.png")
        self.bg = Image(
            source=bg_path if bg_path else "",
            allow_stretch=True,
            keep_ratio=False
        )

        root = FloatLayout()
        root.add_widget(self.bg)

        # 3) 一个按钮（你现在截图里是“切歌”，我不改文字）
        self.btn = Button(
            text="切歌",
            font_name="NotoSansSC" if font_path else None,
            font_size=40,
            size_hint=(None, None),
            size=(360, 160),
            pos_hint={"center_x": 0.5, "center_y": 0.22},
            background_normal="",
            background_color=(0.35, 0.35, 0.35, 0.85),  # 半透明灰
            color=(1, 1, 1, 1)
        )
        self.btn.bind(on_press=self.on_press)
        self.btn.bind(on_release=self.on_release)

        root.add_widget(self.btn)

        return root

    # ——按钮按下：立刻变暗 + 轻微缩放（反馈感）——
    def on_press(self, *_):
        self.btn.background_color = (0.25, 0.25, 0.25, 0.95)
        self.btn.size = (340, 150)

    # ——按钮松开：恢复 + 执行一次切换（你后续可以把这里换成“切歌+切背景”）——
    def on_release(self, *_):
        self.btn.background_color = (0.35, 0.35, 0.35, 0.85)
        self.btn.size = (360, 160)

        # 只做“点击触发”的动作：切换播放/停止（不自动播放）
        if not self.is_playing:
            self.start_music()
        else:
            self.stop_music()

    def start_music(self):
        # 只在点击时加载/播放
        mp3_path = resource_find("bgm.mp3")
        if not mp3_path:
            return

        if self.sound is None:
            self.sound = SoundLoader.load(mp3_path)
            if not self.sound:
                return
            self.sound.loop = True

        self.sound.play()
        self.is_playing = True

        # 按钮文字不改（你要求不改），但我们用“闪一下”表示状态切换
        self.flash_btn()

    def stop_music(self):
        if self.sound:
            self.sound.stop()
        self.is_playing = False
        self.flash_btn()

    # ——轻量“闪一下”反馈：不改按钮文字——
    def flash_btn(self):
        self.btn.background_color = (0.6, 0.6, 0.6, 0.95)
        Clock.schedule_once(lambda dt: self.restore_btn_color(), 0.12)

    def restore_btn_color(self):
        self.btn.background_color = (0.35, 0.35, 0.35, 0.85)


if __name__ == "__main__":
    MusicOneButtonApp().run()
