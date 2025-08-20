import sys
import mpv
from mpv import MpvRenderContext, MpvGlGetProcAddressFn
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtOpenGLWidgets import QOpenGLWidget
# ================== 新增导入 ==================
from PySide6.QtGui import QSurfaceFormat, QOpenGLContext
from PySide6.QtOpenGL import QOpenGLDebugLogger
from PySide6.QtCore import Qt, QMetaObject
# ============================================

class VideoWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mpv =  mpv.MPV(vo='libmpv', hwdec='auto', log_handler=print)
        self.mpv_render_context = None
        self.logger = None # 为日志记录器准备一个变量

    def initializeGL(self):
        # --- 创建 mpv 渲染上下文的部分保持不变 ---
        def _get_proc(_ctx, name):
            glctx = QOpenGLContext.currentContext()
            address = int(glctx.getProcAddress(name.decode('utf-8'))) if glctx else 0
            return address
        
        self.mpv_render_context = MpvRenderContext(
            self.mpv, 'opengl',
            opengl_init_params={'get_proc_address': MpvGlGetProcAddressFn(_get_proc)}
        )
        print("mpv render context initialized.")

        self.logger = QOpenGLDebugLogger(self)
        print("OpenGL debug logger created.")

        # 2. 初始化日志记录器
        #    如果失败（比如系统不支持），会返回 False
        if not self.logger.initialize():
            print("Failed to initialize OpenGL debug logger.")
            self.logger = None
            return
            
        # 3. 将日志记录器的 messageLogged 信号连接到我们的处理函数上
        self.logger.messageLogged.connect(self.log_message)

        # 4. 开始监听日志

        self.logger.startLogging(QOpenGLDebugLogger.AsynchronousLogging)
        print("OpenGL debug logger started.")
        self.mpv_render_context.set_update_callback(
             lambda: QMetaObject.invokeMethod(self, "update", Qt.QueuedConnection)
        )
         
    def paintGL(self):
        if not self.mpv_render_context:
            return
        dpr = self.devicePixelRatioF()
        w, h = int(self.width() * dpr), int(self.height() * dpr)
        fbo_id = int(self.defaultFramebufferObject())

        self.mpv_render_context.render(
            opengl_fbo={'fbo': fbo_id, 'w': w, 'h': h},
            flip_y=True 
        )
        self.mpv_render_context.report_swap()

    def closeEvent(self, e):
        if self.mpv_render_context:
            self.mpv_render_context.free()
            self.mpv_render_context = None
        super().closeEvent(e)

    # ================== 新增日志处理函数 ==================
    def log_message(self, message):
        # message 是一个 QOpenGLDebugMessage 对象
        # 我们可以获取它的详细信息并打印出来
        print(f"[OpenGL Debug] {message.message()}")
    # ============================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("最终阶段: 视频播放！")
        self.resize(800, 600)
        self.widget = VideoWidget()
        self.setCentralWidget(self.widget)

if __name__ == '__main__':
    fmt = QSurfaceFormat()
    fmt.setProfile(QSurfaceFormat.CoreProfile)
    fmt.setVersion(3, 3)
    fmt.setSwapBehavior(QSurfaceFormat.DoubleBuffer)
    fmt.setSwapInterval(1)
    # ================== 新增设置 ==================
    # 请求一个支持调试的 OpenGL 上下文
    fmt.setOption(QSurfaceFormat.DebugContext, on=True)
    # ============================================
    QSurfaceFormat.setDefaultFormat(fmt)

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()

    window.widget.mpv.play('test.mkv')

    sys.exit(app.exec())