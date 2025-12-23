# main.py  (v0 稳定版：无主题特效；优先解决切歌卡顿 + 小说红字清晰)
import os

from kivy.app import App
from kivy.core.audio import SoundLoader
from kivy.resources import resource_find
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label


def find_file(filename: str) -> str | None:
    """
    在 Android 打包后，资源路径可能变化：
    - 先用 resource_find
    - 再尝试根目录 / assets 目录
    """
    p = resource_find(filename)
    if p:
        return p

    candidates = [
        os.path.join(os.getcwd(), filename),
        os.path.join(os.getcwd(), "assets", filename),
    ]
    for c in candidates:
        if os.path.exists(c):
            return c

    return None


class QuietApp(App):
    # 你要的主题曲文件名（根目录已有 listen8.mp3）
    SONG = "listen8.mp3"

    def build(self):
        self.sound = None

        root = FloatLayout()

        # 顶部状态栏：用于确认“是不是新包/新代码” + 音频是否就绪
        self.status = Label(
            text="v0 | 启动中…",
            size_hint=(1, None),
            height=60,
            pos_hint={"x": 0, "top": 1},
            font_size="18sp",
        )
        root.add_widget(self.status)

        # 中间小说显示区（默认隐藏，红色字体）
        self.novel = Label(
            text="",
            markup=False,
            color=(1, 0.2, 0.2, 1),  # 红色（清晰、不刺眼）
            font_size="22sp",
            size_hint=(0.9, 0.55),
            pos_hint={"center_x": 0.5, "center_y": 0.55},
            halign="left",
            valign="top",
        )
        self.novel.bind(size=self._update_novel_text_size)
        root.add_widget(self.novel)

        # 底部按钮区（按钮文字保持不变）
        panel = BoxLayout(
            orientation="vertical",
            spacing=16,
            padding=[24, 24, 24, 24],
            size_hint=(0.92, 0.32),
            pos_hint={"center_x": 0.5, "y": 0.03},
        )

        self.btn_music = Button(
            text="和徐小华一起听歌",
            font_size="22sp",
        )
        self.btn_music.bind(on_press=self.toggle_music)

        self.btn_novel = Button(
            text="和徐小华一起看小说",
            font_size="22sp",
        )
        self.btn_novel.bind(on_press=self.show_novel)

        self.btn_love = Button(
            text="我爱徐小华",
            font_size="22sp",
        )
        self.btn_love.bind(on_press=self.say_love)

        panel.add_widget(self.btn_music)
        panel.add_widget(self.btn_novel)
        panel.add_widget(self.btn_love)

        root.add_widget(panel)

        return root

    def on_start(self):
        # 启动后预加载音频（关键：把“卡顿”从按钮点击挪走）
        path = find_file(self.SONG)
        if not path:
            self.status.text = f"v0 | 找不到 {self.SONG}（请确认在根目录或 assets）"
            return

        try:
            self.sound = SoundLoader.load(path)
            if self.sound:
                self.sound.loop = True  # 需要循环就 True；不循环就改 False
                self.status.text = f"v0 | 音频已预加载：{self.SONG}"
            else:
                self.status.text = f"v0 | 音频加载失败：{self.SONG}"
        except Exception as e:
            self.status.text = f"v0 | 音频异常：{e}"

    def _update_novel_text_size(self, *_):
        # 让小说文字按区域自动换行
        self.novel.text_size = self.novel.size

    def toggle_music(self, *_):
        # 按钮只做 play/stop（不再 load），减少卡顿
        if not self.sound:
            self.status.text = "v0 | 音频未就绪（请等启动预加载或检查文件）"
            return

        try:
            if self.sound.state == "play":
                self.sound.stop()
                self.status.text = "v0 | 已停止播放"
            else:
                self.sound.play()
                self.status.text = f"v0 | 正在播放：{self.SONG}"
        except Exception as e:
            self.status.text = f"v0 | 播放异常：{e}"

    def show_novel(self, *_):
        # 小说内容示例：你后续想换正文，就只改这里的字符串
        self.novel.text = (
            "【小说】\n"
            "这是 v0 稳定版：\n"
            "1）小说文字为红色，清晰可见。\n"
            "2）听歌不再每次点击都加载音频，减少卡顿。\n\n"
            "你可以把这里替换成你的正文内容。\n"
        )
        self.status.text = "v0 | 小说已打开（红字显示）"

    def say_love(self, *_):
        self.status.text = "v0 | ❤️"

    def on_stop(self):
        # 退出时释放音频，避免后台占用
        try:
            if self.sound:
                self.sound.stop()
        except Exception:
            pass

    def on_pause(self):
        # 安卓后台：停掉更稳
        try:
            if self.sound and self.sound.state == "play":
                self.sound.stop()
        except Exception:
            pass
        return True

    def on_resume(self):
        return True


if __name__ == "__main__":
    QuietApp().run()
