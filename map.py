import json
from load_fit import load_fit, get_gps_data
from cv_func import create_power_svg, create_speed_svg, align_video_positoin_and_fit, add_fit_data_to_video
# PyQt5 imports
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QSlider, QApplication, QHBoxLayout, QPushButton, \
    QFileDialog, QSplitter, QTabWidget, QToolBar, QGraphicsView, QGraphicsScene, QSpacerItem, QSizePolicy, \
    QProgressDialog
from PyQt5.QtCore import Qt, QUrl, pyqtSlot, pyqtSignal, QObject, QByteArray, QPointF
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget, QGraphicsVideoItem
from PyQt5.QtGui import QIcon, QTransform
from PyQt5.QtSvg import QSvgWidget, QGraphicsSvgItem, QSvgRenderer
import sys
import os
import inspect


class Signals(QObject):
    videoOpened = pyqtSignal(str)
    add_svg_to_Video = pyqtSignal(str)
    FitOpened = pyqtSignal(str)
    align = pyqtSignal(float, float)


signals = Signals()


class exportSignals(QObject):
    videoSize = pyqtSignal(float, float)
    svgSize = pyqtSignal(dict)
    svgPos = pyqtSignal(dict)


export_signals = exportSignals()


class MapWidget(QWidget):
    def __init__(self, fps, fit_gap):
        super().__init__()
        self.fps = fps  # 储存fps值，暂时不从视频中读取
        self.fit_gap = fit_gap  # fit中记录的间隔时间，单位为s
        self.video_slider_position = 0  # 储存对齐时的video时间，单位ms
        self.map_slider_position = 0  # 储存对齐时的fit时间，单位fit_gap s
        self.user_is_interacting = True  # 是否是主动更改map slider
        self.fit_is_loaded = False  # fit文件是否被加载进来了（如果未加载则进度条不联动）
        self.video_is_loaded = False
        self.signals = signals
        self.initUI()

    def initUI(self):
        """
        初始化界面
        :return:
        """
        self.setupWindowAndLayout()
        self.setupMapView()
        self.setupVideoPlayer()
        self.main_layout.addWidget(self.splitter)
        self.splitter.setSizes([self.width() // 2, self.width() // 2])

    def setupWindowAndLayout(self):
        self.setWindowTitle("Map and Video Viewer")  # 设定标题
        self.main_layout = QHBoxLayout(self)  # 设定main布局
        self.splitter = QSplitter(Qt.Horizontal)  # 设定splitter（map和视频要等分）

    # -------------------------------------------------------- #
    # 这里放map相关的组件
    # -------------------------------------------------------- #
    def create_fit_openButton(self):
        self.mapOpenButton = QPushButton('Open FIT')
        self.mapOpenButton.clicked.connect(self.open_fit_file)
        self.map_layout.addWidget(self.mapOpenButton)
        print('mapOpenButton初始初始化完毕')

    def create_map_view(self):
        self.map_view = QWebEngineView()
        dir_path = os.path.dirname(os.path.realpath(__file__))
        self.map_view.load(QUrl.fromLocalFile(os.path.join(dir_path, "map.html")))
        self.map_view.loadFinished.connect(self.initMap)
        print('mapView初始初始化完毕')

    def create_map_slider(self):
        self.map_slider = QSlider(Qt.Horizontal)
        self.map_slider.valueChanged.connect(self.sliderMoved)
        self.map_slider.setMinimum(0)
        self.map_slider.setMaximum(len(self.gps_coordinates) - 1)
        print('slider初始初始化完毕')

    def setupMapLayout(self):
        self.create_map_view()
        self.create_map_slider()
        # 上面是map，下面是滑动条
        self.map_layout.addWidget(self.map_view)
        self.map_layout.addWidget(self.map_slider)
        print('mapView layout初始初始化完毕')

    # -------------------------------------------------------- #
    # 这里放map相关的函数
    # -------------------------------------------------------- #
    def open_fit_file(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Open FIT")
        if fileName != '':
            self.gps_coordinates = get_gps_data(file_path=fileName)
            self.setupMapLayout()
            self.map_layout.removeWidget(self.mapOpenButton)
            self.fit_is_loaded = True
            self.signals.FitOpened.emit(fileName)
        print('fit文件已打开')

    def initMap(self):
        code = f"initMap({self.gps_coordinates[0][0]}, {self.gps_coordinates[0][1]}, {19});"
        self.map_view.page().runJavaScript(code)
        print("Map初始化成功")
        code = f"initMapTrack({json.dumps(self.gps_coordinates)});"
        self.map_view.page().runJavaScript(code)
        print("Map轨迹初始化成功")

    @pyqtSlot(int)
    def sliderMoved(self, position):
        if self.user_is_interacting and self.video_is_loaded:
            self.map_slider_position = position
            self.video_slider_position = self.video_slider.value()
            print(f'map_slider主动更新：当前视频位置{self.video_slider_position / 1000}s,'
                  f' 当前gps位置{self.map_slider_position * self.fit_gap}s')
            self.signals.align.emit(self.video_slider_position, self.map_slider_position)
        lat = self.gps_coordinates[position][0]
        lon = self.gps_coordinates[position][1]
        self.updateMap(lat, lon)

    def updateMap(self, lat, lon):
        code = f"updateMapWithNewData({lat}, {lon});"
        self.map_view.page().runJavaScript(code)

    # -------------------------------------------------------- #
    # 初始化map窗口
    # -------------------------------------------------------- #
    def setupMapView(self):
        # 定义mapWidget，所有map相关内容放到mapWidget中
        # 布局为垂直布局
        self.mapWidget = QWidget()
        self.map_layout = QVBoxLayout(self.mapWidget)
        # 初始化界面只有OPENFIT这个button
        self.create_fit_openButton()
        # 将map加入到splitter中
        self.splitter.addWidget(self.mapWidget)

    # -------------------------------------------------------- #
    # 这里放videoPlayer组件
    # -------------------------------------------------------- #
    def create_VideoPlayer(self):
        self.video_player = QMediaPlayer(None, QMediaPlayer.VideoSurface)
        self.video_widget = QVideoWidget()
        self.video_player.setVideoOutput(self.video_widget)
        # Connect signals to slots for video progress and duration updates
        self.video_player.positionChanged.connect(self.positionChanged)
        self.video_player.durationChanged.connect(self.durationChanged)

    def create_play_pause_button(self):
        self.play_pause_button = QPushButton("播放/暂停")
        self.play_pause_button.setEnabled(False)  # Initially disabled, enabled after video is loaded
        self.play_pause_button.clicked.connect(self.togglePlayPause)

    def create_openVideoButton(self):
        self.videoOpenButton = QPushButton('Open Video')
        self.videoOpenButton.clicked.connect(self.open_video_file)
        self.create_play_pause_button()
        self.video_layout.addWidget(self.videoOpenButton)

    def create_VideoSlider(self):
        self.video_slider = QSlider(Qt.Horizontal)
        self.video_slider.setRange(0, 0)  # Initial range, will be updated when video is loaded
        self.video_slider.sliderMoved.connect(self.setPosition)

    def setupVideoLayout(self):
        self.create_VideoPlayer()
        self.create_VideoSlider()
        # step 1. 创建一个装播放暂停+进度条的布局
        self.video_button_and_slider_layout = QHBoxLayout(self.videoWidget)
        # step 2. 将video_slider 和 play_pause_button放入布局
        self.video_button_and_slider_layout.addWidget(self.video_slider)
        self.video_button_and_slider_layout.addWidget(self.play_pause_button)
        # step 3. 将video_widget和video_button_and_slider_layout放入布局
        self.video_layout.addWidget(self.video_widget)
        self.video_layout.addLayout(self.video_button_and_slider_layout)

    # -------------------------------------------------------- #
    # 这里放videoPlayer函数
    # -------------------------------------------------------- #
    def loadVideo(self, video_path):
        # Load the video file into the player
        self.video_player.setMedia(QMediaContent(QUrl.fromLocalFile(video_path)))
        # Enable the play/pause button now that a video is loaded
        self.play_pause_button.setEnabled(True)
        # Optionally, play the video (or you can leave it paused to start)
        self.video_player.play()
        self.video_player.pause()

    def open_video_file(self):
        fileName, _ = QFileDialog.getOpenFileName(self, "Open Video")
        if fileName != '':
            self.video_layout.removeWidget(self.videoOpenButton)
            self.setupVideoLayout()
            self.loadVideo(video_path=fileName)
            self.video_is_loaded = True
            # 传递信号给视另一个窗口
            self.signals.videoOpened.emit(fileName)

    def togglePlayPause(self):
        if self.video_player.state() == QMediaPlayer.PlayingState:
            self.video_player.pause()
        else:
            self.video_player.play()

    def positionChanged(self, position):
        self.video_slider.setValue(position)
        # Link the map slider to the video slider if needed
        if self.fit_is_loaded:
            self.user_is_interacting = False
            map_add_position = int((position - self.video_slider_position) * self.fit_gap / 1000)
            new_map_slider_position = self.map_slider_position + map_add_position
            lat = self.gps_coordinates[new_map_slider_position][0]
            lon = self.gps_coordinates[new_map_slider_position][1]
            self.updateMap(lat, lon)
            self.map_slider.setSliderPosition(new_map_slider_position)
            print(f'map_slider联动更新：当前视频位置{position / 1000}s,'
                  f' 当前gps位置{new_map_slider_position * self.fit_gap}s')
            self.user_is_interacting = True

    def durationChanged(self, duration):
        self.video_slider.setRange(0, duration)

    def setPosition(self, position):
        self.video_player.setPosition(position)

    # -------------------------------------------------------- #
    # 初始化VideoPlayer窗口
    # -------------------------------------------------------- #
    def setupVideoPlayer(self):
        # 创建view窗口
        self.videoWidget = QWidget()
        self.video_layout = QVBoxLayout(self.videoWidget)
        # 创建open Video 按钮
        self.create_openVideoButton()
        # 将videoWidget加入splitter
        self.splitter.addWidget(self.videoWidget)


class ClicableSvgWidget(QSvgWidget):
    """
    点击SVG图片的时候，在视频上添加预览
    """

    def __init__(self, svg_func, data_type):
        super().__init__()
        self.svg_func = svg_func
        self.data_type = data_type
        self.load_svg()
        self.setFixedSize(self.size())

    def load_svg(self):
        svg_string = self.svg_func()
        svg_bytes = QByteArray(svg_string.encode('utf-8'))  # 将SVG字符串转换为字节数组
        self.load(svg_bytes)  # 使用QSvgWidget的load方法加载SVG字节数组
        self.resizeToMaxDimension()

    def mousePressEvent(self, event):
        """
        数遍左键单机时调用self.clicked函数
        :param event:
        :return:
        """
        if event.button() == Qt.LeftButton:
            self.clicked()

    def clicked(self):
        """
        当点击的时候发送data_type信息
        :return:
        """
        print(f"SVG图片 {self.data_type} 被点击了！")
        # 在这里添加你的事件触发逻辑
        signals.add_svg_to_Video.emit(self.data_type)

    def resizeToMaxDimension(self, max_dimension=200):
        svgSize = self.renderer().defaultSize()
        # 确保原始尺寸不为零
        if svgSize.width() == 0 or svgSize.height() == 0:
            return
        # 计算缩放比例
        scale_width = max_dimension / svgSize.width()
        scale_height = max_dimension / svgSize.height()
        scale_factor = min(scale_width, scale_height)

        # 应用缩放比例
        newWidth = svgSize.width() * scale_factor
        newHeight = svgSize.height() * scale_factor
        # 调整svgPic的尺寸为缩放后的大小
        self.resize(int(newWidth), int(newHeight))
        # self.show()


class MyGraphicsView(QGraphicsView):
    """
    GraphicView中的 videoItem 可以自主调节大小
    """

    def __init__(self, videoItem, parent=None):
        super(MyGraphicsView, self).__init__(parent)
        self.videoItem = videoItem

    def resizeEvent(self, event):
        super(MyGraphicsView, self).resizeEvent(event)
        if self.scene():
            # 调整videoItem的大小以适应新的视图大小
            rect = self.mapToScene(self.viewport().rect()).boundingRect()
            self.videoItem.setSize(rect.size())


class DraggableSvgItem(QGraphicsSvgItem):
    def __init__(self):
        super(DraggableSvgItem, self).__init__()
        self.setFlags(QGraphicsSvgItem.ItemIsSelectable | QGraphicsSvgItem.ItemIsMovable)
        self.isDragging = False
        self.startPos = QPointF()
        self.currentScale = 0.5  # 初始缩放比例
        transform = QTransform().scale(self.currentScale, self.currentScale)
        self.setTransform(transform)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.isDragging = True
            self.startPos = event.pos()
        super(DraggableSvgItem, self).mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.isDragging:
            # 在这里，我们直接移动整个item
            self.setPos(self.mapToScene(event.pos() - self.startPos))
        super(DraggableSvgItem, self).mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.isDragging = False
        super(DraggableSvgItem, self).mouseReleaseEvent(event)

    def wheelEvent(self, event):
        scaleFactor = 1.1  # 定义缩放的因子
        if event.delta() > 0:
            # 放大
            self.currentScale *= scaleFactor
        else:
            # 缩小
            self.currentScale /= scaleFactor

        # 应用当前的缩放比例
        transform = QTransform().scale(self.currentScale, self.currentScale)
        self.setTransform(transform)

        super(DraggableSvgItem, self).wheelEvent(event)


class StaticSvgItem(DraggableSvgItem):
    def __init__(self, file_path):
        super(StaticSvgItem, self).__init__()
        if os.path.isfile(file_path):
            self.renderer = QSvgRenderer(file_path)
        else:
            raise ValueError("file_path must be a valid file path.")
        self.setSharedRenderer(self.renderer)


class DynamicSvgItem(DraggableSvgItem):
    def __init__(self, svg_func, data, init_row=None, **kwargs):
        super(DynamicSvgItem, self).__init__()
        self.svg_func = svg_func
        self.kwargs = kwargs
        self.data = data
        self.updateSvg(init_row)  # 使用svg_func初始化

    def updateSvg(self, curr_row):
        # 使用svg_func生成新的SVG字符串并加载
        svg_data = self.svg_func(self.data.iloc[curr_row], **self.kwargs)
        self.renderer = QSvgRenderer()
        self.renderer.load(svg_data.encode('utf-8'))
        self.setSharedRenderer(self.renderer)
        self.update()  # 更新视图


def param_wrapper(svg_func, data_frame, data_type):
    # 获取函数需要的参数名
    params = inspect.signature(svg_func).parameters
    param_names = list(params.keys())

    # 建立参数映射
    args = {}
    for name in param_names:
        if name == 'max_data':
            args[name] = data_frame[data_type].max()  # 当前data_type列的最大值
        elif name == 'min_data':
            args[name] = data_frame[data_type].min()  # 当前data_type列的最小值
        elif name == 'all_data':
            args[name] = data_frame[data_type].values  # 当前data_type列的所有数据
        # 可以根据需要添加更多条件

    # 调用函数并传入参数
    return args


class VideoSvgWidget(QWidget):
    def __init__(self, fps, fit_gap):
        super().__init__()
        self.fps = fps
        self.fit_gap = fit_gap
        self.video_slider_position = 0  # 储存对齐时的video时间，单位ms
        self.map_slider_position = 0  # 储存对齐时的fit时间，单位fit_gap s
        self.signals = signals
        self.signals.videoOpened.connect(self.open_video_file)
        self.signals.add_svg_to_Video.connect(self.add_svg_to_video)
        self.signals.FitOpened.connect(self.open_fit_file)
        self.signals.align.connect(self.update_align)
        self.svg_in_view = {}
        self.svg_in_widget = {}
        self.data_type_svg_func_dict = {}
        self.video_loaded = False
        self.fit_loaded = False
        self.initUI()

    def initUI(self):
        self.setupWindowAndLayout()
        self.setupSvgView()
        self.setupVideoPlayer()
        self.main_layout.addWidget(self.splitter)
        self.splitter.setSizes([self.width() // 2, self.width() // 2])

    def setupWindowAndLayout(self):
        self.setWindowTitle("Map and Video Viewer")  # 设定标题
        self.main_layout = QHBoxLayout(self)  # 设定main布局
        self.splitter = QSplitter(Qt.Horizontal)  # 设定splitter（map和视频要等分）

    def update_align(self, video_slider_position, map_slider_position):
        self.video_slider_position = video_slider_position  # 储存对齐时的video时间，单位ms
        self.map_slider_position = map_slider_position  # 储存对齐时的fit时间，单位fit_gap s

    def open_fit_file(self, filePath):
        """
        打开fit文件
        :return:
        """
        fit_data = load_fit(filePath)
        # 将速度由m/s换成km/h
        fit_data['speed'] = fit_data['speed'] * 3.6
        self.fit_data = fit_data
        self.fit_loaded = True

    def create_svg(self):
        svgPic = ClicableSvgWidget(create_speed_svg, "speed")
        self.svg_layout.addWidget(svgPic)
        self.svg_in_widget["speed"] = svgPic

        svgPic = ClicableSvgWidget(create_power_svg, "power")
        self.svg_layout.addWidget(svgPic)
        self.svg_in_widget["power"] = svgPic

    def setupSvgView(self):
        self.svgWidget = QWidget()
        self.svgWidget.setStyleSheet('background-color: #3D3D3D;')
        self.svg_layout = QVBoxLayout(self.svgWidget)
        self.create_svg()
        self.splitter.addWidget(self.svgWidget)

    def add_svg_to_video(self, data_type):
        try:
            if not self.video_loaded:
                print("视频未导入")
                return
            if not self.fit_loaded:
                return
            if data_type not in self.svg_in_view.keys():
                fit_row = align_video_positoin_and_fit(aligned_video_position=self.video_slider_position,
                                                       aligned_fit_position=self.map_slider_position,
                                                       fit_gap=self.fit_gap,
                                                       fps=self.fps,
                                                       curr_video_position=self.video_slider.value())
                svg_func = self.svg_in_widget[data_type].svg_func
                args = param_wrapper(svg_func=svg_func,
                                     data_frame=self.fit_data,
                                     data_type=data_type)

                svgItem = DynamicSvgItem(svg_func=svg_func,
                                         data=self.fit_data[data_type],
                                         init_row=fit_row,
                                         **args)
                self.svg_in_view[data_type] = svgItem
                self.data_type_svg_func_dict[data_type] = svg_func
                svgItem.setPos(0, 500)
                self.scene.addItem(svgItem)
        except Exception as e:
            raise Exception(e)

    def update_svg(self, position):
        if not self.fit_loaded:
            print("fit文件未导入")
            return
        if not self.video_loaded:
            print("视频未导入")
            return
        for svgItem in self.svg_in_view.values():
            fit_row = align_video_positoin_and_fit(aligned_video_position=self.video_slider_position,
                                                   aligned_fit_position=self.map_slider_position,
                                                   fit_gap=self.fit_gap,
                                                   fps=self.fps,
                                                   curr_video_position=position)
            svgItem.updateSvg(fit_row)

    # -------------------------------------------------------- #
    # 这里放videoPlayer组件
    # -------------------------------------------------------- #

    # -------------------------------------------------------- #
    # 这里放videoPlayer函数
    # -------------------------------------------------------- #
    def loadVideo(self, video_path):
        # Load the video file into the player
        self.video_player.setMedia(QMediaContent(QUrl.fromLocalFile(video_path)))
        self.video_player.play()
        self.video_player.pause()
        self.play_pause_button.setEnabled(True)
        self.video_loaded = True

    def open_video_file(self, video_path):
        self.loadVideo(video_path)

    # -------------------------------------------------------- #
    # 初始化VideoPlayer窗口
    # -------------------------------------------------------- #
    def create_VideoSlider(self):
        self.video_slider = QSlider(Qt.Horizontal)
        self.video_slider.setRange(0, 0)  # Initial range, will be updated when video is loaded
        self.video_slider.sliderMoved.connect(self.setPosition)

    def create_play_pause_button(self):
        self.play_pause_button = QPushButton("播放/暂停")
        self.play_pause_button.setEnabled(False)  # Initially disabled, enabled after video is loaded
        self.play_pause_button.clicked.connect(self.togglePlayPause)

    def togglePlayPause(self):
        if self.video_player.state() == QMediaPlayer.PlayingState:
            self.video_player.pause()
        else:
            self.video_player.play()

    def positionChanged(self, position):
        self.video_slider.setValue(position)
        # 关联 svg update
        self.update_svg(position)

    def durationChanged(self, duration):
        self.video_slider.setRange(0, duration)

    def setPosition(self, position):
        self.video_player.setPosition(position)

    def setupVideoPlayer(self):
        # 创建view窗口
        self.videoWidget = QWidget()
        self.video_layout = QVBoxLayout(self.videoWidget)

        self.scene = QGraphicsScene()
        self.video_player = QMediaPlayer()
        self.videoItem = QGraphicsVideoItem()
        self.video_player.setVideoOutput(self.videoItem)
        self.video_player.positionChanged.connect(self.positionChanged)
        self.video_player.durationChanged.connect(self.durationChanged)
        self.create_VideoSlider()
        self.create_play_pause_button()
        self.scene.addItem(self.videoItem)

        # 创建视图来显示场景
        self.view = MyGraphicsView(self.videoItem, self.scene)

        # step 1. 创建一个装播放暂停+进度条的布局
        self.video_button_and_slider_layout = QHBoxLayout(self.videoWidget)
        # step 2. 将video_slider 和 play_pause_button放入布局
        self.video_button_and_slider_layout.addWidget(self.video_slider)
        self.video_button_and_slider_layout.addWidget(self.play_pause_button)
        # step 3. 将video_widget和video_button_and_slider_layout放入布局

        self.video_layout.addWidget(self.view)
        self.video_layout.addLayout(self.video_button_and_slider_layout)

        self.splitter.addWidget(self.videoWidget)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.fps = 30
        self.fit_gap = 1
        self.signals = signals
        self.signals.videoOpened.connect(self.get_video_path)

        self.setWindowTitle("Tabbed Interface - Map and Video Viewer")
        self.set_menu_bar()
        # 创建一个 QTabWidget
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # 创建 MapWidget 实例并将其添加为标签页
        self.map_tab = MapWidget(self.fps, self.fit_gap)
        self.tabs.addTab(self.map_tab, "地图")

        # 创建另一个标签页
        self.other_tab = VideoSvgWidget(self.fps, self.fit_gap)
        self.tabs.addTab(self.other_tab, "模板")

        self.showMaximized()

    def get_video_path(self, filePath):
        self.video_path = filePath

    def set_menu_bar(self):
        self.toolbar = QToolBar("My Toolbar", self)
        self.addToolBar(self.toolbar)

        # 创建一个水平布局
        toolbarLayout = QHBoxLayout()

        # 添加一个弹簧来推动按钮到右侧
        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        toolbarLayout.addSpacerItem(spacer)

        # 创建按钮并设置图标
        btn = QPushButton(self)
        btn.setIcon(QIcon('imgs/export.png'))  # 替换为你的图标路径
        btn.setMaximumSize(40, 40)  # 调整为所需的尺寸
        btn.clicked.connect(self.export)

        toolbarLayout.addWidget(btn)

        # 创建一个容器部件并设置布局
        container = QWidget()
        container.setLayout(toolbarLayout)

        # 将容器部件添加到工具栏
        self.toolbar.addWidget(container)

    def export(self):
        progressDialog = QProgressDialog("Processing video...", "Cancel", 0, 100, self)
        progressDialog.setModal(True)
        progressDialog.show()

        def update_progress(frame_number, total_frames):
            progress = int((frame_number / total_frames) * 100)
            progressDialog.setValue(progress)
            QApplication.processEvents()

            if progressDialog.wasCanceled():
                return False  # 或者处理取消操作

        sceneRect = self.other_tab.scene.sceneRect()
        sceneWidth = sceneRect.width()
        sceneHeight = sceneRect.height()

        # print(viewWidth, viewHeight, viewSize)
        print(sceneWidth, sceneHeight)

        # 1. 获取到视频大小
        position = self.other_tab.videoItem.pos()
        video_x = position.x()
        video_y = position.y()
        boundingRect = self.other_tab.videoItem.boundingRect()
        videoWidth = boundingRect.width()
        videoHeight = boundingRect.height()

        video_y = video_y + (sceneHeight - videoHeight) // 2

        data_type_position_dict = {}
        sizes = {}
        # 2. 获取到每个svg的大小和位置
        for data_type, svgItem in self.other_tab.svg_in_view.items():
            scale_factor = svgItem.currentScale
            print(scale_factor)

            boundingRect = svgItem.boundingRect()
            svgWidth = boundingRect.width() * scale_factor
            svgHeight = boundingRect.height() * scale_factor

            position = svgItem.pos()
            svg_x = position.x()
            svg_y = position.y()

            print(videoWidth, videoHeight)
            print(video_x, video_y)
            print(svg_x, svg_y)
            print(svgWidth, svgHeight)

            # 3. 计算svg在视频上的位置，并生成data_type_positoin_dict和sizes两个字典
            relativeX = (svg_x - video_x) / videoWidth
            relativeY = (svg_y - video_y) / videoHeight

            print(relativeX, relativeY)
            print((svgWidth / videoWidth, svgHeight / videoHeight))

            data_type_position_dict[data_type] = (relativeX, relativeY)
            sizes[data_type] = (svgWidth / videoWidth, svgHeight / videoHeight)

        # 4. 导出视频
        add_fit_data_to_video(input_video_path=self.video_path,
                              fit_data=self.other_tab.fit_data,
                              output_video_path='video/output.mp4',
                              aligned_video_position=self.map_tab.video_slider_position,
                              aligned_fit_position=self.map_tab.map_slider_position,
                              fit_gap=self.fit_gap,
                              data_type_svg_func_dict=self.other_tab.data_type_svg_func_dict,
                              data_type_position_dict=data_type_position_dict,
                              sizes=sizes,
                              progress_callback=update_progress)
        progressDialog.close()


# Set up the application and window
app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec_())
