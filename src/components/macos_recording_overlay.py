import sys


"""/**
 * macOS 原生 Cocoa 录音浮层（不抢占输入光标）。
 *
 * 设计目标：
 * - 显示在屏幕底部居中，尺寸固定
 * - 透明背景 + 黑色胶囊 + 彩色描边光晕 + 语音助手文案 + 5 条音量竖线
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

    def __init__(self, width: int = 140, height: int = 44, bottom_margin: int = 20):
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

    def set_progress(self, progress: float) -> None:
        """
        /**
         * 设置转写进度（0.0~1.0），触发重绘。
         *
         * @param {number} progress - 0~1。
         * @returns {void}
         */
        """
        if self._view is None:
            return

        try:
            p = float(progress)
        except Exception:
            p = 0.0

        p = max(0.0, min(1.0, p))

        try:
            self._view.setProgress_(p)
        except Exception as e:
            print(f"⚠️ Cocoa 浮层设置进度失败（可忽略）: {e}")
            return

        try:
            if self._panel is not None:
                self._panel.displayIfNeeded()
        except Exception:
            pass

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
            NSFont,
            NSFontAttributeName,
            NSForegroundColorAttributeName,
            NSGraphicsContext,
            NSPanel,
            NSRoundLineCapStyle,
            NSRoundLineJoinStyle,
            NSView,
        )
        from Foundation import NSMakePoint, NSMakeRect, NSString
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
                    self._progress = 0.0
                    self._wave_phase = 0

                    # 浮层内容布局参数（与窗口尺寸强相关）
                    self._num_bars = 5
                    self._bar_width = 2
                    self._gap = 3
                    self._pill_inset = 4
                    self._content_padding_x = 13
                    self._wave_right_padding = 18
                    self._wave_min_h = 4
                    self._wave_max_h = 19

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
                        self._wave_phase = int(getattr(self, "_wave_phase", 0) or 0) + 1
                    except Exception:
                        self._wave_phase = 0

                    try:
                        self.setNeedsDisplay_(True)
                    except Exception:
                        pass
                def setProgress_(self, progress):
                    """/**
                     * 设置转写进度并触发重绘。
                     *
                     * @param {number} progress - 转写进度 (0.0-1.0)
                     */"""
                    try:
                        self._progress = float(progress)
                    except Exception:
                        self._progress = 0.0

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
                    inset = float(getattr(self, "_pill_inset", 7) or 7)
                    pill_rect = NSMakeRect(rect.origin.x + inset, rect.origin.y + inset, w - inset * 2, h - inset * 2)
                    radius = pill_rect.size.height / 2.0

                    try:
                        bg_path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(pill_rect, radius, radius)

                        # 背景先画，避免后续光晕/文字绘制失败时整个浮窗透明。
                        NSColor.colorWithCalibratedRed_green_blue_alpha_(0.0, 0.0, 0.0, 0.96).set()
                        bg_path.fill()
                    except Exception:
                        pass

                    try:
                        bg_path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(pill_rect, radius, radius)

                        # 彩色柔光：用几层不同颜色的圆角描边叠出截图中的彩边气质。
                        glow_specs = [
                            (3.5, 0.20, (0.95, 0.72, 0.22)),
                            (2.5, 0.26, (0.93, 0.34, 0.72)),
                            (1.8, 0.28, (0.49, 0.35, 1.00)),
                            (1.1, 0.30, (0.18, 0.74, 1.00)),
                        ]
                        for line_w, alpha, rgb in glow_specs:
                            NSColor.colorWithCalibratedRed_green_blue_alpha_(rgb[0], rgb[1], rgb[2], alpha).set()
                            bg_path.setLineWidth_(line_w)
                            bg_path.stroke()
                    except Exception:
                        pass

                    try:
                        bg_path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(pill_rect, radius, radius)
                        # 覆盖一次黑色主体，让彩色描边主要留在外缘。
                        NSColor.colorWithCalibratedRed_green_blue_alpha_(0.0, 0.0, 0.0, 0.96).set()
                        bg_path.fill()

                        # 转写阶段保留轻量进度覆盖层（从左向右增长），不影响录音态样式。
                        try:
                            progress = float(getattr(self, "_progress", 0.0) or 0.0)
                            progress = max(0.0, min(1.0, progress))
                            if progress > 0.0:
                                try:
                                    NSGraphicsContext.saveGraphicsState()
                                except Exception:
                                    pass

                                try:
                                    bg_path.addClip()
                                except Exception:
                                    pass

                                pw = pill_rect.size.width * progress
                                if pw > 0.5:
                                    overlay_rect = NSMakeRect(pill_rect.origin.x, pill_rect.origin.y, pw, pill_rect.size.height)
                                    NSColor.colorWithCalibratedRed_green_blue_alpha_(0.00, 0.48, 1.00, 0.32).set()
                                    NSBezierPath.fillRect_(overlay_rect)

                                try:
                                    NSGraphicsContext.restoreGraphicsState()
                                except Exception:
                                    pass
                        except Exception:
                            pass

                        border_path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(pill_rect, radius, radius)
                        try:
                            border_path.setLineJoinStyle_(NSRoundLineJoinStyle)
                            border_path.setLineCapStyle_(NSRoundLineCapStyle)
                        except Exception:
                            pass
                        NSColor.whiteColor().colorWithAlphaComponent_(0.22).set()
                        border_path.setLineWidth_(1.0)
                        border_path.stroke()
                    except Exception:
                        pass

                    try:
                        text = NSString.stringWithString_("语音输入")
                        font = NSFont.boldSystemFontOfSize_(13.0)
                        attrs = {
                            NSFontAttributeName: font,
                            NSForegroundColorAttributeName: NSColor.whiteColor(),
                        }
                        text_size = text.sizeWithAttributes_(attrs)
                        text_x = pill_rect.origin.x + float(getattr(self, "_content_padding_x", 24) or 24)
                        text_y = pill_rect.origin.y + (pill_rect.size.height - text_size.height) / 2.0 - 1.0
                        text.drawAtPoint_withAttributes_(NSMakePoint(text_x, text_y), attrs)
                    except Exception:
                        pass

                    try:
                        lv = max(0, min(100, int(getattr(self, "_volume_level", 0) or 0)))
                        num_bars = int(getattr(self, "_num_bars", 5) or 5)
                        bar_w = float(getattr(self, "_bar_width", 4) or 4)
                        gap = float(getattr(self, "_gap", 6) or 6)
                        min_h = float(getattr(self, "_wave_min_h", 8) or 8)
                        max_h = float(getattr(self, "_wave_max_h", 38) or 38)
                        total_width = num_bars * bar_w + (num_bars - 1) * gap
                        start_x = pill_rect.origin.x + pill_rect.size.width - float(getattr(self, "_wave_right_padding", 36) or 36) - total_width
                        center_y = pill_rect.origin.y + pill_rect.size.height / 2.0
                        norm = lv / 100.0
                        base_h = min_h + (max_h - min_h) * norm
                        phase = int(getattr(self, "_wave_phase", 0) or 0)
                        patterns = [
                            [0.42, 0.78, 1.0, 0.72, 0.50],
                            [0.56, 0.92, 0.76, 1.0, 0.44],
                            [0.38, 0.68, 1.0, 0.88, 0.62],
                            [0.50, 1.0, 0.70, 0.86, 0.46],
                        ]
                        multipliers = patterns[phase % len(patterns)]

                        NSColor.whiteColor().colorWithAlphaComponent_(0.92).set()

                        for i in range(num_bars):
                            mul = multipliers[i] if i < len(multipliers) else 0.65
                            idle_lift = 1.0 if lv > 0 else (1.0 if i == num_bars // 2 else 0.55)
                            bar_h = max(2.0, base_h * mul * idle_lift)

                            x0 = start_x + i * (bar_w + gap)
                            y0 = center_y - bar_h / 2.0
                            bar_rect = NSMakeRect(x0, y0, bar_w, bar_h)
                            bar_path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(bar_rect, bar_w / 2.0, bar_w / 2.0)

                            bar_path.fill()
                    except Exception:
                        pass

            _MVI_VIEW_CLS = MVIRecordingOverlayContentView

    if _MVI_PANEL_CLS is None or _MVI_VIEW_CLS is None:
        raise RuntimeError("初始化 ObjC overlay class 失败")

    return _MVI_PANEL_CLS, _MVI_VIEW_CLS
