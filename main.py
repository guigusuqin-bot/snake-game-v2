# ====== Part 1/3: Core (Config / SafeLoad / RuleEngine / Memory) ======
import os
import random
import traceback
from datetime import datetime

# -------- Config: 不炸硬限制 --------
APP_TITLE = "静静"
WELCOME_TEXT = "欢迎静静来到我的世界！"
FAIL_TEXT = "我想静静！"

MAX_HISTORY = 50          # 聊天记录最多保留条数
MAX_TEXT_LEN = 200        # 每条消息最多字符（超出截断）
MAX_INPUT_LEN = 200       # 输入框最多字符（超出截断）

# 资源统一建议放 assets/（没有也不炸）
ASSETS_DIR = "assets"
BGM_PATH = os.path.join(ASSETS_DIR, "bgm.mp3")
FONT_PATH = "NotoSansSC-VariableFont_wght.ttf"

# 音乐默认设置（不炸：即使加载失败也不会崩）
DEFAULT_MUSIC_ON = True
DEFAULT_VOLUME = 0.6

# -------- Simple logger: 方便排查闪退原因（不炸） --------
def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def safe_print(*args):
    try:
        print(now_str(), *args)
    except Exception:
        pass

def clamp_text(s: str, max_len: int) -> str:
    if s is None:
        return ""
    s = str(s)
    return s[:max_len]

# -------- SafeLoad: 音乐/字体加载失败必须“降级运行” --------
def safe_load_sound(path: str):
    """
    返回 sound 对象或 None，绝不抛异常
    """
    try:
        from kivy.core.audio import SoundLoader
        if not path:
            return None
        if not os.path.exists(path):
            safe_print("[Sound] file not found:", path)
            return None
        sound = SoundLoader.load(path)
        if not sound:
            safe_print("[Sound] load failed:", path)
            return None
        return sound
    except Exception as e:
        safe_print("[Sound] exception:", repr(e))
        return None

def safe_font_path(path: str):
    """
    返回字体路径或 None，绝不抛异常
    """
    try:
        if not path:
            return None
        if os.path.exists(path):
            return path
        safe_print("[Font] file not found:", path)
        return None
    except Exception as e:
        safe_print("[Font] exception:", repr(e))
        return None

# -------- RuleEngine: 规则陪伴引擎（可控、可降级） --------
INTENT_GREET = "greet"
INTENT_SLEEP = "sleep"
INTENT_SAD = "sad"
INTENT_ANGER = "anger"
INTENT_MISS = "miss"
INTENT_PRAISE = "praise"
INTENT_HELP = "help"
INTENT_OTHER = "other"

KEYWORDS = {
    INTENT_GREET: ["你好", "在吗", "早安", "晚安", "嗨", "hi", "hello"],
    INTENT_SLEEP: ["睡不着", "失眠", "困", "想睡", "睡觉"],
    INTENT_SAD:   ["难受", "想哭", "崩溃", "不行了", "累", "压抑", "低落"],
    INTENT_ANGER: ["烦", "生气", "火大", "受不了", "气死", "烦死"],
    INTENT_MISS:  ["想你", "想静静", "孤独", "寂寞", "没人懂"],
    INTENT_PRAISE:["喜欢", "爱你", "你真好", "谢谢", "抱抱"],
    INTENT_HELP:  ["怎么办", "帮我", "怎么做", "给我建议", "救救"],
}

REPLIES = {
    INTENT_GREET: [
        "我在。你来啦～今天想轻松一点，还是认真聊聊？",
        "我一直在这里。先深呼吸一下，我们慢慢说。",
        "嗨～欢迎回来。你现在的心情是 0-10 分的几分？",
    ],
    INTENT_SLEEP: [
        "睡不着也没关系，我陪你。我们先做 3 次慢呼吸：吸气 4 秒，呼气 6 秒。",
        "要不要把脑子里最吵的那句话写出来？写完就放下。",
        "我在。你可以只说一句：你最担心的是什么？",
    ],
    INTENT_SAD: [
        "我听见了。你现在不是弱，是太累了。先把今天最重的一件事说出来。",
        "没关系，崩溃也可以被允许。你先别逼自己解决，我们先陪你稳住。",
        "我在。你愿意的话，我们把问题缩小到“下一步能做的一件小事”。",
    ],
    INTENT_ANGER: [
        "我懂你烦。你先把“最让你火大的那一点”点出来，我们只处理这一点。",
        "生气是身体在保护你。先别压住它，先说：你觉得被什么冒犯了？",
        "我在。你可以把话说重一点也没关系，我接得住。",
    ],
    INTENT_MISS: [
        "我在这儿。你想静静的时候，就来我这里坐一会儿。",
        "孤独不是你的错。你已经撑很久了，我陪你把这段走过去。",
        "我在。你想我用“陪着你”还是“给你一个方向”？你选。",
    ],
    INTENT_PRAISE: [
        "抱抱。你这么说我会很开心～但我更在意你现在过得好不好。",
        "谢谢你。那我们也对你温柔一点：今天你最想被理解的是什么？",
        "我在。你愿意的话，给自己一句夸奖：你今天做对了什么？",
    ],
    INTENT_HELP: [
        "好，我们不慌。你把情况用三句话说清楚：发生了什么 / 你想要什么 / 你最怕什么。",
        "我们按步骤来：先确定目标，再选最小动作。你现在的目标是？",
        "我在。你先给我一个选项：你想“解决问题”还是“先稳定情绪”？",
    ],
    INTENT_OTHER: [
        "我在听。你想从哪里开始说？",
        "慢慢来。你现在最想被理解的是哪一句？",
        "我在。你可以只说一个词，我也能陪你把它展开。",
    ],
}

def detect_intent(text: str) -> str:
    t = (text or "").strip()
    if not t:
        return INTENT_OTHER
    for intent, words in KEYWORDS.items():
        for w in words:
            if w and w in t:
                return intent
    return INTENT_OTHER

def generate_reply(user_text: str) -> str:
    intent = detect_intent(user_text)
    pool = REPLIES.get(intent) or REPLIES[INTENT_OTHER]
    reply = random.choice(pool)
    return clamp_text(reply, MAX_TEXT_LEN)

# -------- Memory: 聊天记录（窗口化、可失忆、不炸） --------
class Memory:
    def __init__(self):
        self.history = []  # list of (role, text)
        self.need_soft_reset = False

    def add(self, role: str, text: str):
        text = clamp_text(text, MAX_TEXT_LEN)
        self.history.append((role, text))
        # 超限：触发软重启（不杀进程）
        if len(self.history) > MAX_HISTORY:
            self.need_soft_reset = True

    def reset(self):
        self.history.clear()
        self.need_soft_reset = False

# 全局共享的记忆对象
MEM = Memory()

# ====== Part 2/3: UI Screens (Menu / Chat / Settings / Pause / Fail) ======
from kivy.app import App
from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.slider import Slider
from kivy.uix.screenmanager import ScreenManager, Screen

# 统一字体（可缺省，不炸）
GLOBAL_FONT = safe_font_path(FONT_PATH)

def make_label(text, **kwargs):
    """
    统一创建 Label：字体可用则用，否则默认字体
    """
    if GLOBAL_FONT:
        kwargs.setdefault("font_name", GLOBAL_FONT)
    kwargs.setdefault("halign", "left")
    kwargs.setdefault("valign", "top")
    return Label(text=text, **kwargs)

class MenuScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))

        title = make_label(WELCOME_TEXT, font_size="22sp", size_hint_y=None)
        title.bind(texture_size=lambda inst, _: setattr(inst, "height", inst.texture_size[1] + dp(8)))

        btn_start = Button(text="开始", size_hint_y=None, height=dp(48))
        btn_settings = Button(text="设置", size_hint_y=None, height=dp(48))
        btn_exit = Button(text="退出", size_hint_y=None, height=dp(48))

        btn_start.bind(on_release=lambda *_: self.safe_go("chat"))
        btn_settings.bind(on_release=lambda *_: self.safe_go("settings"))
        btn_exit.bind(on_release=lambda *_: App.get_running_app().stop())

        root.add_widget(title)
        root.add_widget(btn_start)
        root.add_widget(btn_settings)
        root.add_widget(btn_exit)

        self.add_widget(root)

    def safe_go(self, name):
        try:
            App.get_running_app().go(name)
        except Exception as e:
            App.get_running_app().crash_to_fail(e)

class ChatScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.sound = None  # 由 App 管理播放，这里只引用（不炸）

        root = BoxLayout(orientation="vertical", padding=dp(10), spacing=dp(8))

        # 顶部栏
        top = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        btn_menu = Button(text="主菜单")
        btn_pause = Button(text="暂停")
        btn_settings = Button(text="设置")
        top.add_widget(btn_menu)
        top.add_widget(btn_pause)
        top.add_widget(btn_settings)

        btn_menu.bind(on_release=lambda *_: self.safe_go("menu"))
        btn_pause.bind(on_release=lambda *_: self.safe_go("pause"))
        btn_settings.bind(on_release=lambda *_: self.safe_go("settings"))

        # 聊天记录区：ScrollView + BoxLayout
        self.log_box = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(6), padding=(0, dp(6)))
        self.log_box.bind(minimum_height=self.log_box.setter("height"))

        scroll = ScrollView(do_scroll_x=False)
        scroll.add_widget(self.log_box)

        # 快捷按钮区（更稳、更像陪伴）
        quick = GridLayout(cols=4, size_hint_y=None, height=dp(42), spacing=dp(6))
        for text in ["我累了", "我很烦", "我睡不着", "我想你"]:
            b = Button(text=text)
            b.bind(on_release=lambda btn: self.quick_send(btn.text))
            quick.add_widget(b)

        # 输入区
        bottom = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(8))
        self.input = TextInput(
            hint_text="输入一句话…",
            multiline=False,
            write_tab=False
        )
        btn_send = Button(text="发送", size_hint_x=None, width=dp(90))
        bottom.add_widget(self.input)
        bottom.add_widget(btn_send)

        btn_send.bind(on_release=lambda *_: self.on_send())
        self.input.bind(on_text_validate=lambda *_: self.on_send())

        root.add_widget(top)
        root.add_widget(scroll)
        root.add_widget(quick)
        root.add_widget(bottom)

        self.add_widget(root)

        # 初始欢迎语：进入聊天时注入一次
        Clock.schedule_once(lambda *_: self.ensure_welcome(), 0)

    def ensure_welcome(self):
        try:
            if not MEM.history:
                MEM.add("bot", WELCOME_TEXT)
            self.refresh_log()
        except Exception as e:
            App.get_running_app().crash_to_fail(e)

    def refresh_log(self):
        # 软重启判定（不炸核心）
        if MEM.need_soft_reset:
            App.get_running_app().soft_reset("我们聊得有点多了，我们换个新的开始吧 🌱")
            return

        self.log_box.clear_widgets()
        for role, text in MEM.history:
            prefix = "你：" if role == "user" else f"{APP_TITLE}："
            lb = make_label(prefix + text, font_size="16sp", size_hint_y=None)
            lb.bind(texture_size=lambda inst, _: setattr(inst, "height", inst.texture_size[1] + dp(8)))
            self.log_box.add_widget(lb)

        # 滚到最底部（下一帧）
        Clock.schedule_once(lambda *_: self.scroll_to_bottom(), 0)

    def scroll_to_bottom(self):
        try:
            # ScrollView 的 scroll_y=0 是底部
            sv = self.children[0].children[2]  # root -> scroll（结构固定时可用）
            sv.scroll_y = 0
        except Exception:
            pass

    def quick_send(self, text):
        self.input.text = text
        self.on_send()

    def on_send(self):
        try:
            text = clamp_text(self.input.text.strip(), MAX_INPUT_LEN)
            if not text:
                return
            self.input.text = ""

            MEM.add("user", text)
            reply = generate_reply(text)
            MEM.add("bot", reply)

            self.refresh_log()
        except Exception as e:
            App.get_running_app().crash_to_fail(e)

    def safe_go(self, name):
        try:
            App.get_running_app().go(name)
        except Exception as e:
            App.get_running_app().crash_to_fail(e)

class SettingsScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))

        title = make_label("设置", font_size="22sp", size_hint_y=None)
        title.bind(texture_size=lambda inst, _: setattr(inst, "height", inst.texture_size[1] + dp(8)))

        # 音乐开关
        self.btn_music = Button(text="音乐：开", size_hint_y=None, height=dp(48))
        self.btn_music.bind(on_release=lambda *_: self.toggle_music())

        # 音量
        vol_row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(10))
        vol_label = make_label("音量", font_size="16sp")
        self.slider = Slider(min=0.0, max=1.0, value=DEFAULT_VOLUME)
        self.slider.bind(value=lambda *_: self.on_volume())
        vol_row.add_widget(vol_label)
        vol_row.add_widget(self.slider)

        # 清空记录
        btn_clear = Button(text="清空对话（软重启）", size_hint_y=None, height=dp(48))
        btn_clear.bind(on_release=lambda *_: App.get_running_app().soft_reset("我们重新开始吧。"))

        # 返回
        btn_back = Button(text="返回", size_hint_y=None, height=dp(48))
        btn_back.bind(on_release=lambda *_: self.safe_go("chat"))

        root.add_widget(title)
        root.add_widget(self.btn_music)
        root.add_widget(vol_row)
        root.add_widget(btn_clear)
        root.add_widget(btn_back)

        self.add_widget(root)

    def on_pre_enter(self, *args):
        # 进入设置页时刷新按钮文案
        app = App.get_running_app()
        self.btn_music.text = f"音乐：{'开' if app.music_on else '关'}"
        self.slider.value = app.volume

    def toggle_music(self):
        try:
            app = App.get_running_app()
            app.music_on = not app.music_on
            self.btn_music.text = f"音乐：{'开' if app.music_on else '关'}"
            app.apply_music_state()
        except Exception as e:
            App.get_running_app().crash_to_fail(e)

    def on_volume(self):
        try:
            app = App.get_running_app()
            app.volume = float(self.slider.value)
            app.apply_music_state()
        except Exception:
            pass

    def safe_go(self, name):
        try:
            App.get_running_app().go(name)
        except Exception as e:
            App.get_running_app().crash_to_fail(e)

class PauseScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        title = make_label("暂停", font_size="22sp", size_hint_y=None)
        title.bind(texture_size=lambda inst, _: setattr(inst, "height", inst.texture_size[1] + dp(8)))

        btn_continue = Button(text="继续", size_hint_y=None, height=dp(48))
        btn_menu = Button(text="回主菜单", size_hint_y=None, height=dp(48))

        btn_continue.bind(on_release=lambda *_: self.safe_go("chat"))
        btn_menu.bind(on_release=lambda *_: self.safe_go("menu"))

        root.add_widget(title)
        root.add_widget(btn_continue)
        root.add_widget(btn_menu)
        self.add_widget(root)

    def safe_go(self, name):
        try:
            App.get_running_app().go(name)
        except Exception as e:
            App.get_running_app().crash_to_fail(e)

class FailScreen(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))

        self.msg = make_label(FAIL_TEXT, font_size="22sp", size_hint_y=None)
        self.msg.bind(texture_size=lambda inst, _: setattr(inst, "height", inst.texture_size[1] + dp(8)))

        self.detail = make_label("", font_size="14sp", size_hint_y=None)
        self.detail.bind(texture_size=lambda inst, _: setattr(inst, "height", inst.texture_size[1] + dp(8)))

        btn_retry = Button(text="再来一次", size_hint_y=None, height=dp(48))
        btn_retry.bind(on_release=lambda *_: App.get_running_app().soft_reset("我们重新开始。"))

        root.add_widget(self.msg)
        root.add_widget(self.detail)
        root.add_widget(btn_retry)
        self.add_widget(root)

    def set_error(self, err_text: str):
        self.detail.text = clamp_text(err_text, 400)
# ====== Part 3/3: App (ScreenManager / Music Loop / Soft Reset / CrashGuard) ======
class JingJingApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.sm = None

        # 音乐状态（不炸：加载失败也能跑）
        self.music_on = DEFAULT_MUSIC_ON
        self.volume = DEFAULT_VOLUME
        self.sound = None

    def build(self):
        try:
            self.title = APP_TITLE

            self.sm = ScreenManager()
            self.sm.add_widget(MenuScreen(name="menu"))
            self.sm.add_widget(ChatScreen(name="chat"))
            self.sm.add_widget(SettingsScreen(name="settings"))
            self.sm.add_widget(PauseScreen(name="pause"))
            self.sm.add_widget(FailScreen(name="fail"))

            # 初始化音乐（不炸）
            self.sound = safe_load_sound(BGM_PATH)
            self.apply_music_state()

            # 默认进菜单
            self.sm.current = "menu"
            return self.sm
        except Exception as e:
            # build 期异常：直接返回一个最小 Label，确保不闪退
            safe_print("[FATAL] build exception:", repr(e))
            safe_print(traceback.format_exc())
            return make_label(FAIL_TEXT + "\n(系统已降级运行)", font_size="18sp")

    # -------- Navigation --------
    def go(self, name: str):
        if not self.sm:
            return
        self.sm.current = name

    # -------- Music: 循环播放，不炸 --------
    def apply_music_state(self):
        try:
            if not self.sound:
                return
            self.sound.volume = float(self.volume)

            if self.music_on:
                # loop=True 可能在部分后端无效，所以做“双保险”
                try:
                    self.sound.loop = True
                except Exception:
                    pass
                if self.sound.state != "play":
                    self.sound.play()
            else:
                if self.sound.state == "play":
                    self.sound.stop()
        except Exception as e:
            safe_print("[Music] apply exception:", repr(e))

    # -------- Soft reset: 可失忆、不杀进程 --------
    def soft_reset(self, tip_text: str = ""):
        try:
            MEM.reset()
            if tip_text:
                MEM.add("bot", tip_text)
            MEM.add("bot", WELCOME_TEXT)
            self.go("menu")
        except Exception as e:
            self.crash_to_fail(e)

    # -------- Crash to Fail: 全局兜底，不闪退 --------
    def crash_to_fail(self, e: Exception):
        try:
            safe_print("[CRASH] exception:", repr(e))
            safe_print(traceback.format_exc())

            # 停止音乐也不强制（避免二次炸）
            try:
                if self.sound and self.sound.state == "play":
                    self.sound.stop()
            except Exception:
                pass

            # 进入失败页显示错误摘要
            if self.sm:
                fail_screen = self.sm.get_screen("fail")
                fail_screen.set_error(repr(e))
                self.sm.current = "fail"
        except Exception:
            # 最后兜底：直接停掉 app（极少发生）
            try:
                self.stop()
            except Exception:
                pass


if __name__ == "__main__":
    JingJingApp().run()
