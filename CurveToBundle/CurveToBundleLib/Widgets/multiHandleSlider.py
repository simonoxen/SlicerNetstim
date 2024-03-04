import qt


class MultiHandleSliderWidget(qt.QSlider):

    handleIndexChanged = qt.Signal()
    valuesChanged = qt.Signal()

    def __init__(self):
        qt.QSlider.__init__(self)

        self.setOrientation(qt.Qt.Horizontal)
        self.setTickPosition(qt.QSlider.TicksBelow)
        self.setTickInterval(25)
        self.setSingleStep(1)
        self.setMaximum(100)
        self.setMinimum(0)

        # hide default handle
        self.setStyleSheet("""
                           QSlider::handle:horizontal {background-color:rgba(255, 255, 255, 0);}
                           QSlider {height: 40px;}
                           """)

        self._handles = [0]    
        self._dragging_handle = None
        self._mouse_offset = 0

    def setHandles(self, handles):
        if not handles:
            handles = [0]
        self._handles = handles
        self.update()
    
    def setHandleValue(self, index, value):
        self._handles[index] = value
        self.update()
    
    def getHandleValue(self, index):
        return self._handles[index]
    
    def getHandleIndex(self):
        return self._dragging_handle

    def paintEvent(self, event):
        qt.QSlider.paintEvent(self, event)
        painter = qt.QPainter(self)
        painter.setRenderHint(qt.QPainter.Antialiasing)

        opt = qt.QStyleOptionSlider()
        self.initStyleOption(opt)   
        
        groove_rect = self.style().subControlRect(qt.QStyle.CC_Slider, opt, self.style().SC_SliderGroove)
        groove_length = groove_rect.width() 
        groove_start = groove_rect.left() 

        for handle in self._handles:
            handle_pos = groove_start + int(groove_length * (handle - self.minimum) / (self.maximum - self.minimum))
            handle_center = qt.QPointF(handle_pos, groove_rect.center().y()) 
            handle_radius = self.style().pixelMetric(qt.QStyle.PM_SliderLength) / 2
            handle_rect = qt.QRect(handle_center.x() - handle_radius, handle_center.y() - handle_radius, 2 * handle_radius, 2 * handle_radius)
            painter.setBrush(qt.QColor(180, 180, 180))
            painter.drawEllipse(handle_rect)

    def mousePressEvent(self, event):
        opt = qt.QStyleOptionSlider()
        self.initStyleOption(opt)  
        if event.button() == qt.Qt.LeftButton:
            groove_rect = self.style().subControlRect(qt.QStyle.CC_Slider, opt, self.style().SC_SliderGroove)
            for i, handle in enumerate(self._handles):
                handle_pos = groove_rect.left() + int(groove_rect.width() * (handle - self.minimum) / (self.maximum - self.minimum))
                handle_center = qt.QPointF(handle_pos, groove_rect.center().y())
                handle_radius = self.style().pixelMetric(qt.QStyle.PM_SliderLength) / 2
                handle_rect = qt.QRect(handle_center.x() - handle_radius, handle_center.y() - handle_radius, 2 * handle_radius, 2 * handle_radius)
                if handle_rect.contains(event.pos()):
                    self._dragging_handle = i
                    self.mouse_offset = event.pos().x() - handle_center.x()
                    self.handleIndexChanged.emit()
                    return

    def mouseMoveEvent(self, event):
        opt = qt.QStyleOptionSlider()
        self.initStyleOption(opt) 
        if self._dragging_handle is not None:
            groove_rect = self.style().subControlRect(qt.QStyle.CC_Slider, opt, self.style().SC_SliderGroove)
            handle_pos = event.pos().x() - self.mouse_offset
            handle_pos = max(handle_pos, groove_rect.left())
            handle_pos = min(handle_pos, groove_rect.right())
            value = self.minimum + (handle_pos - groove_rect.left()) / groove_rect.width() * (self.maximum - self.minimum)
            self._handles[self._dragging_handle] = int(value)
            self.update()
            self.valuesChanged.emit()
