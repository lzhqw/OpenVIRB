import json
from load_fit import load_fit, get_gps_data
# PyQt5 imports
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QSlider, QApplication, QHBoxLayout, QPushButton, \
    QFileDialog, QSplitter, QTabWidget, QLabel, QGraphicsView, QGraphicsScene,QStackedLayout,QFrame
from PyQt5.QtCore import Qt, QUrl, pyqtSlot, pyqtSignal, QObject, QPoint
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtGui import QPixmap,QColor, QBrush
from PyQt5.QtSvg import QSvgWidget, QGraphicsSvgItem
import sys
import os


class VideoSignal(QObject):
    """
    创建一个信号，传递视频路径。在地图-视频页面打开视频时，svg-视频页面也会打开视频
    """
    videoOpened = pyqtSignal(str)


videoSignal = VideoSignal()


class SvgSignal(QObject):
    """
    创建一个信号，传递svg序号。在地图-视频页面打开视频时，svg-视频页面也会打开视频
    """
    add_svg_to_Video = pyqtSignal(str)


svgSignal = SvgSignal()


class MapWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.fps = 30  # 储存fps值，暂时不从视频中读取
        self.fit_gap = 1  # fit中记录的间隔时间，单位为s
        self.video_slider_position = 0  # 储存对齐时的video时间，单位ms
        self.map_slider_position = 0  # 储存对齐时的fit时间，单位fit_gap s
        self.user_is_interacting = True  # 是否是主动更改map slider
        self.fit_is_loaded = False  # fit文件是否被加载进来了（如果未加载则进度条不联动）
        self.video_is_loaded = False
        self.videoSignal = videoSignal
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
        self.showMaximized()
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
            self.videoSignal.videoOpened.emit(fileName)

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

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked()

    def clicked(self):
        print("SVG图片被点击了！")
        # 在这里添加你的事件触发逻辑
        svgSignal.add_svg_to_Video.emit("1")


class VideoSvgWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.videoSignal = videoSignal
        self.videoSignal.videoOpened.connect(self.open_video_file)
        self.svgSignal = svgSignal
        self.svgSignal.add_svg_to_Video.connect(self.add_svg_to_video)

    def initUI(self):
        self.setupWindowAndLayout()
        self.setupSvgView()
        self.setupVideoPlayer()
        self.main_layout.addWidget(self.splitter)
        self.showMaximized()
        self.splitter.setSizes([self.width() // 2, self.width() // 2])

    def setupWindowAndLayout(self):
        self.setWindowTitle("Map and Video Viewer")  # 设定标题
        self.main_layout = QHBoxLayout(self)  # 设定main布局
        self.splitter = QSplitter(Qt.Horizontal)  # 设定splitter（map和视频要等分）

    def create_svg(self):
        self.svgPic = ClicableSvgWidget(self.svgWidget)
        self.svgPic.load('imgs/哑铃2.svg')
        svgSize = self.svgPic.renderer().defaultSize()
        # 您想要缩放到的尺寸
        max_dimension = 200

        # 计算缩放比例
        scale_width = max_dimension / svgSize.width()
        scale_height = max_dimension / svgSize.height()
        scale_factor = min(scale_width, scale_height)

        # 应用缩放比例
        newWidth = svgSize.width() * scale_factor
        newHeight = svgSize.height() * scale_factor
        # 调整svgPic的尺寸为缩放后的大小
        self.svgPic.resize(int(newWidth), int(newHeight))
        self.svgPic.show()

    def setupSvgView(self):
        self.svgWidget = QWidget()
        self.svgWidget.setStyleSheet('background-color: #3D3D3D;')
        self.svg_layout = QVBoxLayout(self.svgWidget)
        self.create_svg()
        self.splitter.addWidget(self.svgWidget)

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

    def open_video_file(self, fileName):
        self.video_layout.removeWidget(self.videoOpenButton)
        self.setupVideoLayout()
        self.loadVideo(video_path=fileName)
        self.video_is_loaded = True

    def togglePlayPause(self):
        if self.video_player.state() == QMediaPlayer.PlayingState:
            self.video_player.pause()
        else:
            self.video_player.play()

    def positionChanged(self, position):
        self.video_slider.setValue(position)

    def durationChanged(self, duration):
        self.video_slider.setRange(0, duration)

    def setPosition(self, position):
        self.video_player.setPosition(position)

    def add_svg_to_video(self, svg_number):
        print(1, svg_number)
        # self.svg_item = QGraphicsSvgItem('imgs/哑铃2.svg')
        # self.scene.addItem(self.svg_item)
        # # 可以设置SVG项的位置，确保它在视频上方
        # self.svg_item.setPos(50, 50)  # 举例，将SVG图片放置在场景中的(50, 50)位置

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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Tabbed Interface - Map and Video Viewer")

        # 创建一个 QTabWidget
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # 创建 MapWidget 实例并将其添加为标签页
        self.map_tab = MapWidget()
        self.tabs.addTab(self.map_tab, "地图视图")

        # 创建另一个标签页
        self.other_tab = VideoSvgWidget()
        self.tabs.addTab(self.other_tab, "其他")

        self.showMaximized()


# Set up the application and window
app = QApplication(sys.argv)
window = MainWindow()
window.show()
sys.exit(app.exec_())
