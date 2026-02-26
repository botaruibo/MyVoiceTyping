import random
import sys


"""/**
 * macOS 原生 Cocoa 录音浮层（不抢占输入光标）。
 *
 * 设计目标：
 * - 显示在屏幕底部居中，尺寸固定（默认 220x60，与 Tk 版本一致）
 * - 透明背景 + 胶囊圆角黑底 + 白色描边
 * - 不抢焦点：不成为 key/main window，不影响当前前台应用的输入光标
 * - 鼠标穿透：不影响点击与输入
 * - 支持全屏/Spaces：设置 collectionBehavior（CanJoinAllSpaces + Transient + FullScreenAuxiliary）
 */"""


class CocoaRecordingOverlay:
    """/**
     * Cocoa 录音浮层封装。
     *
     * 注意：
     * - 仅在 macOS 下可用（sys.platform == 'darwin'）。
     * - 必须在主线程调用（通常 Tk 主线程就是主线程）。
     */"""

    def __init__(self, width: int = 80, height: int = 40, bottom_margin: int = 20):
        self._width = int(width)
        self._height = int(height)
        self._bottom_margin = int(bottom_margin)

        self._panel = None
        self._view = None

        # 标记当前是否处于“隐藏状态”（即使 NSPanel 仍可见，也按隐藏处理）
        self._is_hidden = True

        # 防止日志刷屏：仅在极少数情况下提示一次
        self._warned_not_visible = False

        self._ensure_created()

    def is_available(self) -> bool:
        return sys.platform == "darwin" and self._panel is not None and self._view is not None

    def is_visible(self) -> bool:
        try:
            if getattr(self, "_is_hidden", False):
                return False
            if self._panel is None:
                return False
            return bool(self._panel.isVisible())
        except Exception:
            return False

    def show(self) -> None:
        """
        /**
         * 显示浮层。
         *
         * 说明：
         * - 当前项目主事件循环是 Tk（mainloop），不会自动驱动 Cocoa 的 RunLoop。
         * - 这里会主动“pump”一次 Cocoa RunLoop，确保窗口真正显示/重绘。
         *
         * @returns {void}
         */
        """
        self._is_hidden = False

        self._ensure_created()
        if self._panel is None:
            return

        # hide() 里可能设置了 alpha=0，这里确保恢复可见
        try:
            self._panel.setAlphaValue_(1.0)
        except Exception:
            pass

        try:
            self._reposition()
        except Exception as e:
            print(f"⚠️ Cocoa 浮层定位失败（可忽略）: {e}")

        try:
            self._panel.orderFrontRegardless()
        except Exception as e:
            print(f"⚠️ Cocoa 浮层显示失败（可忽略）: {e}")
            return

        try:
            if self._view is not None:
                self._view.setNeedsDisplay_(True)
        except Exception:
            pass

        try:
            self._panel.displayIfNeeded()
        except Exception:
            pass

        self._pump_events()

        try:
            if not self.is_visible() and not self._warned_not_visible:
                self._warned_not_visible = True
                print(
                    "⚠️ Cocoa overlay 已调用 show，但窗口仍不可见。"
                    "这通常是因为 Cocoa RunLoop 未被驱动；当前实现已尝试 pump。"
                )
        except Exception:
            pass

    def hide(self) -> None:
        """
        /**
         * 隐藏浮层。
         *
         * 说明：
         * - 这里同时做两层兜底：
         *   1) alpha=0 让浮层在视觉上立即消失
         *   2) orderOut_ 让窗口从 window server 移除（如果可用）
         * - 并设置 _is_hidden=True，使 is_visible 立即返回 False，停止 GUI 轮询。
         *
         * @returns {void}
         */
        """
        self._is_hidden = True

        if self._panel is None:
            return

        try:
            self._panel.setAlphaValue_(0.0)
        except Exception:
            pass

        try:
            self._panel.orderOut_(None)
        except Exception as e:
            print(f"⚠️ Cocoa 浮层隐藏失败（可忽略）: {e}")

    def set_volume(self, level: int) -> None:
        """
        /**
         * 设置当前音量值（0~100），触发重绘。
         *
         * 说明：
         * - Tk 作为主事件循环时，Cocoa 的重绘可能不会立刻发生。
         * - 这里会在必要时 pump 一次 Cocoa RunLoop，提升显示稳定性。
         *
         * @param {number} level - 0~100。
         * @returns {void}
         */
        """
        if self._view is None:
            return

        try:
            lv = int(level)
        except Exception:
            lv = 0

        lv = max(0, min(100, lv))

        try:
            # 注意：这里调用的是 ObjC selector `setVolumeLevel:`（对应 Python 方法名 `setVolumeLevel_`）
            self._view.setVolumeLevel_(lv)
        except Exception as e:
            print(f"⚠️ Cocoa 浮层设置音量失败（可忽略）: {e}")
            return

        try:
            if self._panel is not None:
                self._panel.displayIfNeeded()
        except Exception:
            pass
        # 注意：这里不再每帧 _pump_events()，避免系统层 IMK RunLoop 日志刷屏
        self._pump_events()

    def _pump_events(self) -> None:
        """
        /**
         * 主动驱动一次 Cocoa RunLoop。
         *
         * 背景：
         * - 本项目 UI 主循环是 Tk（mainloop），不会自动驱动 Cocoa RunLoop。
         * - NSPanel 的显示/重绘依赖 RunLoop；因此这里做一次非阻塞的 runUntilDate。
         *
         * @returns {void}
         */
        """
        if sys.platform != "darwin":
            return

        try:
            from AppKit import NSApplication
            from Foundation import NSDate, NSRunLoop

            try:
                NSApplication.sharedApplication().updateWindows()
            except Exception:
                pass

            try:
                NSRunLoop.currentRunLoop().runUntilDate_(NSDate.dateWithTimeIntervalSinceNow_(0.0))
            except Exception:
                pass
        except Exception:
            pass

    def _ensure_created(self) -> None:
        if sys.platform != "darwin":
            return
        if self._panel is not None and self._view is not None:
            return

        try:
            from AppKit import (
                NSApplication,
                NSColor,
                NSFloatingWindowLevel,
                NSWindowCollectionBehaviorCanJoinAllSpaces,
                NSWindowCollectionBehaviorFullScreenAuxiliary,
                NSWindowCollectionBehaviorTransient,
                NSWindowStyleMaskBorderless,
                NSWindowStyleMaskNonactivatingPanel,
            )
            from Foundation import NSMakeRect

            NSApplication.sharedApplication()

            PanelCls, ViewCls = _get_objc_overlay_classes()

            frame = NSMakeRect(0, 0, self._width, self._height)
            style = NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel

            panel = PanelCls.alloc().initWithContentRect_styleMask_backing_defer_(
                frame,
                style,
                2,  # NSBackingStoreBuffered
                False,
            )

            try:
                panel.setOpaque_(False)
            except Exception:
                pass

            try:
                panel.setBackgroundColor_(NSColor.clearColor())
            except Exception:
                pass

            try:
                # 更强的置顶层级（不激活），在某些全屏/置顶窗口场景更容易被看到
                try:
                    from AppKit import NSStatusWindowLevel
                    panel.setLevel_(NSStatusWindowLevel)
                except Exception:
                    panel.setLevel_(NSFloatingWindowLevel)
            except Exception:
                pass

            try:
                panel.setIgnoresMouseEvents_(True)
            except Exception:
                pass

            try:
                panel.setHidesOnDeactivate_(False)
            except Exception:
                pass

            # 你要求的 collectionBehavior（支持 Spaces/全屏）
            try:
                behavior = (
                    NSWindowCollectionBehaviorCanJoinAllSpaces
                    | NSWindowCollectionBehaviorTransient
                    | NSWindowCollectionBehaviorFullScreenAuxiliary
                )
                panel.setCollectionBehavior_(behavior)
            except Exception as e:
                print(f"⚠️ Cocoa 浮层设置 collectionBehavior 失败（可忽略）: {e}")

            try:
                panel.setReleasedWhenClosed_(False)
            except Exception:
                pass

            view = ViewCls.alloc().initWithFrame_(frame)
            panel.setContentView_(view)

            self._panel = panel
            self._view = view

            self._reposition()
        except Exception as e:
            self._panel = None
            self._view = None
            print(f"⚠️ Cocoa 录音浮层初始化失败（将禁用录音浮层）: {e}")

    def _reposition(self) -> None:
        """
        /**
         * 重新定位浮层到屏幕底部居中位置。
         *
         * 说明：
         * - 使用 `visibleFrame()` 避免被 Dock/菜单栏遮挡。
         * - 多屏场景下优先使用 mainScreen；获取失败则回退到 screens[0]。
         *
         * @returns {void}
         */
        """
        if self._panel is None:
            return

        try:
            from AppKit import NSScreen
        except Exception as e:
            print(f"⚠️ 导入 NSScreen 失败（可忽略）: {e}")
            return

        screen = None
        try:
            screen = NSScreen.mainScreen()
        except Exception:
            screen = None

        if screen is None:
            try:
                screens = NSScreen.screens()
                if screens:
                    screen = screens[0]
            except Exception:
                screen = None

        if screen is None:
            return

        try:
            vf = screen.visibleFrame()
        except Exception:
            try:
                vf = screen.frame()
            except Exception:
                return

        x = vf.origin.x + (vf.size.width - self._width) / 2.0
        y = vf.origin.y + float(self._bottom_margin)

        try:
            from Foundation import NSMakeRect
        except Exception:
            NSMakeRect = None

        # 优先用 NSMakeRect 直接设置 frame（更稳）
        if NSMakeRect is not None:
            try:
                self._panel.setFrame_display_(NSMakeRect(x, y, self._width, self._height), True)
                return
            except Exception as e:
                print(f"⚠️ Cocoa 浮层设置 frame 失败（可忽略）: {e}")

        # 回退：基于当前 frame 修改 origin
        try:
            frame = self._panel.frame()
            frame.origin.x = x
            frame.origin.y = y
            self._panel.setFrame_display_(frame, True)
        except Exception as e:
            print(f"⚠️ Cocoa 浮层更新坐标失败（可忽略）: {e}")


_MVI_PANEL_CLS = None
_MVI_VIEW_CLS = None


def _get_objc_overlay_classes():
    """
    /**
     * 获取/缓存 ObjC 类（避免重复定义导致初始化失败）。
     *
     * 关键点：
     * - PyObjC 会把 Python 子类注册进 ObjC runtime，类名必须唯一。
     * - 反复初始化/重试时如果重复定义同名类，会触发：
     *   "is overriding existing Objective-C class"。
     * - 此函数确保在同一进程内只注册一次 ObjC class。
     *
     * @returns {tuple} (PanelCls, ViewCls)
     */
    """
    global _MVI_PANEL_CLS, _MVI_VIEW_CLS

    if _MVI_PANEL_CLS is not None and _MVI_VIEW_CLS is not None:
        return _MVI_PANEL_CLS, _MVI_VIEW_CLS

    try:
        import objc
        from AppKit import (
            NSBezierPath,
            NSColor,
            NSPanel,
            NSRoundLineCapStyle,
            NSRoundLineJoinStyle,
            NSView,
        )
        from Foundation import NSMakeRect
    except Exception as e:
        raise RuntimeError(f"PyObjC/Cocoa 依赖不可用: {e}")

    if _MVI_PANEL_CLS is None:
        try:
            _MVI_PANEL_CLS = objc.lookUpClass("MVIRecordingNonActivatingPanel")
        except Exception:
            class MVIRecordingNonActivatingPanel(NSPanel):
                """/**
                 * 自定义 NSPanel 子类，禁止成为 Key/Main Window。
                 *
                 * @extends NSPanel
                 */"""

                def canBecomeKeyWindow(self):
                    """/**
                     * 禁止成为 Key Window。
                     *
                     * @returns {boolean} 始终返回 False
                     */"""
                    return False

                def canBecomeMainWindow(self):
                    """/**
                     * 禁止成为 Main Window。
                     *
                     * @returns {boolean} 始终返回 False
                     */"""
                    return False

            _MVI_PANEL_CLS = MVIRecordingNonActivatingPanel

    if _MVI_VIEW_CLS is None:
        try:
            _MVI_VIEW_CLS = objc.lookUpClass("MVIRecordingOverlayContentView")
        except Exception:
            class MVIRecordingOverlayContentView(NSView):
                """/**
                 * 自定义 NSView 子类，用于绘制录音浮层内容。
                 *
                 * 包含：
                 * - 圆角胶囊背景
                 * - 音量波形动画
                 *
                 * @extends NSView
                 */"""

                def initWithFrame_(self, frame):
                    """/**
                     * 初始化视图。
                     *
                     * @param {NSRect} frame - 视图框架
                     * @returns {MVIRecordingOverlayContentView} 实例
                     */"""
                    self = objc.super(MVIRecordingOverlayContentView, self).initWithFrame_(frame)
                    if self is None:
                        return None

                    self._volume_level = 0

                    # 浮层内容布局参数（与窗口尺寸强相关）
                    self._num_bars = 9
                    self._bar_width = 2
                    self._gap = 3
                    self._padding_x = 0
                    self._padding_y = 6

                    try:
                        self.setWantsLayer_(True)
                        # 使用 None 代替 NSColor.clearColor().CGColor() 以避免 ObjCPointerWarning
                        # CALayer 的默认背景色即为 nil (透明)
                        self.layer().setBackgroundColor_(None)
                    except Exception:
                        pass

                    return self

                def isOpaque(self):
                    """/**
                     * 声明视图不透明属性。
                     *
                     * @returns {boolean} False 表示视图是透明的
                     */"""
                    return False

                def setVolumeLevel_(self, lv):
                    """/**
                     * 设置音量级别并触发重绘。
                     *
                     * @param {number} lv - 音量级别 (0-100)
                     */"""
                    try:
                        self._volume_level = int(lv)
                    except Exception:
                        self._volume_level = 0

                    try:
                        self.setNeedsDisplay_(True)
                    except Exception:
                        pass

                def drawRect_(self, rect):
                    """/**
                     * 绘制视图内容。
                     *
                     * 包括：
                     * 1. 绘制圆角矩形背景和描边
                     * 2. 根据音量绘制波形条
                     *
                     * @param {NSRect} rect - 脏矩形区域
                     */"""
                    w = rect.size.width
                    h = rect.size.height
                    radius = h / 2.0

                    try:
                        # 背景：直接用整个 rect 画胶囊
                        bg_path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(rect, radius, radius)
                        NSColor.blackColor().set()
                        bg_path.fill()

                        # 白色描边：stroke 会以 path 为中心向内/向外各扩一半线宽。
                        # 如果直接对 rect stroke，会因为外侧被裁剪，导致圆角处“看起来粗细不均匀”。
                        # 因此这里把描边路径向内 inset（线宽/2），保证描边完全落在可见区域内。
                        border_lw = max(1.0, min(1.0, float(h) * 0.12))
                        inset = border_lw / 2.0
                        bw = w - inset * 2.0
                        bh = h - inset * 2.0
                        if bw > 1.0 and bh > 1.0:
                            border_rect = NSMakeRect(rect.origin.x + inset, rect.origin.y + inset, bw, bh)
                            border_radius = bh / 2.0

                            border_path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
                                border_rect,
                                border_radius,
                                border_radius,
                            )
                            try:
                                border_path.setLineJoinStyle_(NSRoundLineJoinStyle)
                            except Exception:
                                pass
                            try:
                                border_path.setLineCapStyle_(NSRoundLineCapStyle)
                            except Exception:
                                pass

                            NSColor.whiteColor().set()
                            border_path.setLineWidth_(border_lw)
                            border_path.stroke()
                    except Exception:
                        pass

                    try:
                        content_h = max(1.0, h - self._padding_y * 2)
                        total_width = self._num_bars * (self._bar_width + self._gap) - self._gap
                        start_x = (w - total_width) / 2.0

                        max_bar_h = max(1.0, content_h)
                        min_bar_h = 0.0

                        lv = max(0, min(100, int(getattr(self, "_volume_level", 0) or 0)))
                        base_max_h = min_bar_h + (max_bar_h - min_bar_h) * (lv / 100.0)

                        NSColor.whiteColor().set()

                        for i in range(self._num_bars):
                            distance = abs(i - self._num_bars // 2)
                            damp = 1.0 - (distance / (self._num_bars / 2.0)) ** 2
                            damp = max(0.0, min(1.0, damp))

                            jitter = random.uniform(0.85, 1.15)
                            bar_h = max(min_bar_h, base_max_h * damp * jitter)

                            x0 = start_x + i * (self._bar_width + self._gap)
                            y0 = (h - bar_h) / 2.0
                            bar_rect = NSMakeRect(x0, y0, self._bar_width, bar_h)

                            NSBezierPath.fillRect_(bar_rect)
                    except Exception:
                        pass

            _MVI_VIEW_CLS = MVIRecordingOverlayContentView

    if _MVI_PANEL_CLS is None or _MVI_VIEW_CLS is None:
        raise RuntimeError("初始化 ObjC overlay class 失败")

    return _MVI_PANEL_CLS, _MVI_VIEW_CLS